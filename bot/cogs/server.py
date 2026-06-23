"""Server management commands: /status, /info, /start, /stop, /restart, /panel."""

from __future__ import annotations

import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from ..aternos_client import AternosError
from ..constants import BLUE, GREEN, RED, TRANSITIONAL_STATES, YELLOW, status_color, status_emoji
from ..embeds import error_embed, footer
from ..permissions import is_authorized
from ..views import ConfirmView, ControlPanelView

log = logging.getLogger('AternosBot.server')

START_POLL_ATTEMPTS = 60  # 60 * 5s = 5 minutes
START_POLL_INTERVAL = 5


class ServerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.aternos = bot.aternos

    async def _fetch_or_raise(self) -> None:
        ok = await self.aternos.fetch()
        if not ok:
            raise AternosError('Could not reach Aternos after multiple retries.')

    @staticmethod
    def _edition(server) -> str:
        return 'Bedrock' if server.is_bedrock else 'Java'

    # ── /status ──────────────────────────────────────────────────────────

    @app_commands.command(name='status', description='Check live Minecraft server status')
    async def status(self, interaction: discord.Interaction):
        log.info(f'/status used by {interaction.user} in #{interaction.channel}')
        await interaction.response.defer()
        try:
            await self._fetch_or_raise()
            await interaction.followup.send(embed=self._status_embed())
        except Exception as e:
            log.error(f'/status error: {e}')
            await interaction.followup.send(embed=error_embed('Error fetching status', e))

    def _status_embed(self) -> discord.Embed:
        server = self.aternos.server
        s = server.status.lower()
        embed = discord.Embed(title=f'{status_emoji(s)}  Server Status', color=status_color(s))
        embed.add_field(name='Status', value=f'`{server.status}`', inline=True)
        embed.add_field(name='Address', value=f'`{server.address}`', inline=True)
        embed.add_field(name='Players', value=f'`{server.players_count}`', inline=True)
        if server.players_list:
            embed.add_field(
                name='Online Players',
                value=', '.join(f'`{p}`' for p in server.players_list),
                inline=False,
            )
        return footer(embed)

    # ── /info ────────────────────────────────────────────────────────────

    @app_commands.command(name='info', description='Show detailed server information')
    async def info(self, interaction: discord.Interaction):
        log.info(f'/info used by {interaction.user} in #{interaction.channel}')
        await interaction.response.defer()
        try:
            await self._fetch_or_raise()
            server = self.aternos.server
            embed = discord.Embed(title='ℹ️  Server Information', color=BLUE)
            embed.add_field(name='🌐  Address', value=f'`{server.address}`', inline=True)
            embed.add_field(name='🔌  Port', value=f'`{server.port}`', inline=True)
            embed.add_field(name='📦  Software', value=f'`{server.software}`', inline=True)
            embed.add_field(name='🏷️  Version', value=f'`{server.version}`', inline=True)
            embed.add_field(name='💾  RAM', value=f'`{server.ram} MB`', inline=True)
            embed.add_field(name='👥  Slots', value=f'`{server.slots}`', inline=True)
            embed.add_field(name='📋  Edition', value=f'`{self._edition(server)}`', inline=True)
            embed.add_field(name='💬  MOTD', value=f'`{server.motd}`', inline=False)
            footer(embed)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            log.error(f'/info error: {e}')
            await interaction.followup.send(embed=error_embed('Error fetching info', e))

    # ── /panel ───────────────────────────────────────────────────────────

    @app_commands.command(name='panel', description='Post an interactive server control panel')
    async def panel(self, interaction: discord.Interaction):
        log.info(f'/panel used by {interaction.user} in #{interaction.channel}')
        await interaction.response.defer()
        try:
            await self._fetch_or_raise()
            await interaction.followup.send(embed=self._panel_embed(), view=ControlPanelView(self))
        except Exception as e:
            log.error(f'/panel error: {e}')
            await interaction.followup.send(embed=error_embed('Error building panel', e))

    def _panel_embed(self) -> discord.Embed:
        server = self.aternos.server
        s = server.status.lower()
        embed = discord.Embed(title='🎮  Server Control Panel', color=status_color(s))
        embed.add_field(name='Status', value=f'{status_emoji(s)} `{server.status}`', inline=True)
        embed.add_field(name='Players', value=f'`{server.players_count}/{server.slots}`', inline=True)
        embed.add_field(name='Address', value=f'```{self.aternos.address}```', inline=False)
        return footer(embed)

    async def panel_refresh(self, interaction: discord.Interaction):
        try:
            await self._fetch_or_raise()
            await interaction.response.edit_message(embed=self._panel_embed(), view=ControlPanelView(self))
        except Exception as e:
            log.error(f'/panel refresh error: {e}')
            await interaction.response.send_message(embed=error_embed('Error refreshing panel', e), ephemeral=True)

    # ── shared confirmation helper ───────────────────────────────────────

    async def _confirm(self, interaction: discord.Interaction, action: str) -> bool:
        view = ConfirmView(author_id=interaction.user.id)
        embed = footer(
            discord.Embed(
                title=f'⚠️  Confirm {action}',
                description=f'Are you sure you want to **{action.lower()}** the server?',
                color=YELLOW,
            )
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()
        await view.wait()
        return bool(view.confirmed)

    async def _poll_until(self, predicate, attempts: int = START_POLL_ATTEMPTS, interval: int = START_POLL_INTERVAL) -> bool:
        for _ in range(attempts):
            await asyncio.sleep(interval)
            await self.aternos.fetch()
            log.info(f'Polling server status: {self.aternos.server.status}')
            if predicate():
                return True
        return False

    @staticmethod
    async def _respond_error(interaction: discord.Interaction, title: str, err: Exception) -> None:
        log.error(f'{title}: {err}')
        embed = error_embed(title, err)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.followup.send(embed=embed)
        except discord.HTTPException:
            pass

    # ── /start (shared with the panel's Start button) ───────────────────

    @app_commands.command(name='start', description='Start the Minecraft server')
    @is_authorized()
    async def start(self, interaction: discord.Interaction):
        log.info(f'/start used by {interaction.user} in #{interaction.channel}')
        await self.start_flow(interaction)

    async def start_flow(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        try:
            await self._fetch_or_raise()
            server = self.aternos.server
            current = server.status.lower()

            if current == 'online':
                embed = discord.Embed(
                    title='🟢  Server Already Online',
                    description=(
                        '> The server is already up and running!\n\n'
                        '**📋  How to join**\n1. Open Minecraft\n2. Go to **Multiplayer → Add Server**\n'
                        '3. Paste the address below and hit **Join**'
                    ),
                    color=GREEN,
                )
                embed.add_field(name='🌐  Server Address', value=f'```{self.aternos.address}```', inline=False)
                embed.add_field(name='🔌  Port', value=f'`{server.port}`', inline=True)
                embed.add_field(name='📦  Software', value=f'`{server.software} {server.version}`', inline=True)
                embed.add_field(name='👥  Open Slots', value=f'`{server.slots}`', inline=True)
                footer(embed)
                await interaction.followup.send(embed=embed)
                return

            if current in TRANSITIONAL_STATES:
                embed = discord.Embed(
                    title='🟡  Server is Already Starting',
                    description="The server is booting up — hang tight!\nUse `/status` to monitor progress.",
                    color=YELLOW,
                )
                embed.add_field(name='🌐  Address', value=f'```{self.aternos.address}```', inline=False)
                footer(embed)
                await interaction.followup.send(embed=embed)
                return

            embed_starting = discord.Embed(
                title='⏳  Booting Server...',
                description=(
                    '> Startup usually takes **2 – 4 minutes**.\n'
                    "> You'll be pinged right here the moment it's live!\n\n"
                    f'🚀  Started by **{interaction.user.display_name}**'
                ),
                color=YELLOW,
            )
            embed_starting.add_field(name='🌐  Address (ready soon)', value=f'```{self.aternos.address}```', inline=False)
            embed_starting.add_field(name='📦  Software', value=f'`{server.software} {server.version}`', inline=True)
            embed_starting.add_field(name='👥  Slots', value=f'`{server.slots}`', inline=True)
            embed_starting.add_field(name='🖥️  Edition', value=f'`{self._edition(server)}`', inline=True)
            footer(embed_starting)
            await interaction.followup.send(embed=embed_starting)

            log.info('Sending start command to Aternos...')
            started = await self.aternos.start()
            if not started:
                raise AternosError('Failed to send start command to Aternos.')

            online = await self._poll_until(lambda: self.aternos.server.status.lower() == 'online')
            server = self.aternos.server

            if online:
                embed_done = discord.Embed(
                    title='🎉  Server is LIVE!',
                    description=(
                        f'> {interaction.user.mention} your server is ready!\n\n'
                        '**📋  How to join**\n1. Open **Minecraft**\n2. Go to **Multiplayer → Add Server**\n'
                        '3. Copy the address below and click **Join Server**'
                    ),
                    color=GREEN,
                )
                embed_done.add_field(name='🌐  Server Address  *(copy & paste this)*', value=f'```{self.aternos.address}```', inline=False)
                embed_done.add_field(name='🔌  Port', value=f'`{server.port}`', inline=True)
                embed_done.add_field(name='📦  Software', value=f'`{server.software} {server.version}`', inline=True)
                embed_done.add_field(name='👥  Open Slots', value=f'`{server.slots}`', inline=True)
                embed_done.add_field(name='🖥️  Edition', value=f'`{self._edition(server)}`', inline=True)
                embed_done.add_field(name='💬  MOTD', value=f'`{server.motd}`', inline=False)
                footer(embed_done)
                await interaction.channel.send(content=f'🟢 {interaction.user.mention}', embed=embed_done)
                log.info(f'Server online at {self.aternos.address}:{server.port}')
            else:
                embed_timeout = discord.Embed(
                    title='⏳  Taking Longer Than Expected',
                    description='The server is still starting up.\nUse `/status` to check progress, or try `/start` again in a few minutes.',
                    color=YELLOW,
                )
                embed_timeout.add_field(name='🌐  Address', value=f'```{self.aternos.address}```', inline=False)
                footer(embed_timeout)
                await interaction.channel.send(embed=embed_timeout)
                log.warning('Server did not come online within the 5-minute timeout.')

        except Exception as e:
            log.error(f'/start error: {e}')
            try:
                await interaction.followup.send(embed=error_embed('Error Starting Server', e))
            except discord.HTTPException:
                pass

    # ── /stop (shared with the panel's Stop button) ─────────────────────

    @app_commands.command(name='stop', description='Stop the Minecraft server')
    @is_authorized()
    async def stop(self, interaction: discord.Interaction):
        log.info(f'/stop used by {interaction.user} in #{interaction.channel}')
        await self.stop_flow(interaction)

    async def stop_flow(self, interaction: discord.Interaction) -> None:
        try:
            await self._fetch_or_raise()
        except Exception as e:
            await self._respond_error(interaction, 'Error Stopping Server', e)
            return

        server = self.aternos.server
        if server.status.lower() == 'offline':
            embed = footer(
                discord.Embed(
                    title='🔴  Server Already Offline',
                    description='The server is not running. Use `/start` to boot it up.',
                    color=RED,
                )
            )
            await interaction.response.send_message(embed=embed)
            return

        if not await self._confirm(interaction, 'Stop'):
            await interaction.followup.send('Cancelled — the server was **not** stopped.', ephemeral=True)
            return

        try:
            stopped = await self.aternos.stop()
            if not stopped:
                raise AternosError('Failed to send stop command to Aternos.')
            server = self.aternos.server
            log.info(f'Stop command sent by {interaction.user}')
            embed = discord.Embed(
                title='⏹️  Shutting Down...',
                description=(
                    '> The server is gracefully shutting down.\n\n'
                    f"🛑  Stopped by **{interaction.user.display_name}**\nUse `/status` to confirm it's fully offline."
                ),
                color=RED,
            )
            embed.add_field(name='🌐  Server', value=f'```{self.aternos.address}```', inline=False)
            embed.add_field(name='📦  Software', value=f'`{server.software} {server.version}`', inline=True)
            footer(embed)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await self._respond_error(interaction, 'Error Stopping Server', e)

    # ── /restart (shared with the panel's Restart button) ───────────────

    @app_commands.command(name='restart', description='Restart the Minecraft server')
    @is_authorized()
    async def restart(self, interaction: discord.Interaction):
        log.info(f'/restart used by {interaction.user} in #{interaction.channel}')
        await self.restart_flow(interaction)

    async def restart_flow(self, interaction: discord.Interaction) -> None:
        try:
            await self._fetch_or_raise()
        except Exception as e:
            await self._respond_error(interaction, 'Error Restarting Server', e)
            return

        if not await self._confirm(interaction, 'Restart'):
            await interaction.followup.send('Cancelled — the server was **not** restarted.', ephemeral=True)
            return

        try:
            restarted = await self.aternos.restart()
            if not restarted:
                raise AternosError('Failed to send restart command to Aternos.')
            server = self.aternos.server
            log.info(f'Restart command sent by {interaction.user}')
            embed = discord.Embed(
                title='🔄  Restarting Server...',
                description=(
                    '> The server is rebooting — this takes **2 – 4 minutes**.\n\n'
                    f'🔁  Restarted by **{interaction.user.display_name}**\nUse `/status` to track the progress.'
                ),
                color=BLUE,
            )
            embed.add_field(name='🌐  Server Address', value=f'```{self.aternos.address}```', inline=False)
            embed.add_field(name='🔌  Port', value=f'`{server.port}`', inline=True)
            embed.add_field(name='📦  Software', value=f'`{server.software} {server.version}`', inline=True)
            embed.add_field(name='👥  Slots', value=f'`{server.slots}`', inline=True)
            footer(embed)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await self._respond_error(interaction, 'Error Restarting Server', e)


async def setup(bot: commands.Bot):
    await bot.add_cog(ServerCog(bot))
