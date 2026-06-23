from unittest.mock import Mock

import discord

from bot.config import Config
from bot.permissions import user_is_authorized

RESTRICTED_CONFIG = Config(
    discord_token='t',
    aternos_user='u',
    aternos_pass='p',
    admin_role_ids=frozenset({555}),
    admin_user_ids=frozenset({999}),
)


def make_interaction(*, user_id, role_ids=(), is_member=True, config=RESTRICTED_CONFIG):
    interaction = Mock()
    interaction.client.config = config
    if is_member:
        user = Mock(spec=discord.Member)
        user.roles = [Mock(id=rid) for rid in role_ids]
    else:
        user = Mock(spec=discord.User)
    user.id = user_id
    interaction.user = user
    return interaction


def test_unrestricted_allows_everyone():
    config = Config(discord_token='t', aternos_user='u', aternos_pass='p')
    interaction = make_interaction(user_id=1, config=config)
    assert user_is_authorized(interaction) is True


def test_admin_user_id_allowed():
    assert user_is_authorized(make_interaction(user_id=999)) is True


def test_admin_role_allowed():
    assert user_is_authorized(make_interaction(user_id=1, role_ids=[555])) is True


def test_non_admin_denied():
    assert user_is_authorized(make_interaction(user_id=1, role_ids=[1, 2])) is False


def test_non_member_without_admin_id_denied():
    assert user_is_authorized(make_interaction(user_id=1, is_member=False)) is False
