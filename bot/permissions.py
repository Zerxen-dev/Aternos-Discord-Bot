"""Optional role/user-based access control for server-altering commands.

If no ADMIN_ROLE_IDS / ADMIN_USER_IDS are configured, every command is open
to everyone (matching the bot's previous behaviour). Once configured, the
decorated commands (and the control panel's buttons) are restricted.
"""

from __future__ import annotations

import discord
from discord import app_commands


def user_is_authorized(interaction: discord.Interaction) -> bool:
    config = interaction.client.config
    if not config.restricted:
        return True
    if interaction.user.id in config.admin_user_ids:
        return True
    member = interaction.user
    if isinstance(member, discord.Member):
        role_ids = {role.id for role in member.roles}
        if role_ids & config.admin_role_ids:
            return True
    return False


def is_authorized():
    """App-command check decorator wrapping :func:`user_is_authorized`."""
    return app_commands.check(user_is_authorized)
