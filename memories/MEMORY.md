Dave (CanOfWorms77) runs Hermes Agent on a Linux VPS with minimal setup: Abacus RouteLLM (deepseek-v4-flash) primary, OpenRouter fallback. Sessions auto-prune at 30 days. 9 skills enabled (hermes-agent, multi-model-subagents, hermes-cleanup-reset, code-review, plan, subagent-driven-development, systematic-debugging, test-driven-development, writing-plans). Config git-tracked at github.com/CanOfWorms77/HermesConfig.
§
Uses Perplexity Sonar API for web research (Pro subscription). Key in .env. Endpoint: https://api.perplexity.ai/chat/completions. Prefer Sonar Pro for crypto/niche research over DDGS.
§
Primary interface: Hermes Workspace web UI. Also uses terminal and VS Code (via ACP) for coding.
§
Projects: Hermes Agent, ELISE (intelligence brief system), crypto portfolio tracking.
§
Wants subagents used for multi-step tasks to keep main context lean (~11K token baseline).
§
Interested in crypto meme coin early detection. Pump.fun + DexScreener + Birdeye stack for new token scanning. BELKA contract: 4df1wZoygsynEZ6XmpcoabrVwv7nBgjHLyCns5xApump.