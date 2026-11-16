import discord

from combat.stats import calculate_stats
import io
from utils.shiny import get_card_file
import asyncio



def build_stats_embed(
    card_id: str,
    card_name: str,
    rarity: str,
    level: int = 1,
    instance_id: int | None = None
):
    stats = calculate_stats(
        rarity=rarity,
        card_id=card_id,
        level=level
    )

    embed = discord.Embed(
        title=f"⚔️ {card_name} — Combat Stats",
        description=(
            f"**Rarity:** {rarity.replace('_', ' ').title()}\n"
            f"**Level:** {level}/20"
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="❤️ HP",
        value=f"{stats.hp:,}"
    )

    embed.add_field(
        name="⚔️ ATK",
        value=f"{stats.atk:,}"
    )

    embed.add_field(
        name="🛡️ DEF",
        value=f"{stats.defense:,}"
    )

    embed.add_field(
        name="💨 SPD",
        value=f"{stats.speed:,}"
    )

    embed.add_field(
        name="🎯 Crit Rate",
        value=f"{stats.crit_rate}%"
    )

    if instance_id is not None:
        embed.set_footer(
            text=f"Card Instance #{instance_id}"
        )

    return embed


class CardStatsButton(discord.ui.Button):
    def __init__(
        self,
        card_id,
        card_name,
        rarity,
        instance_id=None,
        level=1,
        row=None
    ):
        super().__init__(
            label="Stats",
            emoji="⚔️",
            style=discord.ButtonStyle.primary,
            row=row
        )

        self.card_id = card_id
        self.card_name = card_name
        self.rarity = rarity
        self.instance_id = instance_id
        self.level = level

    async def callback(self, interaction: discord.Interaction):
        view = self.view

        if view is None:
            return

        # Acknowledge immediately to avoid Discord's 3-second timeout.
        await interaction.response.defer()

        try:
            # RETURN TO CARD VIEW
            if getattr(view, "showing_stats", False):

                image_file = await asyncio.to_thread(
                    get_card_file,
                    view.image_path,
                    view.shiny
                )
                # Copy the original embed
                card_embed = view.original_embed.copy()

                # Point the embed to the newly uploaded image
                card_embed.set_image(
                    url=f"attachment://{image_file.filename}"
                )

                await interaction.edit_original_response(
                    embed=card_embed,
                    attachments=[image_file],
                    view=view
                )

                view.showing_stats = False

                self.label = "View Stats"
                self.emoji = "⚔️"
                self.style = discord.ButtonStyle.primary

                await interaction.edit_original_response(
                    view=view
                )
                return

            # SAVE ORIGINAL EMBED
            if getattr(view, "original_embed", None) is None:
                view.original_embed = (
                    interaction.message.embeds[0].copy()
                )

            # BUILD STATS EMBED
            stats_embed = await asyncio.to_thread(
                build_stats_embed,
                self.card_id,
                self.card_name,
                self.rarity,
                self.level,
                self.instance_id
            )

            await interaction.edit_original_response(
                embed=stats_embed,
                attachments=[]
            )

            view.showing_stats = True

            self.label = "Back to Card"
            self.emoji = "🔙"
            self.style = discord.ButtonStyle.secondary

            await interaction.edit_original_response(
                view=view
            )

        except Exception:
            import logging

            logging.exception(
                "Failed to switch card display"
            )

            await interaction.followup.send(
                "❌ Couldn't update the card display. "
                "Check the bot console for details.",
                ephemeral=True
            )