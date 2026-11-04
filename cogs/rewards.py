
import asyncio
import discord

from discord.ext import commands

from database import (
    claim_reward,
    get_reward_cooldowns
)


def format_duration(seconds):
    days, remainder = divmod(int(seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []

    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds and not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts) or "Ready!"


class Rewards(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def handle_claim(self, ctx, reward_type):
        result = await asyncio.to_thread(
            claim_reward,
            ctx.author.id,
            reward_type
        )

        if result["status"] == "cooldown":
            await ctx.send(
                f"⏳ You've already claimed your "
                f"**{reward_type}** reward!\n"
                f"Come back in "
                f"**{format_duration(result['remaining'])}**."
            )
            return

        icon = (
            "🎁" if reward_type == "daily"
            else "💰"
        )

        embed = discord.Embed(
            title=(
                f"{icon} {reward_type.title()} "
                "Reward Claimed!"
            ),
            description=(
                f"**+{result['reward']:,} BaoCoins!**"
            ),
            color=discord.Color.gold()
        )

        embed.add_field(
            name="🪙 New Balance",
            value=f"{result['coins']:,} BC",
            inline=True
        )

        embed.add_field(
            name="🎫 Roll Purchasing Power",
            value=f"{result['coins'] // 100:,} rolls",
            inline=True
        )

        embed.add_field(
            name="⏳ Next Claim",
            value=f"<t:{result['next_claim']}:R>",
            inline=False
        )

        embed.set_footer(
            text="Use !buyroll to purchase extra rolls!"
        )

        await ctx.send(embed=embed)

    @commands.command(name="daily")
    @commands.guild_only()
    async def daily(self, ctx):
        await self.handle_claim(ctx, "daily")

    @commands.command(name="weekly")
    @commands.guild_only()
    async def weekly(self, ctx):
        await self.handle_claim(ctx, "weekly")

    @commands.command(name="rewards")
    @commands.guild_only()
    async def rewards(self, ctx):
        cooldowns = await asyncio.to_thread(
            get_reward_cooldowns,
            ctx.author.id
        )

        embed = discord.Embed(
            title="🥟 BaoBot Rewards",
            description="Your available claim rewards",
            color=discord.Color.blurple()
        )

        for name, amount, icon in [
            ("daily", 200, "🎁"),
            ("weekly", 1000, "💰")
        ]:
            remaining = cooldowns[name]

            status = (
                "✅ Ready to claim!"
                if remaining == 0
                else f"⏳ {format_duration(remaining)}"
            )

            embed.add_field(
                name=f"{icon} {name.title()} — {amount} BC",
                value=(
                    f"{status}\n"
                    f"Use `!{name}`"
                ),
                inline=False
            )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Rewards(bot))
