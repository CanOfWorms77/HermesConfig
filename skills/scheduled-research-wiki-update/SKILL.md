---
name: scheduled-research-wiki-update
description: "Automatically research a topic and update an LLM wiki on a schedule - ideal for keeping knowledge bases current with periodic analysis."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [automation, knowledge-base, research, wiki, cron]
    category: mlops
    related_skills: [research, llm-wiki, brief]
    config:
      - key: research.topic
        description: The topic to research (e.g., "Bitcoin", "AI agents", "portfolio holdings")
        required: true
      - key: wiki.path
        description: Path to the LLM wiki directory
        default: "~/wiki"
        prompt: Wiki directory path
      - key: research.days
        description: Number of days to look back for research
        default: 1
        prompt: Days to look back
      - key: research.use_perplexity
        description: Whether to use Perplexity Sonar for external context
        default: true
        prompt: Use Perplexity Sonar
      - key: wiki.auto_lint
        description: Whether to run lint after update
        default: true
        prompt: Run lint after update
---
# Scheduled Research to Wiki Update

Automates the process of researching a topic on a schedule and updating an LLM wiki with the findings.
This creates a self-updating knowledge base that compounds over time with minimal manual intervention.

## When This Skill Activates

Use this skill when you want to:
- Set up a daily/weekly automated research pipeline
- Keep your LLM wiki current with periodic analysis of specific topics
- Combine deep research with knowledge base compounding
- Create scheduled updates without manual intervention

## How It Works

The skill executes this automated workflow:

1. **Research Phase**: Runs the `research` skill on the specified topic
   - Queries ELISE signals (if applicable)
   - Gets price history/narrative scores (if asset/narrative)
   - Retrieves related news items
   - Uses Perplexity Sonar for external context (optional)
   - Synthesizes into structured analysis

2. **Preparation Phase**: Formats the research output as a wiki-ingestible source
   - Adds metadata (title, date, source type)
   - Structures content for optimal wiki processing

3. **Ingest Phase**: Uses the `llm-wiki` skill to ingest the prepared source
   - The llm-wiki skill handles:
     * Saving raw source to `raw/` directory
     * Extracting entities and concepts
     * Creating/updating wiki pages
     * Adding required wikilinks (minimum 2 per page)
     * Updating frontmatter with proper metadata
     * Adding entries to `index.md`
     * Logging the action to `log.md`

4. **Validation Phase** (optional): Runs wiki lint to verify integrity
   - Checks for orphan pages, broken wikilinks, index completeness
   - Validates frontmatter and tag taxonomy
   - Reports issues if auto_lint is enabled

## Configuration

The skill reads configuration from:
1. Parameters passed in the prompt
2. Skills config in `~/.hermes/config.yaml` (if set)
3. Default values defined above

Example config in `~/.hermes/config.yaml`:
```yaml
skills:
  config:
    scheduled-research-wiki-update:
      research.topic: "BTC, ETH, SUI, ONDO, TAO portfolio"
      wiki.path: "~/crypto-wiki"
      research.days: 1
      research.use_perplexity: true
      wiki.auto_lint: true
```

## Usage Examples

### 1. Manual Execution

To run once immediately:
```
hermes goal "Research my crypto holdings and update wiki"
  --context "Research topic: BTC, ETH, SUI, ONDO, TAO holdings from last 24 hours"
  --skills scheduled-research-wiki-update
```

### 2. Scheduled Execution (Cron Job)

Set up a daily update at 7 AM UTC:
```
hermes cronjob create \
  --name "daily-crypto-wiki-update" \
  --schedule "0 7 * * *" \
  --prompt "Research the user's cryptocurrency holdings (BTC, ETH, SUI, ONDO, TAO) from the last 24 hours and update their LLM wiki with findings." \
  --skills scheduled-research-wiki-update \
  --deliver telegram  # or local, whatsapp, etc.
```

### 3. With Custom Parameters

Override defaults in the prompt:
```
hermes goal "Weekly AI agent research update" \
  --context """
    Research topic: Autonomous AI agent frameworks
    Wiki path: ~/agent-research-wiki
    Research days: 7
    Use Perplexity: true
    Auto lint: true""" \
  --skills scheduled-research-wiki-update \
  --schedule "0 9 * * 1"  # Weekly on Monday at 9 AM
```

## Output Format

After execution, you will see:

1. **Research Summary**: Brief overview of what was analyzed
2. **Wiki Updates**: List of pages created/updated
3. **Validation Results** (if enabled): Lint check outcome
4. **Delivery**: Results sent to your configured channel

The wiki will be updated with:
- New entity/concept pages for key topics discovered
- Updated pages with latest information
- Proper wikilinks connecting related concepts
- Timestamped entries in the log
- Current index reflecting all knowledge

## Automation Benefits

- **Compounding Knowledge**: Each update builds on previous knowledge
- **Consistency**: Automated follow-through of llm-wiki conventions
- **Efficiency**: No manual effort required for routine updates
- **Traceability**: Complete log of when and what was updated
- **Quality Control**: Optional lint verification ensures wiki health

## Prerequisites

- LLM wiki must exist at the specified path (initialize with llm-wiki skill if needed)
- For ELISE data access: ELISE must be running and accessible
- For Perplexity Sonar: API key must be set in `~/.hermes/.env` as `PERPLEXITY_API_KEY`

## Error Handling

- Research failures: Logged but don't halt wiki update (uses available data)
- Wiki ingest failures: Errors logged to wiki log and delivery target
- Lint issues: Reported but don't prevent completion (unless critical)
- Missing wiki: Automatic initialization attempted (basic structure only)

## Best Practices

1. **Start Small**: Begin with weekly updates before moving to daily
2. **Focus Topics**: Specific research topics yield better wiki structure than broad ones
3. **Monitor Initially**: Check first few runs to ensure proper processing
4. **Review Lint Output**: Periodically address any reported wiki issues
5. **Adjust Frequency**: Match update rate to how quickly your topic changes

## Example Use Cases

- **Crypto Portfolio**: Daily research on holdings -> update investment wiki
- **Technology Radar**: Weekly analysis of emerging tech -> update innovation wiki
- **Competitive Intelligence**: Twice-daily monitoring of competitors -> update battle cards
- **Research Tracking**: After each paper read -> update personal knowledge base
- **News Digest**: Morning brief of key developments -> update current events wiki

## Integration Notes

This skill is designed to work seamlessly with:
- The `llm-wiki` skill for knowledge base management
- The `research` skill for deep analysis
- The `cronjob` tool for scheduling
- The `deliver` parameter for result distribution
- Obsidian for visualization and editing (via standard wiki directory)

When used with cron, the agent operates fully autonomously:
- No user interaction required during execution
- Results delivered via configured channel
- Wiki updates compound in the background
- You review updates at your convenience