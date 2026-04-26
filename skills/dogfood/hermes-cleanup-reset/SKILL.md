---
name: hermes-cleanup-reset
category: dogfood
description: Clean up a running Hermes Agent installation — wipe accumulated session bloat, diagnose prompt token overhead, fix credential cache corruption, and rebuild with minimal config. For when the agent has been running through many model/provider switches and accumulated too much dead weight.
version: 1.0.0
---

## When to Use

This skill covers the general class: **"Hermes is slow, costs too many tokens, or has accumulated too much cruft from switching models/providers multiple times."**

Trigger conditions:
- API calls to providers keep returning 403/unauthorized even though the API key is correct
- Prompt tokens per call are 10,000+ for a simple "hi" message
- The credential pool has multiple entries marked "exhausted" with stale tokens
- Config.yaml has 5+ providers but you only use 1-2
- Session storage is 50+ MB with hundreds of old sessions
- You've been through several model/provider switches without cleaning up

## Diagnosis: Find the Token Bloat

First, measure the actual per-call token cost. Make a curl request to the gateway API server (port 8642 by default):

```bash
curl -s -w '\n%{http_code}' -H "Authorization: Bearer $(grep API_SERVER_KEY ~/.hermes/.env | cut -d= -f2)" \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"hi"}],"model":"<your-model>","max_tokens":3}' \
  http://localhost:8642/v1/chat/completions
```

If prompt tokens > 5,000 for a single "hi", diagnose the sources:

### Check skills snapshot bloat
The skills snapshot file injects descriptions of ALL installed skills into the system prompt (~58KB):

```bash
ls -la ~/.hermes/.skills_prompt_snapshot.json
cat ~/.hermes/.skills_prompt_snapshot.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(str(d))} chars')"
```

### Check model-fallback skill overhead
If `hermes skills list | grep model-fallback` shows it enabled, it wraps `chat_completion` via Python. Every API call goes through the fallback chain logic:

```bash
cat ~/.hermes/skills/model-fallback/model_fallback.py | head -25
```

### Check session search DB size
```bash
ls -lh ~/.hermes/state.db*
python3 -c "
import sqlite3
c = sqlite3.connect('$HOME/.hermes/state.db')
t = c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()
for table in t:
    count = c.execute(f'SELECT COUNT(*) FROM \"{table[0]}\"').fetchone()[0]
    print(f'  {table[0]}: {count} rows')
"
```

### Check credential health
```bash
python3 -c "
import json
d = json.load(open('$HOME/.hermes/auth.json'))
for pool, entries in d.get('credential_pool', {}).items():
    for e in entries[:1]:
        s = e.get('last_status','?')
        err = (e.get('last_error_message') or '')[:60]
        print(f'  {pool}: status={s} err={err}')
print(f'Active provider: {d.get(\"active_provider\")}')
"
```

## Procedure: Clean Reset

### Step 1: Backup first
```bash
BACKUP_DIR=~/hermes-backup-$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
cp -r ~/.hermes/.env $BACKUP_DIR/.env              # API keys
cp -r ~/.hermes/auth.json $BACKUP_DIR/auth.json    # Credential cache
cp -r ~/.hermes/skills $BACKUP_DIR/skills          # Custom skills
cp -r ~/.hermes/memories $BACKUP_DIR/memories      # Agent memories
cp -r ~/.hermes/cron $BACKUP_DIR/cron              # Cron jobs
cp ~/.hermes/config.yaml $BACKUP_DIR/config.yaml   # Config reference
```

For a full snapshot:
```bash
tar -czf $BACKUP_DIR/hermes-full-backup.tar.gz -C ~ .hermes
```

### Step 2: Stop the gateway
```bash
hermes gateway stop
# Kill any stale gateway processes
ps aux | grep -E "hermes.*gateway" | grep -v grep
kill <PID>  # if any remain
rm -f ~/.hermes/gateway.lock ~/.hermes/gateway.pid
```

### Step 3: Wipe accumulated data
```bash
# Session history (major token bloat source)
rm -rf ~/.hermes/sessions/*
rm -rf ~/.hermes/state.db*  # SQLite search index

# Checkpoints and cache
rm -rf ~/.hermes/checkpoints/*
rm -rf ~/.hermes/cache/*
rm -rf ~/.hermes/logs/*

# Stale config files
rm -f ~/.hermes/config.yaml
rm -f ~/.hermes/auth.json
rm -f ~/.hermes/.skills_prompt_snapshot.json
rm -f ~/.hermes/models_dev_cache.json
rm -f ~/.hermes/gateway_state.json
rm -f ~/.hermes/response_store.db

# Keep: .env, skills/, memories/, cron/
```

### Step 4: Rebuild minimal config.yaml
Write a clean config with ONLY active providers. Key principles:
- One primary provider + 1 fallback maximum
- Use `key_env:` not `api_key:` for env-var-based API keys (prevents cache corruption)
- Set `sessions.auto_prune: true` and `sessions.retention_days: 30` to prevent future bloat

