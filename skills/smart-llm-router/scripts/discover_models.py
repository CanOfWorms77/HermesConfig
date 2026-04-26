#!/usr/bin/env python3
"""
Smart LLM Router — Daily Model Discovery

Probes available models across providers, benchmarks them with lightweight
prompts, and updates the router config with the best options per tier.

Usage:
    python scripts/discover_models.py           # full discovery + update config
    python scripts/discover_models.py --dry-run # test only, don't write config
    python scripts/discover_models.py --tier free  # only discover free-tier models
    python scripts/discover_models.py --providers openrouter,groq

Exit codes:
    0 — success, config updated (or would be updated in dry-run)
    1 — error
"""

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import aiohttp
import yaml

LOG = print  # simple logging; could swap for proper logger

DEFAULT_CONFIG_PATH = Path.home() / ".hermes" / "skills" / "smart-llm-router" / "config.yaml"
DISCOVERY_DB_PATH = Path.home() / ".hermes" / "skills" / "smart-llm-router" / "discovery.json"
ENV_PATH = Path.home() / ".hermes" / ".env"

# ── Benchmark prompts ─────────────────────────────────────────────────────────

BENCHMARKS = {
    "free": {
        "prompt": "Reply with exactly: 'Hello! How can I help you today?'",
        "max_tokens": 20,
        "evaluator": lambda text: "hello" in text.lower() and "help" in text.lower(),
        "target_latency": 2.0,
    },
    "low": {
        "prompt": "What is the capital of France? Reply in one word.",
        "max_tokens": 10,
        "evaluator": lambda text: "paris" in text.lower(),
        "target_latency": 3.0,
    },
    "medium": {
        "prompt": "Write a Python one-liner to sum a list of integers. Reply with code only, no explanation.",
        "max_tokens": 50,
        "evaluator": lambda text: "sum(" in text and "[" in text,
        "target_latency": 5.0,
    },
    "high": {
        "prompt": (
            "Explain the trade-offs between breadth-first and depth-first search "
            "in 2 sentences. Be concise."
        ),
        "max_tokens": 80,
        "evaluator": lambda text: len(text.split()) >= 10 and "breadth" in text.lower(),
        "target_latency": 8.0,
    },
}

# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class ModelResult:
    provider: str
    model: str
    tier: str
    latency_ms: float
    success: bool
    quality_pass: bool
    tokens_used: int = 0
    error: Optional[str] = None

    def score(self) -> float:
        """Higher is better. Weights: success > quality > speed."""
        if not self.success:
            return -1000.0
        s = 100.0
        if self.quality_pass:
            s += 50.0
        # Latency bonus: faster = higher score
        target = BENCHMARKS[self.tier]["target_latency"]
        if self.latency_ms <= target * 1000:
            s += 30.0
        else:
            s += max(0, 30.0 - (self.latency_ms / 1000 - target))
        return s


# ── Env loader ────────────────────────────────────────────────────────────────

def load_env(path: Path) -> dict:
    env = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


# ── Provider model fetchers ───────────────────────────────────────────────────

