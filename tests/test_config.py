import pytest

from bot.config import ConfigError, load_config

BASE_ENV = {
    'DISCORD_TOKEN': 'tok',
    'ATERNOS_USER': 'user',
    'ATERNOS_PASS': 'pass',
}


def test_minimal_valid_env():
    config = load_config(BASE_ENV)
    assert config.discord_token == 'tok'
    assert config.aternos_user == 'user'
    assert config.aternos_pass == 'pass'
    assert config.restricted is False
    assert config.autostart_poll_seconds == 60
    assert config.autostop_default_minutes == 20


@pytest.mark.parametrize('missing', ['DISCORD_TOKEN', 'ATERNOS_USER', 'ATERNOS_PASS'])
def test_missing_required_raises(missing):
    env = dict(BASE_ENV)
    del env[missing]
    with pytest.raises(ConfigError):
        load_config(env)


def test_admin_ids_parsed_and_restricted():
    env = dict(BASE_ENV, ADMIN_ROLE_IDS='111, 222', ADMIN_USER_IDS='333')
    config = load_config(env)
    assert config.admin_role_ids == frozenset({111, 222})
    assert config.admin_user_ids == frozenset({333})
    assert config.restricted is True


def test_invalid_admin_id_raises():
    env = dict(BASE_ENV, ADMIN_ROLE_IDS='not-a-number')
    with pytest.raises(ConfigError):
        load_config(env)


def test_invalid_int_env_raises():
    env = dict(BASE_ENV, AUTOSTART_POLL_SECONDS='soon')
    with pytest.raises(ConfigError):
        load_config(env)
