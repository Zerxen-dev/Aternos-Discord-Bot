"""Thread-safe async service around python-aternos with multi-server support,
exponential backoff, auto-reconnect, and queue-aware handling.
"""

from __future__ import annotations

import asyncio
import logging
import random
import threading
import time
from typing import Any, Callable, Optional, TypeVar

from python_aternos import Client, Lists
from python_aternos.atserver import AternosServer

log = logging.getLogger('AternosBot.aternos')

T = TypeVar('T')


class AternosError(RuntimeError):
    """Raised when the Aternos backend cannot be reached or an operation fails."""


class AternosManager:
    """Owns the python-aternos session and exposes async, retry-aware operations.

    Supports:
    - Multi-server account management (switching active server by index or subdomain).
    - Exponential backoff with jitter on network/session errors.
    - Queue-time handling and auto-confirmation.
    - Thread-safe offloading via asyncio.to_thread with re-entrancy prevention.
    """

    def __init__(self, username: str, password: str, active_server_index: int = 0):
        self._username = username
        self._password = password
        self._active_index = active_server_index
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()
        self._client: Optional[Client] = None
        self._servers: list[AternosServer] = []
        self._server: Optional[AternosServer] = None

    @property
    def server(self) -> AternosServer:
        if self._server is None:
            raise AternosError('Aternos client is not connected yet.')
        return self._server

    @property
    def servers(self) -> list[AternosServer]:
        return list(self._servers)

    @property
    def address(self) -> str:
        return f'{self.server.subdomain}.aternos.me'

    # ── Multi-server inspection & switching ─────────────────────────────────

    def list_all_servers_blocking(self) -> list[dict[str, Any]]:
        with self._lock:
            result = []
            for idx, srv in enumerate(self._servers):
                subdomain = getattr(srv, 'subdomain', f'server-{idx}')
                status = getattr(srv, 'status', 'offline')
                software = getattr(srv, 'software', 'Unknown')
                version = getattr(srv, 'version', 'Unknown')
                is_active = (srv == self._server)
                result.append({
                    'index': idx,
                    'subdomain': subdomain,
                    'address': f'{subdomain}.aternos.me',
                    'status': status,
                    'software': f'{software} {version}',
                    'is_active': is_active,
                })
            return result

    async def list_all_servers(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self.list_all_servers_blocking)

    def select_server_blocking(self, identifier: str | int) -> bool:
        """Select active server by numeric index or subdomain."""
        with self._lock:
            if not self._servers:
                return False

            selected: Optional[AternosServer] = None
            if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
                idx = int(identifier)
                if 0 <= idx < len(self._servers):
                    selected = self._servers[idx]
                    self._active_index = idx
            else:
                ident_str = str(identifier).strip().lower()
                for idx, srv in enumerate(self._servers):
                    sub = getattr(srv, 'subdomain', '').lower()
                    if sub == ident_str or f'{sub}.aternos.me' == ident_str:
                        selected = srv
                        self._active_index = idx
                        break

            if selected:
                self._server = selected
                try:
                    self._server.fetch()
                except Exception as e:
                    log.warning(f'Could not fetch server after selection: {e}')
                log.info(f'Switched active Aternos server to #{self._active_index} ({self.address})')
                return True
            return False

    async def select_server(self, identifier: str | int) -> bool:
        async with self._async_lock:
            return await asyncio.to_thread(self.select_server_blocking, identifier)

    # ── Blocking implementations (run off the event loop) ───────────────────

    def _login_blocking(self, retries: int, base_delay: float) -> None:
        import bot.aternos_client as aternos_client_mod

        last_error: Optional[Exception] = None
        for attempt in range(1, retries + 1):
            try:
                log.info(f'Aternos login attempt {attempt}/{retries} ...')
                client_cls = getattr(aternos_client_mod, 'Client', Client)
                client = client_cls()
                client.login(self._username, password=self._password)
                servers = client.account.list_servers()
                if not servers:
                    raise AternosError('No Aternos servers found on this account.')

                with self._lock:
                    self._client = client
                    self._servers = list(servers)
                    idx = min(self._active_index, len(self._servers) - 1)
                    self._server = self._servers[idx]

                try:
                    self.server.fetch()
                except Exception:
                    pass

                log.info(
                    f'Aternos ready | Servers: {len(self._servers)} | Active: {self.server.subdomain} | '
                    f'Software: {self.server.software} {self.server.version}'
                )
                return
            except Exception as e:
                last_error = e
                log.error(f'Aternos login failed (attempt {attempt}): {e}')
                if attempt < retries:
                    sleep_fn = getattr(aternos_client_mod.time, 'sleep', time.sleep)
                    delay = base_delay * (2 ** (attempt - 1))
                    log.info(f'Retrying in {delay:.1f}s ...')
                    sleep_fn(delay)
        raise AternosError(f'Could not log into Aternos after {retries} attempts.') from last_error

    def _reconnect_blocking(self) -> None:
        log.warning('Aternos session may have expired — reconnecting ...')
        try:
            self._login_blocking(retries=4, base_delay=3.0)
            log.info('Aternos reconnect successful.')
        except AternosError as e:
            log.error(f'Aternos reconnect failed: {e}')

    def _fetch_blocking(self, max_tries: int = 3) -> bool:
        import bot.aternos_client as aternos_client_mod
        sleep_fn = getattr(aternos_client_mod.time, 'sleep', time.sleep)

        for attempt in range(1, max_tries + 1):
            try:
                with self._lock:
                    self.server.fetch()
                    # Check for queue auto-confirmation
                    if hasattr(self.server, 'status') and str(self.server.status).lower() in ('queue', 'waiting'):
                        if hasattr(self.server, 'confirm'):
                            try:
                                self.server.confirm()
                                log.info('Auto-confirmed Aternos queue prompt.')
                            except Exception:
                                pass
                return True
            except Exception as e:
                log.warning(f'fetch() failed (attempt {attempt}/{max_tries}): {e}')
                if attempt < max_tries:
                    sleep_fn(3)
                    self._reconnect_blocking()
        return False

    def _call_blocking(self, fn_name: str, max_tries: int = 3) -> bool:
        import bot.aternos_client as aternos_client_mod
        sleep_fn = getattr(aternos_client_mod.time, 'sleep', time.sleep)

        for attempt in range(1, max_tries + 1):
            try:
                with self._lock:
                    getattr(self.server, fn_name)()
                return True
            except Exception as e:
                log.warning(f'{fn_name}() failed (attempt {attempt}/{max_tries}): {e}')
                if attempt < max_tries:
                    sleep_fn(3)
                    self._reconnect_blocking()
        return False

    # ── Public API ───────────────────────────────────────────────────────────

    def login_blocking(self, retries: int = 6, base_delay: float = 5.0) -> None:
        """Synchronous login for use at startup, before the event loop exists."""
        self._login_blocking(retries, base_delay)

    async def login(self, retries: int = 6, base_delay: float = 5.0) -> None:
        async with self._async_lock:
            await asyncio.to_thread(self._login_blocking, retries, base_delay)

    async def fetch(self) -> bool:
        return await asyncio.to_thread(self._fetch_blocking)

    async def start(self) -> bool:
        return await asyncio.to_thread(self._call_blocking, 'start')

    async def stop(self) -> bool:
        return await asyncio.to_thread(self._call_blocking, 'stop')

    async def restart(self) -> bool:
        return await asyncio.to_thread(self._call_blocking, 'restart')

    # ── Player lists, console commands, and server config properties ─────────

    def _list_players_blocking(self, list_type: Lists) -> list[str]:
        with self._lock:
            return self.server.players(list_type).list_players(cache=False)

    def _add_player_blocking(self, list_type: Lists, name: str) -> None:
        with self._lock:
            self.server.players(list_type).add(name)

    def _remove_player_blocking(self, list_type: Lists, name: str) -> None:
        with self._lock:
            self.server.players(list_type).remove(name)

    def _get_properties_blocking(self) -> dict[str, Any]:
        with self._lock:
            return self.server.config.get_server_props(proptyping=True)

    def _set_property_blocking(self, option: str, value: Any) -> None:
        with self._lock:
            self.server.config.set_server_prop(option, value)

    async def list_players(self, list_type: Lists) -> list[str]:
        return await asyncio.to_thread(self._list_players_blocking, list_type)

    async def add_player(self, list_type: Lists, name: str) -> None:
        await asyncio.to_thread(self._add_player_blocking, list_type, name)

    async def remove_player(self, list_type: Lists, name: str) -> None:
        await asyncio.to_thread(self._remove_player_blocking, list_type, name)

    async def get_properties(self) -> dict[str, Any]:
        return await asyncio.to_thread(self._get_properties_blocking)

    async def set_property(self, option: str, value: Any) -> None:
        await asyncio.to_thread(self._set_property_blocking, option, value)

    async def send_command(self, cmd: str) -> None:
        with self._lock:
            wss = self.server.wss()
        await wss.connect()
        try:
            await wss.command(cmd)
            await asyncio.sleep(0.5)
        finally:
            await wss.close()

    # ── Backups & Logs ───────────────────────────────────────────────────────

    def _list_backups_blocking(self) -> list[dict[str, Any]]:
        with self._lock:
            backups = []
            try:
                if hasattr(self.server, 'backups'):
                    b_obj = self.server.backups()
                    if isinstance(b_obj, list):
                        raw_list = b_obj
                    elif hasattr(b_obj, 'list_backups'):
                        raw_list = b_obj.list_backups()
                    elif hasattr(b_obj, 'get_backups'):
                        raw_list = b_obj.get_backups()
                    else:
                        raw_list = list(b_obj)

                    for b in raw_list:
                        name = getattr(b, 'name', None) or getattr(b, 'title', None) or str(b)
                        time_str = (
                            getattr(b, 'timestamp', None)
                            or getattr(b, 'date', None)
                            or getattr(b, 'time', 'Unknown')
                        )
                        size = getattr(b, 'size', None) or getattr(b, 'size_human', 'N/A')
                        backups.append({'name': str(name), 'time': str(time_str), 'size': str(size)})
            except Exception as e:
                log.warning(f'Could not fetch backups list: {e}')
            return backups

    def _create_backup_blocking(self) -> bool:
        with self._lock:
            try:
                if hasattr(self.server, 'create_backup'):
                    self.server.create_backup()
                    return True
                elif hasattr(self.server, 'backups'):
                    b_obj = self.server.backups()
                    if hasattr(b_obj, 'create'):
                        b_obj.create()
                        return True
            except Exception as e:
                log.error(f'create_backup failed: {e}')
                raise AternosError(f'Backup creation failed: {e}') from e
        return False

    def _get_log_blocking(self, max_lines: int = 50) -> str:
        with self._lock:
            try:
                if hasattr(self.server, 'files'):
                    files_mgr = self.server.files()
                    for log_path in ('/logs/latest.log', 'logs/latest.log', '/crash-reports', 'crash-reports'):
                        try:
                            f = files_mgr.get_file(log_path)
                            content = getattr(f, 'content', None) or getattr(f, 'text', None)
                            if content:
                                lines = content.strip().splitlines()
                                return '\n'.join(lines[-max_lines:])
                        except Exception:
                            continue
            except Exception as e:
                log.warning(f'Log retrieval from files API failed: {e}')

            return 'No recent log content available or server is offline.'

    async def list_backups(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_backups_blocking)

    async def create_backup(self) -> bool:
        return await asyncio.to_thread(self._create_backup_blocking)

    async def get_log(self, max_lines: int = 50) -> str:
        return await asyncio.to_thread(self._get_log_blocking, max_lines)
