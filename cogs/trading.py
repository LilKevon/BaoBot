
import asyncio
import sqlite3

import discord
from discord.ext import commands

from database import (
    get_trade_preview,
    execute_trade
)


RARITY_ICONS = {
    "common": "⚪",
    "uncommon": "🟢",
    "rare": "🔵",
    "epic": "🟣",
    "legendary": "🟡",
    "mythical": "🔴",
    "divine": "💎",
    "peebing_cool": "🥟"
}


def card_description(card, lookup):
    info = lookup.get(card["card_id"], {})
    name = info.get("name", card["card_id"])

    rarity = card["rarity"]
    rarity_name = rarity.replace("_", " ").title()
    icon = RARITY_ICONS.get(rarity, "❔")
    shiny = "✨ Shiny" if card["is_shiny"] else "Normal"

    return (
        f"**{discord.utils.escape_markdown(name)}**\n"
        f"{icon} {rarity_name} • {shiny}\n"
        f"Instance `#{card['instance_id']}`"
    )


class TradeView(discord.ui.View):
    def __init__(
        self,
        sender_id,
        receiver_id,
        sender_card_id,
        receiver_card_id
    ):
        super().__init__(timeout=120)

        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.sender_card_id = sender_card_id
        self.receiver_card_id = receiver_card_id

        self.message = None
        self.finished = False
        self.lock = asyncio.Lock()

    def disable_buttons(self):
        for item in self.children:
            item.disabled = True

    async def finish(self, interaction, message):
        self.finished = True
        self.disable_buttons()
        self.stop()

        await interaction.response.edit_message(
            content=message,
            view=self
        )

    @discord.ui.button(
        label="Accept",
        emoji="✅",
        style=discord.ButtonStyle.success,
        row=0
    )
    async def accept(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user.id != self.receiver_id:
            await interaction.response.send_message(
                "❌ Only the recipient can accept this trade.",
                ephemeral=True
            )
            return

        async with self.lock:
            if self.finished:
                await interaction.response.send_message(
                    "This trade is no longer available.",
                    ephemeral=True
                )
                return

            try:
                result = await asyncio.to_thread(
                    execute_trade,
                    self.sender_id,
                    self.receiver_id,
                    self.sender_card_id,
                    self.receiver_card_id
                )
            except sqlite3.Error:
                await interaction.response.send_message(
                    "⚠️ Database error. Trade not completed.",
                    ephemeral=True
                )
                return

            if result["status"] == "success":
                await self.finish(
                    interaction,
                    (
                        "✅ **Trade completed!**\n"
                        f"<@{self.sender_id}> received "
                        f"card `#{self.receiver_card_id}`.\n"
                        f"<@{self.receiver_id}> received "
                        f"card `#{self.sender_card_id}`."
                    )
                )
            else:
                await self.finish(
                    interaction,
                    (
                        "❌ **Trade failed.**\n"
                        "One of the offered cards is no longer "
                        "owned by the original player.\n"
                        "No cards were exchanged."
                    )
                )

    @discord.ui.button(
        label="Decline",
        emoji="❌",
        style=discord.ButtonStyle.danger,
        row=0
    )
    async def decline(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user.id != self.receiver_id:
            await interaction.response.send_message(
                "Only the recipient can decline this trade.",
                ephemeral=True
            )
            return

        async with self.lock:
            if self.finished:
                await interaction.response.send_message(
                    "This trade is already closed.",
                    ephemeral=True
                )
                return

            await self.finish(
                interaction,
                "❌ **Trade declined.** No cards exchanged."
            )

    @discord.ui.button(
        label="Cancel",
        emoji="🛑",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user.id != self.sender_id:
            await interaction.response.send_message(
                "Only the sender can cancel this trade.",
                ephemeral=True
            )
            return

        async with self.lock:
            if self.finished:
                await interaction.response.send_message(
                    "This trade is already closed.",
                    ephemeral=True
                )
                return

            await self.finish(
                interaction,
                "🛑 **Trade cancelled.** No cards exchanged."
            )

    async def on_timeout(self):
        async with self.lock:
            if self.finished:
                return

            self.finished = True
            self.disable_buttons()

            if self.message:
                try:
                    await self.message.edit(
                        content=(
                            "⏰ **Trade expired.** "
                            "No cards exchanged."
                        ),
                        view=self
                    )
                except discord.HTTPException:
                    pass


class Trading(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="trade")
    @commands.guild_only()
    @commands.cooldown(
        1, 15, commands.BucketType.user
    )
    async def trade(
        self,
        ctx,
        member: discord.Member,
        my_card_id: int,
        their_card_id: int
    ):
        if member.bot:
            await ctx.send(
                "❌ You can't trade with bots."
            )
            return

        if member.id == ctx.author.id:
            await ctx.send(
                "❌ You can't trade with yourself."
            )
            return

        preview = await asyncio.to_thread(
            get_trade_preview,
            ctx.author.id,
            member.id,
            my_card_id,
            their_card_id
        )

        if preview["status"] != "valid":
            await ctx.send(
                "❌ Invalid trade. Check that you own "
                "your card and the other player owns theirs.\n"
                "Use `!inventory` to find card instance IDs."
            )
            return

        gacha = self.bot.get_cog("Gacha")
        lookup = gacha.card_lookup if gacha else {}

        embed = discord.Embed(
            title="🤝 BaoBot Trade Request",
            description=(
                f"{ctx.author.mention} wants to trade "
                f"with {member.mention}!\n\n"
                "**Review both cards before accepting.**"
            ),
            color=discord.Color.blurple()
        )

        embed.add_field(
            name=f"📤 {ctx.author.display_name} offers",
            value=card_description(
                preview["sender_card"], lookup
            ),
            inline=False
        )

        embed.add_field(
            name=f"📥 {member.display_name} offers",
            value=card_description(
                preview["receiver_card"], lookup
            ),
            inline=False
        )

        embed.set_footer(
            text=(
                "Recipient: Accept / Decline • "
                "Sender: Cancel • Expires in 2 minutes"
            )
        )

        view = TradeView(
            ctx.author.id,
            member.id,
            my_card_id,
            their_card_id
        )

        view.message = await ctx.send(
            content=member.mention,
            embed=embed,
            view=view,
            allowed_mentions=discord.AllowedMentions(
                users=True,
                roles=False,
                everyone=False
            )
        )


async def setup(bot):
    await bot.add_cog(Trading(bot))
