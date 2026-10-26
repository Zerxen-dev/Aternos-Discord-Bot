---
name: aternos-bot-expert
description: Domain knowledge, quirks, architecture, and operational guidelines for the Aternos Discord Bot.
---

# Aternos Bot Expert Domain Knowledge

This skill documents the domain expertise, architectural invariants, API quirks, and operational rules for developing and maintaining the **Aternos-Discord-Bot**.

---

## 1. Aternos API Quirks & Operational Realities

The bot integrates with Aternos via `python-aternos` (which reverse-engineers Aternos web endpoints). Aternos does not provide an official REST API, meaning communication relies on web scraping and simulated browser sessions.

### A. Cloudflare & Anti-Bot Protection
- **Cloudflare Challenge**: Aternos uses Cloudflare WAF protection. Requests must maintain valid browser headers and cookies (`ATERNOS_SESSION`, `SEC` token).
- **Session Expiration**: Sessions expire unpredictably during server idle time or when Aternos rotates security cookies.
- **Re-authentication**: When an API call fails with session/auth errors (e.g. 401/403 or invalid token), the bot must trigger `_reconnect_blocking` with exponential backoff rather than crashing.

### B. Rate Limits & Concurrency Hazards
- **Aggressive Polling Risks**: Polling Aternos faster than every 30–60 seconds can result in HTTP 429 (Too Many Requests), Cloudflare IP rate limits, or temporary account bans.
- **Synchronous Library Core**: Most `python-aternos` methods are synchronous and blocking (using `requests` / `cloudscraper`).
  - **Inviolable Rule**: Never invoke synchronous `python-aternos` methods directly on the Discord `asyncio` event loop. Always offload them with `asyncio.to_thread`.
- **Thread Safety & Session Mutex**: Multiple concurrent coroutines attempting to modify the same Aternos session (e.g. polling while starting/stopping) causes race conditions and broken state.
  - A thread-safe mutex (`threading.Lock()` or an `asyncio.Lock()` around worker executions) must guard all session access.

### C. Server Lifecycle & Queue Times
- **Queues**: Aternos servers frequently enter an operational waiting queue (seconds to 15+ minutes depending on datacenter load).
- **Transitional States**: Aternos server states include:
  - `offline` (0)
  - `online` (1)
  - `starting` (2)
  - `loading` (3)
  - `preparing` (10)
  - `stopping` (4)
- **Confirmations**: During peak hours, Aternos queues may require confirmation (`server.confirm()`).
- **Start Timeout**: Starting an Aternos server can take between 2 to 5 minutes under normal conditions. Polling loops must allow sufficient time (e.g. 60 attempts × 5s = 5 minutes) before timing out.

---

## 2. Command Architecture & Permission Model

### A. Command Organization
The bot uses Discord slash commands (`app_commands`) grouped into clean cogs:
- **Server Cog**: `/status`, `/info`, `/start`, `/stop`, `/restart`, `/panel` (interactive buttons for start, stop, restart, refresh).
- **Automation Cog**: `/autostart`, `/autostop`, `/statuschannel` (text & dynamic voice), `/alerts` (state transitions & player join/leave), `/schedule` (timed actions).
- **Management Cog**: `/console`, `/whitelist` (list, add, remove), `/op` (list, add, remove), `/ban` (list, add, remove), `/properties`, `/setproperty`, `/logs`, `/backup` (create, list).
- **General Cog**: `/help`, `/hello`, `/stats`.

### B. Access Control Model
- Configured via:
  - `ADMIN_ROLE_IDS`: Comma-separated Discord role snowflakes.
  - `ADMIN_USER_IDS`: Comma-separated Discord user snowflakes.
- **Fail-Open vs. Restricted**:
  - If neither `ADMIN_ROLE_IDS` nor `ADMIN_USER_IDS` is set, `config.restricted` evaluates to `False`. The bot is unrestricted, matching default community expectations.
  - If either list is non-empty, `config.restricted` evaluates to `True`. Destructive / server-altering commands (`start`, `stop`, `restart`, `autostart`, `autostop`, `console`, `setproperty`, `whitelist add/remove`, etc.) are protected by `is_authorized()` checks.
  - UI Views (`ControlPanelView`, `ConfirmView`) must also verify user authorization before invoking actions.

---

## 3. Persistent State Management (`autostart_state.json`)

### A. State Storage Invariants
- Persistent settings are stored in `autostart_state.json` (or path specified by `STATE_FILE`).
- **Atomic Persistence**: Changes to state must be saved cleanly using JSON serialization.
- **Backward Compatibility**:
  - Legacy v1 format used `{"enabled": true, "channel_id": 123, "set_by": "User"}`.
  - Modern format tracks:
    - `autostart_enabled`, `autostart_channel_id`, `autostart_set_by`
    - `autostop_enabled`, `autostop_minutes`, `autostop_channel_id`, `autostop_set_by`
    - `status_channel_id`, `status_message_id`, `status_voice_channel_id`
    - `alerts_channel_id`, `alerts_role_id`, `alerts_notify_on`
    - `schedules` (list of `{id, action, time, days, created_by}`)
  - Any state loader must automatically deserialize and migrate older shapes without data loss.

---

## 4. Multi-Server & Multi-Account Guidelines

- A single Aternos account can have multiple servers (e.g. `server1.aternos.me`, `server2.aternos.me`).
- Advanced multi-server operations should allow selecting or configuring target servers per guild or command execution.
- Session managers must cleanly isolate server instances and maintain dedicated locks or identifiers.
