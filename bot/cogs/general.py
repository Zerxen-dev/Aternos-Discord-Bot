"""General-purpose commands: /help and /hello."""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from ..constants import PURPLE, TEAL
from ..embeds import footer

log = logging.getLogger('AternosBot.general')


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
        embed.add_field(name='👋  /hello', value='The bot greets you personally.', inline=False)
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
            value='Manage your server lists (list, add, or remove players).',
            inline=False,
        )
        embed.add_field(
            name='⚙️  /properties, /setproperty',
            value='View or update server configuration properties.',
            inline=False,
        )
        embed.add_field(
            name='🖥️  /console',
            value='Send direct console commands to your running Minecraft server.',
            inline=False,
        )
        if interaction.client.config.restricted:
            embed.add_field(
                name='🔒  Restricted commands',
                value='`/start`, `/stop`, `/restart`, `/autostart`, `/autostop`, `/console`, `/setproperty`, and list modifications (`add`/`remove`) are limited to configured admins.',
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


async def setup(bot: commands.Bot):
    await bot.add_cog(GeneralCog(bot))
