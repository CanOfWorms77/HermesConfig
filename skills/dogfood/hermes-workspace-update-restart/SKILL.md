---
name: hermes-workspace-update-restart
description: Update hermes-workspace repository and restart dev server with minimal service disruption. Handles port conflicts (WhatsApp bridge on 3000), gateway port verification, and validation checklist.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [workspace, update, restart, deployment, troubleshooting]
    related_skills: [hermes-agent]
---

## When to use
- The workspace dev server has crashed and needs restarting (most common).
- You intentionally pulled upstream changes and need to rebuild + restart.
- Workspace is unreachable on its expected port.

## Prerequisites
- Workspace cloned at ~/hermes-workspace
- hermes-agent gateway running separately (typically port 8642 or 8643)
- Other services may occupy port 3000 (default workspace port)

## Decision: update needed or just a crash?
Check whether the server is simply down versus needing an update.

```bash
ss -tlnp | grep -E ':(3000|3001|3002|8643)'
ps aux | grep -E 'vite|node.*hermes-workspace|gateway'
```

If the workspace port is missing but the gateway is up, it is likely a **crash** — skip to [Quick restart after crash](#quick-restart-after-crash).

If the gateway is also missing, the problem may be a **full stack outage** (e.g., WhatsApp bridge died and took the gateway with it). See [Full stack diagnostic](#full-stack-diagnostic).

If you specifically want latest code, follow [Update path](#1-pull-latest-changes).

---

## Full stack diagnostic
When the user says "workspace is not working again," always check the whole chain before assuming it's just Vite.

Service dependency chain:
```
WhatsApp bridge (port 3000) → Gateway (port 8643) → Workspace (port 3002)
```

If the bridge crashes or stops, the gateway may also stop after repeated connection failures. The workspace then has nothing to talk to.

Check each layer:
```bash
# Layer 1: WhatsApp bridge
ss -tlnp | grep :3000
curl -s http://127.0.0.1:3000/health

# Layer 2: Gateway
ss -tlnp | grep :8643
curl -s http://127.0.0.1:8643/health

# Layer 3: Workspace
ss -tlnp | grep :3002
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:3002/
```

If the bridge is down, start it first (see `whatsapp-troubleshooting` skill), then restart the gateway, then restart the workspace.

If the gateway is down but the bridge is up, just restart the gateway:
```bash
hermes gateway start
```

If only the workspace is down, use [Quick restart after crash](#quick-restart-after-crash).

---

## Quick restart after crash
No git pull or rebuild required. The Vite dev server often dies with errors like `transport was disconnected, cannot call "fetchModule"` (exit 143).

### 1. Inspect crash evidence in tmux
```bash
tmux capture-pane -pt hermes -S -30
```
Look for `ELIFECYCLE  Command failed` or Vite stack traces.

### 2. Kill any stale Vite/node processes
```bash
pkill -f "vite dev"
```
Do **not** kill the gateway (python webapi on 8643) or WhatsApp bridge.

### 3. Restart in the existing tmux session
```bash
tmux send-keys -t hermes "cd /root/hermes-workspace && PORT=3002 pnpm dev" Enter
```
Wait 5 s, then verify:
```bash
ss -tlnp | grep 3002
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:3002/
```

Skip ahead to [Verify gateway connection](#6-verify-gateway-connection).

---

## Update path

### 1. Pull latest changes
```bash
cd ~/hermes-workspace
git fetch origin
git pull origin main
```

Review changes:
```bash
git log --oneline main..origin/main -10
git diff --stat main..origin/main
```

### 2. Update dependencies
Use pnpm (lockfile-aware, faster than npm):
```bash
pnpm install --frozen-lockfile=false
```

### 3. Rebuild
```bash
pnpm build
```
Confirm `dist/` contains updated assets.

### 4. Identify port conflicts
Check what occupies port 3000:
```bash
ss -tlnp | grep 3000
lsof -i :3000
```

**Do NOT kill WhatsApp bridge** — it's an independent long-lived service. Instead, pick an alternate workspace port (3001, 3002, etc.).

### 5. Restart workspace on intended port
Kill any previous Vite dev process:
```bash
pkill -f "vite dev"
```

Start on the intended port (3002 is typical; use 3001/3002 only if 3000 is taken by WhatsApp):
```bash
PORT=3002 pnpm dev
```

Verify listening:
```bash
ss -tlnp | grep 3002
```

### 6. Verify gateway connection
Workspace reads `HERMES_API_URL` from `.env`. Check actual value:
```bash
grep HERMES_API ~/hermes-workspace/.env
```

Test all common gateway ports:
```bash
curl -s http://127.0.0.1:8642/health
curl -s http://127.0.0.1:8643/health
```
Use whichever responds OK. Update `.env` if needed:
```
HERMES_API_URL=http://127.0.0.1:8642
```

Verify workspace serves:
```bash
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:3002/
```

### 7. Confirm external accessibility
```bash
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://<external-ip>:3002/
```

## Common pitfalls
- **Crash vs update needed** — if the user says "not working again" it is usually a Vite crash, not a code update issue. Check tmux logs before pulling git changes.
- **Full stack outage** — the workspace depends on the gateway, which depends on the WhatsApp bridge. If all three are down, start the bridge first, then gateway, then workspace.
- Vite `transport was disconnected` error → dev server crashed; quick restart is enough.
- Port 3000 conflict → use PORT=3001/3002, don't kill WhatsApp.
- Stale Vite process → `pkill -f "vite dev"` cleans all.
- Wrong gateway port → override HERMES_API_URL in .env.
- Docker ≠ dev server → docker-compose pulls images; dev server managed separately.
- Enhanced-fork mode warnings → expected when connecting to vanilla gateway.

## Verification checklist
- [ ] Determined whether this is a crash or an intentional update
- [ ] Tmux logs inspected (for crashes)
- [ ] Git pulled clean, no uncommitted work (update path only)
- [ ] pnpm install completed successfully (update path only)
- [ ] Build succeeded, dist/ updated (update path only)
- [ ] Workspace dev server listening on intended port
- [ ] Gateway health returns JSON `{"status":"ok"}`
- [ ] Workspace root returns HTTP 200
- [ ] External IP:port reachable from client
- [ ] .env uses correct HERMES_API_URL

## Notes
- Workspace v2.0.0+ is zero-fork — no gateway patches needed
- New: Connection-settings UI (`/settings/connection`) supports live URL override without restart
- Docker compose uses pre-built images from ghcr.io and Docker Hub; local builds unnecessary for production
- Startup logs indicate detected gateway capabilities — watch for `missing=[...]` to detect mode mismatches
