"""Multi-Server management commands: /servers list and /servers select."""

from __future__ import annotations

import logging
import discord
from discord import app_commands
from discord.ext import commands

from ..constants import BLUE, GREEN, RED, status_emoji
from ..embeds import error_embed, footer
from ..permissions import is_authorized

log = logging.getLogger('AternosBot.servers')


class MultiServerCog(commands.Cog):
    """Cog for managing and switching between multiple Aternos servers."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.aternos = bot.aternos

    servers_group = app_commands.Group(name='servers', description='Manage multiple Aternos servers on your account')

    @servers_group.command(name='list', description='List all Minecraft servers available on this Aternos account')
    async def servers_list(self, interaction: discord.Interaction):
        log.info(f'/servers list used by {interaction.user}')
        await interaction.response.defer()
        try:
            servers = await self.aternos.list_all_servers()
            if not servers:
                embed = footer(
                    discord.Embed(
                        title='🌐  Aternos Servers',
                        description='No servers found on this Aternos account.',
                        color=BLUE,
                    )
                )
                await interaction.followup.send(embed=embed)
                return

            embed = discord.Embed(
                title=f'🌐  Aternos Servers ({len(servers)})',
                description='Select a server using `/servers select <index>`.\n',
                color=BLUE,
            )

            for srv in servers:
                status = srv['status']
                active_badge = ' **(Active 🟢)**' if srv['is_active'] else ''
                embed.add_field(
                    name=f"#{srv['index']} — `{srv['subdomain']}`{active_badge}",
                    value=(
                        f"• **Status:** {status_emoji(status)} `{status}`\n"
                        f"• **Address:** `{srv['address']}`\n"
                        f"• **Software:** `{srv['software']}`"
                    ),
                    inline=False,
                )

            await interaction.followup.send(embed=footer(embed))
        except Exception as e:
            log.error(f'/servers list error: {e}')
            await interaction.followup.send(embed=error_embed('Error listing servers', e))

    @servers_group.command(name='select', description='Switch the active Aternos server managed by the bot')
    @app_commands.describe(server='Server index number (e.g. 0, 1) or subdomain')
    @is_authorized()
    async def servers_select(self, interaction: discord.Interaction, server: str):
        log.info(f'/servers select used by {interaction.user}: {server}')
        await interaction.response.defer()
        try:
            success = await self.aternos.select_server(server)
            if success:
                active_server = self.aternos.server
                # Persist active server in bot state
                if hasattr(self.bot, 'state') and hasattr(self.bot, 'config'):
                    self.bot.state.active_server_id = getattr(active_server, 'subdomain', str(server))
                    self.bot.state.save(self.bot.config.state_file)

                embed = footer(
                    discord.Embed(
                        title='✅  Active Server Switched',
                        description=(
                            f'> Active server changed to **{active_server.subdomain}**.\n'
                            f'🌐  **Address:** `{self.aternos.address}`\n'
                            f'📦  **Software:** `{active_server.software} {active_server.version}`\n'
                            f'⚡  **Status:** `{active_server.status}`'
                        ),
                        color=GREEN,
                    )
                )
            else:
                embed = error_embed(
                    'Server Not Found',
                    f"Could not find a server matching `{server}`. Use `/servers list` to see available servers.",
                )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            log.error(f'/servers select error: {e}')
            await interaction.followup.send(embed=error_embed('Error selecting server', e))


async def setup(bot: commands.Bot):
    await bot.add_cog(MultiServerCog(bot))
