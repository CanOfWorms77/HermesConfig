# skill: elise-intelligence-brief

## Purpose
Generate a concise crypto intelligence brief from ELISE's live database.

## Trigger
- Cron: 09:00 and 18:00 daily
- Manual: Dave says /brief or asks for a brief

## Process
1. Query active signals (last 12h for morning, last 8h for evening)
2. Query narrative heat scores for today
3. Query price changes for held assets (BTC, ETH, SUI, ONDO, TAO)
4. Query holdings with current P&L
5. Query top 5 recent news items by relevancy
6. For any signal with strength > 70, call Perplexity Sonar for context
7. Synthesise into brief format below

## Brief Format
📊 ELISE INTELLIGENCE BRIEF — {date} {morning/evening}

🗂️ PORTFOLIO
{each holding: symbol, current_price, 24h_change%, P&L%}
Total value: ${total}

🚦 ACTIVE SIGNALS ({count} in last {hours}h)
{for each signal strength > 50, sorted by strength:}
  [{strength}] {signal_type} — {asset_symbol or narrative_id}
  {reasoning}
  {if perplexity context available: "Context: {1-sentence summary}"}

🌡️ NARRATIVE HEAT
{for each narrative with heat_status in HEATING/PEAK:}
  {display_name}: {heat_status} ({heat_score})

📰 KEY NEWS
{top 5 news items: title — source — matched narratives}

🧠 SYNTHESIS
{2-3 sentences: what matters right now, what correlates, what to watch}
{if any signals align with each other, note the convergence}
{if nothing notable: "Markets quiet. No actionable convergence detected."}

## Rules
- No hype. No financial advice. Facts and uncertainty only.
- Corroboration required: only flag high-conviction when 2+ signal types align
- Always cite which signals support each observation
- If ELISE data is stale (no signals in 6h+), say so explicitly
- Budget: max 3 Perplexity searches per brief