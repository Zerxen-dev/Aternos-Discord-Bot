"""Embed-building helpers shared across cogs."""

from __future__ import annotations

import datetime

import discord

from .constants import RED


def footer(embed: discord.Embed) -> discord.Embed:
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%d %b %Y %H:%M UTC')
    embed.set_footer(text=f'Aternos Bot  •  {stamp}')
    return embed


def error_embed(title: str, err: Exception) -> discord.Embed:
    embed = discord.Embed(title=f'❌  {title}', description=f'```{err}```', color=RED)
    return footer(embed)
