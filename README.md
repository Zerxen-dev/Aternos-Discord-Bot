# 🤖 Aternos Discord Bot

A Discord bot for managing your Aternos Minecraft server directly from Discord — slash commands, an interactive button panel, live status, autostart, and autostop.

---

## ✨ Features

✅ Start, stop and restart your server (with confirmation on destructive actions)
✅ Interactive control panel with buttons (`/panel`)
✅ Live server status and detailed server info
✅ Auto-Start — automatically restarts the server when it goes offline
✅ Auto-Stop — automatically stops the server after it sits empty
✅ Optional permission restrictions (admin roles / user IDs)
✅ Persistent settings across restarts
✅ Automatic Discord + Aternos reconnect with retry/backoff
✅ Production-ready logging

---

## 📸 Commands

| Command | Description |
|----------|-------------|
| `/help` | Show the command guide |
| `/hello` | Friendly greeting |
| `/status` | View live server status |
| `/info` | Detailed server information |
| `/panel` | Post an interactive control panel (Start/Stop/Restart/Refresh buttons) |
| `/start` | Start the Minecraft server |
| `/stop` | Stop the Minecraft server (asks for confirmation) |
| `/restart` | Restart the Minecraft server (asks for confirmation) |
| `/autostart enabled:<bool>` | Auto-restart the server whenever it goes offline |
| `/autostop enabled:<bool> minutes:<int>` | Auto-stop the server after it's empty for `minutes` |
| `/console command:<text>` | Send a console command directly to the running server |
| `/whitelist <list\|add\|remove>` | Manage the Minecraft server whitelist |
| `/op <list\|add\|remove>` | Manage server operators (OPs) |
| `/ban <list\|add\|remove>` | Manage banned players |
| `/properties` | View key server options (difficulty, game mode, whitelist, cracked, pvp, etc.) |
| `/setproperty option:<name> value:<value>` | Update a server option (creative, true, false, 20, etc.) |

If `ADMIN_ROLE_IDS` or `ADMIN_USER_IDS` is configured (see below), all server-altering commands (`/start`, `/stop`, `/restart`, `/autostart`, `/autostop`, `/console`, `/setproperty`, and list modifications like `add`/`remove`) are restricted to those admins. Commands that only fetch information (like `/status`, `/info`, `/properties`, and list `list` commands) remain open to everyone.

---

## 🛠 Requirements

- Python **3.9+**
- A Discord bot token
- An Aternos account with a Minecraft server

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` and fill in the required values:

```env
# Required
DISCORD_TOKEN=your_discord_bot_token
ATERNOS_USER=your_aternos_username
ATERNOS_PASS=your_aternos_password

# Optional
ADMIN_ROLE_IDS=               # comma-separated Discord role IDs allowed to manage the server
ADMIN_USER_IDS=               # comma-separated Discord user IDs allowed to manage the server
AUTOSTART_POLL_SECONDS=60     # how often the bot checks server status
AUTOSTOP_DEFAULT_MINUTES=20   # default idle-minutes before autostop, if not specified
STATE_FILE=autostart_state.json
```

Leaving `ADMIN_ROLE_IDS` and `ADMIN_USER_IDS` empty means everyone can use every command (unrestricted mode).

---

## 📦 Installation & Run

### Method 1: Local Run (Python)

1. Clone the repository:
   ```bash
   git clone https://github.com/SAMRAT69/Aternos-Discord-Bot.git
   cd Aternos-Discord-Bot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and fill in the required values:
   ```bash
   cp .env.example .env
   ```

4. Run the Bot:
   ```bash
   python main.py
   ```

### Method 2: Docker (Recommended for VPS)

Build and run with docker-compose:
```bash
docker-compose up -d --build
```

### Method 3: Systemd Service (VPS Daemon)

1. Copy the systemd service file template to your system services:
   ```bash
   cp aternos-bot.service /etc/systemd/system/aternos-bot.service
   ```
2. Reload systemd, enable and start the service:
   ```bash
   systemctl daemon-reload
   systemctl enable aternos-bot
   systemctl start aternos-bot
   ```

The launcher automatically:

- Checks the Python version
- Validates environment variables (fails fast with a clear error if anything required is missing)
- Installs dependencies
- Applies compatibility patches
- Starts the bot

---

## 🎮 Control Panel

`/panel` posts a persistent embed with **Refresh / Start / Stop / Restart** buttons, so anyone with permission can manage the server without typing commands. Stop and Restart ask for confirmation before acting, whether triggered from the panel or from the equivalent slash command.

---

## 🤖 Auto-Start

```text
/autostart enabled:True
/autostart enabled:False
```

The bot checks the server every `AUTOSTART_POLL_SECONDS` (default 60s) and restarts it automatically if it goes offline. The setting persists across bot restarts.

## 💤 Auto-Stop

```text
/autostop enabled:True minutes:20
/autostop enabled:False
```

If the server has had zero players for the configured number of minutes, the bot stops it automatically to save your Aternos queue time. The setting persists across bot restarts.

---

## 🏗 Architecture

The bot is organized as a Python package:

```
bot/
  config.py          # env var loading & validation
  state.py            # persisted autostart/autostop settings
  permissions.py      # admin role/user gating
  aternos_client.py   # thread-safe wrapper around python-aternos
  embeds.py           # shared embed helpers
  views.py            # buttons: confirmation dialogs, control panel
  core.py             # the Discord bot client
  app.py              # process entry point, startup & reconnect logic
  cogs/
    general.py        # /help, /hello
    server.py         # /status, /info, /panel, /start, /stop, /restart
    automation.py     # /autostart, /autostop, background monitor loop
```

`aternos_server_bot.py` is a thin entry-point shim kept for backwards compatibility with existing deployments — it just calls into `bot.app.main()`.

---

## 🧪 Tests

```bash
pip install -r requirements-dev.txt
pytest
```

---

## 📝 Notes

- Startup may take **2–4 minutes** depending on the Aternos queue.
- Slash commands may take a few minutes to appear globally after the first sync.
- Use the `ADMIN_ROLE_IDS` / `ADMIN_USER_IDS` env vars to restrict who can start/stop/restart the server.

---

## ❤️ Credits

**MADE BY — .samratt**
`1154000002927050853`

Discord: https://discord.com/users/1154000002927050853
GitHub: https://github.com/SAMRAT69

---

## 📜 License

MIT — see [LICENSE](LICENSE). Credit to the original author is required when reusing this code (see the license file for details).

This project is for educational and personal server management purposes. Use responsibly.
