---
name: elise-intelligence-brief
category: elise
description: Generate evening brief covering last 8 hours, emphasizing what changed since morning.
---

## Usage
Run this skill to produce a brief summarizing changes over the specified period (default: last 8 hours for evening, last 12 hours for morning). Highlight what changed and macro risk assessment.

## Research Methodology

### Step 0: Retrieve Morning Baseline
Before gathering data, use `session_search` to find the morning brief from today. This is critical for the "what changed since morning" emphasis.

```
session_search(query="brief April 26 2026 morning", limit=3)
```

The morning brief provides baseline prices and signals so you can compare evening vs morning.

### Step 1: Try MCP Elise DB (primary — usually fails)
```python
mcp_elise_db_query(sql="SELECT * FROM news_items WHERE published_at >= datetime('now', '-12 hours') ORDER BY relevance_score DESC")
```
If this fails with McpError (it ALWAYS does — Elise DB has been non-functional for months), fall back to web search immediately. Do NOT retry.

### Step 2: Price Fetching — CoinGecko Batch API
CoinGecko is the primary source for current prices. The free tier has aggressive rate limits — follow the strategy below carefully.

#### Batch call (10-12 tokens, single request)
```python
ids = "bitcoin,ethereum,sui,solana,destra-network,aethir,io,sui,superfarm,moonwell-artemis,clearpool,turbo,tao-bot"
url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true"
# Wait 6-10s between batch and single calls
```

#### Single-token calls with 8-12s delays (for tokens that 429'd in batch)
```python
tokens = {
    "superfarm": "superfarm",
    "moonwell-artemis": "moonwell-artemis",
    "clearpool": "clearpool",
    "turbo": "turbo",
    "aethir": "aethir",
    "destra-network": "destra-network",
    "tao-bot": "tao-bot"
}
for token_id in tokens:
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={token_id}&vs_currencies=usd&include_24hr_change=true"
    # Wait 8-12s between calls to avoid 429
    time.sleep(10)
```

If a token 429s on first retry, wait 12-15s and retry with a smaller group:
```python
# Pair 2-3 tokens per retry call for better throughput
url = "https://api.coingecko.com/api/v3/simple/price?ids=superfarm,tao-bot&vs_currencies=usd&include_24hr_change=true"
```

### Step 3: Web Research with DuckDuckGo (fallback for news)
Install ddgs if needed: `pip install ddgs --break-system-packages`

Use `execute_code` with the Python DDGS API — do NOT delegate to subagents because web tools may not be injected into child contexts.

**IMPORTANT — DDGS rate limiting and failures:**
- `ddgs.news()` with `timelimit="d"` frequently fails with `DDGSException: DecodeError`. When that happens:
  1. Retry with `timelimit="w"` (past week) as fallback — it's more reliable
  2. If `news()` still fails, fall back to `ddgs.text()` for price/text results
  3. If text search also fails, use RSS feeds (CoinDesk, Google News RSS) as final fallback
- Always use `time.sleep(1-2)` between ddgs calls

```python
from ddgs import DDGS
import time

with DDGS() as ddgs:
    # Crypto market overview
    for r in ddgs.news("cryptocurrency market bitcoin ethereum", max_results=8, timelimit="d"):
        process_result(r)
    
    time.sleep(2)
    
    # Portfolio-specific news
    for token in ["SUI cryptocurrency", "TAO Bittensor AI", "ONDO RWA tokenization"]:
        for r in ddgs.news(token, max_results=5, timelimit="d"):
            process_result(r)
        time.sleep(2)
    
    # Macro & regulation — use timelimit="w" if "d" fails
    for r in ddgs.news("Federal Reserve interest rates 2026", max_results=6, timelimit="w"):
        process_result(r)
```

Also use `ddgs.text()` for current prices when news doesn't have them:
```python
for r in ddgs.text("bitcoin price today", max_results=3):
    print(f"{r['body'][:250]}")
```

### Step 4: Compile & Send
Structure the brief with these sections:
1. **Market Snapshot** — prices for all portfolio tokens (BTC, ETH, SOL, SUI, DSYNC, ATH, IO, SUPER, WELL, CPOOL, TURBO, tao.bot) with 24h change and P&L vs entry where known
2. **Top Changes Since Morning** — 3-4 most significant developments, with morning baseline comparison for context
3. **Macro Risk Assessment** — LOW / ELEVATED / HIGH with directional arrows (↑ upgrade, ↓ downgrade, ↔ unchanged) and a table of weighted factors
4. **Portfolio Impact** — per-holding exposure analysis with emoji status (🟢/🟡/🔴) and P&L
5. **Affected Narratives** — ELISE-tracked narratives (ai_infra, l1, rwa, depin) with emoji status
6. **Scenarios** — bull/base/bear with probabilities, targets, triggers, time horizon (next 7 days)
7. **Key Watch Levels** — support/resistance for BTC, ETH, SUI, SOL, oil, plus this week's calendar

## Pitfalls
- Subagents don't get web tools injected — do all searching in parent context with `execute_code`
- **MCP Elise DB is permanently offline** (all sessions since March 31, 2026). Don't retry — fall back to CoinGecko + DDGS immediately
- `ddgs.news()` with `timelimit="d"` frequently returns DecodeError — use `timelimit="w"` as fallback
- CoinGecko free tier 429s aggressively — wait 8-12s between calls, batch when possible, retry failed tokens in pairs
- `ddgs.text()` dates may be stale — prefer `ddgs.news()` for recency, text for current prices
- Browser tools may be unavailable (Playwright not installed) — ddgs + RSS + CoinGecko API is the reliable stack
- Always retrieve morning brief via `session_search` before writing the evening brief — the value is in the comparison
- ddgs.news() dates shown in results may be DDGS's ingest date, not the article date — verify freshness by content, not timestamp
- Some CoinGecko IDs differ from token names: WELL = "moonwell-artemis" (not "moonwell" or "well3"), IO = "io" (not "io-net")
