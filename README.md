<div align="center">

# 🤖 Aternos Discord Bot
### *Manage, Monitor, Autostart & Control Your Aternos Minecraft Server Directly from Discord*

[![Python Version](https://img.shields.io/badge/python-3.9+-30d158?style=flat-square&logo=python)](https://python.org)
[![Discord.py](https://img.shields.io/badge/discord.py-2.7+-0a84ff?style=flat-square&logo=discord)](https://github.com/Rapptz/discord.py)
[![License](https://img.shields.io/badge/license-MIT-ff375f?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Android%20Termux%20%7C%20Linux%20%7C%20Windows%20%7C%20macOS%20%7C%20Docker-ffd60a?style=flat-square)](https://github.com/Zerxen-dev/Aternos-Discord-Bot)

**Aternos Discord Bot** gives you complete remote control over your Aternos Minecraft server right inside Discord — interactive button control panels, live auto-updating status embeds, server alerts with role pings, scheduled timers, one-click world backups, live console/crash logs, and automated auto-start & auto-stop routines.

</div>

---

## ✨ Features

- 🎮 **Interactive Control Panel (`/panel`)**: One-click Start, Stop, Restart, and live status refresh buttons.
- 🟢 **Live Auto-Updating Status Channel (`/statuschannel`)**: Dedicated channel with a continuously updating rich embed and dynamic voice channel name (e.g. `🟢 4/20 Online`).
- 🔔 **Server Online & Player Alerts (`/alerts`)**: Dispatch notifications to a Discord channel with `@Role` pings when the server comes online, goes offline, or players join/leave.
- ⏰ **Automated Server Scheduler (`/schedule`)**: Schedule automatic server start, stop, or restart routines at specific times (UTC).
- 💾 **One-Click World Backups (`/backup`)**: Create and list Aternos backups directly from Discord so your world progress is always protected.
- 📜 **Live Console & Crash Logs (`/logs`)**: Fetch recent server console lines and error reports directly into formatted Discord codeblocks.
- 🤖 **Auto-Start**: Automatically monitors and restarts the server whenever it goes offline.
- 💤 **Auto-Stop**: Automatically stops the server after sitting empty for a configurable duration to save Aternos queue time.
- 🖥️ **Live Console Execution (`/console`)**: Execute Minecraft server commands directly from Discord.
- 📋 **Player & Permission Lists**:
  - Whitelist management (`/whitelist list`, `/whitelist add`, `/whitelist remove`)
  - Operator management (`/op list`, `/op add`, `/op remove`)
  - Ban management (`/ban list`, `/ban add`, `/ban remove`)
- ⚙️ **Live Server Properties (`/properties`, `/setproperty`)**: View and change difficulty, gamemode, cracked, PvP, and whitelist options on the fly.
- 🛡️ **Role & User-Based Access Control**: Gate destructive and administrative commands behind Discord roles or user IDs.
- 🔄 **Resilient Auto-Reconnect**: Automatic reconnection and exponential backoff on network dropouts.
- 💾 **Persistent Settings**: All configurations, status channels, alerts, and schedules persist across bot and host restarts.

---

## 📸 Command Reference

| Command | Category | Description |
| :--- | :---: | :--- |
| `/panel` | Control | Post an interactive embed panel with Start, Stop, Restart & Refresh buttons |
| `/status` | Info | View live server status, player counts, and address |
| `/info` | Info | View detailed server information (RAM, software, version, port) |
| `/statuschannel set` | Live Status | Configure live auto-updating status text embed & dynamic voice channel name |
| `/statuschannel remove` | Live Status | Disable live status channel auto-updates |
| `/alerts set` | Alerts | Configure alert channel, role ping (`@Minecraft`), and event triggers |
| `/alerts remove` | Alerts | Disable server state and player alerts |
| `/schedule add` | Automation | Schedule automated start/stop/restart routines at specific times (UTC) |
| `/schedule list` | Automation | View all active scheduled timers |
| `/schedule remove` | Automation | Delete a scheduled timer by ID |
| `/backup create` | Backups | Create a new world backup on Aternos immediately |
| `/backup list` | Backups | List all existing world backups with timestamps and sizes |
| `/logs` | Diagnostics | Fetch recent console logs and crash reports |
| `/start` | Lifecycle | Start the Minecraft server |
| `/stop` | Lifecycle | Stop the server (with confirmation prompt) |
| `/restart` | Lifecycle | Restart the server (with confirmation prompt) |
| `/autostart enabled:<bool>` | Automation | Automatically restart the server when it goes offline |
| `/autostop enabled:<bool> minutes:<int>` | Automation | Automatically stop the server after it remains empty |
| `/console command:<text>` | Management | Send a console command directly to the running server |
| `/whitelist <list\|add\|remove>` | Management | View, add, or remove players from the server whitelist |
| `/op <list\|add\|remove>` | Management | View, grant, or revoke server Operator (OP) status |
| `/ban <list\|add\|remove>` | Management | View, ban, or unban players |
| `/properties` | Settings | View key server configuration (gamemode, difficulty, pvp, etc.) |
| `/setproperty option:<name> value:<val>` | Settings | Update a server configuration option live |
| `/help` | General | Display the interactive command guide |
| `/hello` | General | Friendly greeting and latency check |

> [!NOTE]
> If `ADMIN_ROLE_IDS` or `ADMIN_USER_IDS` is set, all server-altering commands (`/start`, `/stop`, `/restart`, `/autostart`, `/autostop`, `/console`, `/setproperty`, `/backup create`, `/schedule add/remove`, and list modifications) are restricted to authorized admins only. Informational commands remain accessible to everyone.

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```env
# Required
DISCORD_TOKEN=your_discord_bot_token
ATERNOS_USER=your_aternos_username
ATERNOS_PASS=your_aternos_password

# Optional
ADMIN_ROLE_IDS=               # Comma-separated Discord role IDs allowed to manage the server
ADMIN_USER_IDS=               # Comma-separated Discord user IDs allowed to manage the server
AUTOSTART_POLL_SECONDS=60     # How often the bot polls server status (default: 60s)
AUTOSTOP_DEFAULT_MINUTES=20   # Default idle minutes before autostop (default: 20m)
STATE_FILE=autostart_state.json
```

---

## 📦 Installation & Setup

### 📱 Method 1: Android (Termux)

```bash
# 1. Update Termux and install Python, development libraries & Git
pkg update && pkg install python libxml2 libxslt git -y

# 2. Clone repository
git clone https://github.com/Zerxen-dev/Aternos-Discord-Bot.git
cd Aternos-Discord-Bot

# 3. Configure environment
cp .env.example .env
nano .env

# 4. Launch (dependencies auto-install on first run)
python main.py
```

---

### 🐧 Method 2: Linux / VPS (Ubuntu, Debian, Arch)

```bash
# 1. Install Python 3.9+ & Git
sudo apt update && sudo apt install python3 python3-pip git -y

# 2. Clone repository
git clone https://github.com/Zerxen-dev/Aternos-Discord-Bot.git
cd Aternos-Discord-Bot

# 3. Configure environment
cp .env.example .env
nano .env

# 4. Launch
python3 main.py
```

---

### 🪟 Method 3: Windows (PowerShell / Command Prompt)

1. Install **[Python 3.9+](https://www.python.org)** (make sure to check *"Add Python to PATH"*).
2. Open PowerShell or Command Prompt:

```powershell
# Clone and enter directory
git clone https://github.com/Zerxen-dev/Aternos-Discord-Bot.git
cd Aternos-Discord-Bot

# Copy configuration
copy .env.example .env

# Edit .env with your favorite editor (e.g. notepad .env)
notepad .env

# Run launcher
python main.py
```

---

### 🐳 Method 4: Docker & Docker Compose

```bash
# 1. Clone repository
git clone https://github.com/Zerxen-dev/Aternos-Discord-Bot.git
cd Aternos-Discord-Bot

# 2. Configure .env
cp .env.example .env
nano .env

# 3. Build & start container
docker-compose up -d --build
```

---

### 🛠 Method 5: Systemd Service (Linux Background Daemon)

```bash
# 1. Copy service template
sudo cp aternos-bot.service /etc/systemd/system/aternos-bot.service

# 2. Reload and enable
sudo systemctl daemon-reload
sudo systemctl enable aternos-bot
sudo systemctl start aternos-bot

# Check status
sudo systemctl status aternos-bot
```

---

## 🏗 Project Architecture

```text
Aternos-Discord-Bot/
├── bot/
│   ├── app.py              # Application entry point, logging & reconnect loop
│   ├── aternos_client.py   # Thread-safe async wrapper around python-aternos (backups, logs, commands)
│   ├── config.py           # Environment variable loading & fail-fast validation
│   ├── constants.py        # Embed colors and UI constants
│   ├── core.py             # Discord bot client & cog loader
│   ├── embeds.py           # Reusable embed builders and formatters
│   ├── permissions.py      # Admin role and user authorization checks
│   ├── state.py            # Persistent JSON state for autostart, status channels, alerts & schedules
│   ├── views.py            # Interactive UI buttons & confirmation dialogs
│   └── cogs/
│       ├── automation.py   # Live status channel, role ping alerts, scheduler, autostart & autostop
│       ├── general.py      # /help, /hello
│       ├── management.py   # /console, /whitelist, /op, /ban, /properties, /setproperty, /backup, /logs
│       └── server.py       # /status, /info, /panel, /start, /stop, /restart
├── main.py                 # Automated launcher & dependency installer
├── requirements.txt        # Production dependencies
├── Dockerfile              # Container definition
├── docker-compose.yml      # Multi-container orchestrator
└── tests/                  # Pytest test suite
```

---

## ❤️ Credits

**Created by: Zerxen-dev**  
- **GitHub**: [https://github.com/Zerxen-dev](https://github.com/Zerxen-dev)
- **Repository**: [https://github.com/Zerxen-dev/Aternos-Discord-Bot](https://github.com/Zerxen-dev/Aternos-Discord-Bot)

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).
