
import asyncio
import sqlite3

import discord

from database import (
    sell_card,
    SELL_VALUES,
    SHINY_MULTIPLIER
)


class CardSaleView(discord.ui.View):
    def __init__(
        self,
        owner_id: int,
        instance_id: int,
        card_name: str,
        rarity: str,
        shiny: bool
    ):
        super().__init__(timeout=180)

        self.owner_id = owner_id
        self.instance_id = instance_id
        self.card_name = card_name
        self.rarity = rarity
        self.shiny = shiny

        self.value = (
            SELL_VALUES[rarity]
            * (SHINY_MULTIPLIER if shiny else 1)
        )

        self.confirming = False
        self.sold = False
        self.closed = False
        self.message = None
        self.lock = asyncio.Lock()

        self.confirm_button.disabled = True
        self.cancel_button.disabled = True

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "🥟 This isn't your card to sell!",
                ephemeral=True
            )
            return False

        return True

    def update_buttons(self):
        self.sell_button.disabled = (
            self.confirming or self.closed
        )
        self.confirm_button.disabled = (
            not self.confirming or self.closed
        )
        self.cancel_button.disabled = (
            not self.confirming or self.closed
        )

        if self.sold:
            self.sell_button.label = "Sold"
            self.sell_button.emoji = "✅"

    @discord.ui.button(
        label="Sell Card",
        emoji="🪙",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def sell_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        async with self.lock:
            if self.closed:
                await interaction.response.send_message(
                    "This sale is no longer available.",
                    ephemeral=True
                )
                return

            self.confirming = True
            self.update_buttons()

            await interaction.response.edit_message(
                content=(
                    f"⚠️ <@{self.owner_id}>, sell "
                    f"**{discord.utils.escape_markdown(self.card_name)}** "
                    f"(instance `#{self.instance_id}`) "
                    f"for **{self.value:,} BC**?\n"
                    "This cannot be undone."
                ),
                view=self,
                allowed_mentions=discord.AllowedMentions.none()
            )

    @discord.ui.button(
        label="Confirm Sale",
        emoji="✅",
        style=discord.ButtonStyle.danger,
        row=0
    )
    async def confirm_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
      
        async with self.lock:
            if self.closed or not self.confirming:
                await interaction.response.send_message(
                    "This sale is no longer pending.",
                    ephemeral=True
                )
                return

            # Acknowledge the interaction immediately.
            await interaction.response.defer()

            try:
                result = await asyncio.to_thread(
                    sell_card,
                    self.owner_id,
                    self.instance_id,
                    True
                )
            except (sqlite3.Error, OSError):
                await interaction.followup.send(
                    "⚠️ Couldn't complete the sale. "
                    "Please try again.",
                    ephemeral=True
                )
                return

            if result["status"] == "success":
                self.sold = True
                self.closed = True
                self.confirming = False
                self.update_buttons()

                # Only update the buttons.
                # Keep the original embed and image untouched.
                await interaction.message.edit(
                    content=None,
                    view=self
                )

                self.stop()
                return

            if result["status"] == "not_found":
                self.closed = True
                self.confirming = False
                self.update_buttons()

                await interaction.message.edit(
                    content=(
                        "❌ This card is no longer "
                        "in your inventory."
                    ),
                    view=self
                )

                self.stop()
                return

            await interaction.followup.send(
                f"⚠️ Sale failed: {result['status']}",
                ephemeral=True
            )


            # Card may have been sold or traded meanwhile.
            if result["status"] == "not_found":
                self.closed = True
                self.confirming = False
                self.update_buttons()

                await interaction.message.edit(
                    content=(
                        "❌ This card is no longer in "
                        "your inventory. No sale occurred."
                    ),
                    view=self
                )
                self.stop()
                return

            await interaction.followup.send(
                f"⚠️ Sale failed: {result['status']}",
                ephemeral=True
            )

    @discord.ui.button(
        label="Cancel",
        emoji="❌",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def cancel_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        async with self.lock:
            if self.closed or not self.confirming:
                await interaction.response.send_message(
                    "There's no pending sale.",
                    ephemeral=True
                )
                return

            self.confirming = False
            self.update_buttons()

            await interaction.response.edit_message(
                content=None,
                view=self
            )

    async def on_timeout(self):
        async with self.lock:
            if self.closed:
                return

            self.closed = True

            for item in self.children:
                item.disabled = True

            if self.message:
                try:
                    await self.message.edit(view=self)
                except discord.HTTPException:
                    pass
