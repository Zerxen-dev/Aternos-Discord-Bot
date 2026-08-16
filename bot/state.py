"""Persistent bot settings (autostart / autostop) backed by a small JSON file."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Optional, Any


log = logging.getLogger('AternosBot.state')


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

    def save(self, path: Path) -> None:
        try:
            path.write_text(json.dumps(asdict(self), indent=2), encoding='utf-8')
        except OSError as e:
            log.error(f'Failed to save state to {path}: {e}')

    @classmethod
    def load(cls, path: Path) -> 'BotState':
        if not path.exists():
            log.info('No saved state file found — starting fresh.')
            return cls()
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as e:
            log.error(f'Failed to load state from {path}: {e} — starting fresh.')
            return cls()

        # Migrate the old (v1) autostart-only state file shape.
        if 'autostart_enabled' not in data and 'enabled' in data:
            data = {
                'autostart_enabled': data.get('enabled', False),
                'autostart_channel_id': data.get('channel_id'),
                'autostart_set_by': data.get('set_by'),
            }

        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)
