# skill: elise-research

## Purpose
Deep-dive analysis on a specific asset, narrative, or question.

## Trigger
Dave says /research {topic} or asks for analysis on something specific.

## Process
1. Query all ELISE signals related to {topic} (last 7 days)
2. Query narrative scores if topic is a narrative
3. Query price history if topic is an asset
4. Query related news items (last 7 days, limit 20)
5. Call Perplexity Sonar: "{topic} crypto analysis latest developments"
6. Call Perplexity Sonar: "{topic} crypto risks concerns"
7. Synthesise into structured analysis

## Output Format
🔍 RESEARCH: {topic}

OBSERVED FACTS (from ELISE data)
- {bullet points of what the data shows}

EXTERNAL CONTEXT (from Perplexity)
- {bullet points from web search, with source attribution}

INTERPRETATION
- {what the combined picture suggests}
- {where signals agree/disagree}

OPEN QUESTIONS
- {what we don't know, what would change the picture}

RISK FACTORS
- {specific risks identified}

## Rules
- Separate facts from interpretation explicitly
- Never present interpretation as fact
- Always note data gaps or staleness
- Max 5 Perplexity searches per research session
- If Dave asks about something ELISE doesn't track, say so and offer web-only research