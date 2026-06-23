"""Environment-based configuration with fail-fast validation."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


def _split_ids(raw: str) -> frozenset:
    ids = set()
    for chunk in raw.split(','):
        chunk = chunk.strip()
        if not chunk:
            continue
        if not chunk.isdigit():
            raise ConfigError(f"Invalid ID '{chunk}' — IDs must be numeric Discord snowflakes.")
        ids.add(int(chunk))
    return frozenset(ids)


def _int_env(env: Mapping[str, str], name: str, default: int) -> int:
    raw = (env.get(name) or '').strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as e:
        raise ConfigError(f"Environment variable {name} must be an integer, got '{raw}'.") from e


@dataclass(frozen=True)
class Config:
    discord_token: str
    aternos_user: str
    aternos_pass: str
    admin_role_ids: frozenset = field(default_factory=frozenset)
    admin_user_ids: frozenset = field(default_factory=frozenset)
    autostart_poll_seconds: int = 60
    autostop_default_minutes: int = 20
    state_file: Optional[Path] = None

    @property
    def restricted(self) -> bool:
        """True if admin-only commands are gated behind specific roles/users."""
        return bool(self.admin_role_ids or self.admin_user_ids)


def load_config(env: Optional[Mapping[str, str]] = None) -> Config:
    """Load and validate configuration from environment variables.

    Raises ConfigError with a clear, actionable message if anything required
    is missing or malformed — callers should let this crash startup rather
    than silently falling back to defaults.
    """
    env = env if env is not None else os.environ

    def required(name: str) -> str:
        value = (env.get(name) or '').strip()
        if not value:
            raise ConfigError(
                f"Missing required environment variable: {name}. "
                "Set it in your .env file (local) or the Variables tab of your "
                "hosting panel, then restart the bot."
            )
        return value

    base_dir = Path(__file__).resolve().parent.parent
    state_file = Path(env.get('STATE_FILE') or (base_dir / 'autostart_state.json'))

    return Config(
        discord_token=required('DISCORD_TOKEN'),
        aternos_user=required('ATERNOS_USER'),
        aternos_pass=required('ATERNOS_PASS'),
        admin_role_ids=_split_ids(env.get('ADMIN_ROLE_IDS', '')),
        admin_user_ids=_split_ids(env.get('ADMIN_USER_IDS', '')),
        autostart_poll_seconds=_int_env(env, 'AUTOSTART_POLL_SECONDS', 60),
        autostop_default_minutes=_int_env(env, 'AUTOSTOP_DEFAULT_MINUTES', 20),
        state_file=state_file,
    )