Example for Abacus RouteLLM:
```yaml
model:
  provider: abacus
  default: deepseek-v4-flash
providers:
  abacus:
    api: https://routellm.abacus.ai/v1
    name: Abacus.ai (RouteLLM)
    key_env: ROUTELLM_API_KEY    # NOT api_key — prevents literal string caching
    default_model: deepseek-v4-flash
  openrouter:
    api: https://openrouter.ai/api/v1
    name: OpenRouter
    api_key: OPENROUTER_API_KEY
    default_model: qwen/qwen3.6-plus-preview:free
```

### Step 5: Fix credential cache (if needed)
If auth.json exists and has stale entries, clear the problematic pools:

```bash
python3 -c "
import json
d = json.load(open('$HOME/.hermes/auth.json'))
# Remove problematic pools
d['credential_pool'].pop('custom:abacus.ai', None)
d['credential_pool'].pop('abacus', None)
d['active_provider'] = 'abacus'  # set to your primary
json.dump(d, open('$HOME/.hermes/auth.json', 'w'), indent=2)
"
```

### Step 6: Restart gateway
```bash
hermes gateway start
sleep 10
hermes gateway status  # Should show "active (running)"
```

### Step 7: Verify
```bash
# Test API call
curl -s -w '\n%{http_code}' -H 'Authorization: Bearer <KEY>' \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"hi"}],"model":"<model>","max_tokens":3}' \
  http://localhost:8642/v1/chat/completions

# Check skills loaded
hermes skills list | grep model-fallback
```

### Step 8: Initialize git (recommended — do this now)
```bash
cd ~/.hermes
git init
git config user.email "you@example.com"
git config user.name "Your Name"
# Create .gitignore
cat > .gitignore << 'EOF'
# Secrets and auto-generated
.env
auth.json
channel_directory.json
*.lock
# Session data (regenerated)
sessions/*
!sessions/.gitkeep
checkpoints/*
!checkpoints/.gitkeep
cache/*
!cache/.gitkeep
logs/*
!logs/.gitkeep
# Runtime state
state.db*
*.db-shm
*.db-wal
response_store.db
processes.json
tasks.json
gateway_state.json
# Temp/generated
*.pyc
__pycache__/
.skills_prompt_snapshot.json
models_dev_cache.json
ollama_cloud_models_cache.json
.hermes_history
EOF
git add config.yaml skills/ cron/ memories/ .gitignore SOUL.md
git commit -m "Initial commit: clean Hermes config"
git remote add origin <your-github-repo-url>
git push -u origin main
```

## Token Bloat Diagnosis Reference

| Symptom | Likely Source | Fix |
|---------|--------------|-----|
| 13K+ tokens for "hi" | Skills snapshot (58KB) sysprompt injection | Use `skills.disabled` list in config.yaml (non-destructive) OR remove unused skill dirs |
| 10K+ growing per turn | Session history in context | Enable auto_prune in config or set retention_days lower |
| 403 errors with correct API key | Credential pool cached literal env-var name | Clear stale pool entries, use key_env instead of api_key in config |
| Varying token counts | model-fallback tries multiple models per call | Disable skill: `hermes skills config` or add to disabled list |
| 20M+ state.db | Months of session search index | Delete state.db (auto-rebuilds) |

## Pitfalls

- **auth.json will NOT exist on first startup** after wipe — the gateway creates it on first successful API call. Don't panic if it's missing.
- **model-fallback skill** wraps `chat_completion` — every call goes through a Python function. This adds latency but minimal token overhead. Consider disabling if you have a stable provider.
- **Skills snapshot auto-regenerates** after gateway restart. Deleting `.skills_prompt_snapshot.json` only helps until next restart. To permanently reduce it, **use the `skills.disabled` list in config.yaml** (recommended, non-destructive) or remove skill directories you don't use. The `build_skills_system_prompt()` function in `agent/prompt_builder.py` properly filters disabled skills — they remain in the cache file but are excluded from the injected system prompt. Disabled = not in prompt. Deleting = gone forever. Prefer disabling.
- **Typical cost breakdown** for context: ~11K tokens per fresh call ≈ $0.0017 on RouteLLM DeepSeek V4 Flash. A full 400-message session ≈ 200 API calls ≈ $0.34. If costs seem high, check: (1) session history growing unbounded (set `sessions.retention_days: 30`), (2) too many enabled skills in the prompt (use `skills.disabled`), (3) the model being routed through an expensive tier (check `provider` in config). The `build_skills_system_prompt()` function properly filters disabled skills — they're still in the snapshot file (cached) but excluded from the injected system prompt.
- **Disabling skills via config is better than deleting them** — you can re-enable any skill later with a single config edit. The system prompt only includes enabled skills (verified against the prompt builder code).
- **Git init is now required after cleanup** to track the clean state. See Step 8.
- **.env is NOT loaded by systemd** — the gateway unit file (`~/.config/systemd/user/hermes-gateway.service`) only has `Environment` directives for PATH/VIRTUAL_ENV/HERMES_HOME. If using `key_env`, the gateway reads from process env, so ensure `.env` is sourced. Use `hermes gateway start` (not systemctl directly) which handles this.
- **Old gateway process may linger** after stop. Always check: `ps aux | grep "hermes.*gateway"` and kill remaining processes before starting fresh. Use `hermes gateway run --replace` if needed.
