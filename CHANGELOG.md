# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-10-26

### 🚀 Added
- **Web Management Suite**: Integrated modern FastAPI web dashboard (`http://host:8080`) with live status indicators, player count, real-time uptime bar chart, console log viewer, and start/stop controls.
- **REST API Endpoints**: `/api/status`, `/api/uptime`, `/api/logs`, `/api/server/start`, `/api/server/stop`, `/api/server/restart`, protected with configurable API key.
- **AI Natural Language Assistant**: New `/ask` slash command supporting Google Gemini and OpenAI models to interpret conversational requests ("is the server online?", "start server", "who is playing?") with intelligent deterministic NLP fallback.
- **Multi-Server Management**: Seamlessly manage multiple Minecraft servers on the same Aternos account with `/servers list` and `/servers select`.
- **Discord Modals**: Interactive popup forms for `/setproperty` and `/schedule modal` to eliminate parameter syntax errors.
- **UI Pagination**: Interactive Previous/Next button pagination for long player and backup lists (`/whitelist list`, `/op list`, `/ban list`, `/backup list`).
- **Bot Statistics**: Added `/stats` command displaying real-time WebSocket ping, bot uptime, guilds connected, and runtime details.
- **Observability**: Prometheus metrics export at `/metrics` (tracking command counts, active server state, player counts, response latency) and structured JSON logging with `structlog`.
- **Security Hardening**:
  - Sliding-window command rate limiting (`CommandRateLimiter`).
  - Strict input sanitization for `/console` commands against shell injections and control character exploits.
  - Safe atomic JSON file writes (`.tmp` write + `os.replace`) to prevent state corruption during power loss.

### 🔄 Changed
- **Pydantic Settings**: Refactored configuration loading to use `pydantic-settings` with strict type validation and Discord snowflake parsing.
- **Modular Architecture**: Restructured codebase into clean layers: `bot/cogs/`, `bot/services/`, `bot/utils/`.
- **Aternos Client Resilience**: Implemented thread-safe concurrent locks, exponential backoff with jitter on reconnects, and improved Cloudflare queue handling.
- **Docker Optimization**: Converted `Dockerfile` to an ultra-lean multi-stage build running under an unprivileged `appuser` (UID 10000) with container healthchecks.

### 🧪 Tests
- Expanded test suite from 31 to 52 automated tests covering configuration, state persistence, Aternos client, web dashboard, AI NLP, rate limiting, and multi-server switching.

---

## [1.0.0] - 2024-03-01
- Initial public release of Aternos Discord Bot.
- Core slash commands: `/start`, `/stop`, `/restart`, `/status`, `/panel`.
- Auto-start and auto-stop background monitoring loop.
