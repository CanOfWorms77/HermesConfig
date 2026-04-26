---
name: model-quality-comparison
description: Compare LLM quality across providers/models on a specific task. Uses ground-truth source + identical prompt to evaluate accuracy, hallucination, and usefulness.
---

# Model Quality Comparison

Use when evaluating which model/provider to use for a specific task type (research, coding, analysis, etc).

## Methodology

1. **Establish ground truth** — Use a reliable source for the same query:
   - Perplexity Sonar (web-searching LLM, best for current events/prices)
   - Manual web search + verification
   - Known correct answer for coding/math tasks

2. **Craft a standardized test prompt** — Same prompt to all models. Include:
   - Clear task definition
   - Specific output format request
   - Domain the user actually cares about (don't test generic prompts)

3. **Test models via direct API calls** — Use curl with JSON payload files to avoid escaping issues:
   ```python
   with open("/tmp/llm_payload.json", "w") as f:
       json.dump(payload, f)
   terminal(f'curl -s {base_url}/chat/completions -H "Authorization: Bearer {key}" -H "Content-Type: application/json" -d @/tmp/llm_payload.json', timeout=120)
   ```

4. **Score against ground truth** — Check for:
   - Factual accuracy (numbers, dates, names)
   - Hallucination (confident but wrong details)
   - Completeness (did it cover all requested items)
   - Usefulness (actionable vs vague)

## Key Findings (Free/Cheap Models for Research)

**Critical lesson: Web access > Model size for current-events research.**
- Models without web search hallucinate confidently (2-7x wrong on prices, invent fake news)
- Model parameter count doesn't compensate for knowledge cutoff
- Perplexity Sonar (with web search) vastly outperforms larger models without it

**For research tasks specifically:**
- Use web-searching tools (Sonar, DDG) for data gathering
- Use any capable model for summarization/analysis of fetched data
- Never trust a non-web-connected model for current facts

## Provider-Specific Notes

### Nous Research (inference-api.nousresearch.com)
- Free models listed on API but require Nous-specific API key (not NVIDIA nvapi)
- `:free` models are OpenRouter routes — not directly available on Nous API
- Check key validity at portal.nousresearch.com

### NVIDIA NIM (integrate.api.nvidia.com)
- nvapi keys work here
- Many open models available (nemotron, llama, qwen, deepseek)
- Some models have EOL dates (check availability)

### OpenRouter (openrouter.ai)
- Free tier: 50 requests/day for `:free` models
- Add $5 credit for 1000/day
- Rate limit resets at midnight UTC

## Template Comparison Table

| Model | Provider | Cost | Accuracy | Hallucination | Notes |
|-------|----------|------|----------|---------------|-------|
| sonar | Perplexity | ~$0.005/query | HIGH | Low | Has web search |
| nemotron-3-super | NVIDIA NIM | Free | LOW | High | No web, invents data |
| llama-3.3-70b | NVIDIA NIM | Free | LOW | High | No web, invents data |
