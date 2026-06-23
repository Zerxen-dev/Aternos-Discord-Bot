"""Thread-safe async wrapper around python-aternos with login retry + auto-reconnect."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Optional

from python_aternos import Client
from python_aternos.atserver import AternosServer

log = logging.getLogger('AternosBot.aternos')


class AternosError(RuntimeError):
    """Raised when the Aternos backend cannot be reached after retries."""


class AternosManager:
    """Owns the python-aternos session and exposes async, retry-aware operations.

    All blocking python-aternos calls run in a worker thread via
    ``asyncio.to_thread`` so the Discord event loop never stalls on them.
    """

    def __init__(self, username: str, password: str):
        self._username = username
        self._password = password
        self._lock = threading.Lock()
        self._server: Optional[AternosServer] = None

    @property
    def server(self) -> AternosServer:
        if self._server is None:
            raise AternosError('Aternos client is not connected yet.')
        return self._server

    @property
    def address(self) -> str:
        return f'{self.server.subdomain}.aternos.me'

    # ── blocking implementations (run off the event loop) ──────────────────

    def _login_blocking(self, retries: int, base_delay: float) -> None:
        last_error: Optional[Exception] = None
        for attempt in range(1, retries + 1):
            try:
                log.info(f'Aternos login attempt {attempt}/{retries} ...')
                client = Client()
                client.login(self._username, password=self._password)
                servers = client.account.list_servers()
                if not servers:
                    raise AternosError('No Aternos servers found on this account.')
                server = servers[0]
                server.fetch()
                with self._lock:
                    self._server = server
                log.info(
                    f'Aternos ready  |  Server: {server.subdomain}  |  '
                    f'Software: {server.software} {server.version}'
                )
                return
            except Exception as e:
                last_error = e
                log.error(f'Aternos login failed (attempt {attempt}): {e}')
                if attempt < retries:
                    delay = base_delay * (2 ** (attempt - 1))
                    log.info(f'Retrying in {delay:.0f}s ...')
                    time.sleep(delay)
        raise AternosError(f'Could not log into Aternos after {retries} attempts.') from last_error

    def _reconnect_blocking(self) -> None:
        log.warning('Aternos session may have expired — reconnecting ...')
        try:
            self._login_blocking(retries=4, base_delay=3.0)
            log.info('Aternos reconnect successful.')
        except AternosError as e:
            log.error(f'Aternos reconnect failed: {e}')

    def _fetch_blocking(self, max_tries: int = 3) -> bool:
        for attempt in range(1, max_tries + 1):
            try:
                with self._lock:
                    self.server.fetch()
                return True
            except Exception as e:
                log.warning(f'fetch() failed (attempt {attempt}/{max_tries}): {e}')
                if attempt < max_tries:
                    time.sleep(3)
                    self._reconnect_blocking()
        return False

    def _call_blocking(self, fn_name: str, max_tries: int = 3) -> bool:
        for attempt in range(1, max_tries + 1):
            try:
                with self._lock:
                    getattr(self.server, fn_name)()
                return True
            except Exception as e:
                log.warning(f'{fn_name}() failed (attempt {attempt}/{max_tries}): {e}')
                if attempt < max_tries:
                    time.sleep(3)
                    self._reconnect_blocking()
        return False

    # ── public API ───────────────────────────────────────────────────────────

    def login_blocking(self, retries: int = 6, base_delay: float = 5.0) -> None:
        """Synchronous login for use at startup, before the event loop exists."""
        self._login_blocking(retries, base_delay)

    async def login(self, retries: int = 6, base_delay: float = 5.0) -> None:
        await asyncio.to_thread(self._login_blocking, retries, base_delay)

    async def fetch(self) -> bool:
        return await asyncio.to_thread(self._fetch_blocking)

    async def start(self) -> bool:
        return await asyncio.to_thread(self._call_blocking, 'start')

    async def stop(self) -> bool:
        return await asyncio.to_thread(self._call_blocking, 'stop')

    async def restart(self) -> bool:
        return await asyncio.to_thread(self._call_blocking, 'restart')
