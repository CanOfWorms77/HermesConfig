---
name: self-capability-assessment-and-current-info-retrieval
description: Skill for assessing capabilities and retrieving current info when knowledge is outdated
parameters: []
---
# Self-Capability Assessment and Current Info Retrieval

Use this skill when you need to correctly assess your own capabilities and limitations, particularly when there's a mismatch between what you think you can do and what you're actually able to do.

## Core behavior

For this turn:
- Acknowledge your internal knowledge boundaries (e.g., training data cutoff dates)
- Accept corrections about capability misconceptions from users or external sources
- Use appropriate tools (browser, search, file operations, etc.) to gather current evidence when needed
- Verify findings through multiple sources before accepting them as fact
- Update your persistent memory or skills with verified information for future use
- Apply your corrected understanding to future similar tasks

## Output requirements

Provide a clear assessment that includes:
- What you initially thought you could/couldn't do
- What you learned about your actual capabilities
- What tools you used to gather current information
- How you updated your understanding
- How this changes your approach to similar future tasks

## Save location

Save this skill with `skill_manage` using:
- `action`: "create"
- `name`: "self-capability-assessment-and-current-info-retrieval"
- `category`: "mlops" (or another appropriate category)

## Interaction style

- If you realize you misunderstood your capabilities, acknowledge it openly
- When corrected, thank the person and adjust your understanding immediately
- After gathering current evidence, share what you learned and how it changed your approach
- Apply this corrected framework to future similar situations automatically