---
name: model-fallback
category: mlops
description: Automatically switches to a fallback model when free-tier quotas are exhausted. Detects 429/rate-limit/billing errors and retries with next model in priority chain.
version: 1.0.0
---

## Overview

The **model-fallback** skill wraps the `chat_completion` tool to provide automatic failover when a model becomes unavailable due to quota exhaustion, rate limits, or billing issues.

## Configuration via Environment Variables

Set these **before** starting the Hermes gateway (`~/.hermes/.env`):

```bash
# Comma-separated free model chain (in order)
FALLBACK_FREE_CHAIN="openrouter/free:qwen/qwen3.6-plus-preview:free,groq/llama-3.3-70b-versatile,groq/llama-3.1-8b-instant,openrouter/free:anthropic/claude-3-haiku"

# Paid fallback model (when free chain exhausted)
# For Abacus.ai RouteLLM: use RouteLLM model IDs (e.g., gpt-5.4-nano, deepseek-v4-flash), NOT provider-prefixed names.
# Paid fallback model (when free chain exhausted)
FALLBACK_PAID_MODEL="deepseek-v4-flash"   # RouteLLM model ID, NOT "abacus/..."

# Enable/disable paid fallback
FALLBACK_USE_PAID="true"
```

**Model ID format:** `<provider>/<model-name>` for most providers (OpenRouter, Groq, etc.). For **Abacus RouteLLM** use the bare model ID only (e.g., `gpt-5.4-nano`, `deepseek-v4-flash`) — the provider is already configured separately. Examples:
- OpenRouter free: `openrouter/free:qwen/qwen3.6-plus-preview:free`
- Groq: `groq/llama-3.3-70b-versatile`
- **RouteLLM: `deepseek-v4-flash`** (no `abacus/` prefix)

## How It Works

1. User requests a model (via chat `/model` or workspace selector)
2. Skill tries requested model first
3. On quota error, tries next model from `FALLBACK_FREE_CHAIN`
4. If all free models fail and `FALLBACK_USE_PAID=true`, tries `FALLBACK_PAID_MODEL`
5. Auth errors (401/invalid key) fail immediately — don't retry

**Error detection keywords:** `quota`, `limit exceeded`, `billing`, `credit`, `insufficient`, `rate limit`, `too many requests`, `429`

## Setup Checklist

- [ ] Configure provider(s) in `~/.hermes/config.yaml` with `api_key: ${ENV_VAR}` references
- [ ] Ensure API key env var name matches (RouteLLM uses `ROUTELLM_API_KEY`, NOT `ABACUS_API_KEY`)
- [ ] Add API keys to `~/.hermes/.env`
- [ ] Set `FALLBACK_*` environment variables with valid model IDs
- [ ] **Verify provider connectivity:** Test the endpoint with curl before relying on it
- [ ] **Verify model availability:** Fetch `/v1/models` and confirm model IDs exist in provider's catalog
- [ ] Place `model_fallback.py` in `~/.hermes/skills/model-fallback/`
- [ ] Restart gateway: `hermes gateway restart`
- [ ] Verify: `hermes skills list | grep model-fallback`

## Notes

- The skill overrides the **`chat_completion` tool**, so it affects workspace chat and any tool that calls LLMs through the tool gateway. CLI `hermes chat` uses the core agent loop directly and would need a separate patch to `~/.hermes/hermes-agent/run_agent.py` around line 5213.
- For system-wide intelligent routing (all entry points), see `~/.hermes/rfc-llm-router.md` — a gateway-side solution that queries provider model catalogs before attempting calls.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| No fallback occurs | Skill not loaded | Restart gateway; check `hermes skills list` |
| "Invalid API key" on startup | Hardcoded key in config.yaml | Replace all `api_key:` values with `${ENV_VAR}` |
| Only ROUTELLM key visible in process env | `.env` not loaded | Ensure gateway started from shell with `source ~/.hermes/.env` or use `hermes gateway start` (systemd) |
| "Invalid model: ... Must be one of the supported..." | Model ID not in provider's catalog | Run `curl -s -H "Authorization: Bearer $ROUTELLM_API_KEY" https://routellm.abacus.ai/v1/models \| python3 -m json.tool` to list valid IDs |
| 401/403 errors with correct key | Wrong env var name in config.yaml | RouteLLM uses `ROUTELLM_API_KEY`, not `ABACUS_API_KEY` |
| **HTTP 403 on Abacus/RouteLLM even though key is correct** | `config.yaml` uses `api_key: ROUTELLM_API_KEY` (literal env var name) instead of `key_env: ROUTELLM_API_KEY` | Change `api_key: ROUTELLM_API_KEY` to `key_env: ROUTELLM_API_KEY` in the abacus provider block. Then clear the stale credential cache: `python3 -c "import json; d=json.load(open('/root/.hermes/auth.json')); d['credential_pool'].pop('custom:abacus.ai', None); d['credential_pool'].pop('abacus', None); d['active_provider']='abacus'; json.dump(d, open('/root/.hermes/auth.json','w'), indent=2)"` and restart gateway. |
| **Credential pool marked "exhausted" with 403** | Stale auth.json caches the literal env-var name as the API key | Clear the abacus credential pool entry (see row above). On next startup, the gateway re-resolves `key_env` and stores the actual API key value. |

---

## Abacus.ai (RouteLLM) Integration Notes

RouteLLM (`https://routellm.abacus.ai/v1`) is Abacus.ai's multi-provider LLM gateway with auto-routing. Important quirks:

**API Key**: The environment variable is `ROUTELLM_API_KEY` (despite the provider name "abacus" in Hermes config).

**Model IDs**: RouteLLM uses its own catalog of model IDs. They are NOT provider-qualified (no `anthropic/` or `openai/` prefixes). Examples:
- `deepseek-v4-flash` (Deepseek V4 Flash)
- `gpt-5.4-nano` (GPT-5.4 Nano)
- `claude-sonnet-4-6` (Claude Sonnet 4.6)
- `route-llm` (auto-router that picks best available model)

**Verify before using**:
```bash
# 1. Test endpoint connectivity
curl -s -X POST https://routellm.abacus.ai/v1/chat/completions \
  -H "Authorization: Bearer $ROUTELLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"route-llm","messages":[{"role":"user","content":"test"}],"max_tokens":5}' | python3 -m json.tool

# 2. List all available models
curl -s -H "Authorization: Bearer $ROUTELLM_API_KEY" https://routellm.abacus.ai/v1/models | python3 -m json.tool

# 3. Test specific model
curl -s -X POST https://routellm.abacus.ai/v1/chat/completions \
  -H "Authorization: Bearer $ROUTELLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'
```

**Hermes config.yaml entry**:
```yaml
abacus:
  api: https://routellm.abacus.ai/v1
  name: Abacus.ai
  api_key: ROUTELLM_API_KEY    # Must match .env variable name
  default_model: deepseek-v4-flash  # Use RouteLLM model IDs
```

**.env fallback variable**:
```bash
ABACUS_FALLBACK_MODEL=gpt-5.4-nano   # RouteLLM model ID, NOT "abacus/gpt-5.4-nano"
```

**After config changes**: Always restart gateway: `hermes gateway restart`
