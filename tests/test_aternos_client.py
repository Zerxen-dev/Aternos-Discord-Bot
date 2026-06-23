import pytest

import bot.aternos_client as aternos_client
from bot.aternos_client import AternosError, AternosManager


class FakeServer:
    def __init__(self, subdomain='myserver', fail_fetch=False):
        self.subdomain = subdomain
        self.software = 'Vanilla'
        self.version = '1.20.1'
        self.fetch_calls = 0
        self.fail_fetch = fail_fetch
        self.started = False
        self.stopped = False
        self.restarted = False

    def fetch(self):
        self.fetch_calls += 1
        if self.fail_fetch:
            raise RuntimeError('fetch failed')

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def restart(self):
        self.restarted = True


class FakeAccount:
    def __init__(self, servers):
        self._servers = servers

    def list_servers(self):
        return self._servers


class FakeClient:
    """Stand-in for python_aternos.Client; instantiated fresh on every login."""

    instances = []
    fail_logins = 0
    servers = None

    def __init__(self):
        FakeClient.instances.append(self)
        self.account = None

    def login(self, username, password=None, code=None):
        if FakeClient.fail_logins > 0:
            FakeClient.fail_logins -= 1
            raise RuntimeError('login failed')
        self.account = FakeAccount(FakeClient.servers if FakeClient.servers is not None else [FakeServer()])


@pytest.fixture(autouse=True)
def reset_fake_client(monkeypatch):
    FakeClient.instances = []
    FakeClient.fail_logins = 0
    FakeClient.servers = None
    monkeypatch.setattr(aternos_client, 'Client', FakeClient)
    monkeypatch.setattr(aternos_client.time, 'sleep', lambda seconds: None)


def test_login_blocking_success():
    manager = AternosManager('user', 'pass')
    manager.login_blocking(retries=3, base_delay=1.0)
    assert manager.server is not None
    assert len(FakeClient.instances) == 1


def test_login_blocking_retries_then_succeeds():
    FakeClient.fail_logins = 2
    manager = AternosManager('user', 'pass')
    manager.login_blocking(retries=3, base_delay=1.0)
    assert manager.server is not None
    assert len(FakeClient.instances) == 3


def test_login_blocking_raises_after_exhausting_retries():
    FakeClient.fail_logins = 5
    manager = AternosManager('user', 'pass')
    with pytest.raises(AternosError):
        manager.login_blocking(retries=3, base_delay=1.0)


def test_login_blocking_raises_when_no_servers_found():
    FakeClient.servers = []
    manager = AternosManager('user', 'pass')
    with pytest.raises(AternosError):
        manager.login_blocking(retries=1, base_delay=1.0)


def test_server_property_before_login_raises():
    manager = AternosManager('user', 'pass')
    with pytest.raises(AternosError):
        _ = manager.server


def test_address_uses_subdomain():
    manager = AternosManager('user', 'pass')
    manager.login_blocking(retries=1, base_delay=1.0)
    assert manager.address == 'myserver.aternos.me'


async def test_fetch_success():
    manager = AternosManager('user', 'pass')
    manager.login_blocking(retries=1, base_delay=1.0)
    assert await manager.fetch() is True
    assert manager.server.fetch_calls >= 1


async def test_fetch_failure_returns_false():
    manager = AternosManager('user', 'pass')
    manager.login_blocking(retries=1, base_delay=1.0)
    manager.server.fail_fetch = True
    # _reconnect_blocking will create a fresh, also-failing FakeServer on retry.
    FakeClient.servers = [FakeServer(fail_fetch=True)]
    assert await manager.fetch() is False


async def test_start_stop_restart():
    manager = AternosManager('user', 'pass')
    manager.login_blocking(retries=1, base_delay=1.0)

    assert await manager.start() is True
    assert manager.server.started is True

    assert await manager.stop() is True
    assert manager.server.stopped is True

    assert await manager.restart() is True
    assert manager.server.restarted is True
