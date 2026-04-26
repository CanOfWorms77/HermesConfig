Dave (CanOfWorms77) runs Hermes Agent on a Linux VPS with minimal setup: Abacus RouteLLM (deepseek-v4-flash) primary, OpenRouter fallback. Sessions auto-prune at 30 days. 9 skills enabled (hermes-agent, multi-model-subagents, hermes-cleanup-reset, code-review, plan, subagent-driven-development, systematic-debugging, test-driven-development, writing-plans). Config git-tracked at github.com/CanOfWorms77/HermesConfig.
§
Tiered research pipeline: (1) Perplexity Sonar (free basic tier) for general fact research — use when main model needs accurate sourced info. (2) Perplexity Sonar Pro for deep/niche research. (3) DuckDuckGo (DDGS) for quick web lookups, URLs, pricing, live data. (4) Firecrawl scraper (to be configured) for deep site extraction. Perplexity key in .env, endpoint https://api.perplexity.ai/chat/completions. Sonar basic = sonar model. Sonar Pro = sonar-pro model. Deep research = sonar-deep-research model (use only when explicitly requested).
§
Primary interface: Hermes Workspace web UI. Also uses terminal and VS Code (via ACP) for coding.
§
Projects: Hermes Agent, ELISE (intelligence brief system), crypto portfolio tracking.
§
Wants subagents used for multi-step tasks to keep main context lean (~11K token baseline).
§
Interested in crypto meme coin early detection. Pump.fun + DexScreener + Birdeye stack for new token scanning. BELKA contract: 4df1wZoygsynEZ6XmpcoabrVwv7nBgjHLyCns5xApump.