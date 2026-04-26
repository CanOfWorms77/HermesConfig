---
name: gateway-systemd-env
description: Fix Hermes Gateway platform connections when running as a systemd user service by loading environment variables from ~/.hermes/.env
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [gateway, systemd, deployment, troubleshooting, platforms]
    related_skills: [hermes-agent]
---

# Systemd Environment File for Hermes Gateway

## When to Use

Use this skill when:
- Hermes Gateway is installed as a systemd user service (`hermes-gateway.service`)
- Platform adapters (Telegram, Discord, Slack, etc.) fail to connect despite tokens being present in `~/.hermes/.env`
- The gateway process environment lacks expected `*_BOT_TOKEN` variables
- `gateway_state.json` shows platforms as `disconnected` or `unknown`
- No platform connection logs appear in journalctl

## Problem Diagnosis

The Hermes Gateway systemd unit does **not** automatically load environment variables from `~/.hermes/.env`. The Python code calls `load_hermes_dotenv()` at runtime, but under systemd's minimal environment this can fail silently or load too late for platform initialization.

**Symptoms:**
- `TELEGRAM_ENABLED=true` in `.env` but Telegram never connects
- `/proc/<pid>/environ` missing `TELEGRAM_BOT_TOKEN` or `DISCORD_BOT_TOKEN`
- No `[Telegram] Connected` or similar logs
- Platform state in `gateway_state.json` stays `"disconnected"` or `"unknown"`

## Solution: Add EnvironmentFile to Systemd Unit

1. **Edit the systemd user service file:**
   ```bash
   nano ~/.config/systemd/user/hermes-gateway.service
   ```

2. **Add `EnvironmentFile` directive after `HERMES_HOME`:**
   ```ini
   [Service]
   Environment="HERMES_HOME=/root/.hermes"
   EnvironmentFile=/root/.hermes/.env
   Restart=on-failure
   ```
   Use absolute path. Adjust path if HERMES_HOME differs.

3. **Reload systemd daemon and restart gateway:**
   ```bash
   systemctl --user daemon-reload
   hermes gateway restart
   ```

4. **Verify the fix:**
   - Check process environment:
     ```bash
     cat /proc/$(cat ~/.hermes/gateway.pid)/environ | tr '\0' '\n' | grep -i telegram
     ```
     Should show `TELEGRAM_BOT_TOKEN=<your_token>` and `TELEGRAM_ENABLED=true`.

   - Check gateway state:
     ```bash
     hermes gateway status
     ```
     Should show platforms as connected, or:
     ```bash
     cat ~/.hermes/gateway_state.json | jq '.platforms.telegram.state'
     # => "connected"
     ```

   - Check logs for connection messages:
     ```bash
     journalctl --user -u hermes-gateway -n 50 | grep -i 'telegram'
     ```
     Look for `[Telegram] Connected` or polling started.

## Why This Works

`EnvironmentFile` instructs systemd to parse `KEY=VALUE` lines from the specified file and inject them into the service's environment **before** launching the process. This ensures all platform tokens are present from the earliest startup, allowing `_apply_env_overrides()` in `gateway/config.py` to read them and the platform adapters to initialize successfully.

## Affected Platforms

Any platform that reads a token from environment variables:
- Telegram → `TELEGRAM_BOT_TOKEN`
- Discord → `DISCORD_BOT_TOKEN`
- Slack → `SLACK_BOT_TOKEN` (and `SLACK_APP_TOKEN`)
- And others (check `gateway/config.py::_apply_env_overrides`)

## Common Pitfalls

- **Forgot `daemon-reload`**: After editing the unit, systemd won't pick up changes without `systemctl --user daemon-reload`.
- **Wrong `.env` path**: Must be absolute. Use `$HERMES_HOME/.env` or explicit `/root/.hermes/.env`.
- **Missing `enabled: true`**: In addition to the token env var, you still need either `TELEGRAM_ENABLED=true` in `.env` or `platforms.telegram.enabled: true` in `config.yaml`. The `EnvironmentFile` approach typically sets both.
- **Old process still running**: Stop the service first: `hermes gateway stop` before editing and reloading.
- **Linger not enabled**: If you want the gateway to survive logout, enable linger: `sudo loginctl enable-linger $USER`. (Not strictly required for this fix.)

## Verification Checklist

- [ ] Systemd unit contains `EnvironmentFile=/root/.hermes/.env`
- [ ] `systemctl --user daemon-reload` completed successfully
- [ ] Gateway service restarted without errors
- [ ] `ps` shows gateway process running
- [ ] `cat /proc/$(cat ~/.hermes/gateway.pid)/environ | grep TELEGRAM` shows `TELEGRAM_BOT_TOKEN`
- [ ] `~/.hermes/gateway_state.json` shows `"telegram": {"state": "connected", ...}`
- [ ] `journalctl --user -u hermes-gateway` contains `[Telegram]` connection messages

## Related Files

- Systemd unit: `~/.config/systemd/user/hermes-gateway.service`
- Hermes env: `~/.hermes/.env`
- Gateway config: `~/.hermes/config.yaml` (`platforms.telegram.enabled` must be true)
- Gateway state: `~/.hermes/gateway_state.json`
- Logs: `~/.hermes/logs/gateway.log` and `journalctl --user -u hermes-gateway`
