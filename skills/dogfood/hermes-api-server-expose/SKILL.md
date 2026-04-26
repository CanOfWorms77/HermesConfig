---
name: hermes-api-server-expose
description: Expose the Hermes API server externally (or to other apps) by configuring the gateway's built-in API adapter. Covers bind address, authentication, testing, and common pitfalls.
version: 1.0.0
tags: [hermes, api, gateway, expose, external, openai-compatible]
---

# Expose Hermes API Server

Hermes gateway includes a built-in API server adapter that exposes an OpenAI-compatible REST API. Other apps (web UIs, scripts, external services) can call Hermes through it.

## Prerequisites

Already configured if these environment variables are set:
- API_SERVER_ENABLED=true
- API_SERVER_KEY=<your_key>

Check with: grep API_SERVER ~/.hermes/.env

## Expose Externally

The bind address is controlled by environment variable only -- NOT config.yaml.

Step 1: Add API_SERVER_HOST=0.0.0.0 to ~/.hermes/.env

WARNING: `hermes config set api_server.host 0.0.0.0` writes to config.yaml but does NOT work. The gateway reads API_SERVER_HOST from env vars only (see gateway/config.py).

Step 2: Restart the gateway:
  hermes gateway restart

Step 3: Verify bind:
  ss -tlnp | grep 8642
  Should show: 0.0.0.0:8642 (not 127.0.0.1:8642)

## Testing

  curl -s http://YOUR_IP:8642/
  # Returns "404: Not Found" if running (not an error)

  curl -X POST \
    -H "Authorization: Bearer YOUR_API_SERVER_KEY" \
    -H "Content-Type: application/json" \
    http://YOUR_IP:8642/v1/chat/completions \
    -d '{"model":"gpt-4","messages":[{"role":"user","content":"hello"}]}'

## Configuration Reference

All settings via environment variables in ~/.hermes/.env:

- API_SERVER_ENABLED (default: false) -- Enable the API server adapter
- API_SERVER_KEY -- Bearer token for auth
- API_SERVER_HOST (default: 127.0.0.1) -- Bind address (0.0.0.0 for external)
- API_SERVER_PORT (default: 8642) -- Listen port
- API_SERVER_CORS_ORIGINS -- Comma-separated allowed origins
- API_SERVER_MODEL_NAME -- Override model name in responses

## Security

- API is protected by bearer token (API_SERVER_KEY)
- No firewall rules are auto-configured
- For production: consider UFW allow rules, nginx reverse proxy with HTTPS, or IP allowlisting

## Common Pitfalls

1. Config.yaml host setting is ignored -- must use API_SERVER_HOST env var
2. Gateway crashes on restart if conflicting processes exist -- kill stale processes first:
     pkill -f "hermes_cli.main gateway" 2>/dev/null; sleep 2; hermes gateway start
3. Exit code 75 (TEMPFAIL) -- usually port conflict or WhatsApp bridge issue. Check with:
     journalctl --user -u hermes-gateway.service
4. 404 on root path is normal -- API only responds on specific endpoints like /v1/chat/completions
