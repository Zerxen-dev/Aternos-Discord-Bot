"""Prometheus metrics collection and observability for AternosBot."""

from __future__ import annotations

import logging
from typing import Optional

try:
    from prometheus_client import (
        Counter,
        Gauge,
        Histogram,
        REGISTRY,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )
    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _PROMETHEUS_AVAILABLE = False

log = logging.getLogger('AternosBot.metrics')

if _PROMETHEUS_AVAILABLE:
    COMMANDS_TOTAL = Counter(
        'aternos_commands_total',
        'Total number of executed Discord commands',
        ['command', 'status'],
    )
    SERVER_STATUS_GAUGE = Gauge(
        'aternos_server_status',
        'Current status of the active Minecraft server (1=online, 0=offline, 2=starting)',
        ['subdomain'],
    )
    PLAYERS_ONLINE_GAUGE = Gauge(
        'aternos_players_online',
        'Current number of players online on the server',
        ['subdomain'],
    )
    API_LATENCY_HISTOGRAM = Histogram(
        'aternos_api_latency_seconds',
        'Latency of Aternos API interactions in seconds',
        ['operation'],
    )
else:
    COMMANDS_TOTAL = None
    SERVER_STATUS_GAUGE = None
    PLAYERS_ONLINE_GAUGE = None
    API_LATENCY_HISTOGRAM = None


class MetricsManager:
    """Helper wrapper for recording Prometheus metrics safely."""

    @staticmethod
    def record_command(command: str, success: bool = True) -> None:
        if _PROMETHEUS_AVAILABLE and COMMANDS_TOTAL:
            try:
                status = 'success' if success else 'failure'
                COMMANDS_TOTAL.labels(command=command, status=status).inc()
            except Exception:
                pass

    @staticmethod
    def update_server_state(subdomain: str, status: str, players_count: int) -> None:
        if not _PROMETHEUS_AVAILABLE:
            return
        try:
            status_val = 1 if status.lower() == 'online' else (2 if status.lower() in ('starting', 'loading', 'preparing') else 0)
            if SERVER_STATUS_GAUGE:
                SERVER_STATUS_GAUGE.labels(subdomain=subdomain).set(status_val)
            if PLAYERS_ONLINE_GAUGE:
                PLAYERS_ONLINE_GAUGE.labels(subdomain=subdomain).set(players_count)
        except Exception:
            pass

    @staticmethod
    def get_metrics_payload() -> tuple[bytes, str]:
        """Return Prometheus metrics bytes and content type."""
        if not _PROMETHEUS_AVAILABLE:
            return b'# Prometheus metrics not installed\n', 'text/plain'
        return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
