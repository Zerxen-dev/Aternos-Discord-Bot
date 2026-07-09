"""Server management and console commands: /console, /whitelist, /op, /ban, /properties, /setproperty."""

from __future__ import annotations

import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from python_aternos import Lists
from ..aternos_client import AternosError
from ..constants import BLUE, GREEN, RED, YELLOW
from ..embeds import error_embed, footer
from ..permissions import is_authorized

log = logging.getLogger('AternosBot.management')


class ManagementCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.aternos = bot.aternos

    async def _fetch_or_raise(self) -> None:
        ok = await self.aternos.fetch()
        if not ok:
            raise AternosError('Could not reach Aternos after multiple retries.')

    # ── /console ──────────────────────────────────────────────────────────

    @app_commands.command(name='console', description='Send a console command directly to the server')
    @app_commands.describe(command='The Minecraft command to run (slash at the beginning is optional)')
    @is_authorized()
    async def console(self, interaction: discord.Interaction, command: str):
        log.info(f'/console used by {interaction.user}: {command}')
        await interaction.response.defer()
        try:
            await self._fetch_or_raise()
            status = self.aternos.server.status.lower()
            if status != 'online':
                embed = footer(
                    discord.Embed(
                        title='🔴  Server Offline',
                        description='The server must be online to execute console commands.',
                        color=RED,
                    )
                )
                await interaction.followup.send(embed=embed)
                return

            await self.aternos.send_command(command)
            embed = footer(
                discord.Embed(
                    title='🖥️  Console Command Sent',
                    description=f'Command `/{command.lstrip("/")}` has been sent to the console.',
                    color=GREEN,
                )
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            log.error(f'/console error: {e}')
            await interaction.followup.send(embed=error_embed('Error sending command', e))

    # ── Whitelist commands ────────────────────────────────────────────────

    whitelist = app_commands.Group(name="whitelist", description="Manage the server whitelist")

    @whitelist.command(name='list', description='List all players on the whitelist')
    async def whitelist_list(self, interaction: discord.Interaction):
        log.info(f'/whitelist list used by {interaction.user}')
        await interaction.response.defer()
        try:
            await self._fetch_or_raise()
            players = await self.aternos.list_players(Lists.whl)
            embed = discord.Embed(
                title='📋  Whitelisted Players',
                description='\n'.join(f'• `{p}`' for p in players) if players else 'The whitelist is empty.',
                color=BLUE,
            )
            embed.add_field(name='Total Players', value=str(len(players)), inline=True)
            await interaction.followup.send(embed=footer(embed))
        except Exception as e:
            log.error(f'/whitelist list error: {e}')
            await interaction.followup.send(embed=error_embed('Error listing whitelist', e))

    @whitelist.command(name='add', description='Add a player to the whitelist')
    @app_commands.describe(player="The player's Minecraft username")
    @is_authorized()
    async def whitelist_add(self, interaction: discord.Interaction, player: str):
        log.info(f'/whitelist add used by {interaction.user}: {player}')
        await interaction.response.defer()
        try:
            await self._fetch_or_raise()
            await self.aternos.add_player(Lists.whl, player)
            embed = footer(
                discord.Embed(
                    title='✅  Added to Whitelist',
                    description=f'Player `{player}` has been added to the whitelist.',
                    color=GREEN,
                )
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            log.error(f'/whitelist add error: {e}')
            await interaction.followup.send(embed=error_embed('Error adding to whitelist', e))

    @whitelist.command(name='remove', description='Remove a player from the whitelist')
    @app_commands.describe(player="The player's Minecraft username")
    @is_authorized()
    async def whitelist_remove(self, interaction: discord.Interaction, player: str):
        log.info(f'/whitelist remove used by {interaction.user}: {player}')
        await interaction.response.defer()
        try:
            await self._fetch_or_raise()
            await self.aternos.remove_player(Lists.whl, player)
            embed = footer(
                discord.Embed(
                    title='❌  Removed from Whitelist',
                    description=f'Player `{player}` has been removed from the whitelist.',
                    color=RED,
                )
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            log.error(f'/whitelist remove error: {e}')
            await interaction.followup.send(embed=error_embed('Error removing from whitelist', e))

    # ── Operator (OP) commands ───────────────────────────────────────────

    op = app_commands.Group(name="op", description="Manage server operators (OPs)")

    @op.command(name='list', description='List all operators (OPs) on the server')
    async def op_list(self, interaction: discord.Interaction):
        log.info(f'/op list used by {interaction.user}')
        await interaction.response.defer()
        try:
            await self._fetch_or_raise()
            players = await self.aternos.list_players(Lists.ops)
            embed = discord.Embed(
                title='👑  Server Operators (OPs)',
                description='\n'.join(f'• `{p}`' for p in players) if players else 'No operators configured.',
                color=BLUE,
            )
            embed.add_field(name='Total Operators', value=str(len(players)), inline=True)
            await interaction.followup.send(embed=footer(embed))
        except Exception as e:
            log.error(f'/op list error: {e}')
            await interaction.followup.send(embed=error_embed('Error listing operators', e))

    @op.command(name='add', description='Promote a player to server operator (OP)')
    @app_commands.describe(player="The player's Minecraft username")
    @is_authorized()
    async def op_add(self, interaction: discord.Interaction, player: str):
        log.info(f'/op add used by {interaction.user}: {player}')
        await interaction.response.defer()
        try:
            await self._fetch_or_raise()
            await self.aternos.add_player(Lists.ops, player)
            embed = footer(
                discord.Embed(
                    title='👑  Operator Promoted',
                    description=f'Player `{player}` is now a server operator.',
                    color=GREEN,
                )
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            log.error(f'/op add error: {e}')
            await interaction.followup.send(embed=error_embed('Error promoting operator', e))

    @op.command(name='remove', description='Demote a player from server operator (OP)')
    @app_commands.describe(player="The player's Minecraft username")
    @is_authorized()
    async def op_remove(self, interaction: discord.Interaction, player: str):
        log.info(f'/op remove used by {interaction.user}: {player}')
        await interaction.response.defer()
        try:
            await self._fetch_or_raise()
            await self.aternos.remove_player(Lists.ops, player)
            embed = footer(
                discord.Embed(
                    title='❌  Operator Demoted',
                    description=f'Player `{player}` has been demoted from server operator.',
                    color=RED,
                )
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            log.error(f'/op remove error: {e}')
            await interaction.followup.send(embed=error_embed('Error demoting operator', e))

    # ── Ban commands ─────────────────────────────────────────────────────

    ban = app_commands.Group(name="ban", description="Manage banned players")

    @ban.command(name='list', description='List all banned players')
    async def ban_list(self, interaction: discord.Interaction):
        log.info(f'/ban list used by {interaction.user}')
        await interaction.response.defer()
        try:
            await self._fetch_or_raise()
            players = await self.aternos.list_players(Lists.ban)
            embed = discord.Embed(
                title='🚫  Banned Players',
                description='\n'.join(f'• `{p}`' for p in players) if players else 'No players are banned.',
                color=BLUE,
            )
            embed.add_field(name='Total Banned', value=str(len(players)), inline=True)
            await interaction.followup.send(embed=footer(embed))
        except Exception as e:
            log.error(f'/ban list error: {e}')
            await interaction.followup.send(embed=error_embed('Error listing banned players', e))

    @ban.command(name='add', description='Ban a player from the server')
    @app_commands.describe(player="The player's Minecraft username")
    @is_authorized()
    async def ban_add(self, interaction: discord.Interaction, player: str):
        log.info(f'/ban add used by {interaction.user}: {player}')
        await interaction.response.defer()
        try:
            await self._fetch_or_raise()
            await self.aternos.add_player(Lists.ban, player)
            embed = footer(
                discord.Embed(
                    title='🚫  Player Banned',
                    description=f'Player `{player}` has been banned from the server.',
                    color=RED,
                )
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            log.error(f'/ban add error: {e}')
            await interaction.followup.send(embed=error_embed('Error banning player', e))

    @ban.command(name='remove', description='Pardon/Unban a player')
    @app_commands.describe(player="The player's Minecraft username")
    @is_authorized()
    async def ban_remove(self, interaction: discord.Interaction, player: str):
        log.info(f'/ban remove used by {interaction.user}: {player}')
        await interaction.response.defer()
        try:
            await self._fetch_or_raise()
            await self.aternos.remove_player(Lists.ban, player)
            embed = footer(
                discord.Embed(
                    title='✅  Player Pardoned',
                    description=f'Player `{player}` has been unbanned.',
                    color=GREEN,
                )
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            log.error(f'/ban remove error: {e}')
            await interaction.followup.send(embed=error_embed('Error unbanning player', e))

    # ── Properties commands ──────────────────────────────────────────────

    @app_commands.command(name='properties', description='View main server config properties')
    async def properties(self, interaction: discord.Interaction):
        log.info(f'/properties used by {interaction.user}')
        await interaction.response.defer()
        try:
            await self._fetch_or_raise()
            props = await self.aternos.get_properties()
            embed = discord.Embed(title='⚙️  Server Properties', color=BLUE)

            # Extract key properties
            display_keys = {
                'difficulty': 'Difficulty',
                'gamemode': 'Game Mode',
                'white-list': 'Whitelist',
                'online-mode': 'Cracked',
                'pvp': 'PvP',
                'max-players': 'Max Players',
                'allow-flight': 'Allow Flight',
                'spawn-animals': 'Spawn Animals',
                'spawn-monsters': 'Spawn Monsters',
            }

            for key, display in display_keys.items():
                if key in props:
                    val = props[key]
                    if isinstance(val, bool):
                        val_str = '✅ Yes' if val else '❌ No'
                        # Invert Cracked representation to make it clearer
                        if key == 'online-mode':
                            val_str = '❌ Yes (Premium Only)' if val else '✅ Yes (Cracked Allowed)'
                    else:
                        val_str = f'`{val}`'
                    embed.add_field(name=display, value=val_str, inline=True)

            await interaction.followup.send(embed=footer(embed))
        except Exception as e:
            log.error(f'/properties error: {e}')
            await interaction.followup.send(embed=error_embed('Error fetching properties', e))

    @app_commands.command(name='setproperty', description='Update a server configuration option')
    @app_commands.describe(
        option='Property key (e.g. difficulty, gamemode, white-list, online-mode, pvp)',
        value='Value to set (e.g. true, false, hard, creative, 20)',
    )
    @is_authorized()
    async def setproperty(self, interaction: discord.Interaction, option: str, value: str):
        log.info(f'/setproperty used by {interaction.user}: {option} = {value}')
        await interaction.response.defer()
        try:
            await self._fetch_or_raise()

            # Normalise option key
            option = option.strip().lower()
            # Map standard friendly names if given
            mapping = {
                'whitelist': 'white-list',
                'cracked': 'online-mode',
                'gamemode': 'gamemode',
            }
            if option in mapping:
                option = mapping[option]

            # Parse value
            parsed_val: str | bool | int = value
            val_lower = value.strip().lower()
            if val_lower in ('true', 'yes', 'on', 'enabled'):
                # Invert Cracked representation logic mapping if setting online-mode
                parsed_val = False if option == 'online-mode' and val_lower in ('true', 'yes') else True
                if option == 'online-mode':
                    # If setting cracked to True, online-mode must be false (online-mode=false means cracked=true)
                    parsed_val = False
            elif val_lower in ('false', 'no', 'off', 'disabled'):
                parsed_val = True if option == 'online-mode' and val_lower in ('false', 'no') else False
                if option == 'online-mode':
                    # If setting cracked to False, online-mode must be true
                    parsed_val = True
            elif val_lower.isdigit():
                parsed_val = int(val_lower)

            await self.aternos.set_property(option, parsed_val)

            embed = footer(
                discord.Embed(
                    title='⚙️  Property Updated',
                    description=f'Option `{option}` has been updated to `{value}`.\n*Note: A server restart is required for changes to take effect.*',
                    color=GREEN,
                )
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            log.error(f'/setproperty error: {e}')
            await interaction.followup.send(embed=error_embed('Error setting property', e))


async def setup(bot: commands.Bot):
    await bot.add_cog(ManagementCog(bot))
