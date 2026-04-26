# skill: elise-opportunity-bundler

## Purpose
Detect when multiple signals converge on the same asset or narrative, suggesting a high-conviction opportunity.

## Trigger
- Run during morning brief when 3+ signals with strength > 60 exist for the same target
- Manual: Dave says /opportunities

## Process
1. Query signals from last 48h with strength > 60
2. Group by asset_symbol and narrative_id
3. For each cluster with 3+ signals:
   a. Check signal diversity (different types = higher conviction)
   b. Check direction alignment (all bullish/bearish = higher conviction)
   c. Call Perplexity: "{asset} opportunity analysis crypto"
   d. Score conviction 0-100:
      - Base: 40 (for having 3+ signals)
      - +10 per additional signal type represented
      - +10 if all directions align
      - +10 if Perplexity context supports thesis
      - -20 if Perplexity finds contradicting information
4. Only surface opportunities with conviction > 70

## Output Format
🎯 OPPORTUNITY: {asset or narrative}
Conviction: {score}/100
Signals: {n} aligned ({list signal types})
Direction: {BULLISH/BEARISH}
Thesis: {2-sentence synthesis of why signals converge}
Counter: {1-sentence devil's advocate}
Watch: {what would invalidate this — specific price level or event}

## Rules
- This is observation, NOT financial advice
- Dave decides. You observe and report.
- Never use urgency language ("act now", "don't miss")
- Always include the counter-argument
- Always include invalidation criteria