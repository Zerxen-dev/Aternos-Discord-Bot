"""AI-powered natural language command interface for conversational bot control."""

from __future__ import annotations

import logging
import discord
from discord import app_commands
from discord.ext import commands

from ..constants import BLUE, GREEN, PURPLE, RED, YELLOW, status_color, status_emoji
from ..embeds import error_embed, footer
from ..services.ai_service import AIService

log = logging.getLogger('AternosBot.ai_cog')


class AICog(commands.Cog):
    """Cog providing the /ask natural language command."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.aternos = bot.aternos

    @app_commands.command(name='ask', description='Ask the bot anything about the server in plain English')
    @app_commands.describe(query='Natural language command or question (e.g. "who is online?", "is the server up?")')
    async def ask(self, interaction: discord.Interaction, query: str):
        log.info(f'/ask used by {interaction.user}: {query}')
        await interaction.response.defer()

        try:
            # Check if AI is configured in config
            api_key = getattr(self.bot.config, 'ai_api_key', None)
            provider = getattr(self.bot.config, 'ai_provider', 'gemini')

            # Parse intent via AI Service
            result = await AIService.interpret_query(query, api_key=api_key, provider=provider)
            intent = result.get('intent', 'unknown')
            explanation = result.get('explanation', '')

            # Execute or query corresponding action
            if intent == 'status':
                await self.aternos.fetch()
                srv = self.aternos.server
                s = srv.status.lower()
                embed = discord.Embed(
                    title=f'{status_emoji(s)}  Server Status ({result.get("action_label")})',
                    description=f'> 🧠 *AI Interpretation:* {explanation}\n\n'
                                f'• **Status:** `{srv.status}`\n'
                                f'• **Address:** `{self.aternos.address}`\n'
                                f'• **Players:** `{srv.players_count}/{srv.slots}`',
                    color=status_color(s),
                )
                await interaction.followup.send(embed=footer(embed))

            elif intent == 'players':
                await self.aternos.fetch()
                srv = self.aternos.server
                players = getattr(srv, 'players_list', []) or []
                embed = discord.Embed(
                    title='👥  Online Players',
                    description=f'> 🧠 *AI Interpretation:* {explanation}\n\n' + (
                        ', '.join(f'`{p}`' for p in players) if players else 'No players are currently online.'
                    ),
                    color=GREEN if players else BLUE,
                )
                embed.add_field(name='Count', value=f'{len(players)} / {srv.slots}', inline=True)
                await interaction.followup.send(embed=footer(embed))

            elif intent == 'info':
                await self.aternos.fetch()
                srv = self.aternos.server
                embed = discord.Embed(
                    title='ℹ️  Server Specifications',
                    description=f'> 🧠 *AI Interpretation:* {explanation}\n\n'
                                f'• **Software:** `{srv.software} {srv.version}`\n'
                                f'• **Address:** `{self.aternos.address}`\n'
                                f'• **Port:** `{srv.port}`\n'
                                f'• **RAM:** `{srv.ram} MB`',
                    color=BLUE,
                )
                await interaction.followup.send(embed=footer(embed))

            elif intent in ('start', 'stop', 'restart'):
                # For safety, ask user to confirm or run direct slash command
                embed = footer(
                    discord.Embed(
                        title=f'⚡  Action Identified: {result.get("action_label")}',
                        description=(
                            f'> 🧠 *AI Interpretation:* {explanation}\n\n'
                            f'To execute server-altering actions safely, please use the direct command:\n'
                            f'• `/{intent}` or `/panel`'
                        ),
                        color=YELLOW,
                    )
                )
                await interaction.followup.send(embed=embed)

            else:
                embed = footer(
                    discord.Embed(
                        title='🤖  AI Assistant',
                        description=(
                            f'> *Query:* "{query}"\n\n'
                            f'{explanation}\n\n'
                            '**Try asking:**\n'
                            '• *"Is the server online?"*\n'
                            '• *"Who is currently playing?"*\n'
                            '• *"What is the server address and RAM?"*'
                        ),
                        color=PURPLE,
                    )
                )
                await interaction.followup.send(embed=embed)

        except Exception as e:
            log.error(f'/ask error: {e}')
            await interaction.followup.send(embed=error_embed('Error processing question', e))


async def setup(bot: commands.Bot):
    await bot.add_cog(AICog(bot))
