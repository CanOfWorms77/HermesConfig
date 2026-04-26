---
name: hermes-web-frontend
description: Set up a web UI for Hermes Agent using Hermes Workspace (third-party project). Includes installing the WebAPI backend, configuring the frontend, and connecting to existing Hermes setup.
version: 1.0.0
author: Hermes Agent
tags: [web, frontend, ui, workspace, webapi]
---

# Hermes Web Frontend Setup

Hermes Workspace is a third-party web UI for Hermes Agent with chat, terminal, file browser, memory viewer, and skills inspector. Built for the Nous Research hackathon.

## Project Links

- **Frontend**: https://github.com/outsourc-e/hermes-workspace
- **Backend (forked hermes-agent)**: https://github.com/outsourc-e/hermes-agent

## What Hermes Workspace Provides

- Chat interface with real-time SSE streaming
- File browser
- Terminal panel
- Memory viewer/editor
- Skills browser (2000+ skills)
- 8 themes (light/dark variants)
- Mobile PWA (install as app)
- Security with auth and approval prompts

## Architecture

Hermes Workspace requires a **WebAPI backend** that the upstream Hermes doesn't have yet. The WebAPI is a FastAPI server providing:
- Chat streaming (SSE)
- Session management
- Memory endpoints
- Skills endpoints
- Config endpoints

## Integration Options

### Option 1: Use the Fork (Easiest)

Clone the forked hermes-agent with WebAPI built-in:

```bash
# Clone the fork with WebAPI support
git clone https://github.com/outsourc-e/hermes-agent.git
cd hermes-agent
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Run setup with your existing config
hermes setup

# Start the WebAPI server
hermes webapi
# Or: uvicorn webapi.app:app --host 0.0.0.0 --port 8642
```

### Option 2: Add WebAPI to Existing Hermes (Advanced)

Extract just the `webapi/` module from the fork and add to your existing Hermes installation:

1. Clone the fork temporarily
2. Copy the `webapi/` directory to your hermes-agent
3. Add CLI entry point for `hermes webapi`
4. Install FastAPI dependencies: `pip install fastapi uvicorn`

The WebAPI module structure:
- `webapi/app.py` - Main FastAPI app
- `webapi/sse.py` - Server-Sent Events streaming
- `webapi/deps.py` - Dependencies/injection
- `webapi/errors.py` - Error handling
- `webapi/routes/` - API endpoints:
  - chat.py
  - config.py
  - health.py
  - memory.py
  - models.py
  - sessions.py
  - skills.py

## Frontend Setup

Once the backend is running:

```bash
git clone https://github.com/outsourc-e/hermes-workspace.git
cd hermes-workspace
pnpm install
cp .env.example .env
printf '\nHERMES_API_URL=http://127.0.0.1:8642\n' >> .env
pnpm dev  # Starts on http://localhost:3000
```

### Docker Option

```bash
git clone https://github.com/outsourc-e/hermes-workspace.git
cd hermes-workspace
cp .env.example .env
docker compose up
```

## Environment Variables

```env
# Hermes FastAPI backend URL
HERMES_API_URL=http://127.0.0.1:8642

# Optional: password-protect the web UI
HERMES_PASSWORD=your_password_here

# API keys for Hermes (use existing .env)
# Hermes Workspace auto-detects missing endpoints and gracefully disables features
```

## Verify Setup

1. Backend health check: `curl http://localhost:8642/health` → should return `{"status": "ok"}`
2. Open `http://localhost:3000` in browser
3. Should see chat interface with connection to Hermes

## Platform Differences

| Feature | CLI | WhatsApp/Telegram | Web Workspace |
|---------|-----|-------------------|---------------|
| File paste | Unlimited | ~4096 char limit | Upload support |
| Screenshots | Path-based | Send directly | Upload directly |
| File upload | No | No | Yes |
| Output display | Full | Truncated/split | Rich rendering |
| Vision analysis | Via path | Direct send | Direct upload |

## Install as PWA

Hermes Workspace is a Progressive Web App:

**Desktop (Chrome/Edge):**
1. Open in browser at localhost:3000
2. Click install icon (⊕) in address bar
3. Click Install

**Mobile (iOS Safari):**
1. Open in Safari
2. Tap Share button (□↑)
3. Tap "Add to Home Screen"

## Notes

- The WebAPI is not yet in upstream Hermes - may be merged later
- Hermes Workspace gracefully degrades if backend doesn't have all endpoints
- For full functionality (chat, sessions, skills, memory), use the fork or integrate WebAPI
- MIT licensed - can modify and extend freely

## Maturity Status (as of March 2026)

Hermes Workspace is still early (v0.1.0, hackathon-built). Consider waiting for:

1. **One-click VPS deployment** - Currently in progress
2. **Official desktop app** - Currently in progress
3. **WebAPI upstreamed** - May be merged into official Hermes
4. **Maturity indicators** - Version 1.0+, more stars/usage, active maintenance

### Monitoring for Updates

You can set up a cron job to check for updates:

```
hermes cronjob create --name "Check hermes-workspace updates" --schedule "0 9 * * 1" --deliver whatsapp
```

Prompt for the cron job:
```
Check https://github.com/outsourc-e/hermes-workspace for updates. Look for:
1) New releases or version bumps
2) Merging into official NousResearch/hermes-agent repo
3) One-click VPS deployment feature
4) Official desktop app
5) WebAPI being upstreamed
Report any significant progress.
```

### When Ready to Adopt

Once the project matures:
- Your existing `~/.hermes/config.yaml` and `.env` are portable
- Can switch to the fork without losing configuration
- Watch both repos (upstream and fork) for updates

### Integration Strategy

If you want to use it before full maturity:
1. Use their fork temporarily
2. Keep config separate (already done)
3. `git remote add upstream https://github.com/NousResearch/hermes-agent`
4. Merge upstream changes periodically

Or reach out to the fork author to ask if WebAPI will be contributed upstream.
