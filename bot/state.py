"""Persistent bot settings backed by atomic JSON persistence."""

from __future__ import annotations

from .services.state_service import BotState, _STATE_LOCK

__all__ = ['BotState', '_STATE_LOCK']
