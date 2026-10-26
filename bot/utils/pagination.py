"""Interactive pagination view for Discord lists (whitelists, OPs, bans, backups)."""

from __future__ import annotations

import math
from typing import Any, Callable, Sequence

import discord
from ..constants import BLUE
from ..embeds import footer


class PaginatorView(discord.ui.View):
    """Generic pagination view with Previous and Next buttons."""

    def __init__(
        self,
        items: Sequence[str],
        title: str,
        per_page: int = 10,
        author_id: int | None = None,
        color: int = BLUE,
        format_item: Callable[[int, str], str] | None = None,
    ):
        super().__init__(timeout=180)
        self.items = list(items)
        self.title = title
        self.per_page = max(1, per_page)
        self.author_id = author_id
        self.color = color
        self.format_item = format_item or (lambda idx, it: f"• `{it}`")

        self.current_page = 0
        self.total_pages = max(1, math.ceil(len(self.items) / self.per_page))

        self._update_buttons()

    def _update_buttons(self) -> None:
        self.prev_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page >= self.total_pages - 1)
        self.page_indicator.label = f"Page {self.current_page + 1}/{self.total_pages} ({len(self.items)} total)"

    def build_embed(self) -> discord.Embed:
        start = self.current_page * self.per_page
        end = start + self.per_page
        page_items = self.items[start:end]

        if not page_items:
            desc = "List is empty."
        else:
            desc = "\n".join(self.format_item(start + i + 1, it) for i, it in enumerate(page_items))

        embed = discord.Embed(
            title=f"{self.title}",
            description=desc,
            color=self.color,
        )
        return footer(embed)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.author_id and interaction.user.id != self.author_id:
            await interaction.response.send_message("Only the command author can change pages.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self._update_buttons()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Page 1/1", style=discord.ButtonStyle.secondary, disabled=True)
    async def page_indicator(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._update_buttons()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)
