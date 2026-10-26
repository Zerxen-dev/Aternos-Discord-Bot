"""Thread-safe async wrapper around python-aternos with login retry + auto-reconnect.

Delegates core implementation to `bot.services.aternos_service` while maintaining
complete module-level API compatibility.
"""

from __future__ import annotations

import time
from python_aternos import Client, Lists
from .services.aternos_service import AternosError, AternosManager

__all__ = [
    'AternosManager',
    'AternosError',
    'Client',
    'Lists',
    'time',
]
