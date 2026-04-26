#!/bin/bash
# Smart LLM Router — Daily Model Discovery Cron
# Probes free models across providers, benchmarks them, updates config,
# and restarts the proxy if the config changed.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$HOME/.hermes/skills/smart-llm-router/config.yaml"
PYTHON="$HOME/.hermes/hermes-agent/venv/bin/python"
MANAGER="$PYTHON $SCRIPT_DIR/manage_proxy.py"

# Backup current config
cp "$CONFIG" "$CONFIG.bak.$(date +%s)"

# Run discovery for free/low tiers (where models change most often)
$PYTHON "$SCRIPT_DIR/discover_models.py" \
    --config "$CONFIG" \
    --tier all \
    --providers openrouter,groq,nvidia \
    --max-per-tier 2 \
    --concurrency 4 \
    >> "$HOME/.hermes/skills/smart-llm-router/discovery.log" 2>&1

# Check if config changed
if ! diff -q "$CONFIG" "$CONFIG.bak."* >/dev/null 2>&1; then
    echo "Config changed. Restarting proxy..."
    $MANAGER restart
else
    echo "Config unchanged. No restart needed."
fi

# Clean up old backups (keep last 7)
ls -t "$HOME/.hermes/skills/smart-llm-router/config.yaml.bak."* 2>/dev/null | tail -n +8 | xargs -r rm -f
