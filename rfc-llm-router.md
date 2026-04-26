# RFC: Intelligent LLM Router with Self-Improving Model Discovery

**Author:** Dave (@CanOfWorms777)
**Status:** Draft
**Created:** 2026-04-19
**Target:** [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)

---

## Summary

A provider-aware, self-improving LLM routing system for Hermes that discovers new models across platforms, evaluates them automatically, and routes queries intelligently — with graceful fallback when providers are rate-limited or down. Users define their preferred models per tier (free/low/medium/high), the system keeps free-tier models current by probing availability daily, and notifies users when new frontier models appear.

---

## Motivation

Hermes currently supports 20+ providers and has basic smart model routing (`agent/smart_model_routing.py`) that routes short/simple queries to a single configured "cheap model." This is useful but limited:

1. **No provider fallback** — if your primary provider is rate-limited or down, the session fails
2. **No free-model discovery** — OpenRouter, NVIDIA NIM, and Groq regularly rotate free models; users have to manually track what's available
3. **No intent-based routing** — a "hello" and a "design me a distributed system" both hit the same model unless the user manually switches
4. **No model news** — users don't know when a better model becomes available unless they're actively watching the space

The user behind this RFC built a similar system for a personal investment intelligence engine (ELISE), using daily model evaluation with Perplexity Sonar as a judge, tier-based routing across NVIDIA NIM, RouteLLM, and custom providers, and self-improving promotion logic that automatically adopts better models after a 3-day observation window. That design proved the concept works. This RFC generalizes it for any use case.

---

## Design Overview

Four components, each shippable independently:

```
┌─────────────────────────────────────────────────┐
│              User Message                        │
└──────────────────┬──────────────────────────────┘
                   │
         ┌─────────▼──────────┐
         │  Intent Classifier  │  ← how complex is this query?
         └─────────┬──────────┘
                   │
         ┌─────────▼──────────┐
         │  Tier Selector      │  ← which tier does this task need?
         └─────────┬──────────┘
                   │
         ┌─────────▼──────────┐
         │  Provider Router    │  ← which provider/model for this tier?
         │  (with fallback)    │     try primary → fallback → fallback
         └─────────┬──────────┘
                   │
         ┌─────────▼──────────┐
         │  Model Executor     │  ← call the LLM
         └─────────────────────┘

  Background:
  ┌──────────────────────────────────────────────┐
  │  Model Discovery (daily cron)                │
  │  • Probe free models across providers        │
  │  • Evaluate new models against benchmarks    │
  │  • Notify user of new frontier models        │
  │  • Auto-promote best free model              │
  └──────────────────────────────────────────────┘
```

---

## Component 1: Provider Fallback Chains

### Problem

Currently, if NVIDIA NIM is rate-limited or OpenRouter is down, the session errors out. Users have to manually switch providers.

### Design

Extend the existing `smart_model_routing` config to support ordered fallback chains per tier.

```yaml
# config.yaml
smart_model_routing:
  enabled: true
  tiers:
    free:
      - provider: nvidia
        model: "auto"  # use discovery winner
      - provider: groq
        model: "llama-3.3-70b-versatile"
      - provider: openrouter
        model: "meta-llama/llama-3.3-70b-instruct:free"
    low:
      - provider: openrouter
        model: "google/gemini-2.5-flash"
      - provider: groq
        model: "llama-3.3-70b-versatile"
    medium:
      - provider: anthropic
        model: "claude-sonnet-4"
      - provider: openrouter
        model: "anthropic/claude-sonnet-4"
    high:
      - provider: anthropic
        model: "claude-opus-4-6"
      - provider: openrouter
        model: "anthropic/claude-opus-4-6"
  # Custom provider support (any OpenAI-compatible endpoint)
  custom_providers:
    abacus:
      base_url: "https://api.abacus.ai/v1"
      api_key_env: "ABACUS_API_KEY"
      default_model: "gpt-4o"
    local_ollama:
      base_url: "http://localhost:11434/v1"
      api_key: "ollama"
      default_model: "qwen2.5:14b"
```

### Behavior

- On each turn, try the first provider in the tier's list
- If the call fails (rate limit, timeout, auth error, 502/503), try the next
- If all providers in a tier fail, fall back to the next tier up (free → low → medium)
- Log the fallback chain for the user to see: `nvidia (rate limited) → groq (ok)`
- Health status tracked per provider with exponential backoff on failures

### Files to modify

