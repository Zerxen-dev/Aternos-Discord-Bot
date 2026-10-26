from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from bot.aternos_client import AternosManager


@pytest.fixture
def manager():
    mgr = AternosManager("testuser", "testpass")
    
    server1 = MagicMock()
    server1.subdomain = "survival"
    server1.status = "online"
    server1.software = "Paper"
    server1.version = "1.20.4"
    server1.fetch = MagicMock()

    server2 = MagicMock()
    server2.subdomain = "creative"
    server2.status = "offline"
    server2.software = "Spigot"
    server2.version = "1.19.2"
    server2.fetch = MagicMock()

    mgr._servers = [server1, server2]
    mgr._server = server1
    mgr._active_index = 0
    return mgr


def test_list_all_servers(manager):
    servers = manager.list_all_servers_blocking()
    assert len(servers) == 2
    assert servers[0]["subdomain"] == "survival"
    assert servers[0]["is_active"] is True
    assert servers[1]["subdomain"] == "creative"
    assert servers[1]["is_active"] is False


def test_select_server_by_index(manager):
    assert manager.select_server_blocking(1) is True
    assert manager._active_index == 1
    assert manager.server.subdomain == "creative"

    # Out of range index fails
    assert manager.select_server_blocking(99) is False
    assert manager._active_index == 1  # Unchanged


def test_select_server_by_subdomain(manager):
    assert manager.select_server_blocking("survival") is True
    assert manager._active_index == 0
    assert manager.server.subdomain == "survival"

    # Full address also works
    assert manager.select_server_blocking("creative.aternos.me") is True
    assert manager._active_index == 1
    assert manager.server.subdomain == "creative"

    # Non-existent subdomain fails
    assert manager.select_server_blocking("unknown-server") is False
    assert manager._active_index == 1  # Unchanged


@pytest.mark.asyncio
async def test_async_multi_server_methods(manager):
    servers = await manager.list_all_servers()
    assert len(servers) == 2

    success = await manager.select_server("survival")
    assert success is True
    assert manager._active_index == 0
