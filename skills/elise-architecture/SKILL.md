---
name: elise-architecture
description: ELISE system architecture notes. Load when working with ELISE components, database, or intelligence pipeline.
version: 1.0.0
category: elise
---

# ELISE Architecture

Runs as daemon on Hetzner CX21 VPS. PostgreSQL at postgresql://elise:***@localhost:5432/elise.

## Core Components
- RSS collectors (22 feeds)
- Binance WebSocket
- CoinGecko/KuCoin polling
- Narrative agent
- Telegram bot (configured for brief/alert delivery)

## Known Issues
- **Signals table migration NEVER APPLIED** — most tools depend on it being applied
- Intelligence pipeline incomplete: message bus topics published but not consumed
- llm_router.py (21k chars) is "complexity monster" — over-engineered for actual usage

## Integration
- Database access via MCP server 'elise_db' (PostgreSQL) or terminal psql
- Full instructions in ELISE_HERMES_INSTRUCTIONS.md
