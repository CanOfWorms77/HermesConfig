# skill: elise-signal-review

## Purpose
Weekly retrospective on signal quality, false positives, and system improvements.

## Trigger
- Cron: Sunday 10:00
- Manual: Dave says /signal-review

## Process
1. Query all signals from the last 7 days
2. For each signal, check if the predicted direction materialised:
   - Compare signal direction vs actual price movement 24-48h after signal
   - Check if narrative heat predictions aligned with subsequent news
3. Categorise signals: CORRECT, INCORRECT, INCONCLUSIVE, FALSE_POSITIVE
4. Identify patterns in false positives
5. Check if any threshold adjustments are needed
6. Review your own brief quality from the week

## Output Format
📋 WEEKLY SIGNAL REVIEW — Week of {date}

SIGNAL SCORECARD
Total signals: {n}
Correct: {n} ({%})
Incorrect: {n} ({%})
Inconclusive: {n} ({%})
False positives: {n} ({%})

TOP PERFORMERS
{signals that correctly predicted outcomes}

FALSE POSITIVES
{signals that fired but shouldn't have, with analysis of why}

THRESHOLD RECOMMENDATIONS
{suggest specific changes to alert thresholds or signal parameters}
{e.g., "3% 5-minute crash threshold fired 4 times this week, all recovered within 2h. Consider raising to 4%."}

SKILL IMPROVEMENTS
{note any changes you're making to your own brief/research skills}
{e.g., "Adding BTC dominance context to morning briefs — correlated with 3 missed signals this week."}

ELISE CODE SUGGESTIONS (for Dave's review)
{any daemon-side changes that would improve signal quality}
{NEVER apply these yourself — present them for Dave to review}

## Memory Updates
After completing the review, save key findings to memory:
- "[date] Signal accuracy: {%} correct, {%} false positive"
- "[date] Threshold note: {specific finding}"
- "[date] Pattern: {any recurring pattern discovered}"