async def fetch_openrouter_models(session: aiohttp.ClientSession, api_key: str) -> list[dict]:
    """Return list of {id, provider, pricing} for free models."""
    if not api_key:
        return []
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        async with session.get("https://openrouter.ai/api/v1/models", headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                LOG(f"OpenRouter list failed: HTTP {resp.status}")
                return []
            data = await resp.json()
            models = []
            for m in data.get("data", []):
                mid = m.get("id", "")
                pricing = m.get("pricing", {})
                # Free models have :free suffix or zero pricing
                is_free = ":free" in mid
                if is_free:
                    models.append({
                        "id": mid,
                        "provider": "openrouter",
                        "name": m.get("name", mid),
                    })
            return models
    except Exception as e:
        LOG(f"OpenRouter fetch error: {e}")
        return []


async def fetch_groq_models(session: aiohttp.ClientSession, api_key: str) -> list[dict]:
    """Groq has a limited set; we hardcode the known working ones."""
    if not api_key:
        return []
    # Groq doesn't reliably expose a free list, and their catalog changes.
    # We probe the known open-weight models.
    known = [
        "llama-3.3-70b-versatile",
        "llama-4-scout-17b-16e-instruct",
        "llama-4-maverick-17b-128e-instruct",
        "gemma2-9b-it",
        "mixtral-8x7b-32768",
    ]
    return [{"id": m, "provider": "groq", "name": m} for m in known]


async def fetch_nvidia_models(session: aiohttp.ClientSession, api_key: str) -> list[dict]:
    """NVIDIA NIM models. We probe a few known ones."""
    if not api_key:
        return []
    known = [
        "meta/llama-3.3-70b-instruct",
        "deepseek-ai/deepseek-v3.2",
        "mistralai/mixtral-8x22b-instruct-v0.1",
    ]
    return [{"id": m, "provider": "nvidia", "name": m} for m in known]


# ── Model tester ──────────────────────────────────────────────────────────────

async def test_model(
    session: aiohttp.ClientSession,
    provider_cfg: dict,
    model_id: str,
    provider_name: str,
    tier: str,
) -> ModelResult:
    bench = BENCHMARKS[tier]
    base_url = provider_cfg["base_url"].rstrip("/")
    api_key_env = provider_cfg.get("api_key_env")
    api_key = os.environ.get(api_key_env, "") if api_key_env else provider_cfg.get("api_key", "")

    url = f"{base_url}/chat/completions"
    body = {
        "model": model_id,
        "messages": [{"role": "user", "content": bench["prompt"]}],
        "max_tokens": bench["max_tokens"],
        "temperature": 0.3,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    if provider_name == "openrouter":
        headers["HTTP-Referer"] = "https://hermes-agent.dev"
        headers["X-Title"] = "Hermes Smart Router Discovery"

    start = time.perf_counter()
    try:
        async with session.post(
            url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            latency_ms = (time.perf_counter() - start) * 1000
            if resp.status != 200:
                text = await resp.text()
                return ModelResult(
                    provider=provider_name,
                    model=model_id,
                    tier=tier,
                    latency_ms=latency_ms,
                    success=False,
                    quality_pass=False,
                    error=f"HTTP {resp.status}: {text[:200]}",
                )
            data = await resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            tokens = data.get("usage", {}).get("total_tokens", 0)
            quality = bench["evaluator"](content)
            return ModelResult(
                provider=provider_name,
                model=model_id,
                tier=tier,
                latency_ms=latency_ms,
                success=True,
                quality_pass=quality,
                tokens_used=tokens,
            )
    except asyncio.TimeoutError:
        latency_ms = (time.perf_counter() - start) * 1000
        return ModelResult(
            provider=provider_name, model=model_id, tier=tier,
            latency_ms=latency_ms, success=False, quality_pass=False,
            error="Timeout",
        )
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        return ModelResult(
            provider=provider_name, model=model_id, tier=tier,
            latency_ms=latency_ms, success=False, quality_pass=False,
            error=str(e)[:200],
        )


# ── Config builder ────────────────────────────────────────────────────────────

def load_config(path: Path) -> dict:
    if not path.exists():
        LOG(f"Config not found: {path}")
        sys.exit(1)
    return yaml.safe_load(path.read_text()) or {}


def save_config(path: Path, cfg: dict):
    path.write_text(yaml.dump(cfg, default_flow_style=False, sort_keys=False))


def build_tier_routes(results: list[ModelResult], tier: str, max_models: int = 3) -> list[dict]:
    """Pick top N models for a tier, ranked by score."""
    tier_results = [r for r in results if r.tier == tier and r.success]
    # Sort by score descending
    tier_results.sort(key=lambda r: r.score(), reverse=True)
    routes = []
    seen = set()
    for r in tier_results:
        key = (r.provider, r.model)
        if key in seen:
            continue
        seen.add(key)
        routes.append({"provider": r.provider, "model": r.model})
        if len(routes) >= max_models:
            break
    return routes


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="Discover and benchmark LLM models")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--dry-run", action="store_true", help="Don't write config")
    parser.add_argument("--tier", choices=["free", "low", "medium", "high", "all"], default="all")
    parser.add_argument("--providers", default="openrouter,groq,nvidia", help="Comma-separated provider names to probe")
    parser.add_argument("--max-per-tier", type=int, default=3, help="Max models to keep per tier")
    parser.add_argument("--concurrency", type=int, default=5, help="Parallel benchmark requests")
    args = parser.parse_args()

    env = load_env(ENV_PATH)
    os.environ.update(env)

    cfg = load_config(args.config)
    providers_cfg = cfg.get("providers", {})
    requested_providers = [p.strip() for p in args.providers.split(",")]

    # Validate requested providers exist in config
    for p in requested_providers:
        if p not in providers_cfg:
            LOG(f"Provider '{p}' not in config. Available: {list(providers_cfg.keys())}")
            sys.exit(1)

    tiers_to_test = ["free", "low", "medium", "high"] if args.tier == "all" else [args.tier]

    LOG(f"Discovery starting: providers={requested_providers}, tiers={tiers_to_test}")

    async with aiohttp.ClientSession() as session:
        # 1. Fetch model lists
        all_models = []
        fetchers = {
            "openrouter": fetch_openrouter_models,
            "groq": fetch_groq_models,
            "nvidia": fetch_nvidia_models,
        }
        for pname in requested_providers:
            fetcher = fetchers.get(pname)
            if not fetcher:
                LOG(f"No fetcher for provider '{pname}', skipping list fetch.")
                continue
            api_key = env.get(providers_cfg[pname].get("api_key_env", ""), "")
            models = await fetcher(session, api_key)
            LOG(f"  {pname}: {len(models)} models discovered")
            all_models.extend(models)

        if not all_models:
            LOG("No models discovered. Check API keys and provider connectivity.")
            sys.exit(1)

        # 2. Benchmark each model against each tier
        semaphore = asyncio.Semaphore(args.concurrency)

        async def bounded_test(model, tier):
            async with semaphore:
                pname = model["provider"]
                result = await test_model(
                    session, providers_cfg[pname], model["id"], pname, tier
                )
                status = "PASS" if result.success and result.quality_pass else ("OK" if result.success else "FAIL")
                LOG(f"  [{tier:8s}] {pname}/{model['id'][:50]:50s} -> {status} ({result.latency_ms:.0f}ms)")
                return result

        tasks = []
        for model in all_models:
            for tier in tiers_to_test:
                tasks.append(bounded_test(model, tier))

        LOG(f"Benchmarking {len(tasks)} model×tier combinations...")
        results = await asyncio.gather(*tasks)

    # 3. Summarize
    LOG("\n--- Results ---")
    for tier in tiers_to_test:
        tier_results = [r for r in results if r.tier == tier]
        successes = [r for r in tier_results if r.success]
        quality_passes = [r for r in successes if r.quality_pass]
        avg_latency = sum(r.latency_ms for r in successes) / len(successes) if successes else 0
        LOG(f"{tier:8s}: tested={len(tier_results)}, success={len(successes)}, quality={len(quality_passes)}, avg_latency={avg_latency:.0f}ms")

    # 4. Build new tier routes
    new_tiers = {}
    for tier in tiers_to_test:
        routes = build_tier_routes(results, tier, args.max_per_tier)
        if routes:
            new_tiers[tier] = routes
            best_str = ", ".join(f"{r['provider']}/{r['model']}" for r in routes)
            LOG(f"{tier:8s} best: {best_str}")
        else:
            LOG(f"{tier:8s}: no working models found, keeping existing config")

    # 5. Persist discovery results
    discovery_data = {
        "timestamp": time.time(),
        "results": [asdict(r) for r in results],
    }
    DISCOVERY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DISCOVERY_DB_PATH.write_text(json.dumps(discovery_data, indent=2, default=str))
    LOG(f"Discovery results saved to {DISCOVERY_DB_PATH}")

    if args.dry_run:
        LOG("\nDry run complete. Config NOT updated.")
        sys.exit(0)

    # 6. Update config
    cfg.setdefault("tiers", {})
    for tier, routes in new_tiers.items():
        cfg["tiers"][tier] = routes

    save_config(args.config, cfg)
    LOG(f"Config updated: {args.config}")


if __name__ == "__main__":
    asyncio.run(main())
