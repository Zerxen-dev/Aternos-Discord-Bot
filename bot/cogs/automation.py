"""Background server monitoring, live status channel, alerts with role ping, scheduler, autostart & autostop."""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Optional, Literal

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ..constants import BLUE, GREEN, RED, YELLOW
from ..embeds import footer, error_embed
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
        
        # State tracking for alerts
        self._last_status: Optional[str] = None
        self._last_players: set[str] = set()
        self._last_voice_name_update: float = 0
        self._last_schedule_minute: str = ""

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
        log.info('Automation background monitor started.')

    async def _update_presence(self, status: str, players_count: int, slots: int):
        status = status.lower()
        if status == 'online':
            activity_text = f'Minecraft: {players_count}/{slots} players 🎮'
            activity_type = discord.ActivityType.playing
        elif status in ('starting', 'loading', 'preparing'):
            activity_text = 'Server starting... ⏳'
            activity_type = discord.ActivityType.watching
        elif status == 'stopping':
            activity_text = 'Server stopping... 🛑'
            activity_type = discord.ActivityType.watching
        else:
            activity_text = 'Server offline 🔴'
            activity_type = discord.ActivityType.watching

        await self.bot.change_presence(
            activity=discord.Activity(type=activity_type, name=activity_text)
        )

    async def _tick(self):
        ok = await self.aternos.fetch()
        if not ok:
            log.error('[Monitor] Could not fetch server status — skipping this cycle.')
            return

        server = self.aternos.server
        status = server.status.lower()
        players_count = server.players_count
        slots = server.slots
        players_list = set(getattr(server, 'players_list', []) or [])

        # 1. Update presence
        await self._update_presence(status, players_count, slots)

        # 2. Process State Transition Alerts & Player Join/Leave Events
        await self._handle_alerts(status, players_list)

        # 3. Process Live Status Channel & Dynamic Voice Channel
        await self._handle_status_channel(status, players_count, slots)

        # 4. Process Scheduled Timers (/schedule)
        await self._handle_schedules()

        # 5. Handle Auto-Start
        if status == 'offline':
            self._empty_since = None
            if self.state.autostart_enabled:
                await self._do_autostart()
            return

        if status != 'online':
            return  # starting / stopping / loading — nothing to do yet

        # 6. Handle Auto-Stop
        if not self.state.autostop_enabled:
            self._empty_since = None
            return

        if players_count > 0:
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

    # ── Alerts & Notifications Engine ─────────────────────────────────────

    async def _handle_alerts(self, current_status: str, current_players: set[str]):
        if not self.state.alerts_channel_id:
            self._last_status = current_status
            self._last_players = current_players
            return

        channel = self._channel(self.state.alerts_channel_id)
        if not channel:
            self._last_status = current_status
            self._last_players = current_players
            return

        role_mention = f"<@&{self.state.alerts_role_id}> " if self.state.alerts_role_id else ""
        notify_on = self.state.alerts_notify_on

        # Online Alert
        if self._last_status and self._last_status != 'online' and current_status == 'online':
            if notify_on in ('all', 'online'):
                server = self.aternos.server
                embed = footer(
                    discord.Embed(
                        title='🎉  Server is now ONLINE!',
                        description=(
                            f'> **{server.subdomain}.aternos.me** is ready for players!\n\n'
                            f'**🔌 Port:** `{server.port}`\n'
                            f'**📦 Software:** `{server.software} {server.version}`\n'
                            f'**👥 Slots:** `{server.players_count}/{server.slots}`'
                        ),
                        color=GREEN,
                    )
                )
                embed.add_field(name='🌐  Join Address', value=f'```{self.aternos.address}```', inline=False)
                try:
                    await channel.send(content=f"{role_mention}🚀 Server is online!", embed=embed)
                except Exception as e:
                    log.warning(f'[Alerts] Failed to send online alert: {e}')

        # Offline Alert
        elif self._last_status and self._last_status == 'online' and current_status == 'offline':
            if notify_on in ('all', 'offline'):
                embed = footer(
                    discord.Embed(
                        title='🔴  Server is now OFFLINE',
                        description='The Minecraft server has shut down.\nUse `/start` or `/panel` to launch it back up!',
                        color=RED,
                    )
                )
                try:
                    await channel.send(embed=embed)
                except Exception as e:
                    log.warning(f'[Alerts] Failed to send offline alert: {e}')

        # Player Join & Leave Alerts
        if self._last_status == 'online' and current_status == 'online' and notify_on in ('all', 'players'):
            joined = current_players - self._last_players
            left = self._last_players - current_players

            for p in joined:
                embed = discord.Embed(description=f'👋  **{p}** joined the server!', color=GREEN)
                try:
                    await channel.send(embed=embed)
                except Exception:
                    pass

            for p in left:
                embed = discord.Embed(description=f'🚪  **{p}** left the server.', color=YELLOW)
                try:
                    await channel.send(embed=embed)
                except Exception:
                    pass

        self._last_status = current_status
        self._last_players = current_players

    # ── Live Status Channel Engine ────────────────────────────────────────

    def _build_status_embed(self, status: str, players_count: int, slots: int) -> discord.Embed:
        server = self.aternos.server
        status_upper = status.upper()

        if status == 'online':
            color = GREEN
            status_icon = '🟢'
        elif status in ('starting', 'loading', 'preparing'):
            color = YELLOW
            status_icon = '⏳'
        elif status == 'stopping':
            color = YELLOW
            status_icon = '🛑'
        else:
            color = RED
            status_icon = '🔴'

        embed = discord.Embed(
            title=f'{status_icon}  Minecraft Server Status  ·  {status_upper}',
            description=f'> Direct real-time live monitoring for **{server.subdomain}**',
            color=color,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.add_field(name='🌐  Address', value=f'`{self.aternos.address}`', inline=True)
        embed.add_field(name='🔌  Port', value=f'`{server.port}`', inline=True)
        embed.add_field(name='👥  Players', value=f'`{players_count} / {slots}`', inline=True)
        embed.add_field(name='📦  Software', value=f'`{server.software} {server.version}`', inline=True)
        embed.add_field(name='🧠  RAM', value=f'`{server.ram} MB`', inline=True)
        embed.add_field(name='⚡  Status', value=f'`{status_upper}`', inline=True)
        
        embed.set_footer(text='Auto-updates every 60 seconds • Powered by AternosBot')
        return embed

    async def _handle_status_channel(self, status: str, players_count: int, slots: int):
        # 1. Update text channel pinned embed
        if self.state.status_channel_id:
            channel = self._channel(self.state.status_channel_id)
            if channel and isinstance(channel, discord.TextChannel):
                embed = self._build_status_embed(status, players_count, slots)
                try:
                    if self.state.status_message_id:
                        try:
                            msg = await channel.fetch_message(self.state.status_message_id)
                            await msg.edit(embed=embed)
                        except discord.NotFound:
                            new_msg = await channel.send(embed=embed)
                            self.state.status_message_id = new_msg.id
                            self.state.save(self.config.state_file)
                    else:
                        new_msg = await channel.send(embed=embed)
                        self.state.status_message_id = new_msg.id
                        self.state.save(self.config.state_file)
                except Exception as e:
                    log.warning(f'[StatusChannel] Failed to update embed: {e}')

        # 2. Update dynamic voice channel name
        if self.state.status_voice_channel_id:
            v_channel = self.bot.get_channel(self.state.status_voice_channel_id)
            if v_channel and isinstance(v_channel, (discord.VoiceChannel, discord.StageChannel)):
                now_ts = datetime.datetime.now().timestamp()
                # Rate limit channel renames to once every 5 minutes (300s)
                if (now_ts - self._last_voice_name_update) >= 300:
                    if status == 'online':
                        new_name = f'🟢 {players_count}/{slots} Online'
                    elif status in ('starting', 'loading'):
                        new_name = '⏳ Starting...'
                    else:
                        new_name = '🔴 Server Offline'

                    if v_channel.name != new_name:
                        try:
                            await v_channel.edit(name=new_name)
                            self._last_voice_name_update = now_ts
                            log.info(f'[StatusChannel] Renamed voice channel to: {new_name}')
                        except Exception as e:
                            log.warning(f'[StatusChannel] Failed to rename voice channel: {e}')

    # ── Scheduler Engine (/schedule) ──────────────────────────────────────

    async def _handle_schedules(self):
        if not self.state.schedules:
            return

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        current_time_str = now_utc.strftime('%H:%M')
        current_day_name = now_utc.strftime('%A').lower()  # e.g. monday
        is_weekend = now_utc.weekday() >= 5

        # Avoid executing multiple times in the same minute
        if current_time_str == self._last_schedule_minute:
            return

        self._last_schedule_minute = current_time_str

        for item in self.state.schedules:
            sched_time = item.get('time')
            sched_days = item.get('days', 'all').lower()
            action = item.get('action')

            if sched_time == current_time_str:
                should_run = False
                if sched_days == 'all':
                    should_run = True
                elif sched_days == 'weekdays' and not is_weekend:
                    should_run = True
                elif sched_days == 'weekends' and is_weekend:
                    should_run = True
                elif sched_days == current_day_name:
                    should_run = True

                if should_run:
                    log.info(f'[Scheduler] Executing scheduled action: {action} (ID: {item.get("id")})')
                    if action == 'start':
                        await self.aternos.start()
                    elif action == 'stop':
                        await self.aternos.stop()
                    elif action == 'restart':
                        await self.aternos.restart()

    # ── Autostart & Autostop Actions ──────────────────────────────────────

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
                    description='> The server is back online and ready to join!',
                    color=GREEN,
                )
            )
            embed.add_field(name='🌐  Server Address', value=f'```{self.aternos.address}```', inline=False)
            embed.add_field(name='🔌  Port', value=f'`{server.port}`', inline=True)
            embed.add_field(name='📦  Software', value=f'`{server.software} {server.version}`', inline=True)
            try:
                await channel.send(embed=embed)
            except discord.HTTPException as e:
                log.warning(f'[Autostart] Could not send success embed: {e}')
        else:
            embed = footer(
                discord.Embed(
                    title='⚠️  Auto-Start Timed Out',
                    description='The server took too long to start. Will retry next check.',
                    color=YELLOW,
                )
            )
            try:
                await channel.send(embed=embed)
            except discord.HTTPException as e:
                log.warning(f'[Autostart] Could not send timeout embed: {e}')

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
                        '> Shutting the server down to save your Aternos queue time.'
                    ),
                    color=YELLOW,
                )
            )
            try:
                await channel.send(embed=embed)
            except discord.HTTPException as e:
                log.warning(f'[Autostop] Could not send alert: {e}')

    # ── Slash Commands: /autostart & /autostop ─────────────────────────────

    @app_commands.command(name='autostart', description='Auto-restart the server whenever it goes offline')
    @app_commands.describe(enabled='True to enable auto-start, False to disable it')
    @is_authorized()
    async def autostart(self, interaction: discord.Interaction, enabled: bool):
        self.state.autostart_enabled = enabled
        self.state.autostart_channel_id = interaction.channel_id
        self.state.autostart_set_by = str(interaction.user)
        self.state.save(self.config.state_file)
        
        embed = footer(
            discord.Embed(
                title=f'🤖  Auto-Start · {"ENABLED" if enabled else "DISABLED"}',
                description=f'> Auto-Start has been **{"enabled" if enabled else "disabled"}** by `{interaction.user.display_name}`.',
                color=GREEN if enabled else RED,
            )
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='autostop', description='Auto-stop the server after it sits empty for a while')
    @app_commands.describe(
        enabled='True to enable auto-stop, False to disable it',
        minutes='Minutes of zero players before stopping (default: 20)',
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

        embed = footer(
            discord.Embed(
                title=f'💤  Auto-Stop · {"ENABLED" if enabled else "DISABLED"}',
                description=f'> Auto-Stop set to **{"enabled" if enabled else "disabled"}** ({self.state.autostop_minutes} min timeout).',
                color=GREEN if enabled else RED,
            )
        )
        await interaction.response.send_message(embed=embed)

    # ── Slash Commands: /statuschannel ────────────────────────────────────

    statuschannel_group = app_commands.Group(name='statuschannel', description='Configure live auto-updating status channels')

    @statuschannel_group.command(name='set', description='Set a text or voice channel for live server status')
    @app_commands.describe(
        text_channel='Text channel where the live auto-updating status embed will be posted',
        voice_channel='Optional voice channel whose name will dynamically show live status (e.g. 🟢 3/20)',
    )
    @is_authorized()
    async def statuschannel_set(
        self,
        interaction: discord.Interaction,
        text_channel: Optional[discord.TextChannel] = None,
        voice_channel: Optional[discord.VoiceChannel] = None,
    ):
        if not text_channel and not voice_channel:
            await interaction.response.send_message(
                embed=error_embed('Missing argument', 'Please specify at least a `text_channel` or a `voice_channel`.'),
                ephemeral=True,
            )
            return

        if text_channel:
            self.state.status_channel_id = text_channel.id
            self.state.status_message_id = None  # Will post a fresh message on next cycle

        if voice_channel:
            self.state.status_voice_channel_id = voice_channel.id

        self.state.save(self.config.state_file)

        embed = footer(
            discord.Embed(
                title='🟢  Live Status Channel Configured',
                description=(
                    '> The bot will continuously update live server information:\n\n'
                    f'📄  **Text Channel:** {text_channel.mention if text_channel else "*Not set*"}\n'
                    f'🔊  **Voice Channel:** {voice_channel.mention if voice_channel else "*Not set*"}\n'
                    '⏱️  **Refresh Rate:** Every 60 seconds'
                ),
                color=GREEN,
            )
        )
        await interaction.response.send_message(embed=embed)

    @statuschannel_group.command(name='remove', description='Disable live status channel updates')
    @is_authorized()
    async def statuschannel_remove(self, interaction: discord.Interaction):
        self.state.status_channel_id = None
        self.state.status_message_id = None
        self.state.status_voice_channel_id = None
        self.state.save(self.config.state_file)

        embed = footer(
            discord.Embed(
                title='🔴  Status Channels Removed',
                description='Live status channel auto-updates have been disabled.',
                color=YELLOW,
            )
        )
        await interaction.response.send_message(embed=embed)

    # ── Slash Commands: /alerts ───────────────────────────────────────────

    alerts_group = app_commands.Group(name='alerts', description='Manage server online/offline & player alerts')

    @alerts_group.command(name='set', description='Configure the alerts channel and role ping')
    @app_commands.describe(
        channel='Channel where alerts will be dispatched',
        role='Role to ping when the server comes online (e.g. @Minecraft)',
        notify_on='Types of events to receive',
    )
    @is_authorized()
    async def alerts_set(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        role: Optional[discord.Role] = None,
        notify_on: Literal['all', 'online', 'offline', 'players'] = 'all',
    ):
        self.state.alerts_channel_id = channel.id
        self.state.alerts_role_id = role.id if role else None
        self.state.alerts_notify_on = notify_on
        self.state.save(self.config.state_file)

        embed = footer(
            discord.Embed(
                title='🔔  Server Alerts Configured',
                description=(
                    f'> Notifications will be sent to {channel.mention}.\n\n'
                    f'🏷️  **Role Ping:** {role.mention if role else "*None*"}\n'
                    f'📋  **Events:** `{notify_on.upper()}`\n'
                ),
                color=GREEN,
            )
        )
        await interaction.response.send_message(embed=embed)

    @alerts_group.command(name='remove', description='Disable server alerts')
    @is_authorized()
    async def alerts_remove(self, interaction: discord.Interaction):
        self.state.alerts_channel_id = None
        self.state.alerts_role_id = None
        self.state.save(self.config.state_file)

        embed = footer(
            discord.Embed(
                title='🔕  Alerts Disabled',
                description='Server state and player join/leave alerts have been turned off.',
                color=YELLOW,
            )
        )
        await interaction.response.send_message(embed=embed)

    # ── Slash Commands: /schedule ─────────────────────────────────────────

    schedule_group = app_commands.Group(name='schedule', description='Schedule automated server start/stop times')

    @schedule_group.command(name='add', description='Add a scheduled start/stop timer')
    @app_commands.describe(
        action='Action to perform',
        time_utc='Time in 24-hour UTC format (e.g. 18:00 or 08:30)',
        days='Days when the schedule should trigger',
    )
    @is_authorized()
    async def schedule_add(
        self,
        interaction: discord.Interaction,
        action: Literal['start', 'stop', 'restart'],
        time_utc: str,
        days: Literal['all', 'weekdays', 'weekends', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'] = 'all',
    ):
        time_clean = time_utc.strip()
        parts = time_clean.split(':')
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit() or not (0 <= int(parts[0]) <= 23) or not (0 <= int(parts[1]) <= 59):
            await interaction.response.send_message(
                embed=error_embed('Invalid Time Format', 'Please specify time as `HH:MM` in 24-hour format (e.g. `18:00` or `09:30`).'),
                ephemeral=True,
            )
            return

        formatted_time = f'{int(parts[0]):02d}:{int(parts[1]):02d}'
        new_id = (max([s.get('id', 0) for s in self.state.schedules], default=0)) + 1
        new_entry = {
            'id': new_id,
            'action': action,
            'time': formatted_time,
            'days': days,
            'created_by': interaction.user.display_name,
        }
        self.state.schedules.append(new_entry)
        self.state.save(self.config.state_file)

        embed = footer(
            discord.Embed(
                title='⏰  Scheduled Timer Added',
                description=(
                    f'> Scheduled **{action.upper()}** every **{days.upper()}** at **{formatted_time} UTC**.\n'
                    f'🆔  **Schedule ID:** `#{new_id}`'
                ),
                color=GREEN,
            )
        )
        await interaction.response.send_message(embed=embed)

    @schedule_group.command(name='list', description='List all scheduled timers')
    async def schedule_list(self, interaction: discord.Interaction):
        if not self.state.schedules:
            embed = footer(
                discord.Embed(
                    title='⏰  Active Schedules',
                    description='No scheduled timers configured yet.\nUse `/schedule add` to create one!',
                    color=YELLOW,
                )
            )
        else:
            lines = [
                f"• `#{s['id']}` **{s['action'].upper()}** at `{s['time']} UTC` ({s['days']}) — *by {s.get('created_by', 'Admin')}*"
                for s in self.state.schedules
            ]
            embed = footer(
                discord.Embed(
                    title=f'⏰  Active Schedules ({len(self.state.schedules)})',
                    description='\n'.join(lines),
                    color=BLUE,
                )
            )
        await interaction.response.send_message(embed=embed)

    @schedule_group.command(name='remove', description='Remove a scheduled timer by ID')
    @app_commands.describe(id='The ID number of the schedule to delete')
    @is_authorized()
    async def schedule_remove(self, interaction: discord.Interaction, id: int):
        before_len = len(self.state.schedules)
        self.state.schedules = [s for s in self.state.schedules if s.get('id') != id]
        self.state.save(self.config.state_file)

        if len(self.state.schedules) < before_len:
            embed = footer(
                discord.Embed(
                    title='🗑️  Schedule Removed',
                    description=f'Schedule `#{id}` has been deleted.',
                    color=GREEN,
                )
            )
        else:
            embed = error_embed('Not Found', f'No schedule with ID `#{id}` was found.')

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(AutomationCog(bot))
