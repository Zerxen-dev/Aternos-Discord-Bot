"""Discord Modals for interactive parameter setting and scheduling."""

from __future__ import annotations

import logging
from typing import Any, Callable, Coroutine

import discord

log = logging.getLogger('AternosBot.modals')


class SetPropertyModal(discord.ui.Modal, title='⚙️ Set Server Property'):
    """Interactive modal dialog for configuring Minecraft server properties."""

    property_key = discord.ui.TextInput(
        label='Property Key',
        placeholder='e.g. difficulty, gamemode, white-list, pvp, max-players',
        required=True,
        max_length=50,
    )

    property_value = discord.ui.TextInput(
        label='New Value',
        placeholder='e.g. hard, creative, true, false, 20',
        required=True,
        max_length=100,
    )

    def __init__(self, callback_coro: Callable[[discord.Interaction, str, str], Coroutine[Any, Any, None]]):
        super().__init__()
        self.callback_coro = callback_coro

    async def on_submit(self, interaction: discord.Interaction):
        key = self.property_key.value.strip()
        val = self.property_value.value.strip()
        await self.callback_coro(interaction, key, val)


class AddScheduleModal(discord.ui.Modal, title='⏰ Add Automated Server Timer'):
    """Interactive modal dialog for scheduling recurring start/stop routines."""

    action = discord.ui.TextInput(
        label='Action (start / stop / restart)',
        placeholder='start, stop, or restart',
        default='start',
        required=True,
        max_length=10,
    )

    time_utc = discord.ui.TextInput(
        label='Time UTC (HH:MM)',
        placeholder='e.g. 18:30 or 09:00 (24-hour UTC format)',
        required=True,
        max_length=5,
    )

    days = discord.ui.TextInput(
        label='Days to Run',
        placeholder='all, weekdays, weekends, or day name (e.g. friday)',
        default='all',
        required=True,
        max_length=20,
    )

    def __init__(self, callback_coro: Callable[[discord.Interaction, str, str, str], Coroutine[Any, Any, None]]):
        super().__init__()
        self.callback_coro = callback_coro

    async def on_submit(self, interaction: discord.Interaction):
        act = self.action.value.strip().lower()
        t = self.time_utc.value.strip()
        d = self.days.value.strip().lower()
        await self.callback_coro(interaction, act, t, d)
