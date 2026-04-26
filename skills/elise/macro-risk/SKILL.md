# skill: elise-macro-risk

## Purpose
Assess macro-level risk factors that could affect Dave's portfolio.

## Trigger
- Run as part of morning brief
- When any macro-tagged news item has relevancy_score > 8
- Manual: Dave says /macro

## Process
1. Query recent news with narrative matching "macro" or "regulation" (last 24h)
2. Call Perplexity: "crypto market macro risk factors today" (recency: day)
3. Assess: Fed decisions, regulatory actions, geopolitical events, stablecoin news
4. Map risks to affected narratives in ELISE (ai_infra, depin, rwa, l1, etc.)
5. Map risks to Dave's specific holdings (BTC, ETH, SUI, ONDO, TAO)

## Output Format
⚠️ MACRO RISK ASSESSMENT

Risk Level: {LOW / ELEVATED / HIGH}

Active Factors:
{bullet list of macro factors with source}

Portfolio Impact:
{which of Dave's holdings are most exposed and why}

Affected Narratives:
{which ELISE-tracked narratives are impacted}

## Rules
- Require 2+ corroborating sources before raising to HIGH
- Never single-headline panic
- LOW is the default — only escalate with evidence
- Always note uncertainty and what you don't know