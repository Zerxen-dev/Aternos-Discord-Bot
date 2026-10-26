from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from bot.services.web_service import create_web_app, record_uptime_sample, _UPTIME_HISTORY


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.config.web_api_key = "secret123"
    
    server = MagicMock()
    server.subdomain = "mycraft"
    server.status = "online"
    server.players_count = 5
    server.slots = 20
    server.port = 25565
    server.software = "Paper"
    server.version = "1.20.4"
    server.ip = "mycraft.aternos.me"
    server.ram = 2048
    
    bot.aternos.server = server
    bot.aternos.start = AsyncMock(return_value=True)
    bot.aternos.stop = AsyncMock(return_value=True)
    bot.aternos.restart = AsyncMock(return_value=True)
    bot.aternos.get_log = AsyncMock(return_value="[12:00:00] [Server thread/INFO]: Done (2.1s)!")
    bot.aternos.send_command = AsyncMock(return_value=True)
    return bot


@pytest.fixture
def client(mock_bot):
    app = create_web_app(mock_bot)
    return TestClient(app)


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "time" in data


def test_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "aternos_server_status" in response.text


def test_auth_protection(client):
    # Unauthenticated should fail with 401
    resp = client.get("/api/status")
    assert resp.status_code == 401
    assert "Invalid or missing" in resp.json()["detail"]

    # Wrong key should fail
    resp = client.get("/api/status", headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401

    # Valid header key
    resp = client.get("/api/status", headers={"X-API-Key": "secret123"})
    assert resp.status_code == 200
    assert resp.json()["subdomain"] == "mycraft"
    assert resp.json()["status"] == "online"

    # Valid query key
    resp = client.get("/api/status?key=secret123")
    assert resp.status_code == 200
    assert resp.json()["players_count"] == 5


def test_uptime_recording(client):
    _UPTIME_HISTORY.clear()
    record_uptime_sample("mycraft", "online", 5)
    
    resp = client.get("/api/uptime", headers={"X-API-Key": "secret123"})
    assert resp.status_code == 200
    samples = resp.json()["history"]
    assert len(samples) == 1
    assert samples[0]["subdomain"] == "mycraft"
    assert samples[0]["status"] == "online"
    assert samples[0]["players"] == 5


def test_logs_endpoint(client):
    resp = client.get("/api/logs", headers={"X-API-Key": "secret123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "[Server thread/INFO]" in data["log"]


def test_server_action_endpoints(client, mock_bot):
    # Start
    resp = client.post("/api/server/start", headers={"X-API-Key": "secret123"})
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    mock_bot.aternos.start.assert_called_once()

    # Stop
    resp = client.post("/api/server/stop", headers={"X-API-Key": "secret123"})
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    mock_bot.aternos.stop.assert_called_once()

    # Restart
    resp = client.post("/api/server/restart", headers={"X-API-Key": "secret123"})
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    mock_bot.aternos.restart.assert_called_once()


def test_dashboard_html_view(client):
    resp = client.get("/?key=secret123")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Live Server Dashboard" in resp.text
    assert "Aternos Management Dashboard" in resp.text
    assert "fetchStatus" in resp.text


def test_console_execute_endpoint(client, mock_bot):
    # Valid command
    resp = client.post(
        "/api/console/execute",
        headers={"X-API-Key": "secret123"},
        json={"command": "say Hello Web Terminal"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    mock_bot.aternos.send_command.assert_called_with("say Hello Web Terminal")

    # Malicious injection rejected with 400
    resp = client.post(
        "/api/console/execute",
        headers={"X-API-Key": "secret123"},
        json={"command": "say hello; rm -rf /"},
    )
    assert resp.status_code == 400
    assert "disallowed" in resp.json()["detail"]
