#!/usr/bin/env python3
"""
Smart LLM Router Proxy

An OpenAI-compatible HTTP proxy that sits between Hermes and your providers.
It classifies each query into a tier, picks the best healthy provider, and
falls back automatically if the provider errors or rate-limits.

Chat commands (intercepted by proxy, never sent to provider):
    /models [provider]        — list available models
    /use-model provider/model — force a specific model for all requests
    /auto-route               — clear override, go back to tier-based routing
    /status                   — show proxy health and current override

Usage:
    python scripts/router_proxy.py          # start with default config
    python scripts/router_proxy.py --port 8765 --config ./my_config.yaml

Hermes integration:
    Point Hermes at http://localhost:8765/v1 as a custom OpenAI endpoint.
    The proxy ignores the model name from Hermes — it chooses its own.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any

import aiohttp
from aiohttp import web

LOG = logging.getLogger("llm-router")

DEFAULT_CONFIG_PATH = Path.home() / ".hermes" / "skills" / "smart-llm-router" / "config.yaml"
HEALTH_PATH = Path.home() / ".hermes" / "skills" / "smart-llm-router" / "health.json"
OVERRIDE_PATH = Path.home() / ".hermes" / "skills" / "smart-llm-router" / "override.json"

# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class ProviderHealth:
    last_success: float = 0.0
    consecutive_failures: int = 0
    last_failure: float = 0.0
    backoff_until: float = 0.0

    def record_success(self):
        self.last_success = time.time()
        self.consecutive_failures = 0
        self.backoff_until = 0.0

    def record_failure(self, base_delay: float = 5.0, max_delay: float = 300.0):
        self.last_failure = time.time()
        self.consecutive_failures += 1
        delay = min(base_delay * (2 ** self.consecutive_failures), max_delay)
        self.backoff_until = time.time() + delay

    def is_healthy(self) -> bool:
        return time.time() >= self.backoff_until


@dataclass
class ModelRoute:
    provider: str
    model: str


# ── Override state ────────────────────────────────────────────────────────────

def load_override() -> Optional[ModelRoute]:
    if not OVERRIDE_PATH.exists():
        return None
    try:
        data = json.loads(OVERRIDE_PATH.read_text())
        if data.get("override"):
            return ModelRoute(data["override"]["provider"], data["override"]["model"])
    except Exception as e:
        LOG.warning(f"Failed to load override: {e}")
    return None


def save_override(route: Optional[ModelRoute]):
    try:
        if route:
            data = {"override": {"provider": route.provider, "model": route.model}, "since": time.time()}
        else:
            data = {"override": None}
        OVERRIDE_PATH.write_text(json.dumps(data, indent=2))
    except Exception as e:
        LOG.warning(f"Failed to save override: {e}")


# ── Intent classifier (zero LLM calls) ────────────────────────────────────────

def classify_tier(messages: List[dict]) -> str:
    """Classify conversation tier from the latest user message."""
    text = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            text = msg.get("content", "")
            break
    if not isinstance(text, str):
        text = str(text)
    text = text.strip().lower()
    words = text.split()

    # FREE: very short greetings
    if len(words) < 8:
        greetings = {"hi", "hello", "hey", "thanks", "ok", "yes", "no", "bye", "yo"}
        if words and words[0] in greetings:
            return "free"

    # HIGH: system design, long prompts, multi-line code
    high_signals = [
        any(k in text for k in [
            "design a system", "architect", "full codebase",
            "research and compare", "write a spec", "implement from scratch",
            "distributed system", "microservices architecture"
        ]),
        len(words) > 200,
        text.count("\n") > 10,
        text.count("```") >= 2,
    ]
    if any(high_signals):
        return "high"

    # MEDIUM: code, debug, build
    medium_signals = [
        any(k in text for k in ["debug", "implement", "refactor", "analyze", "python",
                                  "write code", "create a", "build a", "function", "script"]),
        "```" in text,
        any(k in text for k in ["def ", "class ", "import ", "return "]),
        len(words) > 50,
    ]
    if any(medium_signals):
        return "medium"

    return "low"


# ── Config loader ─────────────────────────────────────────────────────────────

def load_config(path: Path) -> dict:
    try:
        import yaml
        return yaml.safe_load(path.read_text()) or {}
    except Exception:
        return json.loads(path.read_text())


def build_config(raw: dict) -> dict:
    return {
        "port": raw.get("port", 8765),
        "providers": raw.get("providers", {}),
        "tiers": raw.get("tiers", {}),
        "default_tier": raw.get("default_tier", "medium"),
        "force_tier": raw.get("force_tier"),
        "fallback": {
            "max_retries_per_provider": 2,
            "timeout": 60,
            **raw.get("fallback", {}),
        },
    }


# ── Health persistence ────────────────────────────────────────────────────────

def load_health() -> Dict[str, ProviderHealth]:
    if not HEALTH_PATH.exists():
        return {}
    try:
        data = json.loads(HEALTH_PATH.read_text())
        return {k: ProviderHealth(**v) for k, v in data.items()}
    except Exception as e:
        LOG.warning(f"Failed to load health state: {e}")
        return {}


def save_health(health: Dict[str, ProviderHealth]):
    try:
        data = {k: asdict(v) for k, v in health.items()}
        HEALTH_PATH.write_text(json.dumps(data, indent=2, default=str))
    except Exception as e:
        LOG.warning(f"Failed to save health state: {e}")


# ── Route selection ───────────────────────────────────────────────────────────

def get_routes_for_tier(tier: str, tiers_config: dict) -> List[ModelRoute]:
    routes = tiers_config.get(tier, [])
    return [ModelRoute(r["provider"], r["model"]) for r in routes]


def pick_route(tier: str, tiers_config: dict, health: Dict[str, ProviderHealth]) -> Optional[ModelRoute]:
    routes = get_routes_for_tier(tier, tiers_config)
    for route in routes:
        h = health.get(route.provider)
        if h is None or h.is_healthy():
            return route
    return None


def get_fallback_chain(tier: str, tiers_config: dict, health: Dict[str, ProviderHealth]) -> List[ModelRoute]:
    routes = get_routes_for_tier(tier, tiers_config)
    result = []
    for route in routes:
        h = health.get(route.provider)
        if h is None or h.is_healthy():
            result.append(route)
    return result


# ── Request forwarding ────────────────────────────────────────────────────────

async def forward_request(
    session: aiohttp.ClientSession,
    route: ModelRoute,
    providers_config: dict,
    request_body: dict,
    timeout: int,
) -> tuple[int, bytes, dict[str, str]]:
    prov = providers_config.get(route.provider)
    if not prov:
        raise ValueError(f"Unknown provider: {route.provider}")

    base_url = prov["base_url"].rstrip("/")
    api_key_env = prov.get("api_key_env")
    api_key = os.environ.get(api_key_env, "") if api_key_env else prov.get("api_key", "")

    url = f"{base_url}/chat/completions"
    body = {**request_body, "model": route.model}

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    if route.provider == "openrouter":
        headers["HTTP-Referer"] = "https://hermes-agent.dev"
        headers["X-Title"] = "Hermes Smart Router"

    LOG.info(f"→ {route.provider}/{route.model}  url={url}")

    async with session.post(url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
        raw = await resp.read()
        return resp.status, raw, dict(resp.headers)


# ── Fake completion builder ───────────────────────────────────────────────────

def fake_completion(content: str) -> dict:
    return {
        "id": f"chatcmpl-router-{int(time.time()*1000)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "smart-router",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


# ── Model list helpers ────────────────────────────────────────────────────────

def build_static_model_list(cfg: dict) -> list[dict]:
    """Build a model list from config tiers + providers."""
    models = []
    seen = set()
    for tier_name, routes in cfg.get("tiers", {}).items():
        for r in routes:
            mid = f"{r['provider']}/{r['model']}"
            if mid not in seen:
                seen.add(mid)
                models.append({
                    "id": mid,
                    "object": "model",
                    "owned_by": r["provider"],
                    "tier": tier_name,
                })
    return models


async def fetch_provider_models(session: aiohttp.ClientSession, provider_name: str, prov_cfg: dict) -> list[dict]:
    """Best-effort fetch of models from a provider."""
    base_url = prov_cfg["base_url"].rstrip("/")
    api_key_env = prov_cfg.get("api_key_env")
    api_key = os.environ.get(api_key_env, "") if api_key_env else prov_cfg.get("api_key", "")

    # OpenRouter has a models endpoint
    if provider_name == "openrouter":
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            async with session.get(f"{base_url}/models", headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [{"id": m.get("id"), "owned_by": "openrouter"} for m in data.get("data", [])]
        except Exception as e:
            LOG.warning(f"OpenRouter model list failed: {e}")

    # Groq, NVIDIA, Abacus — no reliable public list or different auth
    return []


# ── Command parser ────────────────────────────────────────────────────────────

def parse_command(text: str) -> tuple[str, list[str]]:
    """Parse a user message for router commands.
    Returns (cmd_name, args) or ('', []) if not a command.
    """
    text = text.strip()
    if not text.startswith("/"):
        return "", []
    parts = text[1:].split()
    if not parts:
        return "", []
    return parts[0].lower(), parts[1:]


# ── HTTP handlers ─────────────────────────────────────────────────────────────

class RouterHandler:
    def __init__(self, config: dict):
        self.cfg = config
        self.health = load_health()
        self.session: Optional[aiohttp.ClientSession] = None

    async def startup(self):
        self.session = aiohttp.ClientSession()

    async def cleanup(self):
        if self.session:
            await self.session.close()

    async def health_check(self, request: web.Request) -> web.Response:
        override = load_override()
        return web.json_response({
            "status": "ok",
            "override": {"provider": override.provider, "model": override.model} if override else None,
            "providers": {
                name: {
                    "healthy": (h := self.health.get(name)) is None or h.is_healthy(),
                    "consecutive_failures": getattr(h, "consecutive_failures", 0),
                }
                for name in self.cfg["providers"]
            }
        })

    async def list_models(self, request: web.Request) -> web.Response:
        """GET /v1/models — return known models from config tiers."""
        # Best-effort enrich with provider fetchers
        models = build_static_model_list(self.cfg)
        provider_filter = request.query.get("provider", "")
        if provider_filter:
            models = [m for m in models if m.get("owned_by") == provider_filter]
        return web.json_response({
            "object": "list",
            "data": models,
        })

    async def chat_completions(self, request: web.Request) -> web.Response:
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON"}, status=400)

        messages = body.get("messages", [])
        stream = body.get("stream", False)

        # ── Check for router commands in the last user message ──
        last_user_text = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_text = msg.get("content", "")
                break

        cmd, args = parse_command(last_user_text)
        if cmd == "models":
            provider_filter = args[0] if args else None
            models = build_static_model_list(self.cfg)
            if provider_filter:
                models = [m for m in models if m.get("owned_by") == provider_filter]
            lines = ["Available models:"]
            for m in models:
                tier = m.get("tier", "?")
                lines.append(f"  [{tier:6s}] {m['id']}")
            lines.append("")
            lines.append("Use /use-model provider/model to force a specific model.")
            lines.append("Use /auto-route to return to automatic tier-based routing.")
            return web.json_response(fake_completion("\n".join(lines)))

        if cmd == "use-model":
            if not args or "/" not in args[0]:
                return web.json_response(fake_completion(
                    "Usage: /use-model provider/model\n"
                    "Example: /use-model openrouter/anthropic/claude-sonnet-4.6\n"
                    "Use /models to see available options."
                ))
            parts = args[0].split("/", 1)
            provider, model = parts[0], parts[1]
            if provider not in self.cfg.get("providers", {}):
                return web.json_response(fake_completion(
                    f"Unknown provider: '{provider}'.\nConfigured providers: {', '.join(self.cfg['providers'].keys())}"
                ))
            save_override(ModelRoute(provider, model))
            return web.json_response(fake_completion(
                f"Model override set: {provider}/{model}\n"
                f"All subsequent requests will use this model until you run /auto-route."
            ))

        if cmd == "auto-route":
            old = load_override()
            save_override(None)
            if old:
                return web.json_response(fake_completion(
                    f"Cleared override ({old.provider}/{old.model}). Back to automatic tier-based routing."
                ))
            return web.json_response(fake_completion("Already on automatic tier-based routing."))

        if cmd == "status":
            override = load_override()
            lines = ["Smart Router Status"]
            lines.append("=" * 30)
            if override:
                lines.append(f"Override: {override.provider}/{override.model}")
            else:
                lines.append("Routing: automatic (tier-based)")
            lines.append("")
            lines.append("Provider health:")
            for name in self.cfg.get("providers", {}):
                h = self.health.get(name)
                healthy = h is None or h.is_healthy()
                status = "OK" if healthy else f"DOWN (failures={h.consecutive_failures})"
                lines.append(f"  {name:12s}: {status}")
            return web.json_response(fake_completion("\n".join(lines)))

        # ── Override check ──
        override = load_override()
        if override:
            LOG.info(f"Override active: {override.provider}/{override.model}")
            chain = [override]
        else:
            # Determine tier
            forced = self.cfg.get("force_tier")
            tier = forced or classify_tier(messages)
            LOG.info(f"Tier={tier}  stream={stream}  msgs={len(messages)}")

            # Get fallback chain
            chain = get_fallback_chain(tier, self.cfg["tiers"], self.health)
            if not chain:
                tier_order = ["free", "low", "medium", "high"]
                idx = tier_order.index(tier) if tier in tier_order else 1
                for fallback_tier in reversed(tier_order[:idx]):
                    chain = get_fallback_chain(fallback_tier, self.cfg["tiers"], self.health)
                    if chain:
                        LOG.info(f"Tier fallback: {tier} → {fallback_tier}")
                        tier = fallback_tier
                        break

        if not chain:
            return web.json_response({
                "error": {
                    "message": f"All providers unavailable for tier or override",
                    "type": "router_error",
                    "code": "all_providers_down",
                }
            }, status=503)

        last_error = None
        timeout = self.cfg["fallback"]["timeout"]

        for route in chain:
            try:
                status, raw_resp, resp_headers = await forward_request(
                    self.session, route, self.cfg["providers"], body, timeout
                )

                if status == 200:
                    self.health.setdefault(route.provider, ProviderHealth()).record_success()
                    save_health(self.health)
                    LOG.info(f"← {route.provider}/{route.model}  status=200")
                    return web.Response(
                        body=raw_resp,
                        status=status,
                        headers={k: v for k, v in resp_headers.items()
                                 if k.lower() in ("content-type", "cache-control")},
                    )
                else:
                    self.health.setdefault(route.provider, ProviderHealth()).record_failure()
                    save_health(self.health)
                    text = raw_resp.decode("utf-8", errors="replace")[:500]
                    LOG.warning(f"← {route.provider}/{route.model}  status={status}  body={text}")
                    last_error = f"{route.provider} returned HTTP {status}"

            except asyncio.TimeoutError:
                self.health.setdefault(route.provider, ProviderHealth()).record_failure()
                save_health(self.health)
                LOG.warning(f"← {route.provider}/{route.model}  TIMEOUT")
                last_error = f"{route.provider} timed out"

            except Exception as e:
                self.health.setdefault(route.provider, ProviderHealth()).record_failure()
                save_health(self.health)
                LOG.warning(f"← {route.provider}/{route.model}  EXCEPTION: {e}")
                last_error = f"{route.provider} error: {e}"

        # All routes exhausted
        return web.json_response({
            "error": {
                "message": f"All providers failed. Last: {last_error}",
                "type": "router_error",
                "code": "all_providers_failed",
            }
        }, status=503)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Smart LLM Router Proxy")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if not args.config.exists():
        LOG.error(f"Config not found: {args.config}")
        LOG.error("Copy the template from templates/router_config.yaml and fill in your API keys.")
        sys.exit(1)

    raw_cfg = load_config(args.config)
    cfg = build_config(raw_cfg)

    handler = RouterHandler(cfg)
    app = web.Application()
    app.router.add_get("/health", handler.health_check)
    app.router.add_get("/v1/models", handler.list_models)
    app.router.add_post("/v1/chat/completions", handler.chat_completions)
    app.router.add_post("/chat/completions", handler.chat_completions)

    app.on_startup.append(lambda app: handler.startup())
    app.on_cleanup.append(lambda app: handler.cleanup())

    LOG.info(f"Smart LLM Router listening on http://0.0.0.0:{args.port}")
    LOG.info(f"Config: {args.config}")
    LOG.info(f"Tiers: {list(cfg['tiers'].keys())}")
    LOG.info(f"Providers: {list(cfg['providers'].keys())}")

    web.run_app(app, host="0.0.0.0", port=args.port, access_log=LOG)


if __name__ == "__main__":
    main()