- `agent/smart_model_routing.py` — expand `choose_cheap_model_route()` to handle tier chains
- `hermes_cli/config.py` — new config schema with validation
- `run_agent.py` — wire fallback into the conversation loop (catch provider errors, retry with next)
- New: `agent/provider_health.py` — per-provider health tracking (last success, failure count, backoff)

### Estimated scope

~300 lines of new code, ~100 lines modified. Single PR.

---

## Component 2: Intent-Based Routing

### Problem

Currently, smart routing only checks "is this message short and simple?" Real queries have varying complexity that should map to different model tiers.

### Design

Expand the heuristic classifier in `smart_model_routing.py` to categorize queries into tiers.

```python
# Simplified classification logic
class QueryTier(Enum):
    FREE = "free"       # greetings, simple lookups, "what time is it"
    LOW = "low"         # summaries, translations, simple Q&A
    MEDIUM = "medium"   # code generation, analysis, multi-step reasoning
    HIGH = "high"       # architecture design, complex debugging, research

def classify_query(message: str, conversation_history: list) -> QueryTier:
    """Classify query complexity using heuristics (no LLM call needed)."""
    text = message.strip().lower()
    words = text.split()

    # FREE tier signals
    if len(words) < 8 and not contains_code(text):
        greetings = {"hi", "hello", "hey", "thanks", "ok", "yes", "no"}
        if words and words[0] in greetings:
            return QueryTier.FREE

    # HIGH tier signals
    complex_signals = [
        "design a system", "architect", "full codebase",
        "research and compare", "write a spec", "implement from scratch",
        len(words) > 200,
        text.count("\n") > 10,
        contains_code_blocks(text),
    ]
    if sum(complex_signals) >= 2:
        return QueryTier.HIGH

    # MEDIUM tier signals
    medium_signals = [
        "debug", "implement", "refactor", "analyze",
        "write code", "create a", "build a",
        contains_code(text),
        contains_urls(text),
    ]
    if sum(medium_signals) >= 1:
        return QueryTier.MEDIUM

    # Default to LOW
    return QueryTier.LOW
```

### User override

Users can force a tier with a prefix or command:
- `/route low explain quantum entanglement`
- Or in config: `smart_model_routing.force_tier: medium` (always use medium)

### Files to modify

- `agent/smart_model_routing.py` — expand classification logic
- `tests/agent/test_smart_model_routing.py` — new test cases

### Estimated scope

~150 lines of new code. Single PR, depends on Component 1 for tier config.

---

## Component 3: Free Model Discovery

### Problem

Free models on OpenRouter, NVIDIA NIM, and Groq rotate frequently. Users don't know when a better free model appears unless they manually check.

### Design

A daily cron job that:

1. **Probes provider APIs** for available free models
2. **Evaluates top candidates** against a standardized benchmark (8-10 test prompts)
3. **Promotes the winner** to the user's `free` tier automatically
4. **Logs changes** — which models appeared, disappeared, or changed quality

```python
# agent/model_discovery.py

FREE_MODEL_SOURCES = {
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/models",
        "filter": lambda m: ":free" in m["id"] or m.get("pricing", {}).get("prompt") == "0",
    },
    "nvidia_nim": {
        "url": "https://integrate.api.nvidia.com/v1/models",
        "filter": lambda m: True,  # all NIM models are free tier
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1/models",
        "filter": lambda m: True,  # all Groq models are free tier
    },
}

EVALUATION_PROMPTS = [
    # General knowledge
    {"task": "summarize", "prompt": "Summarize in 2 sentences: ...", "criteria": ["accuracy", "conciseness"]},
    # Reasoning
    {"task": "reasoning", "prompt": "If all A are B, and some B are C, ...", "criteria": ["correctness"]},
    # Code generation
    {"task": "code", "prompt": "Write a Python function that ...", "criteria": ["correctness", "style"]},
    # Instruction following
    {"task": "instruction", "prompt": "List exactly 3 things about ...", "criteria": ["format_compliance"]},
    # Factual accuracy
    {"task": "factual", "prompt": "What is the capital of ...", "criteria": ["accuracy"]},
    # Creative writing
    {"task": "creative", "prompt": "Write a haiku about ...", "criteria": ["creativity", "format"]},
    # Extraction
    {"task": "extraction", "prompt": "Extract all dates from: ...", "criteria": ["completeness"]},
    # Safety/refusal
    {"task": "safety", "prompt": "How do I ... [benign but edge-case]", "criteria": ["appropriate_handling"]},
]

async def discover_and_evaluate():
    """Daily model discovery and evaluation."""
    candidates = []

    for source_name, source in FREE_MODEL_SOURCES.items():
        models = await fetch_models(source_name, source)
        new_models = diff_against_registry(models)
        candidates.extend(new_models)

        if new_models:
            notify_user(f"🆕 New free models on {source_name}: {[m['id'] for m in new_models]}")

    # Evaluate top candidates (skip if already evaluated recently)
    for model in candidates[:5]:  # evaluate max 5 new models per day
        scores = await evaluate_model(model, EVALUATION_PROMPTS)
        store_evaluation(model, scores)

    # Check if current winner is still best
    current = get_active_free_model()
    winner = get_highest_scored_free_model()

    if winner and winner != current:
        if winner.days_in_registry >= 3 and winner.score > current.score + 5:
            promote_to_free_tier(winner)
            notify_user(
                f"🤖 Free model upgraded: {current.id} → {winner.id}\n"
                f"   Score: {current.score} → {winner.score}\n"
                f"   New model excels at: {winner.strongest_tasks}"
            )
```

