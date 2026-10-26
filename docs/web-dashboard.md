# 📊 Web Dashboard & REST API Guide

The Aternos Discord Bot features an integrated **FastAPI Web Dashboard** designed for real-time monitoring and administrative control from any desktop or mobile browser.

---

## Accessing the Dashboard

When enabled (`WEB_DASHBOARD_ENABLED=true` in `.env`), the dashboard binds to `http://localhost:8080` (or your configured `WEB_HOST` and `WEB_PORT`).

### Authentication
If `WEB_API_KEY` is configured in your `.env`, you can authenticate through:
1. **URL Query Parameter**:
   ```
   http://your-server-ip:8080/?key=YOUR_SECRET_KEY
   ```
2. **HTTP Header (for REST API calls)**:
   ```http
   X-API-Key: YOUR_SECRET_KEY
   ```

---

## Dashboard Features

- 🟢 **Live Status Indicator**: Visual pulsing badge showing whether the server is Online, Offline, Starting, or Stopping.
- 👥 **Real-Time Player Counter**: Current player count and max slots (e.g., `4 / 20 Players`).
- 📈 **Uptime History Bar Chart**: Historical timeline of the last 120 polling intervals.
- ⚡ **Direct Actions**: Start, Stop, and Restart buttons with safety confirmations.
- 📜 **Live Console Logs**: Tail recent server console lines and error messages directly from the web interface without opening Aternos.

---

## REST API Reference

All REST endpoints return JSON. Include your `X-API-Key` header with requests.

### 1. Server Status
```http
GET /api/status
```
**Response:**
```json
{
  "status": "online",
  "subdomain": "myserver",
  "address": "myserver.aternos.me",
  "port": 25565,
  "software": "Paper",
  "version": "1.20.4",
  "players_count": 3,
  "slots": 20,
  "ram": 2048,
  "motd": "Welcome to my server!"
}
```

### 2. Uptime History
```http
GET /api/uptime
```
**Response:**
```json
{
  "history": [
    {
      "timestamp": "2026-10-26T12:00:00Z",
      "subdomain": "myserver",
      "status": "online",
      "players": 3
    }
  ],
  "total_samples": 120
}
```

### 3. Fetch Console Logs
```http
GET /api/logs?lines=50
```

### 4. Lifecycle Actions
```http
POST /api/server/start
POST /api/server/stop
POST /api/server/restart
```
**Response:**
```json
{
  "success": true,
  "action": "start"
}
```

### 5. Health & Prometheus Metrics
- `GET /healthz` — Used by Docker healthchecks and uptime probes.
- `GET /metrics` — Prometheus metrics exporter (scraped by Prometheus / Grafana).
