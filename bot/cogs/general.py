"""General-purpose commands: /help, /hello, and /stats."""

from __future__ import annotations

import datetime
import logging
import os
import platform
import time

import discord
from discord import app_commands
from discord.ext import commands

from ..constants import BLUE, GREEN, PURPLE, TEAL
from ..embeds import footer

log = logging.getLogger('AternosBot.general')

_START_TIME = time.time()


class GeneralCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name='help', description='Show all available bot commands')
    async def help_command(self, interaction: discord.Interaction):
        log.info(f'/help used by {interaction.user} in #{interaction.channel}')
        embed = discord.Embed(
            title='🤖  Aternos Bot — Command Guide',
            description='Control your Minecraft server directly from Discord.\nAll commands are slash commands — just type `/` to get started.',
            color=PURPLE,
        )
        embed.add_field(name='📋  /help', value='Shows this command guide.', inline=False)
        embed.add_field(name='📈  /stats', value='Show bot uptime, latency, memory, and operational metrics.', inline=False)
        embed.add_field(name='🧠  /ask', value='Ask natural language questions about the server (AI-powered).', inline=False)
        embed.add_field(name='🌐  /servers', value='List and select across multiple Aternos servers on your account.', inline=False)
        embed.add_field(name='📊  /status', value='Shows live server status, player count, address and more.', inline=False)
        embed.add_field(name='ℹ️  /info', value='Shows detailed server info: software, version, RAM, slots, MOTD.', inline=False)
        embed.add_field(name='🎮  /panel', value='Posts an interactive control panel with Start/Stop/Restart/Refresh buttons.', inline=False)
        embed.add_field(name='▶️  /start', value="Starts the server and pings you when it's live.", inline=False)
        embed.add_field(name='⏹️  /stop', value='Stops the server gracefully (asks for confirmation).', inline=False)
        embed.add_field(name='🔄  /restart', value='Restarts the server (asks for confirmation).', inline=False)
        embed.add_field(
            name='🤖  /autostart',
            value=(
                'Automatically restarts the server whenever it goes offline.\n'
                '`/autostart enabled:True` — turn on  •  `/autostart enabled:False` — turn off'
            ),
            inline=False,
        )
        embed.add_field(
            name='💤  /autostop',
            value=(
                'Automatically stops the server after it sits empty for a while.\n'
                '`/autostop enabled:True minutes:20` — turn on  •  `/autostop enabled:False` — turn off'
            ),
            inline=False,
        )
        embed.add_field(
            name='👥  /whitelist, /op, /ban',
            value='Manage your server lists with interactive pagination.',
            inline=False,
        )
        embed.add_field(
            name='⚙️  /properties, /setproperty',
            value='View or update server configuration properties.',
            inline=False,
        )
        embed.add_field(
            name='🖥️  /console',
            value='Send sanitized console commands directly to your running Minecraft server.',
            inline=False,
        )
        embed.add_field(
            name='🟢  /statuschannel',
            value='Set up a live auto-updating text embed and dynamic voice channel name.',
            inline=False,
        )
        embed.add_field(
            name='🔔  /alerts',
            value='Get notified with role pings when server goes online/offline or players join/leave.',
            inline=False,
        )
        embed.add_field(
            name='⏰  /schedule',
            value='Schedule automatic start, stop, or restart routines at specific times.',
            inline=False,
        )
        embed.add_field(
            name='💾  /backup',
            value='Create and list Aternos world backups directly from Discord.',
            inline=False,
        )
        embed.add_field(
            name='📜  /logs',
            value='Fetch recent server console and crash logs.',
            inline=False,
        )
        if interaction.client.config.restricted:
            embed.add_field(
                name='🔒  Restricted commands',
                value='`/start`, `/stop`, `/restart`, `/autostart`, `/autostop`, `/console`, `/setproperty`, `/servers select`, and list modifications are limited to configured admins.',
                inline=False,
            )
        embed.set_thumbnail(url='https://aternos.org/favicon.ico')
        footer(embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='hello', description='Say hello to the bot')
    async def hello(self, interaction: discord.Interaction):
        log.info(f'/hello used by {interaction.user} in #{interaction.channel}')
        embed = discord.Embed(
            title=f'👋  Hey, {interaction.user.display_name}!',
            description="I'm your Aternos server manager. Use `/help` to see everything I can do.",
            color=TEAL,
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        footer(embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='stats', description='Show bot latency, uptime, and system statistics')
    async def stats(self, interaction: discord.Interaction):
        log.info(f'/stats used by {interaction.user} in #{interaction.channel}')
        latency_ms = round(self.bot.latency * 1000, 1)
        uptime_seconds = int(time.time() - _START_TIME)
        uptime_str = str(datetime.timedelta(seconds=uptime_seconds))

        embed = discord.Embed(
            title='📊  Bot & System Statistics',
            description='Current operational metrics and bot status.',
            color=BLUE,
        )
        embed.add_field(name='⚡  Discord Latency', value=f'`{latency_ms} ms`', inline=True)
        embed.add_field(name='⏱️  Bot Uptime', value=f'`{uptime_str}`', inline=True)
        embed.add_field(name='🏰  Connected Guilds', value=f'`{len(self.bot.guilds)}`', inline=True)
        embed.add_field(name='🐍  Python Version', value=f'`{platform.python_version()}`', inline=True)
        embed.add_field(name='📦  discord.py', value=f'`{discord.__version__}`', inline=True)
        embed.add_field(name='🖥️  Platform', value=f'`{platform.system()} {platform.machine()}`', inline=True)

        if hasattr(self.bot, 'aternos'):
            try:
                srv = self.bot.aternos.server
                embed.add_field(
                    name='🎮  Active Server',
                    value=f"`{srv.subdomain}` ({srv.status})",
                    inline=True,
                )
                embed.add_field(
                    name='🌐  Available Servers',
                    value=f"`{len(getattr(self.bot.aternos, 'servers', []))}`",
                    inline=True,
                )
            except Exception:
                pass

        if hasattr(self.bot.config, 'web_dashboard_enabled') and self.bot.config.web_dashboard_enabled:
            embed.add_field(
                name='🌐  Web Dashboard',
                value=f"Running on port `{self.bot.config.web_dashboard_port}`",
                inline=True,
            )

        footer(embed)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(GeneralCog(bot))
