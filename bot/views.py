"""Interactive UI components: confirmation dialogs and the server control panel."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord

from .permissions import user_is_authorized

if TYPE_CHECKING:
    from .cogs.server import ServerCog


class ConfirmView(discord.ui.View):
    """A Confirm/Cancel pair restricted to the original requester (or other admins)."""

    def __init__(self, author_id: int, *, timeout: float = 30.0):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.confirmed: Optional[bool] = None
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.author_id or user_is_authorized(interaction):
            return True
        await interaction.response.send_message(
            'Only the person who ran this command can confirm it.', ephemeral=True
        )
        return False

    def _disable(self) -> None:
        for child in self.children:
            child.disabled = True  # type: ignore[attr-defined]

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.danger, emoji='✅')
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        self._disable()
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.secondary, emoji='✖️')
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = False
        self._disable()
        await interaction.response.edit_message(view=self)
        self.stop()

    async def on_timeout(self) -> None:
        self.confirmed = False
        self._disable()
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class ControlPanelView(discord.ui.View):
    """Persistent-style Start / Stop / Restart / Refresh panel for a ServerCog."""

    def __init__(self, cog: 'ServerCog'):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label='Refresh', style=discord.ButtonStyle.secondary, emoji='🔄', row=0)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.panel_refresh(interaction)

    @discord.ui.button(label='Start', style=discord.ButtonStyle.success, emoji='▶️', row=0)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not user_is_authorized(interaction):
            await interaction.response.send_message("You don't have permission to do that.", ephemeral=True)
            return
        await self.cog.start_flow(interaction)

    @discord.ui.button(label='Stop', style=discord.ButtonStyle.danger, emoji='⏹️', row=0)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not user_is_authorized(interaction):
            await interaction.response.send_message("You don't have permission to do that.", ephemeral=True)
            return
        await self.cog.stop_flow(interaction)

    @discord.ui.button(label='Restart', style=discord.ButtonStyle.primary, emoji='🔁', row=0)
    async def restart(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not user_is_authorized(interaction):
            await interaction.response.send_message("You don't have permission to do that.", ephemeral=True)
            return
        await self.cog.restart_flow(interaction)
