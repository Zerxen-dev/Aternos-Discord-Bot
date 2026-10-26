# 🌐 VPS Deployment Guide

This guide walks you through deploying the **Aternos Discord Bot** on a virtual private server (Ubuntu, Debian, or similar Linux distribution).

---

## Method A: Production Docker Setup (Recommended)

Docker provides an isolated, resilient runtime that automatically handles restarts on failure or system reboot.

### 1. Install Docker & Docker Compose
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Log out and log back in for group changes to take effect
```

### 2. Clone Repository & Configure Environment
```bash
git clone https://github.com/Zerxen-dev/Aternos-Discord-Bot.git
cd Aternos-Discord-Bot

cp .env.example .env
nano .env
```
Fill in your `DISCORD_TOKEN`, `ATERNOS_USER`, `ATERNOS_PASS`, and set a secure `WEB_API_KEY`.

### 3. Launch with Docker Compose
```bash
docker compose up -d --build
```

### 4. Verify Logs & Health Status
```bash
docker compose logs -f
docker ps
```
The container should show `(healthy)` once the internal FastAPI `/healthz` endpoint responds.

---

## Method B: Native Systemd Service

If you prefer running natively with Python on Linux:

### 1. Install System Dependencies
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git curl
```

### 2. Set Up Application Directory & Virtual Environment
```bash
git clone https://github.com/Zerxen-dev/Aternos-Discord-Bot.git /opt/aternosbot
cd /opt/aternosbot

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
```

### 3. Create Systemd Service File
Create `/etc/systemd/system/aternosbot.service`:
```ini
[Unit]
Description=Aternos Discord Bot Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/aternosbot
ExecStart=/opt/aternosbot/venv/bin/python main.py
Restart=always
RestartSec=10
EnvironmentFile=/opt/aternosbot/.env

[Install]
WantedBy=multi-user.target
```

### 4. Enable and Start the Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable aternosbot
sudo systemctl start aternosbot
sudo systemctl status aternosbot
```

---

## Reverse Proxy with SSL (Caddy or Nginx)

To access your Web Dashboard securely over HTTPS via a custom domain:

### Caddy (Easiest, Auto-SSL)
In your `Caddyfile`:
```caddy
panel.yourdomain.com {
    reverse_proxy localhost:8080
}
```
Reload Caddy:
```bash
sudo systemctl reload caddy
```
Your dashboard is now live and protected with automated Let's Encrypt SSL certificates!
