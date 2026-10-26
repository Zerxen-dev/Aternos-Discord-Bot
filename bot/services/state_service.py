"""Thread-safe and atomic persistent state management for bot automation."""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger('AternosBot.state')

_STATE_LOCK = threading.Lock()


@dataclass
class BotState:
    autostart_enabled: bool = False
    autostart_channel_id: Optional[int] = None
    autostart_set_by: Optional[str] = None

    autostop_enabled: bool = False
    autostop_minutes: int = 20
    autostop_channel_id: Optional[int] = None
    autostop_set_by: Optional[str] = None

    # Status Channel & Live Pinned Embed
    status_channel_id: Optional[int] = None
    status_message_id: Optional[int] = None
    status_voice_channel_id: Optional[int] = None

    # Alerts & Role Ping
    alerts_channel_id: Optional[int] = None
    alerts_role_id: Optional[int] = None
    alerts_notify_on: str = 'all'  # 'all', 'online', 'offline', 'players'

    # Scheduled Server Timers
    schedules: list[dict[str, Any]] = field(default_factory=list)

    # Multi-Server / Multi-Account support
    active_server_id: Optional[str] = None
    active_server_name: Optional[str] = None
    server_configs: dict[str, Any] = field(default_factory=dict)

    def save(self, path: Path) -> None:
        """Atomically persist state to disk by writing to a temporary file and renaming."""
        with _STATE_LOCK:
            try:
                target_dir = path.parent
                target_dir.mkdir(parents=True, exist_ok=True)
                temp_path = path.with_suffix('.tmp')
                
                content = json.dumps(asdict(self), indent=2)
                temp_path.write_text(content, encoding='utf-8')
                
                # Atomic rename / replace
                os.replace(temp_path, path)
            except OSError as e:
                log.error(f'Failed to atomically save state to {path}: {e}')

    @classmethod
    def load(cls, path: Path) -> 'BotState':
        """Load persisted state from disk with automated schema migration."""
        with _STATE_LOCK:
            if not path.exists():
                log.info('No saved state file found — starting fresh.')
                return cls()
            try:
                data = json.loads(path.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError) as e:
                log.error(f'Failed to load state from {path}: {e} — starting fresh.')
                return cls()

            # Migrate legacy v1 autostart-only state shape
            if 'autostart_enabled' not in data and 'enabled' in data:
                data = {
                    'autostart_enabled': data.get('enabled', False),
                    'autostart_channel_id': data.get('channel_id'),
                    'autostart_set_by': data.get('set_by'),
                }

            known = {f.name for f in fields(cls)}
            filtered = {k: v for k, v in data.items() if k in known}
            return cls(**filtered)
