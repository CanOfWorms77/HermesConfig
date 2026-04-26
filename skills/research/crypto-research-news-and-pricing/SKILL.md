---
name: crypto-research-news-and-pricing
description: Tactical patterns for crypto research when web search is restricted - RSS news aggregation, multi-API price fetching with fallbacks, handling data gaps, and wiki schema adaptation for crypto domains
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [crypto, research, pricing, rss, api, fallback]
    category: research
    related_skills: [crypto-portfolio, llm-wiki]
---

# Crypto Research: News & Pricing Tactics

## Purpose
Reusable patterns for researching cryptocurrency assets when standard web search/browser tools are blocked or unreliable. Covers price discovery, news aggregation, data-gap handling, and wiki integration for crypto portfolios.

## When to Use
- You need to fetch current crypto prices and 24h changes programmatically
- Web search returns CAPTCHAs or bot blocks (Google, DuckDuckGo, CoinGecko site)
- You need recent crypto news without API keys
- Integrating research outputs into an existing AI/ML–focused wiki that needs crypto tag taxonomy
- Handling tokens with spotty API coverage (IO.net, smaller altcoins)

---

## Pattern 1: Multi-Tiered Price Discovery

**Tier 1 — Batch CoinGecko API (most reliable, free tier)**
```python
import urllib.request, json

ids = "bitcoin,ethereum,sui,solana,destra-network,aethir,io-net,superfarm,well3,tao-bot,clearpool,turbo"
url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true&include_last_updated_at=true"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
data = json.loads(urllib.request.urlopen(req, timeout=20).read().decode('utf-8'))
```
- Works for 10–12 tokens in one call
- Returns JSON or plain text "Throttled" — check before parsing
- Rate limit: ~30 calls/min but implement 6–10s delays between calls in practice

**Tier 2 — Single-Coin CoinGecko Detail (when batch misses IDs)**
```python
url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&community_data=false&developer_data=false"
```
- Wait 10–15 seconds between single calls to avoid 429
- Some tokens return 404 if not listed on free tier

**Tier 3 — CoinMarketCap Browser (when CoinGecko fails)**
```python
url = f"https://coinmarketcap.com/currencies/{token-slug}/"
# NOTE: Simple regex often fails due to JS-rendered prices
# If unable to extract from static HTML, mark as data gap
```
- Often blocked or JS-delivered — use as heuristic only
- No reliable static-price pattern across all tokens

**Tier 4 — CoinCap API (free, no auth, but DNS can fail)**
```python
url = f"https://api.coincap.io/v2/assets/{asset_id}"
```
- Asset IDs differ from CoinGecko; requires mapping table per token

**Tier 5 — Mark data gap**
If all fail, record "price unavailable" with timestamp and intended retrieval method. Do not guess prices.

### Known Token ID Mappings (2026-04 verified)
| Token | CoinGecko ID | CoinCap ID | Notes |
|-------|-------------|------------|-------|
| BTC | bitcoin | bitcoin | |
| ETH | ethereum | ethereum | |
| SUI | sui | sui | |
| SOL | solana | solana | |
| DSYNC | destra-network | destra-network | |
| ATH | aethir | aethir | |
| IO | io-net | ? | Unreliable — may require manual CMC check |
| SUPER | superfarm | superfarm | |
| WELL | well3 | well3 | Confirmed dead; mark as such |
| tao.bot | tao-bot | tao-bot | |
| CPOOL | clearpool | clearpool | |
| TURBO | turbo | turbo | |

---

## Pattern 2: RSS-First News (no auth, no CAPTCHA)

**Why:** Google/DuckDuckGo searches hit bot walls. CoinGecko website Cloudflare-blocked. RSS feeds are stable, no auth.

**CoinDesk RSS**
```bash
curl -s "https://www.coindesk.com/arc/outboundfeeds/rss/"
```
- 15–20 latest items, CDATA-wrapped titles/descriptions
- Parse with regex: `<item>(.*?)</item>` loops

**Google News RSS**
```bash
# Search query encoded
query = urllib.parse.quote("bitcoin ethereum cryptocurrency")
url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
```
- Returns 10 items; source attribution via `<source>` tag
- Titles may include HTML entities; clean with `re.sub(r'<[^>]+>', '', title)`

**CoinTelegraph RSS**
```bash
curl -s "https://cointelegraph.com/rss"
```
- Sometimes returns empty `<title>` fields; filter before display

**Parsing pattern (Python)**
```python
import urllib.request, re

def fetch_rss(url, limit=10):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        content = resp.read().decode('utf-8', errors='replace')
    items = re.findall(r'<item>(.*?)</item>', content, re.DOTALL)
    results = []
    for item in items[:limit]:
        title = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', item) or \
                re.search(r'<title>(.*?)</title>', item)
        link = re.search(r'<link>(.*?)</link>', item)
        date = re.search(r'<pubDate>(.*?)</pubDate>', item)
        results.append({
            'title': title.group(1).strip() if title else '',
            'link': link.group(1).strip() if link else '',
            'date': date.group(1).strip() if date else '',
        })
    return results
```

---

## Pattern 3: Research Output Structure (standard format)

When producing a research report for wiki ingestion, use this structure:

