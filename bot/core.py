"""The Discord bot client: cog loading, presence, and centralized error handling."""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from .aternos_client import AternosManager
from .config import Config
from .constants import RED
from .embeds import error_embed, footer
from .state import BotState

log = logging.getLogger('AternosBot')

_EXTENSIONS = (
    'bot.cogs.general',
    'bot.cogs.server',
    'bot.cogs.automation',
)


class AternosBot(commands.Bot):
    def __init__(self, config: Config, aternos: AternosManager, state: BotState):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=commands.when_mentioned, intents=intents, help_command=None)
        self.config = config
        self.aternos = aternos
        self.state = state

    async def setup_hook(self) -> None:
        for extension in _EXTENSIONS:
            await self.load_extension(extension)

        @self.tree.error
        async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            await self._handle_app_command_error(interaction, error)

        await self.tree.sync()
        log.info('Slash commands synced globally.')

    async def _handle_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.CheckFailure):
            embed = footer(discord.Embed(description="🚫  You don't have permission to use this command.", color=RED))
        else:
            log.error(f'App command error: {error}')
            embed = error_embed('Something went wrong', error)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)
        except discord.HTTPException as e:
            log.error(f'Could not send error response: {e}')

    async def on_ready(self):
        log.info(f'Logged in as {self.user} (ID: {self.user.id})')
        log.info(f'Connected to {len(self.guilds)} guild(s): {[g.name for g in self.guilds]}')
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name='your Minecraft server 🎮')
        )

    async def on_disconnect(self):
        log.warning('Discord connection lost — discord.py will auto-reconnect.')

    async def on_resumed(self):
        log.info('Discord session resumed successfully.')

    async def on_guild_join(self, guild: discord.Guild):
        log.info(f'Joined new guild: {guild.name} (ID: {guild.id})')
