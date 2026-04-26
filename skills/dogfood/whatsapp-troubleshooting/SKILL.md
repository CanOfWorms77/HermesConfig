---
name: whatsapp-troubleshooting
description: Diagnose and fix WhatsApp connection issues - connected but not responding, wrong allowed users, mode configuration.
tags: [whatsapp, troubleshooting, messaging, gateway]
---

# WhatsApp Connection Troubleshooting

## Symptoms
- WhatsApp shows as "connected" in gateway state
- User scanned QR code or entered pairing code successfully
- But Hermes doesn't respond to messages on WhatsApp
- User gets "I don't recognize you" message from Hermes

## Diagnostic Steps

1. **Check gateway status:**
 ```bash
 cat ~/.hermes/gateway_state.json | grep -A5 whatsapp
 ```
 Look for `"state": "connected"` - if present, the bridge is working.

2. **Check gateway log for unauthorized user warnings:**
 ```bash
 tail -50 ~/.hermes/logs/gateway.log | grep "Unauthorized user"
 ```
 Output like: `Unauthorized user: 131116862320724@lid (Dave) on whatsapp`
 The number before `@lid` is your WhatsApp user ID.

3. **Extract user's WhatsApp ID from session:**
 ```bash
 cat ~/.hermes/whatsapp/session/creds.json | grep -o '"me":{[^}]*}'
 ```
 This shows the linked phone number, LID, and name.

4. **Check .env configuration:**
 ```bash
 grep WHATSAPP ~/.hermes/.env
 ```
 
## Common Issues and Fixes

### Issue 1: WHATSAPP_ALLOWED_USERS not set correctly
**Symptom:** "Unauthorized user" warning in gateway log, or Hermes says "I don't recognize you".

**Fix:** Edit `~/.hermes/.env`:
```bash
WHATSAPP_ENABLED=true
WHATSAPP_MODE=self-chat # or "bot" if using separate number
WHATSAPP_ALLOWED_USERS=131116862320724 # User ID from logs (see below)
```

**How to find your WhatsApp user ID:**
- WhatsApp may identify you by LID (numeric ID like `131116862320724`) instead of phone number
- Check gateway log for "Unauthorized user" message - use the number before `@lid`
- Or check `creds.json` for `"lid": "NUMBER:2@lid"` - use the NUMBER part
- The phone number format (e.g., `447789748012`) may NOT work

**Important:** 
- Use the LID number, not necessarily the phone number
- No `+` prefix, no spaces
- For multiple users: comma-separated (e.g., `131116862320724,15551234567`)

### Issue 2: Wrong WHATSAPP_MODE
**Symptom:** Messages not being processed correctly.

**Fix:**
- `self-chat` = You message yourself (your own number)
- `bot` = Separate WhatsApp Business number

### Issue 3: Session exists but not recognized
**Symptom:** Old session from previous installation.

**Fix:** Clear session and re-pair:
```bash
rm -rf ~/.hermes/whatsapp/session
hermes whatsapp
```

## Alternative Fix: Pairing Code Approval

If Hermes sends a pairing code in WhatsApp chat, the admin can approve it from CLI:

```bash
hermes pairing approve whatsapp <CODE>
```

Example:
```bash
hermes pairing approve whatsapp T5X8DPCE
# Output: Approved! User Dave (131116862320724@lid) on whatsapp can now use the bot~
```

This bypasses the need to edit `.env` manually. The pairing is stored and persists.

### Issue 4: WhatsApp bridge is completely stopped / gateway stopped with it

**Symptom:** `ss -tlnp | grep :3000` shows nothing. Gateway logs show repeated `Poll error: Cannot connect to host 127.0.0.1:3000`. Gateway may eventually stop itself.

**Root cause:** The Node.js bridge process crashed or was killed. The gateway depends on the bridge; without it, the gateway gives up and stops.

**Fix:** Start the bridge manually, then restart the gateway.

```bash
# Start bridge in background
cd /root/.hermes/hermes-agent/scripts/whatsapp-bridge
node bridge.js --port 3000 --session /root/.hermes/whatsapp/session > /root/.hermes/whatsapp/bridge.log 2>&1 &

# Wait 5 seconds, then verify
sleep 5
curl -s http://127.0.0.1:3000/health
```

Expected: `{"status":"connected",...}` (or `"status":"pairing"` if QR scan needed).

Then restart the gateway so it picks up the bridge:
```bash
hermes gateway restart
```

**Alternative one-liner via existing tmux session:**
```bash
tmux send-keys -t hermes "cd /root/.hermes/hermes-agent/scripts/whatsapp-bridge && node bridge.js --port 3000 --session /root/.hermes/whatsapp/session" Enter
```

### Issue 5: WhatsApp bridge exits with code -15

**Symptom:** Bridge log shows `Connection closed (reason: 408). Reconnecting in 3s...` followed by `WhatsApp bridge process exited unexpectedly (code -15)`.

**Fix:** Ensure no stale session or pairing data interferes with a fresh start:
```bash
# Remove any existing session files
rm -rf ~/.hermes/whatsapp/session/*
# Optionally clear pairing approval/pending files if they exist
rm -f ~/.hermes/pairing/whatsapp-approved.json ~/.hermes/pairing/whatsapp-pending.json
# Restart the gateway
hermes gateway restart
```

## After Fixing Configuration

Restart the gateway:
```bash
hermes gateway restart
```

## Verification

1. Check bridge is running and healthy:
 ```bash
 curl -s http://127.0.0.1:3000/health
 ```
 Expected: `{"status":"connected",...}`

2. Check gateway status:
 ```bash
 hermes gateway status
 ```

3. Check gateway log shows no warnings:
 ```bash
 tail -50 ~/.hermes/whatsapp/bridge.log
 tail -20 ~/.hermes/logs/gateway.log
 ```

4. Send a test message to yourself on WhatsApp

5. Hermes should respond

## Quick Diagnostic Command

Run this to check everything at once:
```bash
echo "=== Bridge Health ===" && curl -s http://127.0.0.1:3000/health && echo -e "\n=== Gateway Status ===" && cat ~/.hermes/gateway_state.json | grep -A3 whatsapp && echo -e "\n=== Recent Unauthorized Warnings ===" && tail -20 ~/.hermes/logs/gateway.log | grep "Unauthorized" && echo -e "\n=== WhatsApp Session Info ===" && cat ~/.hermes/whatsapp/session/creds.json | grep -o '"me":{[^}]*}' && echo -e "\n=== Current .env Config ===" && grep WHATSAPP ~/.hermes/.env
```

## Related Files
- `~/.hermes/.env` - WhatsApp environment variables
- `~/.hermes/logs/gateway.log` - Gateway logs (check for "Unauthorized user")
- `~/.hermes/whatsapp/session/creds.json` - Session credentials (contains LID)
- `~/.hermes/whatsapp/bridge.log` - Bridge logs
- `~/.hermes/gateway_state.json` - Gateway status
