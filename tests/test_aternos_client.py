import pytest

import bot.aternos_client as aternos_client
from bot.aternos_client import AternosError, AternosManager


class FakePlayersList:
    def __init__(self, list_type):
        self.list_type = list_type
        self.players = ["player1", "player2"]

    def list_players(self, cache=False):
        return self.players

    def add(self, name):
        self.players.append(name)

    def remove(self, name):
        if name in self.players:
            self.players.remove(name)


class FakeAternosConfig:
    def __init__(self):
        self.props = {"difficulty": "easy", "pvp": True}

    def get_server_props(self, proptyping=True):
        return self.props

    def set_server_prop(self, option, value):
        self.props[option] = value


class FakeAternosWss:
    def __init__(self):
        self.connected = False
        self.closed = False
        self.commands_sent = []

    async def connect(self):
        self.connected = True

    async def command(self, cmd):
        self.commands_sent.append(cmd)

    async def close(self):
        self.closed = True


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
        self._players = {}
        self.config = FakeAternosConfig()
        self._wss = FakeAternosWss()

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

    def players(self, list_type):
        if list_type not in self._players:
            self._players[list_type] = FakePlayersList(list_type)
        return self._players[list_type]

    def wss(self):
        return self._wss


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


async def test_player_lists():
    from python_aternos import Lists
    manager = AternosManager('user', 'pass')
    manager.login_blocking(retries=1, base_delay=1.0)

    players = await manager.list_players(Lists.whl)
    assert players == ["player1", "player2"]

    await manager.add_player(Lists.whl, "newplayer")
    players = await manager.list_players(Lists.whl)
    assert "newplayer" in players

    await manager.remove_player(Lists.whl, "player1")
    players = await manager.list_players(Lists.whl)
    assert "player1" not in players


async def test_properties():
    manager = AternosManager('user', 'pass')
    manager.login_blocking(retries=1, base_delay=1.0)

    props = await manager.get_properties()
    assert props["difficulty"] == "easy"

    await manager.set_property("difficulty", "hard")
    props = await manager.get_properties()
    assert props["difficulty"] == "hard"


async def test_send_command():
    manager = AternosManager('user', 'pass')
    manager.login_blocking(retries=1, base_delay=1.0)

    await manager.send_command("say hello")
    assert manager.server._wss.commands_sent == ["say hello"]
    assert manager.server._wss.connected is True
    assert manager.server._wss.closed is True

