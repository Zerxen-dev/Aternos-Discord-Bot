# 🔐 Aternos Credentials & Session Guide

Aternos does not provide a public developer API. The bot interacts with the Aternos web panel via an automated session protocol. Follow this guide to ensure your credentials and accounts remain safe and reliable.

---

## 1. Credentials Best Practices

- **Dedicated Sub-Account**: We strongly recommend creating a separate Aternos account and adding it as a friend / manager to your primary server with the necessary permissions:
  1. Go to your primary Aternos server dashboard.
  2. Click **Access** on the sidebar.
  3. Enter the username of your dedicated bot account.
  4. Grant permissions: *Start / Stop / Restart*, *Console*, *Logs*, *Players* (Whitelist/OP/Ban), and *Backups*.
  5. Use the bot account credentials in `.env`.
- **Never Share Your `.env` File**: Ensure `.env` is listed in `.gitignore` (which it is by default). Never commit credentials to public Git repositories.
- **Two-Factor Authentication**: Aternos does not support 2FA on web panel logins. If you use Google/Twitter OAuth to log into Aternos, you must create a standard username and password in your Aternos account settings to authenticate with the bot.

---

## 2. Session Expiration & Auto-Reconnection

Aternos sessions can expire when:
- The Aternos backend performs scheduled maintenance.
- Cloudflare challenges are periodically updated.
- The IP address of your host changes.

**How the Bot Handles This:**
The bot includes automatic session recovery:
- All Aternos API calls are wrapped in exponential backoff retry loops.
- When an expired session or `401 Unauthorized` is detected, the bot automatically calls `login_blocking()` to refresh its authentication cookies without requiring a container restart.

---

## 3. Server Queues and Starting Delays

When Aternos servers are started, they are frequently placed into a dynamic queue:
- The bot recognizes `pending` and `loading` states.
- The Discord embed presence reflects "Server starting... ⏳" while in queue.
- If the queue requires confirmation, the client's internal background worker automatically sends confirmation tokens to ensure the server starts promptly.
