---
name: crypto-portfolio
description: User's crypto portfolio holdings and daily research workflow. Load when handling portfolio-related tasks, research, or ELISE briefs.
version: 2.0.0
tags: [crypto, portfolio, research, wiki]
---

# Crypto Portfolio

Updated: April 2026

## Holdings

| Asset | Holdings | Entry Price |
|-------|----------|-------------|
| BTC | 0.01657 | $70,220 |
| ETH | 0.3552 | $2,060 |
| SUI | 664 | $0.932 |
| SOL | 7.34 | $87.7 |
| DSYNC | 63,668 | — |
| ATH | 65,615 | — |
| IO | 3,030 | — |
| SUPER | 8,777 | — |
| WELL | 81,500 | — |
| tao.bot | 3,550 | — |
| CPOOL | 26,849 | — |
| TURBO | 266,369 | — |

## Daily Research Workflow

1. Fetch prices via CoinGecko API (see rate-limit notes below)
2. Calculate P&L vs entry prices where available
3. Save research to wiki: `~/wiki/raw/articles/daily-crypto-portfolio-research-YYYY-MM-DD.md`
4. Update/create entity pages in `~/wiki/entities/`
5. Create query page in `~/wiki/queries/`
6. Update `~/wiki/index.md` and `~/wiki/log.md`

## CoinGecko API Strategy

### Rate Limits (Free Tier)
- Official: 30 calls/min but aggressive throttling in practice
- **Wait 6-10 seconds between individual coin lookups** to avoid 429s
- **Batch calls fail too** if you just hit the limit — wait before retrying
- Throttled responses return plain text `"Throttled"` (not JSON) — check before parsing

### Recommended Approach
```python
# Step 1: Batch major tokens in ONE call (most reliable)
GET /simple/price?ids=bitcoin,ethereum,sui,solana,superfarm,turbo,io&vs_currencies=usd&include_24hr_change=true

# Step 2: Single-coin lookups with 6-10s delays for remaining tokens
GET /coins/aethir?localization=false&tickers=false&community_data=false&developer_data=false
GET /coins/well3?...  (after delay)
GET /coins/clearpool?...  (after delay)
```