```
🔍 RESEARCH: {topic} — YYYY-MM-DD

---
OBSERVED FACTS (from price/API data)
- {bullet points with concrete numbers, sources, timestamps}

EXTERNAL CONTEXT (from RSS/news)
- {bullet points with date, source attribution (CoinDesk, Google News via RSS)}

INTERPRETATION
- {what the combined picture suggests — separate facts from interpretation}
- {where signals agree/disagree, contradictions noted}

OPEN QUESTIONS
- {data gaps, tokens with missing prices, unknown entry costs}
- {what info would change the assessment}

RISK FACTORS
- {specific, material risks identified: concentration, dead positions, regulatory, data quality}

---
DATA SOURCES & TIMELINESS
- Prices: CoinGecko API, fetched {timestamp}
- News: RSS feeds ({sources})
- Freshness: {note on recency}

PORTFOLIO SNAPSHOT TABLE (for portfolio research)
| Symbol | Holdings | Price | Value | 24h Chg | Entry | P&L % |
```

**Sources field in frontmatter** (for wiki raw files):
```yaml
---
source_url: N/A (internal synthesis)  # or original URL if web-extracted
ingested: YYYY-MM-DD
sha256: <body-hash>
---
```

---

## Pattern 4: Wiki Schema Adaptation for Crypto Domains

If your wiki's SCHEMA.md is AI/ML focused (model, architecture, training, etc.), extend the tag taxonomy to support crypto content:

### Before (AI/ML only)
```
- Models: model, architecture, benchmark, training
- People/Orgs: person, company, lab, open-source
- Techniques: optimization, fine-tuning, inference, alignment, data
- Meta: comparison, timeline, controversy, prediction
```

### After (with Crypto extension)
```
- Models: model, architecture, benchmark, training
- People/Orgs: person, company, lab, open-source
- Techniques: optimization, fine-tuning, inference, alignment, data, research, analysis
- Meta: comparison, timeline, controversy, prediction
- Hardware: gpu, tpu, accelerator, chip
- Frameworks: pytorch, tensorflow, jax, huggingface
- Crypto: crypto, portfolio, token, defi, layer1, compute, meme, ai-crypto
```

### Entity page tags
Use `[model, network]` for tokens like BTC, ETH, SUI, SOL (representing blockchain networks).
Use `[model]` for protocols/tokens with compute/AI narrative (ATH, DSYNC, IO, SUPER).
Use `[model, network]` for DeFi tokens (CPOOL).

**Never** use a tag not in the taxonomy — add it to SCHEMA.md first, then apply.

---

## Pattern 5: Data Gap Protocol

When a token's price is unavailable:
1. Try Tier 1 → Tier 2 → Tier 3 → Tier 4 in sequence
2. If all fail, log the gap in the research report with clear N/A marking
3. Create a `[[token]]` entity page anyway (if it's a portfolio holding), mark current price as unavailable
4. In the wiki query, include a "Data Gaps" section listing each token with unavailable data
5. Suggest user action: manual CMC check, exchange statement review, or delisting verification

**DO NOT** use stale prices or guesses. Integrity > completeness.

---

## Pattern 6: Cross-Reference Hygiene

After batch updates, verify every entity page has at least 2 outbound `[[wikilinks]]`.

Common fixes:
- Mentioning AI-narrative pressure on [[ethereum]] → add `[[ethereum]]` link
- Comparing volume decline to [[super]] → link both directions if needed
- Central concept `[[crypto-portfolio-analysis]]` should be linked from every entity page

If a page has <2 links, add:
- `[[crypto-portfolio-analysis]]` (always)
- 1–2 relevant peer tokens or conceptual anchors

---

## Pattern 7: Dead Position Detection

A token should be marked "dead"/"rug-pull" if:
- Market cap < $200K and 24h volume < $10K (conversation rate < 10%)
- Price flatlined at same value for >7 days with no trading activity
- Multiple API sources return `null` or stale data
- News search returns zero results for past 30d

Action: Mark with `⚠️ DEAD POSITION` in index.md, note in entity page, list in research "Risk Factors" with "confirmed dead" language, consider tax-loss harvesting recommendation.

---

## Pitfalls to Avoid

1. **Regex extraction from HTML** — modern crypto sites (CMC, CoinGecko) deliver prices via JavaScript. Static HTML regex will fail. Use APIs, not browser scraping.
2. **Assuming CoinGecko IDs** — verify IDs work; IO.net fails, some newer tokens missing from free tier.
3. **Skipping raw frontmatter SHA256** — add provenance to every ingested source even if synthetic.
4. **Updating entity pages without index.md refresh** — always update index and log after batch updates.
5. **Ignoring stale schema tags** — if the wiki started as AI/ML, extend taxonomy before applying crypto tags.
6. **Guessing missing entry prices** — never invent numbers; leave as "unknown" and flag for user.
7. **Markdown anchor typos** — `[[tao.bot]]` vs `[[tao-bot]]` vs `[[tao_bot]]`. Entity filename uses underscore but wikilinks can vary — document the canonical slug.

---

## Related Skills
- `crypto-portfolio`: Domain-specific portfolio workflow, holdings table, CoinGecko rate-limit strategy
- `llm-wiki`: Full wiki ingestion pipeline, frontmatter standards, cross-linking, lint protocol

---

## Revision History
- 2026-04-25: Created after successful batch research despite multiple API failures (IO.net 404, CoinCap DNS) and RSS news-only strategy. Demonstrated that research can succeed without external LLM search when constrained to RSS + price API.