### Model news monitoring

Beyond just probing APIs, the discovery system can optionally do a web search for new model releases:

```python
async def check_model_news():
    """Weekly web search for new model releases."""
    results = await web_search("new LLM model release this week 2026")
    # Parse for model names, check if they're available on user's providers
    # Notify user: "📢 GPT-5 just released — available on OpenRouter at $X/M tokens"
```

### Notification examples

- `🆕 New free model on OpenRouter: google/gemini-3-flash (1M context, multimodal)`
- `🤖 Free model upgraded: llama-3.3-70b → gemini-3-flash (score +12)`
- `⚠️ Free model removed from NVIDIA: mixtral-8x22b (no longer available)`
- `📢 Frontier model alert: Claude Opus 4.7 available on Anthropic ($15/M input)`

### Files

- New: `agent/model_discovery.py` (~400 lines)
- New: `agent/model_evaluator.py` (~200 lines)
- New: `tools/model_discovery_tool.py` (optional tool for manual `/model discover`)
- Modify: `hermes_cli/config.py` — discovery config section
- Modify: `cron/scheduler.py` — built-in discovery job

### Estimated scope

~600 lines of new code. Single PR, can build on Components 1+2 or standalone.

---

## Component 4: Advanced Features (Future)

These are explicitly out of scope for the initial PRs but worth documenting for the roadmap.

### 4a. LLM-as-Judge Evaluation

The daily model evaluation currently uses heuristic scoring (regex, keyword matching). An optional upgrade: use a cheap but capable model (Perplexity Sonar, Gemini Flash) as a judge to score outputs more accurately.

```yaml
smart_model_routing:
  evaluation:
    judge_provider: openrouter
    judge_model: google/gemini-2.5-flash
    # or
    judge_provider: perplexity
    judge_model: sonar
```

Cost: ~$0.006/day for daily evaluations.

### 4b. User Learning

Track which routing decisions the user overrides (`/model claude-opus-4-6` after the router picked free tier) and adjust future routing:

- If user frequently overrides to `high` for "code review" tasks, learn to route code review to high automatically
- Store as routing preferences in memory

### 4c. Cost Dashboard

`/route stats` command showing:
- Tokens used per tier this session/month
- Cost breakdown by provider
- Money saved by using free tier for simple queries
- "You saved $X this month by routing Y% of queries to free tier"

### 4d. Conversation-Aware Routing

Consider conversation context, not just the current message:
- If the last 3 turns were deep coding, the next "ok" is probably still part of that coding session — keep the same model
- If the conversation shifted to casual chat, step down to free tier

---

## Config Schema (Full)

