---
name: multi-model-subagents
description: Spawn subagents using different LLMs/models for task-specific delegation. Covers provider limitations, free tier constraints, and fallback strategies discovered through testing.
version: 1.0.0
author: hermes
tags: [delegation, subagents, model-selection, openrouter, nous, free-tier]
---

# Multi-Model Subagent Spawning

## Key Findings (from testing)

### Nous Research Free Tier
- **ONLY xiaomi/mimo-v2-pro works free** - all other models return HTTP 403 "not supported on Free Tier"
- Nous endpoint **blocks OpenRouter :free models** (HTTP 400)
- Endpoint: https://inference-api.nousresearch.com/v1
- Auth: OAuth via hermes model -> Nous Research (agent_key in auth.json)

### OpenRouter Free Tier
- **50 requests/day** across all free models (without credits)
- **$5 credits = 1000 req/day** on free models
- Rate limits per model: ~8 req/min on popular models (llama-3.3-70b, qwen3-coder)
- Less popular free models may have higher limits

### Available Free Models on OpenRouter (25+)
Best picks:
- meta-llama/llama-3.3-70b-instruct:free - solid general purpose
- qwen/qwen3-coder:free - best for coding tasks
- google/gemma-4-31b-it:free - latest Gemma, 262k context
- nousresearch/hermes-3-llama-3.1-405b:free - largest free Nous model
- nvidia/nemotron-3-super-120b-a12b:free - massive MoE

## How to Spawn Subagents with Different Models

### Method 1: Terminal command (PROVEN WORKING)
Use hermes chat -q with -m and --provider flags:
  hermes chat -q "TASK DESCRIPTION" -m "MODEL_NAME" --provider openrouter

Important: put -q and its argument BEFORE -m to avoid shell parsing issues with :free suffix.

### Method 2: delegate_task (inherits parent model)
- delegate_task does NOT have a model parameter
- Subagents inherit parent model unless delegation config overrides
- Set delegation.model and delegation.provider in config.yaml

### Delegation Config (config.yaml)
```yaml
delegation:
  model: 'meta-llama/llama-3.3-70b-instruct:free'
  provider: openrouter
  max_iterations: 50
  default_toolsets: [terminal, file, web]
```
Config changes may need session restart to take effect for delegate_task.

## Recommended Approach
1. Main chat: Use cheapest working model (e.g., mimo-v2-pro on Nous free)
2. Subagents: Spawn via terminal with -m MODEL --provider openrouter
3. Fallback: If rate limited, try next model in priority list
4. Model priority:
   - Coding: qwen/qwen3-coder:free -> llama-3.3-70b:free -> gemma-4-31b:free
   - General: llama-3.3-70b:free -> gemma-4-31b:free -> hermes-3-405b:free

## Pitfalls
- Shell quoting: model names with : can break shell parsing - use double quotes
- -Q (quiet) flag conflicts with -q (query) in argument parsing - dont use together
- OpenRouter free models rate-limited to ~8 req/min per model - rotate on 429
- hermes chat -m MODEL:free on Nous endpoint returns 400, not 429
- hermes chat -m PAID_MODEL on Nous free tier returns 403