### CoinGecko IDs for Portfolio Tokens (CONFIRMED WORKING 2026-04-19)
| Token | CoinGecko ID | Notes |
|-------|-------------|-------|
| BTC | bitcoin | |
| ETH | ethereum | |
| SUI | sui | |
| SOL | solana | |
| ATH | aethir | |\n| IO | io | CoinGecko ID is "io" (io.net) — confirmed working |\n| SUPER | superfarm | |\n| WELL | moonwell-artemis | CoinGecko ID is "moonwell-artemis" — NOT "moonwell" (that's a different token). Moonwell (WELL) is on Base, ~$0.004, Rank #899. Market cap ~$19M. Perplexity reports ~$333M TVL ($310M on Base). |
| DSYNC | destra-network | NOW AVAILABLE (was previously missing) |
| tao.bot | tao-bot | NOW AVAILABLE (was previously missing) |
| CPOOL | clearpool | |
| TURBO | turbo | |
| Bittensor (ref) | bittensor | |

**IO.net note:** CoinGecko may return empty for io.net. Use CoinMarketCap browser fallback: `https://coinmarketcap.com/currencies/io-net/`

### Fallback APIs (if CoinGecko is down/throttled)
- CoinCap: `GET https://api.coincap.io/v2/assets/{id}` (free, no auth)
- CoinLore: `GET https://api.coinlore.net/api/ticker/?id={numeric_id}` (free, but IDs differ from CoinGecko)
- CoinMarketCap (browser): Navigate to `https://coinmarketcap.com/currencies/{token}/` — no CAPTCHA, shows price, market cap, volume

## News Fetching Strategy

Two-tier approach: **Perplexity Sonar Pro** (primary for depth) + **RSS feeds** (fallback for speed).

### Tier 1: Perplexity Sonar Pro (Primary — Best for Small/Mid-Caps)

Perplexity Sonar Pro performs live web search with citations — ideal for getting real answers about specific tokens that may not have dedicated news coverage. Use this for **all token-specific research**, especially small/mid-cap holdings.

**Setup**: API key stored at `PERPLEXITY_API_KEY` in `~/.hermes/.env`.

```python
import os, json, urllib.request

api_key = os.environ.get("PERPLEXITY_API_KEY")
# Or read from .env:
# with open(os.path.expanduser("~/.hermes/.env")) as f:
#     for line in f:
#         if 'PERPLEXITY_API_KEY' in line:
#             api_key = line.split('=',1)[1].strip().strip('"').strip("'")

url = "https://api.perplexity.ai/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

payload = {
    "model": "sonar-pro",  # or "sonar" for lighter/deeper searches
    "messages": [
        {"role": "system", "content": "You are a crypto research analyst. Search the web for the latest information and provide concise factual answers with specific data points."},
        {"role": "user", "content": "Latest news on Moonwell (WELL) DeFi lending protocol on Base — TVL changes, security incidents, partnerships?"}
    ],
    "max_tokens": 500
}

req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read().decode())
    content = data['choices'][0]['message']['content']
```

**Token-specific research patterns** — use queries like these:

| Token | Perplexity Query Pattern |
|-------|-------------------------|
| BTC/ETH | "Bitcoin latest price action institutional flows April 2026" |
| SOL | "Solana ecosystem TVL fees revenue latest developments" |
| SUI | "Sui network news CME futures ecosystem growth" |
| ATH | "Aethir decentralized GPU cloud latest enterprise contracts revenue" |
| IO | "io.net GPU compute network latest developments tokenomics" |
| WELL | "Moonwell DeFi lending Base TVL security oracles" |
| DSYNC | "Destra Network latest developments partnerships" |
| CPOOL | "Clearpool RWA lending L2 latest TVL cpUSD" |
| SUPER | "SuperVerse SuperFarm NFT gaming latest" |
| TURBO | "Turbo meme coin recent developments" |
| tao.bot | "TAOBOT AI agent crypto latest" |

**Why Perplexity > DDGS for small caps**: DDGS frequently returns empty/error results for niche tokens (DSYNC, SUPER, CPOOL, WELL). Perplexity's multi-source web search finds data even when no single news article exists — it pulls from CoinGecko pages, exchange listings and forum discussions.

### Tier 2: RSS Feeds (Fallback — Speed for Major Tokens)

When Perplexity is unavailable or you just need a quick scan of major headlines:

```bash
# CoinDesk RSS — works consistently
curl -s "https://www.coindesk.com/arc/outboundfeeds/rss/"

# CoinTelegraph RSS
curl -s "https://cointelegraph.com/rss"

# Google News RSS — search any query
curl -s "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
```

## Risk Flags
- **IO.net**: Price API sometimes fails (CoinGecko 404). Use CoinGecko ID "io-net" or CoinCap as fallback. QUALITY project — real DePIN GPU compute being used, not a dead token.
- **ATH (Aethir)**: QUALITY DePIN project — decentralized GPU cloud with real enterprise usage. Low media coverage in 2026 but fundamentally solid infrastructure play.

## CORRECTIONS (learned from user feedback)
- **WELL = Moonwell** (Base DeFi lending protocol), NOT WELL3. Different project entirely. Moonwell is an active lending market on Base chain. CoinGecko ID "moonwell-artemis" (NOT "moonwell" — that's a different token "Moonwell Apollo" / mfam). As of Apr 2026: ~$0.004, $19M market cap, $333M TVL ($310M on Base).
- **IO (io.net)**: High-quality DePIN — decentralized GPU compute network, real usage. Not a dead token. 30K+ GPUs available, $20M+ revenue.
- **ATH (Aethir)**: High-quality DePIN — decentralized GPU cloud for AI/gaming. Record revenue $127.8M, $166M ARR. Enterprise deal: $260M Axe Compute (2,304 B300 GPUs).
- **Always use Perplexity Sonar Pro** for token research — deeper coverage than DDGS, especially for small/mid-caps.

## News Fallback Strategy (RSS-first)

When web search returns CAPTCHAs (Google, DuckDuckGo, CoinGecko site) or browser tools fail, RSS feeds are stable and require no auth:

- **CoinDesk RSS**: `https://www.coindesk.com/arc/outboundfeeds/rss/` — 15–20 items, CDATA-wrapped
- **Google News RSS**: `https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en` — search any query
- **CoinTelegraph RSS**: `https://cointelegraph.com/rss` — sometimes empty titles; filter

RSS bypasses all bot detection and provides sufficient recent market context. Parse with regex: `<item>(.*?)</item>` loops, extract `<title>`, `<link>`, `<pubDate>`.

## Schema Adaptation for Crypto Wikis

If your wiki is AI/ML-focused (tags: model, architecture, training), extend SCHEMA.md taxonomy before tagging crypto entity pages:

```yaml
# Add to Tag Taxonomy:
- Crypto: crypto, portfolio, token, defi, layer1, compute, meme, ai-crypto
- Techniques: add 'research' and 'analysis' if missing
```

Entity tagging guide:
- Layer 1s (BTC, ETH, SUI, SOL): `[model, network]`\n- AI/compute tokens (ATH, DSYNC, IO, SUPER, TURBO, tao.bot): `[model]`\n- DeFi tokens (CPOOL, WELL): `[model, network]`\n- Meme tokens (TURBO): `[model]`

**Never** use a tag not in SCHEMA.md taxonomy — add it there first, then apply.

## Revision History
- v2.0 (2026-04): Initial holdings table, CoinGecko batch + single-fetch strategy, RSS news fallback
- v2.1 (2026-04-25): Added IO.net data-gap protocol, RSS-first news prioritization, schema crypto-tag extension guidance


## Wiki Integration
Research outputs go to LLM wiki at `~/wiki`. See llm-wiki skill for full wiki workflow. Key files:
- Raw sources: `~/wiki/raw/articles/daily-crypto-portfolio-research-YYYY-MM-DD.md`
- Entity pages: `~/wiki/entities/{token}.md`
- Query results: `~/wiki/queries/crypto-portfolio-research-YYYY-MM-DD.md`
- Concept page: `~/wiki/concepts/crypto-portfolio-analysis.md`
