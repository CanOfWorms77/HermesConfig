---
name: local-llm-feasibility
category: mlops
description: Evaluate if an AI model can be run locally, estimate hardware requirements, and recommend deployment strategies.
---
# Local LLM Feasibility & Hardware Guide

## Description
Systematically evaluate whether an AI model can be run locally, determine its RAM/GPU requirements, and recommend a deployment strategy (local vs cloud vs API).

## When to Use
- User asks "How much RAM to run [model]?"
- User wants to run a specific model locally but you're unsure of its weights.
- User is building/buying hardware for LLM inference.
- Evaluating cost/performance tradeoffs (API vs local vs cloud).

## Step-by-Step Process
1. **Check Availability:**
   - Search HuggingFace API: `https://huggingface.co/api/models?search=<model_name>&sort=downloads&direction=-1&limit=10`
   - If no results, check if it's listed as a provider/model on OpenRouter or similar API marketplaces.
   - **Rule:** "Plus", "Max", "Flash" variants from Qwen, OpenAI, etc., are typically **API-only/closed**. If not on HF from the official org, assume closed weights.

2. **Calculate RAM Requirements (if open):**
   - **FP16:** ~2 GB per 1 billion parameters.
   - **Q4 (4-bit GGUF/MLX):** ~0.7 GB per 1 billion parameters.
   - **Context Overhead:** Add 1-4 GB for 32K-100K token context windows.
   - *Example:* 27B model → FP16: ~54 GB, Q4: ~19 GB.

3. **Evaluate Hardware Fit:**
   - **Apple Silicon:** Uses Unified Memory. 64 GB is the sweet spot for mid-range models. Mx Ultra (800 GB/s bandwidth) is ~2x faster for LLMs than Mx Max (400 GB/s).
   - **NVIDIA GPUs:** VRAM is strict limit. 24 GB (3090/4090) can fit ~30B at Q4.
   - **Cloud/Decentralized:** Use services like io.net, RunPod, or Lambda Labs for models requiring 100+ GB RAM/VRAM.

4. **Recommend Deployment Strategy:**
   - **Local:** Daily tasks, privacy-critical work, mid-range models (up to max RAM/VRAM).
   - **Cloud GPU:** Heavy inference, testing larger models without upfront hardware cost.
   - **API:** Best for proprietary/closed models (Qwen-Plus, GPT-4, etc.).

## Common Pitfalls
- **Pitfall:** Assuming all models on OpenRouter have local downloadable weights.
- **Solution:** Many are API endpoints. Verify on HuggingFace.
- **Pitfall:** Forgetting context window RAM usage.
- **Solution:** Llama.cpp uses ~2MB per 1K context for 70B model; KV cache grows with context length.
- **Pitfall:** Ignoring memory bandwidth for Apple Silicon.
- **Solution:** Inference speed is strictly bandwidth-limited. Ultra chips are worth the premium for local LLMs.

## Verification
- Confirm model size from official model card (HuggingFace).
- Calculate Q4/FP16 size.
- Compare against user's hardware specs.