"""Environment-based configuration with Pydantic Settings and fail-fast validation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


def _split_ids(raw: Any) -> frozenset[int]:
    if isinstance(raw, (set, frozenset)):
        return frozenset(raw)
    if isinstance(raw, (list, tuple)):
        return frozenset(int(x) for x in raw)
    if not isinstance(raw, str):
        return frozenset()

    ids: set[int] = set()
    for chunk in raw.split(','):
        chunk = chunk.strip()
        if not chunk:
            continue
        if not chunk.isdigit():
            raise ConfigError(f"Invalid ID '{chunk}' — IDs must be numeric Discord snowflakes.")
        ids.add(int(chunk))
    return frozenset(ids)


class Config(BaseSettings):
    """Application configuration with Pydantic v2 validation."""

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
        arbitrary_types_allowed=True,
    )

    discord_token: str = Field(..., alias='DISCORD_TOKEN')
    aternos_user: str = Field(..., alias='ATERNOS_USER')
    aternos_pass: str = Field(..., alias='ATERNOS_PASS')

    admin_role_ids: frozenset[int] = Field(default_factory=frozenset, alias='ADMIN_ROLE_IDS')
    admin_user_ids: frozenset[int] = Field(default_factory=frozenset, alias='ADMIN_USER_IDS')

    autostart_poll_seconds: int = Field(default=60, alias='AUTOSTART_POLL_SECONDS')
    autostop_default_minutes: int = Field(default=20, alias='AUTOSTOP_DEFAULT_MINUTES')
    state_file: Optional[Path] = Field(default=None, alias='STATE_FILE')

    # Enhanced Features
    web_dashboard_enabled: bool = Field(default=True, alias='WEB_DASHBOARD_ENABLED')
    web_dashboard_port: int = Field(default=8080, alias='WEB_DASHBOARD_PORT')
    web_dashboard_host: str = Field(default='0.0.0.0', alias='WEB_DASHBOARD_HOST')
    web_api_key: Optional[str] = Field(default=None, alias='WEB_API_KEY')

    ai_enabled: bool = Field(default=False, alias='AI_ENABLED')
    ai_provider: str = Field(default='gemini', alias='AI_PROVIDER')
    ai_api_key: Optional[str] = Field(default=None, alias='AI_API_KEY')

    sentry_dsn: Optional[str] = Field(default=None, alias='SENTRY_DSN')
    metrics_enabled: bool = Field(default=True, alias='METRICS_ENABLED')
    active_server_index: int = Field(default=0, alias='ACTIVE_SERVER_INDEX')

    def __init__(self, **values: Any):
        # Support positional and lowercase kwargs for backward compatibility
        try:
            super().__init__(**values)
        except ConfigError:
            raise
        except Exception as e:
            raise ConfigError(f"Configuration error: {e}") from e

    @field_validator('admin_role_ids', 'admin_user_ids', mode='before')
    @classmethod
    def validate_ids(cls, v: Any) -> frozenset[int]:
        return _split_ids(v)

    @field_validator('autostart_poll_seconds', 'autostop_default_minutes', 'web_dashboard_port', mode='before')
    @classmethod
    def validate_ints(cls, v: Any, info) -> int:
        if v is None:
            return 60 if info.field_name == 'autostart_poll_seconds' else 20
        if isinstance(v, int):
            return v
        raw = str(v).strip()
        if not raw:
            return 60 if info.field_name == 'autostart_poll_seconds' else 20
        try:
            return int(raw)
        except ValueError as e:
            field_env = info.field_name.upper()
            raise ConfigError(f"Environment variable {field_env} must be an integer, got '{raw}'.") from e

    @property
    def restricted(self) -> bool:
        """True if admin-only commands are gated behind specific roles/users."""
        return bool(self.admin_role_ids or self.admin_user_ids)


def _load_dotenv_if_present(base_dir: Path) -> None:
    env_file = base_dir / '.env'
    if env_file.is_file():
        try:
            for line in env_file.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k, v = k.strip(), v.strip()
                if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                    v = v[1:-1]
                if k not in os.environ:
                    os.environ[k] = v
        except Exception:
            pass


def load_config(env: Optional[Mapping[str, str]] = None) -> Config:
    """Load and validate configuration from environment variables.

    Raises ConfigError with an actionable message if required parameters are missing.
    """
    base_dir = Path(__file__).resolve().parent.parent
    if env is None:
        _load_dotenv_if_present(base_dir)
        env_dict = dict(os.environ)
    else:
        env_dict = dict(env)

    # Validate required keys explicitly for clear error messages
    required_keys = [
        ('DISCORD_TOKEN', 'discord_token'),
        ('ATERNOS_USER', 'aternos_user'),
        ('ATERNOS_PASS', 'aternos_pass'),
    ]
    for key, attr in required_keys:
        val = env_dict.get(key)
        if val is None:
            val = env_dict.get(attr)
        if val is None or not str(val).strip():
            raise ConfigError(
                f"Missing required environment variable: {key}. "
                "Set it in your .env file (local) or the Variables tab of your "
                "hosting panel, then restart the bot."
            )

    # Set default state_file if not provided
    if not env_dict.get('STATE_FILE') and not env_dict.get('state_file'):
        env_dict['STATE_FILE'] = str(base_dir / 'autostart_state.json')

    try:
        return Config(**env_dict)
    except ConfigError:
        raise
    except Exception as e:
        raise ConfigError(f"Configuration validation failed: {e}") from e
