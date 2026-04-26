"""
Abacus.ai Model Fallback Skill for Hermes
Switches to Abacus.ai (RouteLLM) when free-tier models are exhausted.
"""

from typing import List
import os

# Order: try free models first, then fall back to Abacus
FREE_MODEL_CHAIN = ['openrouter/free:qwen/qwen3.6-plus-preview:free', 'openrouter/free:anthropic/claude-3-haiku', 'openrouter/free:google/gemma-2-9b-it', 'groq/llama-3.3-70b-versatile', 'groq/llama-3.1-8b-instant']

# Abacus.ai RouteLLM model (using the Abacus provider you configured)
ABACUS_FALLBACK_MODEL = os.getenv("ABACUS_FALLBACK_MODEL", "abacus/anthropic/claude-3.5-sonnet")

USE_ABACUS_FALLBACK = True

def _is_quota_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(kw in msg for kw in ["quota", "limit exceeded", "billing", "credit", "insufficient", "rate limit", "too many requests", "429"])

def _is_auth_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(kw in msg for kw in ["unauthorized", "invalid api key", "authentication", "401"])

_original_chat_completion = None

def setup():
    global _original_chat_completion
    try:
        from hermes.tools import get_tool, register_tool_override
        _original_chat_completion = get_tool("chat_completion")
        register_tool_override("chat_completion", wrapped_chat_completion)
        print("[abacus_fallback] Skill loaded — fallback chain active")
    except Exception as e:
        print(f"[abacus_fallback] Failed to load: {e}")

def wrapped_chat_completion(messages, model=None, **kwargs):
    candidates = []
    if model:
        candidates.append(model)
    for m in FREE_MODEL_CHAIN:
        if m not in candidates:
            candidates.append(m)
    if USE_ABACUS_FALLBACK and ABACUS_FALLBACK_MODEL and ABACUS_FALLBACK_MODEL not in candidates:
        candidates.append(ABACUS_FALLBACK_MODEL)

    if not candidates:
        return _original_chat_completion(messages, model=model, **kwargs)

    tried_log = []
    for attempt_model in candidates:
        is_last = (attempt_model == candidates[-1])
        try:
            result = _original_chat_completion(messages=messages, model=attempt_model, **kwargs)
            if attempt_model != (model or "default"):
                print(f"[abacus_fallback] → {attempt_model}")
            return result
        except Exception as e:
            tried_log.append(f"{attempt_model}: {type(e).__name__}")
            if _is_auth_error(e):
                raise RuntimeError(f"Authentication error for {attempt_model}: {e}. Check ~/.hermes/.env") from e
            if _is_quota_error(e):
                if is_last:
                    raise RuntimeError(f"All models exhausted. Tried: {', '.join(candidates)}") from e
                continue
            raise
    raise RuntimeError(f"Chat failed for all models: {tried_log}")
