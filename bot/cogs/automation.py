"""Background server monitoring plus the /autostart and /autostop commands."""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ..constants import GREEN, RED, YELLOW
from ..embeds import footer
from ..permissions import is_authorized

log = logging.getLogger('AternosBot.automation')

START_POLL_ATTEMPTS = 60
START_POLL_INTERVAL = 5


class AutomationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.aternos = bot.aternos
        self.state = bot.state
        self.config = bot.config
        self._empty_since: Optional[datetime.datetime] = None
        self.monitor.change_interval(seconds=self.config.autostart_poll_seconds)
        self.monitor.start()

    def cog_unload(self):
        self.monitor.cancel()

    def _channel(self, channel_id: Optional[int]):
        if channel_id is None:
            return None
        return self.bot.get_channel(channel_id)

    # ── background monitor ──────────────────────────────────────────────

    @tasks.loop(seconds=60)
    async def monitor(self):
        try:
            await self._tick()
        except Exception:
            log.exception('[Monitor] Unhandled error in monitor tick')

    @monitor.before_loop
    async def before_monitor(self):
        await self.bot.wait_until_ready()
        log.info('Autostart/autostop monitor started.')

    async def _tick(self):
        if not (self.state.autostart_enabled or self.state.autostop_enabled):
            self._empty_since = None
            return

        ok = await self.aternos.fetch()
        if not ok:
            log.error('[Monitor] Could not fetch server status — skipping this cycle.')
            return

        status = self.aternos.server.status.lower()

        if status == 'offline':
            self._empty_since = None
            if self.state.autostart_enabled:
                await self._do_autostart()
            return

        if status != 'online':
            return  # starting / stopping / loading — nothing to do yet

        if not self.state.autostop_enabled:
            self._empty_since = None
            return

        if self.aternos.server.players_count > 0:
            self._empty_since = None
            return

        now = datetime.datetime.now(datetime.timezone.utc)
        if self._empty_since is None:
            self._empty_since = now
            return

        idle_minutes = (now - self._empty_since).total_seconds() / 60
        if idle_minutes >= self.state.autostop_minutes:
            await self._do_autostop()
            self._empty_since = None

    async def _poll_for_online(self, attempts: int = START_POLL_ATTEMPTS, interval: int = START_POLL_INTERVAL) -> bool:
        for _ in range(attempts):
            await asyncio.sleep(interval)
            await self.aternos.fetch()
            if self.aternos.server.status.lower() == 'online':
                return True
        return False

    async def _do_autostart(self):
        log.info('[Autostart] Server offline — triggering auto-start...')
        channel = self._channel(self.state.autostart_channel_id)
        if channel:
            embed = footer(
                discord.Embed(
                    title='🤖  Auto-Start Triggered',
                    description=(
                        '> The server went offline and **Auto-Start** is enabled.\n'
                        '> Booting it back up now — this takes **2 – 4 minutes**!'
                    ),
                    color=YELLOW,
                )
            )
            embed.add_field(name='🌐  Server Address', value=f'```{self.aternos.address}```', inline=False)
            embed.add_field(name='⚙️  Set by', value=f'`{self.state.autostart_set_by}`', inline=True)
            try:
                await channel.send(embed=embed)
            except discord.HTTPException as e:
                log.warning(f'[Autostart] Could not send alert: {e}')

        started = await self.aternos.start()
        if not started:
            log.error('[Autostart] start() failed — will retry next cycle.')
            return

        online = await self._poll_for_online()
        if not channel:
            return

        if online:
            server = self.aternos.server
            embed = footer(
                discord.Embed(
                    title='🎉  Server Auto-Started Successfully!',
                    description=(
                        '> The server is back online and ready to join!\n\n'
                        '**📋  How to join**\n1. Open **Minecraft**\n2. Go to **Multiplayer → Add Server**\n'
                        '3. Copy the address below and click **Join Server**'
                    ),
                    color=GREEN,
                )
            )
            embed.add_field(name='🌐  Server Address  *(copy & paste this)*', value=f'```{self.aternos.address}```', inline=False)
            embed.add_field(name='🔌  Port', value=f'`{server.port}`', inline=True)
            embed.add_field(name='📦  Software', value=f'`{server.software} {server.version}`', inline=True)
            embed.add_field(name='👥  Slots', value=f'`{server.slots}`', inline=True)
            try:
                await channel.send(embed=embed)
            except discord.HTTPException as e:
                log.warning(f'[Autostart] Could not send success embed: {e}')
            log.info('[Autostart] Server is back online.')
        else:
            embed = footer(
                discord.Embed(
                    title='⚠️  Auto-Start Timed Out',
                    description='The server took too long to start. Will retry next check.\nYou can also use `/start` manually.',
                    color=YELLOW,
                )
            )
            try:
                await channel.send(embed=embed)
            except discord.HTTPException as e:
                log.warning(f'[Autostart] Could not send timeout embed: {e}')
            log.warning('[Autostart] Server did not come online within timeout.')

    async def _do_autostop(self):
        log.info(f'[Autostop] Server empty for {self.state.autostop_minutes}+ minutes — stopping...')
        stopped = await self.aternos.stop()
        channel = self._channel(self.state.autostop_channel_id)
        if not channel:
            return
        if stopped:
            embed = footer(
                discord.Embed(
                    title='💤  Auto-Stop Triggered',
                    description=(
                        f'> No players have been online for **{self.state.autostop_minutes} minutes**.\n'
                        '> Shutting the server down to save your Aternos queue time.\n\n'
                        'Use `/start` any time to bring it back up.'
                    ),
                    color=YELLOW,
                )
            )
            try:
                await channel.send(embed=embed)
            except discord.HTTPException as e:
                log.warning(f'[Autostop] Could not send alert: {e}')
        else:
            log.error('[Autostop] stop() failed.')

    # ── /autostart ───────────────────────────────────────────────────────

    @app_commands.command(name='autostart', description='Auto-restart the server whenever it goes offline')
    @app_commands.describe(enabled='True to enable auto-start, False to disable it')
    @is_authorized()
    async def autostart(self, interaction: discord.Interaction, enabled: bool):
        self.state.autostart_enabled = enabled
        self.state.autostart_channel_id = interaction.channel_id
        self.state.autostart_set_by = str(interaction.user)
        self.state.save(self.config.state_file)
        log.info(f'/autostart set to {enabled} by {interaction.user} — notifications → #{interaction.channel}')

        if enabled:
            embed = discord.Embed(
                title='🤖  Auto-Start  ·  ENABLED',
                description=(
                    '> The bot will now **automatically restart** the server\n'
                    '> whenever it detects it has gone offline.\n\n'
                    f'📡  Notifications will appear right here in **#{interaction.channel}**\n'
                    f'⏱️  Server is checked every **{self.config.autostart_poll_seconds} seconds**'
                ),
                color=GREEN,
            )
            embed.add_field(name='🌐  Server', value=f'```{self.aternos.address}```', inline=False)
            embed.add_field(name='⚙️  Enabled by', value=f'`{interaction.user.display_name}`', inline=True)
            embed.add_field(name='📢  Channel', value=f'<#{interaction.channel_id}>', inline=True)
            embed.add_field(name='ℹ️  How to disable', value='Run `/autostart enabled:False` at any time.', inline=False)
        else:
            embed = discord.Embed(
                title='🤖  Auto-Start  ·  DISABLED',
                description=(
                    '> Auto-Start has been turned off.\n'
                    '> The server will **not** restart automatically if it goes offline.\n\n'
                    'Use `/start` to bring it back up manually, or\n'
                    'run `/autostart enabled:True` to turn it on again.'
                ),
                color=RED,
            )
            embed.add_field(name='⚙️  Disabled by', value=f'`{interaction.user.display_name}`', inline=True)
        footer(embed)
        await interaction.response.send_message(embed=embed)

    # ── /autostop ────────────────────────────────────────────────────────

    @app_commands.command(name='autostop', description='Auto-stop the server after it sits empty for a while')
    @app_commands.describe(
        enabled='True to enable auto-stop, False to disable it',
        minutes='Minutes of zero players before stopping (default 20)',
    )
    @is_authorized()
    async def autostop(
        self,
        interaction: discord.Interaction,
        enabled: bool,
        minutes: Optional[app_commands.Range[int, 1, 1440]] = None,
    ):
        self.state.autostop_enabled = enabled
        self.state.autostop_channel_id = interaction.channel_id
        self.state.autostop_set_by = str(interaction.user)
        if minutes is not None:
            self.state.autostop_minutes = minutes
        elif self.state.autostop_minutes <= 0:
            self.state.autostop_minutes = self.config.autostop_default_minutes
        self.state.save(self.config.state_file)
        self._empty_since = None
        log.info(f'/autostop set to {enabled} ({self.state.autostop_minutes}m) by {interaction.user}')

        if enabled:
            embed = discord.Embed(
                title='💤  Auto-Stop  ·  ENABLED',
                description=(
                    f'> The server will automatically **stop** after sitting empty\n'
                    f'> for **{self.state.autostop_minutes} minutes**, saving your Aternos queue time.\n\n'
                    f'📡  Notifications will appear right here in **#{interaction.channel}**'
                ),
                color=GREEN,
            )
            embed.add_field(name='⏱️  Empty timeout', value=f'`{self.state.autostop_minutes} min`', inline=True)
            embed.add_field(name='⚙️  Enabled by', value=f'`{interaction.user.display_name}`', inline=True)
            embed.add_field(name='ℹ️  How to disable', value='Run `/autostop enabled:False` at any time.', inline=False)
        else:
            embed = discord.Embed(
                title='💤  Auto-Stop  ·  DISABLED',
                description='> Auto-Stop has been turned off. The server will stay online indefinitely.',
                color=RED,
            )
            embed.add_field(name='⚙️  Disabled by', value=f'`{interaction.user.display_name}`', inline=True)
        footer(embed)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(AutomationCog(bot))
