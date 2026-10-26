"""FastAPI-based modern web dashboard and REST API for Aternos server management."""

from __future__ import annotations

import collections
import datetime
import logging
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Header, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, Response

from .metrics_service import MetricsManager

log = logging.getLogger('AternosBot.web')

# In-memory circular buffer for historical uptime tracking (last 120 samples)
_UPTIME_HISTORY: collections.deque[dict[str, Any]] = collections.deque(maxlen=120)


def record_uptime_sample(subdomain: str, status: str, players: int) -> None:
    """Record an uptime data point for historical graphing."""
    _UPTIME_HISTORY.append({
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'subdomain': subdomain,
        'status': status.lower(),
        'players': players,
    })


def create_web_app(bot_instance: Any) -> FastAPI:
    """Create and configure the FastAPI web dashboard application."""
    app = FastAPI(
        title='Aternos Discord Bot — Web Management Suite',
        version='2.0.0',
        docs_url='/api/docs',
        redoc_url=None,
    )

    async def verify_auth(
        x_api_key: Optional[str] = Header(None, alias='X-API-Key'),
        key: Optional[str] = Query(None),
    ) -> bool:
        required_key = getattr(bot_instance.config, 'web_api_key', None)
        if not required_key:
            return True  # If no key configured, unrestricted access
        token = x_api_key or key
        if token != required_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid or missing authentication credentials (API key).',
            )
        return True

    @app.get('/healthz')
    async def healthcheck():
        return {'status': 'healthy', 'time': datetime.datetime.now(datetime.timezone.utc).isoformat()}

    @app.get('/metrics')
    async def metrics():
        content, media_type = MetricsManager.get_metrics_payload()
        return Response(content=content, media_type=media_type)

    @app.get('/api/status', dependencies=[Depends(verify_auth)])
    async def get_status():
        try:
            srv = bot_instance.aternos.server
            return {
                'status': getattr(srv, 'status', 'offline'),
                'subdomain': getattr(srv, 'subdomain', 'unknown'),
                'address': bot_instance.aternos.address,
                'port': getattr(srv, 'port', 25565),
                'software': getattr(srv, 'software', 'Unknown'),
                'version': getattr(srv, 'version', 'Unknown'),
                'players_count': getattr(srv, 'players_count', 0),
                'slots': getattr(srv, 'slots', 20),
                'ram': getattr(srv, 'ram', 0),
                'motd': getattr(srv, 'motd', ''),
                'active_server_index': getattr(bot_instance.aternos, '_active_index', 0),
                'total_servers': len(getattr(bot_instance.aternos, 'servers', [])),
            }
        except Exception as e:
            return {'status': 'offline', 'error': str(e)}

    @app.get('/api/uptime', dependencies=[Depends(verify_auth)])
    async def get_uptime():
        return {
            'history': list(_UPTIME_HISTORY),
            'total_samples': len(_UPTIME_HISTORY),
        }

    @app.get('/api/logs', dependencies=[Depends(verify_auth)])
    async def get_logs(lines: int = Query(default=50, ge=5, le=200)):
        try:
            log_content = await bot_instance.aternos.get_log(max_lines=lines)
            return {'lines': lines, 'log': log_content}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post('/api/server/start', dependencies=[Depends(verify_auth)])
    async def trigger_start():
        try:
            started = await bot_instance.aternos.start()
            MetricsManager.record_command('web_start', started)
            return {'success': started, 'action': 'start'}
        except Exception as e:
            MetricsManager.record_command('web_start', False)
            raise HTTPException(status_code=500, detail=str(e))

    @app.post('/api/server/stop', dependencies=[Depends(verify_auth)])
    async def trigger_stop():
        try:
            stopped = await bot_instance.aternos.stop()
            MetricsManager.record_command('web_stop', stopped)
            return {'success': stopped, 'action': 'stop'}
        except Exception as e:
            MetricsManager.record_command('web_stop', False)
            raise HTTPException(status_code=500, detail=str(e))

    @app.post('/api/server/restart', dependencies=[Depends(verify_auth)])
    async def trigger_restart():
        try:
            restarted = await bot_instance.aternos.restart()
            MetricsManager.record_command('web_restart', restarted)
            return {'success': restarted, 'action': 'restart'}
        except Exception as e:
            MetricsManager.record_command('web_restart', False)
            raise HTTPException(status_code=500, detail=str(e))

    @app.post('/api/console/execute', dependencies=[Depends(verify_auth)])
    async def trigger_console(request: Request):
        try:
            payload = await request.json()
            raw_cmd = str(payload.get('command', '')).strip()
            from ..utils.security import sanitize_console_command
            cmd = sanitize_console_command(raw_cmd)
            await bot_instance.aternos.send_command(cmd)
            MetricsManager.record_command('web_console', True)
            return {'success': True, 'command': cmd}
        except Exception as e:
            MetricsManager.record_command('web_console', False)
            raise HTTPException(status_code=400, detail=str(e))

    @app.get('/', response_class=HTMLResponse, dependencies=[Depends(verify_auth)])
    @app.get('/dashboard', response_class=HTMLResponse, dependencies=[Depends(verify_auth)])
    async def dashboard_view():
        html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Aternos Bot — Live Server Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #090d16;
      --card-bg: rgba(22, 30, 49, 0.75);
      --card-border: rgba(255, 255, 255, 0.08);
      --text: #e2e8f0;
      --text-muted: #94a3b8;
      --primary: #3b82f6;
      --primary-hover: #2563eb;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --glow: rgba(59, 130, 246, 0.15);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', -apple-system, sans-serif;
      background: radial-gradient(circle at top right, #131c31 0%, #090d16 100%);
      color: var(--text);
      min-height: 100vh;
      padding: 2rem 1.5rem;
    }
    .container { max-width: 1100px; margin: 0 auto; }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 2rem;
      flex-wrap: wrap;
      gap: 1rem;
    }
    .brand { display: flex; align-items: center; gap: 0.75rem; }
    .brand h1 { font-size: 1.5rem; font-weight: 800; letter-spacing: -0.02em; }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.25rem 0.75rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .badge-online { background: rgba(16, 185, 129, 0.15); color: var(--success); border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-offline { background: rgba(239, 68, 68, 0.15); color: var(--danger); border: 1px solid rgba(239, 68, 68, 0.3); }
    .badge-starting { background: rgba(245, 158, 11, 0.15); color: var(--warning); border: 1px solid rgba(245, 158, 11, 0.3); }
    .pulse-dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; animation: pulse 2s infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.85); } }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
    .card {
      background: var(--card-bg);
      backdrop-filter: blur(12px);
      border: 1px solid var(--card-border);
      border-radius: 1rem;
      padding: 1.25rem;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }
    .card-title { font-size: 0.8rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.5rem; }
    .card-value { font-size: 1.6rem; font-weight: 700; color: #fff; font-family: 'JetBrains Mono', monospace; }
    .card-sub { font-size: 0.8rem; color: var(--text-muted); margin-top: 0.25rem; }
    .controls { display: flex; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 2rem; }
    button {
      padding: 0.65rem 1.25rem;
      border-radius: 0.5rem;
      font-weight: 600;
      font-size: 0.875rem;
      border: none;
      cursor: pointer;
      transition: all 0.2s ease;
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
    }
    .btn-primary { background: var(--primary); color: #fff; }
    .btn-primary:hover { background: var(--primary-hover); transform: translateY(-1px); }
    .btn-danger { background: rgba(239, 68, 68, 0.2); color: var(--danger); border: 1px solid rgba(239, 68, 68, 0.4); }
    .btn-danger:hover { background: rgba(239, 68, 68, 0.35); }
    .btn-secondary { background: rgba(255, 255, 255, 0.08); color: var(--text); border: 1px solid var(--card-border); }
    .btn-secondary:hover { background: rgba(255, 255, 255, 0.15); }
    .log-box {
      background: #060910;
      border: 1px solid var(--card-border);
      border-radius: 0.75rem;
      padding: 1rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.8rem;
      color: #cbd5e1;
      height: 320px;
      overflow-y: auto;
      white-space: pre-wrap;
      line-height: 1.5;
    }
    .chart-container {
      margin-top: 1rem;
      display: flex;
      gap: 4px;
      align-items: flex-end;
      height: 60px;
      padding-top: 10px;
    }
    .chart-bar {
      flex: 1;
      border-radius: 2px;
      background: #334155;
      min-height: 6px;
      transition: all 0.3s;
    }
    .chart-bar.online { background: var(--success); }
    .chart-bar.starting { background: var(--warning); }
    .chart-bar.offline { background: var(--danger); }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <svg width="40" height="40" viewBox="0 0 512 512" style="border-radius: 10px; filter: drop-shadow(0 0 8px rgba(88,101,242,0.4));">
          <rect width="512" height="512" rx="112" fill="#0b0f19" stroke="#1f293d" stroke-width="8" />
          <path d="M 130 250 A 136 136 0 0 1 382 250" fill="none" stroke="#5865F2" stroke-width="26" stroke-linecap="round" />
          <rect x="108" y="235" width="28" height="64" rx="14" fill="#5865F2" />
          <rect x="376" y="235" width="28" height="64" rx="14" fill="#5865F2" />
          <polygon points="256,150 360,208 256,266 152,208" fill="#10b981" stroke="#34d399" stroke-width="4" />
          <polygon points="152,208 256,266 256,380 152,322" fill="#3b82f6" stroke="#60a5fa" stroke-width="4" />
          <polygon points="256,266 360,208 360,322 256,380" fill="#6366f1" stroke="#818cf8" stroke-width="4" />
        </svg>
        <div>
          <h1>Aternos Management Dashboard</h1>
          <p style="font-size: 0.85rem; color: var(--text-muted);">Real-time monitoring and server operations</p>
        </div>
      </div>
      <div id="statusBadge" class="badge badge-offline">
        <span class="pulse-dot"></span>
        <span id="statusText">Checking...</span>
      </div>
    </header>

    <div class="grid">
      <div class="card">
        <div class="card-title">Server Address</div>
        <div class="card-value" id="serverAddress" style="font-size: 1.15rem;">...</div>
        <div class="card-sub" id="serverSoftware">Minecraft Server</div>
      </div>
      <div class="card">
        <div class="card-title">Active Players</div>
        <div class="card-value" id="playerCount">0 / 20</div>
        <div class="card-sub">Slots occupied</div>
      </div>
      <div class="card">
        <div class="card-title">Server Port</div>
        <div class="card-value" id="serverPort">...</div>
        <div class="card-sub">Direct connection</div>
      </div>
      <div class="card">
        <div class="card-title">Allocated RAM</div>
        <div class="card-value" id="serverRam">...</div>
        <div class="card-sub">Memory limit</div>
      </div>
    </div>

    <div class="controls">
      <button class="btn-primary" onclick="actionServer('start')">▶ Start Server</button>
      <button class="btn-danger" onclick="actionServer('stop')">⏹ Stop Server</button>
      <button class="btn-secondary" onclick="actionServer('restart')">🔄 Restart</button>
      <button class="btn-secondary" onclick="fetchStatus()">⚡ Refresh Now</button>
    </div>

    <div class="card" style="margin-bottom: 1.5rem;">
      <div class="card-title">Recent Uptime Activity (Last 60 Ticks)</div>
      <div class="chart-container" id="uptimeChart"></div>
    </div>

    <div class="card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
        <div class="card-title" style="margin: 0;">Recent Server Console Logs</div>
        <span style="font-size: 0.75rem; color: var(--text-muted);">Auto-refreshed</span>
      </div>
      <div class="log-box" id="logBox">Loading recent server logs...</div>
      <div style="display: flex; gap: 0.5rem; margin-top: 0.75rem;">
        <input id="terminalInput" type="text" placeholder="Type a Minecraft console command (e.g. say Hello World, time set day)..." style="flex: 1; background: rgba(0,0,0,0.4); border: 1px solid var(--card-border); color: #fff; padding: 0.6rem 0.85rem; border-radius: 8px; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; outline: none;" onkeydown="if(event.key === 'Enter') sendConsoleCommand()" />
        <button class="btn-primary" onclick="sendConsoleCommand()" style="padding: 0.6rem 1.25rem;">Execute ↵</button>
      </div>
      <div id="commandFeedback" style="font-size: 0.75rem; margin-top: 0.4rem; color: var(--text-muted);"></div>
    </div>
  </div>

  <script>
    async function fetchStatus() {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();
        
        document.getElementById('serverAddress').textContent = data.address || 'N/A';
        document.getElementById('serverPort').textContent = data.port || '25565';
        document.getElementById('playerCount').textContent = `${data.players_count || 0} / ${data.slots || 20}`;
        document.getElementById('serverSoftware').textContent = `${data.software || ''} ${data.version || ''}`.trim() || 'Minecraft';
        document.getElementById('serverRam').textContent = data.ram ? `${data.ram} MB` : 'Dynamic';

        const badge = document.getElementById('statusBadge');
        const text = document.getElementById('statusText');
        const st = (data.status || 'offline').toLowerCase();
        text.textContent = st.toUpperCase();
        
        badge.className = 'badge';
        if (st === 'online') badge.classList.add('badge-online');
        else if (['starting', 'loading', 'preparing'].includes(st)) badge.classList.add('badge-starting');
        else badge.classList.add('badge-offline');
      } catch (e) {
        console.error('Status fetch failed:', e);
      }
    }

    async function fetchLogs() {
      try {
        const res = await fetch('/api/logs?lines=40');
        const data = await res.json();
        document.getElementById('logBox').textContent = data.log || 'No logs available.';
      } catch (e) {
        document.getElementById('logBox').textContent = 'Unable to fetch logs.';
      }
    }

    async function fetchUptime() {
      try {
        const res = await fetch('/api/uptime');
        const data = await res.json();
        const container = document.getElementById('uptimeChart');
        container.innerHTML = '';
        const samples = (data.history || []).slice(-60);
        samples.forEach(s => {
          const bar = document.createElement('div');
          bar.className = `chart-bar ${s.status}`;
          bar.title = `${s.timestamp}: ${s.status} (${s.players} players)`;
          bar.style.height = s.status === 'online' ? '100%' : (s.status === 'starting' ? '50%' : '15%');
          container.appendChild(bar);
        });
      } catch (e) {}
    }

    async function actionServer(action) {
      if (!confirm(`Are you sure you want to ${action} the server?`)) return;
      try {
        const res = await fetch(`/api/server/${action}`, { method: 'POST' });
        const data = await res.json();
        alert(data.success ? `Server ${action} command sent successfully!` : `Action failed.`);
        setTimeout(fetchStatus, 1500);
      } catch (e) {
        alert('Request failed: ' + e);
      }
    }

    async function sendConsoleCommand() {
      const input = document.getElementById('terminalInput');
      const feedback = document.getElementById('commandFeedback');
      const cmd = input.value.trim();
      if (!cmd) return;
      
      feedback.textContent = `Dispatching command: /${cmd}...`;
      feedback.style.color = 'var(--text-muted)';
      try {
        const res = await fetch('/api/console/execute', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({command: cmd})
        });
        if (res.ok) {
          feedback.textContent = `✔ Command executed successfully.`;
          feedback.style.color = 'var(--success)';
          input.value = '';
          setTimeout(fetchLogs, 1200);
        } else {
          const err = await res.json();
          feedback.textContent = `✖ Error: ${err.detail || 'Failed'}`;
          feedback.style.color = 'var(--danger)';
        }
      } catch (e) {
        feedback.textContent = `✖ Request failed: ${e.message}`;
        feedback.style.color = 'var(--danger)';
      }
    }

    fetchStatus();
    fetchLogs();
    fetchUptime();
    setInterval(fetchStatus, 15000);
    setInterval(fetchLogs, 30000);
    setInterval(fetchUptime, 30000);
  </script>
</body>
</html>
"""
        return HTMLResponse(content=html)

    return app