```yaml
# config.yaml — smart_model_routing section
smart_model_routing:
  enabled: true

  # Tier definitions — ordered fallback chains
  tiers:
    free:
      - provider: nvidia
        model: "auto"          # "auto" = use discovery winner
      - provider: groq
        model: "llama-3.3-70b-versatile"
      - provider: openrouter
        model: "meta-llama/llama-3.3-70b-instruct:free"
    low:
      - provider: openrouter
        model: "google/gemini-2.5-flash"
    medium:
      - provider: anthropic
        model: "claude-sonnet-4"
      - provider: openrouter
        model: "anthropic/claude-sonnet-4"
    high:
      - provider: anthropic
        model: "claude-opus-4-6"
      - provider: openrouter
        model: "anthropic/claude-opus-4-6"

  # Intent classification thresholds
  classification:
    max_free_chars: 80
    max_free_words: 15
    high_complexity_keywords:
      - "design a system"
      - "architect"
      - "full codebase"
      - "implement from scratch"
      - "research and compare"

  # Provider fallback behavior
  fallback:
    max_retries_per_provider: 2
    retry_delay_ms: 1000
    health_check_interval: 300  # seconds
    backoff_multiplier: 2

  # Model discovery (daily cron)
  discovery:
    enabled: true
    schedule: "0 2 * * *"       # 02:00 UTC daily
    evaluate_new_models: true
    max_evaluations_per_day: 5
    promotion_threshold: 5      # minimum score improvement to promote
    observation_days: 3         # days to watch before promoting

  # Custom providers (any OpenAI-compatible endpoint)
  custom_providers:
    abacus:
      base_url: "https://api.abacus.ai/v1"
      api_key_env: "ABACUS_API_KEY"
    local_ollama:
      base_url: "http://localhost:11434/v1"
      api_key: "ollama"
    my_server:
      base_url: "https://my-llm.example.com/v1"
      api_key_env: "MY_LLM_KEY"
```

---

## Implementation Plan

Each PR is independently shippable and valuable.

### PR 1: Provider Fallback Chains + Health Tracking
- **What:** Extend smart_model_routing to support ordered provider lists per tier with automatic fallback on failure
- **Files:** `agent/smart_model_routing.py`, `hermes_cli/config.py`, `run_agent.py`, new `agent/provider_health.py`
- **Size:** ~400 lines
- **Dependencies:** None
- **User impact:** Immediate — sessions no longer fail when one provider is down

### PR 2: Intent-Based Query Classification
- **What:** Expand the simple "is it short?" check to classify queries into free/low/medium/high tiers
- **Files:** `agent/smart_model_routing.py`, `tests/agent/test_smart_model_routing.py`
- **Size:** ~200 lines
- **Dependencies:** PR 1 (needs tier config)
- **User impact:** Smarter routing — simple queries hit cheap models, complex ones get the good stuff

### PR 3: Free Model Discovery + Auto-Evaluation
- **What:** Daily cron job that probes free model availability, evaluates new candidates, and auto-promotes winners
- **Files:** new `agent/model_discovery.py`, new `agent/model_evaluator.py`, `hermes_cli/config.py`
- **Size:** ~600 lines
- **Dependencies:** PR 1 (needs tier config for auto-promotion)
- **User impact:** "I always have the best free model without thinking about it"

### PR 4: Model News + Frontier Alerts
- **What:** Weekly web search for new model releases, notify user when frontier models become available
- **Files:** `agent/model_discovery.py` (extend), new skill or tool integration
- **Size:** ~200 lines
- **Dependencies:** PR 3 (builds on discovery infrastructure)
- **User impact:** "Opus 4.7 just dropped, here's what changed and where to get it"

---

## Backwards Compatibility

- Existing `smart_model_routing` config continues to work unchanged
- `max_simple_chars` / `max_simple_words` / `cheap_model` are still valid (mapped to `free` tier)
- Users who don't enable the new features see no behavior change
- Discovery cron is opt-in (disabled by default)

---

## Related Work

- **Current routing:** `agent/smart_model_routing.py` (~195 lines, heuristic-only)
- **Model switching:** `hermes_cli/model_switch.py` (mid-conversation `/model` command)
- **Credential pools:** `hermes_cli/auth.py` (multi-key rotation per provider)
- **Cron system:** `cron/scheduler.py` (built-in job scheduling)
- **Models.dev integration:** `agent/models_dev.py` (model catalog + capabilities)

---

## Open Questions

1. **Discovery evaluation cost:** Free models are evaluated using the user's API keys. Should we cap daily evaluation cost (e.g., max $0.10/day)?

2. **Custom provider registry:** Should custom providers be shareable? (e.g., a community list of known OpenAI-compatible endpoints)

3. **Conversation-aware routing:** Should the router consider conversation context (e.g., "keep using the current model if the user is in the middle of a coding session")? This adds complexity but prevents jarring model switches.

4. **Skill vs core:** Should model discovery be a bundled skill or baked into the agent core? A skill is easier to maintain but less integrated. Core integration enables the fallback chain to use discovery results directly.

5. **Evaluation benchmarks:** The 8-prompt evaluation suite is general-purpose. Should users be able to add custom evaluation prompts for their specific use case?

---

## Credits

Original design inspired by the ELISE Intelligence System's LLM Router (self-improving model evaluation with daily discovery, tier-based routing, and promotion logic), built by Dave (@CanOfWorms777) for a personal investment intelligence engine. This RFC generalizes that design for any use case and any provider.
