---
name: hermes-custom-provider-pricing
description: Add token cost tracking for a custom OpenAI-compatible provider in Hermes Agent. Use when a user's custom provider shows no cost/credits in the status bar because it resolves to billing_mode="unknown".
triggers:
  - user wants cost tracking for a custom provider
  - credits not showing for routeLLM / abacus.ai / custom endpoint
  - show_cost is true but cost shows n/a or unknown
  - user asks to add pricing for a custom API endpoint
---

# Adding Cost Tracking for a Custom Provider in Hermes

## Problem

When using a custom OpenAI-compatible provider (e.g. routeLLM, abacus.ai, or any
self-hosted endpoint), Hermes resolves the billing route to billing_mode="unknown"
and shows no cost in the status bar even when show_cost: true is set in config.yaml.

## Key Files

- hermes-agent/agent/usage_pricing.py — billing route resolution + pricing table
- hermes-agent/cli.py — status bar display (_get_status_bar_snapshot, _get_status_bar_fragments)
- config.yaml — ensure display.show_cost: true

## Step-by-Step

### 1. Confirm show_cost is enabled

Check config.yaml for show_cost: true under the display section.

### 2. Query the provider's /v1/models endpoint for pricing

```python
import requests
resp = requests.get(
    'https://YOUR-PROVIDER/v1/models',
    headers={'Authorization': 'Bearer YOUR_API_KEY'},
    timeout=10
)
print(resp.json())
```

Look for fields like input_token_rate, output_token_rate (per-token),
or pricing.prompt / pricing.completion (OpenRouter-style, also per-token).
Convert per-token to per-million by multiplying by 1,000,000.

### 3. Add endpoint detection in resolve_billing_route()

In usage_pricing.py, find the resolve_billing_route() function and add a
check BEFORE the generic custom/local fallback:

```python
# Add this block before the "custom"/"local" check:
if "your-provider-domain.com" in base:
    return BillingRoute(
        provider="yourprovider",
        model=model,
        base_url=base_url or "",
        billing_mode="official_docs_snapshot"
    )
```

The `base` variable is the lowercased base_url. Use billing_mode="official_docs_snapshot"
so the pricing table lookup is triggered.

### 4. Add pricing entries to _OFFICIAL_DOCS_PRICING

In the same file, add entries to the _OFFICIAL_DOCS_PRICING dict (keyed by
(provider_name, model_id) tuples). Per-token rates from the API must be
multiplied by 1,000,000 to get per-million rates:

```python
(
    "yourprovider",
    "your-model-id",
): PricingEntry(
    input_cost_per_million=Decimal("3.00"),   # 0.000003/token * 1M
    output_cost_per_million=Decimal("15.00"), # 0.000015/token * 1M
    cache_read_cost_per_million=Decimal("1.25"),  # if applicable
    source="official_docs_snapshot",
    source_url="https://your-provider/v1/models",
    pricing_version="yourprovider-YYYY-MM-DD",
),
```

Add one entry per model the provider offers.

### 5. Verify with a quick test

```python
import sys
sys.path.insert(0, '/root/.hermes/hermes-agent')
from agent.usage_pricing import resolve_billing_route, estimate_usage_cost, CanonicalUsage

route = resolve_billing_route('your-model', provider='custom', base_url='https://your-provider')
print('Route:', route)  # Should show billing_mode='official_docs_snapshot'

usage = CanonicalUsage(input_tokens=10000, output_tokens=2000)
result = estimate_usage_cost('your-model', usage, provider='custom', base_url='https://your-provider')
print('Cost:', result)  # Should show amount_usd and label like ~$0.06
```

## Abacus.AI / RouteLLM (already patched as of 2026-03-28)

Pricing from the /v1/models endpoint:

  claude-sonnet-4-6 : $3.00/M input, $15.00/M output
  route-llm         : $3.00/M input, $15.00/M output
  gpt-4o-2024-11-20 : $2.50/M input, $10.00/M output
  gpt-4o-mini       : $0.15/M input, $0.60/M output
  o4-mini           : $1.10/M input, $4.40/M output

The formula applied per turn:
  Total Credits = (Input Tokens x Input Price/M) + (Output Tokens x Output Price/M)

## Step 6 (Critical): Wire cost into the status bar

show_cost: true in config.yaml is NOT enough on its own — the status bar code
in cli.py does not read it by default. You must also patch cli.py to compute
and display the cost label.

### 6a. Add session_cost_label to _get_status_bar_snapshot()

In the snapshot dict initialisation, add:
    "session_cost_label": None,

Then after the token fields are populated (after session_api_calls line), add:

```python
if self.config.get("display", {}).get("show_cost", False):
    try:
        cost_result = estimate_usage_cost(
            agent.model,
            CanonicalUsage(
                input_tokens=snapshot["session_input_tokens"],
                output_tokens=snapshot["session_output_tokens"],
                cache_read_tokens=snapshot["session_cache_read_tokens"],
                cache_write_tokens=snapshot["session_cache_write_tokens"],
            ),
            provider=getattr(agent, "provider", None),
            base_url=getattr(agent, "base_url", None),
        )
        if cost_result.amount_usd is not None:
            prefix = "~" if cost_result.status == "estimated" else ""
            snapshot["session_cost_label"] = f"{prefix}${float(cost_result.amount_usd):.4f}"
    except Exception:
        pass
```

### 6b. Add cost label to _get_status_bar_fragments()

In the full-width branch of _get_status_bar_fragments(), just before the
duration frags.extend block, add:

```python
cost_label = snapshot.get("session_cost_label")
if cost_label:
    frags.extend([
        ("class:status-bar-dim", " │ "),
        ("class:status-bar-dim", cost_label),
    ])
```

This produces a status bar like:
  ⚕ claude-sonnet-4-6 | 12K/1M | ████ 1% | ~$0.0042 | 2m

## Pitfalls

- show_cost: true in config.yaml alone does NOT make cost appear in the status bar.
  The status bar code must also be patched (Step 6 above) — this is a known gap.
- The `base` variable in resolve_billing_route() is already lowercased — match accordingly.
- Add the new provider check BEFORE the custom/local fallback block, or it will never be reached.
- Per-token rates (e.g. 0.000003) must be converted to per-million (3.00) for PricingEntry.
- The model key in _OFFICIAL_DOCS_PRICING must match exactly what resolve_billing_route() puts
  in route.model — check the route output first before adding entries.
- If the provider's /models endpoint is not accessible, hardcode pricing from their docs.
- Restart Hermes after patching cli.py for changes to take effect.
