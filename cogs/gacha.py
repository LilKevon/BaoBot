
import asyncio
import json
import random
from pathlib import Path
from database import get_pity, PITY_THRESHOLDS
from cogs.card_sale import CardSaleView


import discord
from discord.ext import commands
from database import (
    perform_roll,
    get_balance,
    buy_rolls,
    sell_card,
    get_collection,
    get_total_rolls
)

from database import get_inventory, get_card_instance

from cogs.inventory import (
    InventoryView,
    build_card_display
)



BASE_DIR = Path(__file__).resolve().parent.parent
CARDS_FILE = BASE_DIR / "data" / "cards.json"


RARITY_WEIGHTS = { 
    "common": 45000,       # Reduced from ~65% to 45%
    "uncommon": 25000,     # Increased to give a steady stream of green drops
    "rare": 15000,         # Boosted for more frequent "good" drops
    "epic": 8000,          # Doubled the chance for major milestones
    "legendary": 5000,     # Quintupled (5x) to make them attainable
    "mythical": 1500,      # Boosted 15x so players actually see them
    "divine": 450,         # Boosted 45x to turn "impossible" into "chasing a jackpot"
    "peebing_cool": 50     # Boosted 50x so the ultimate tier is a rare myth rather than a mathematical miracle
}

RARITY_COLORS = {
    "common": discord.Color.light_grey(),
    "uncommon": discord.Color.green(),
    "rare": discord.Color.blue(),
    "epic": discord.Color.purple(),
    "legendary": discord.Color.gold(),
    "mythical": discord.Color.red(),
    "divine": discord.Color.teal(),
    "peebing_cool": discord.Color.magenta()
}

SHINY_CHANCE = 0.01


class Gacha(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        with open(CARDS_FILE, "r", encoding="utf-8") as f:
            self.cards = json.load(f)

        if not self.cards:
            raise ValueError("No cards found in cards.json")

        self.card_lookup = {
            card["id"]: card for card in self.cards
        }

    

    def roll_card(self, minimum_rarity=None):
        card = random.choice(self.cards)

        rarity = random.choices(
            population=list(RARITY_WEIGHTS.keys()),
            weights=list(RARITY_WEIGHTS.values()),
            k=1
        )[0]

        # Upgrade the result only if pity requires it.
        if minimum_rarity is not None:
            rarity_order = list(RARITY_WEIGHTS)

            rolled_rank = rarity_order.index(rarity)
            minimum_rank = rarity_order.index(
                minimum_rarity
            )

            if rolled_rank < minimum_rank:
                rarity = minimum_rarity

        shiny = random.random() < SHINY_CHANCE

        return card, rarity, shiny



    @commands.command(name="roll")
    @commands.guild_only()
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def roll(self, ctx):
        def generate_roll(guarantee):
            card, rarity, shiny = self.roll_card(
                  minimum_rarity=guarantee
            )

            # Check artwork before committing the roll
            image_path = BASE_DIR / card["image"]

            if not image_path.is_file():
                raise FileNotFoundError(
                    f"Missing card image: {image_path}"
                )

            return card, rarity, shiny

        try:
            result = await asyncio.to_thread(
                perform_roll,
                ctx.author.id,
                generate_roll
            )
        except FileNotFoundError as exc:
            print(f"Gacha image error: {exc}")
            await ctx.send(
                "❌ This card's image is missing. "
                "Your roll was not consumed."
            )
            return

        if result is None:
            await ctx.send(
                "🥟 You're out of rolls!\n"
                "Use `!balance` to check regeneration, "
                "or `!buyroll` for extra rolls."
            )
            return

        card = result["card"]
        rarity = result["rarity"]
        shiny = result["shiny"]
        instance_id = result["instance_id"]

        image_path = BASE_DIR / card["image"]

        sale_view = CardSaleView(
            owner_id=ctx.author.id,
            instance_id=instance_id,
            card_name=card["name"],
            rarity=rarity,
            shiny=shiny
        )
        


        title = (
            f"✨ SHINY {card['name']} ✨"
            if shiny else card["name"]
        )

        embed = discord.Embed(
            title=title,
            description=card.get("description", ""),
            color=RARITY_COLORS[rarity]
        )

        embed.add_field(
    name="Rarity",
    value=rarity.replace("_", " ").title()
)

        embed.add_field(
            name="Variant",
            value="✨ Shiny" if shiny else "Normal"
        )

        embed.set_footer(
            text=f"Card Instance #{instance_id}"
        )

        image = discord.File(
            image_path,
            filename=image_path.name
        )

        embed.set_image(
            url=f"attachment://{image_path.name}"
        )
        if result["guarantee"] is not None:
            embed.add_field(
                name="🎯 Pity Guarantee",
                value=(
                    result["guarantee"]
                    .replace("_", " ")
                    .title() + "+"
                ),
                inline=False
            )

        sale_view.message = await ctx.send(
    file=image,
    embed=embed,
    view=sale_view
)

    
    # @commands.command(name="collection", aliases=["cards"])
    @commands.guild_only()
    async def collection(self, ctx):
        collection = await asyncio.to_thread(
            get_collection,
            ctx.author.id
        )

        total_rolls = await asyncio.to_thread(
            get_total_rolls,
            ctx.author.id
        )

        if not collection:
            await ctx.send(
                "🥟 Your collection is empty! Use `!roll` to get started."
            )
            return

        # Collection statistics
        total_cards = sum(
            entry["quantity"] for entry in collection
        )

        shiny_count = sum(
            entry["quantity"]
            for entry in collection
            if entry["is_shiny"]
        )

        unique_cards = len({
    (entry["card_id"], entry["rarity"])
    for entry in collection
})
        


        rarity_icons = {
    "common": "⚪",
    "uncommon": "🟢",
    "rare": "🔵",
    "epic": "🟣",
    "legendary": "🟡",
    "mythical": "🔴",
    "divine": "💎",
    "peebing_cool": "🥟"
}

        
        rarity_order = {
            "peebing_cool": 0,
            "divine": 1,
            "mythical": 2,
            "legendary": 3,
            "epic": 4,
            "rare": 5,
            "uncommon": 6,
            "common": 7
        }

    
        collection.sort(
            key=lambda entry: (
                not entry["is_shiny"],
                rarity_order.get(entry["rarity"], 99),
                entry["card_id"]
            )
        )


        embed = discord.Embed(
            title="🥟 Bao Collection",
            description=(
                f"**{ctx.author.display_name}'s peebin Bao collection**\n"
                "━━━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.gold()
        )

        embed.set_thumbnail(
            url=ctx.author.display_avatar.url
        )

        embed.add_field(
            name="📦 Total Cards",
            value=f"**{total_cards}**",
            inline=True
        )

        embed.add_field(
            name="🎲 Total Rolls",
            value=f"**{total_rolls}**",
            inline=True
        )

        embed.add_field(
            name="✨ Shinies",
            value=f"**{shiny_count}**",
            inline=True
        )
        max_unique_cards = len(self.cards) * len(RARITY_WEIGHTS)

        embed.add_field(
    name="📚 Unique Cards",
    value=f"**{unique_cards}/{max_unique_cards}**",
    inline=False
)

        lines = []

        for entry in collection:
            card = self.card_lookup.get(entry["card_id"], {})

            name = card.get("name", entry["card_id"])
            rarity = entry["rarity"]
            quantity = entry["quantity"]

            icon = rarity_icons.get(rarity, "⚪")

            if entry["is_shiny"]:
                lines.append(
                    f"✨ {icon} **{name}** `SHINY` — ×{quantity}"
                )
            else:
                lines.append(
                    f"{icon} **{name}** — ×{quantity}"
                )

        embed.add_field(
            name="🃏 Collected Cards",
            value="\n".join(lines)[:1024],
            inline=False
        )

        embed.set_footer(
            text="BaoBot Gacha • Use !roll to collect more!"
        )

        await ctx.send(embed=embed)




    @commands.command(name="balance", aliases=["bal"])
    @commands.guild_only()
    async def bal(self, ctx):
        account = await asyncio.to_thread(
            get_balance,
            ctx.author.id
        )

        embed = discord.Embed(
            title="🥟 BaoBot Wallet",
            description=(
                f"**{ctx.author.display_name}'s economy**"
            ),
            color=discord.Color.gold()
        )

        embed.set_thumbnail(
            url=ctx.author.display_avatar.url
        )

        embed.add_field(
            name="🪙 BaoCoins",
            value=f"**{account['coins']:,} BC**",
            inline=True
        )

        embed.add_field(
            name="🎟️ Free Rolls",
            value=f"**{account['free_rolls']}/5**",
            inline=True
        )

        embed.add_field(
            name="🎫 Purchased Rolls",
            value=f"**{account['paid_rolls']}**",
            inline=True
        )

        if account["free_rolls"] == 5:
            regen = "Free rolls are full!"
        else:
            seconds = account["next_roll"]
            regen = f"Next free roll in **{seconds}s**"

        embed.add_field(
            name="⏳ Regeneration",
            value=regen,
            inline=False
        )

        embed.add_field(
            name="🎲 Lifetime Rolls",
            value=f"{account['total_rolls']:,}",
            inline=False
        )

        embed.set_footer(
            text="1 free roll/min • Extra rolls cost 100 BC"
        )

        await ctx.send(embed=embed)

    @commands.command(name="buyroll")
    @commands.guild_only()
    async def buyroll(self, ctx, quantity: int = 1):
        result = await asyncio.to_thread(
            buy_rolls,
            ctx.author.id,
            quantity
        )

        if result["status"] == "invalid_quantity":
            await ctx.send(
                "You can buy between 1 and 100 rolls at once."
            )
            return

        if result["status"] == "insufficient":
            await ctx.send(
                f"❌ Not enough BaoCoins!\n"
                f"Cost: **{result['cost']:,} BC**\n"
                f"Balance: **{result['coins']:,} BC**"
            )
            return

        await ctx.send(
            f"✅ Purchased **{quantity} roll(s)** "
            f"for **{result['cost']:,} BC**!\n"
            f"Use `!balance` to check your rolls."
        )

    @commands.command(name="sell")
    @commands.guild_only()
    async def sell(
        self,
        ctx,
        instance_id: int,
        confirmation: str = ""
    ):
        confirmed = confirmation.lower() == "confirm"

        result = await asyncio.to_thread(
            sell_card,
            ctx.author.id,
            instance_id,
            confirmed
        )

        status = result["status"]

        if status == "not_found":
            await ctx.send(
                "❌ You don't own a card with that instance ID."
            )
            return

        if status == "unknown_rarity":
            await ctx.send(
                "❌ This card has an unrecognized rarity."
            )
            return

        if status == "confirmation_required":
            rarity = result["rarity"].replace(
                "_", " "
            ).title()

            await ctx.send(
                f"⚠️ **Valuable card warning!**\n"
                f"Card Instance: **#{instance_id}**\n"
                f"Rarity: **{rarity}**\n"
                f"Shiny: **{'Yes' if result['shiny'] else 'No'}**\n"
                f"Sell Value: **{result['value']:,} BC**\n\n"
                f"To confirm, type:\n"
                f"`!sell {instance_id} confirm`"
            )
            return

        card = self.card_lookup.get(
            result["card_id"], {}
        )
        name = card.get(
            "name", result["card_id"]
        )

        rarity = result["rarity"].replace(
            "_", " "
        ).title()

        await ctx.send(
            f"🪙 **Card sold!**\n"
            f"**{name}** ({rarity})\n"
            f"Earned **{result['value']:,} BaoCoins**!"
        )


        
    
    @commands.command(name="inventory", aliases=["inv"])
    @commands.guild_only()
    async def inventory(self, ctx):
        instances = await asyncio.to_thread(
            get_inventory,
            ctx.author.id
        )

        total_rolls = await asyncio.to_thread(
            get_total_rolls,
            ctx.author.id
        )

        if not instances:
            await ctx.send(
                "🥟 Your inventory is empty! "
                "Use `!roll` to collect cards."
            )
            return

        view = InventoryView(
            owner_id=ctx.author.id,
            instances=instances,
            card_lookup=self.card_lookup,
            base_dir=BASE_DIR,
            total_rolls=total_rolls
        )

        embed, image = view.current_display()

        if image:
            message = await ctx.send(
                embed=embed,
                file=image,
                view=view
            )
        else:
            message = await ctx.send(
                embed=embed,
                view=view
            )

        view.message = message



    @commands.command(name="inspect")
    @commands.guild_only()
    async def inspect(self, ctx, instance_id: int):
        instance = await asyncio.to_thread(
            get_card_instance,
            ctx.author.id,
            instance_id
        )

        if instance is None:
            await ctx.send(
                "❌ Card not found, or you don't own it."
            )
            return

        embed, image = build_card_display(
            instance,
            self.card_lookup,
            BASE_DIR
        )

        if image:
            await ctx.send(embed=embed, file=image)
        else:
            await ctx.send(embed=embed)



    @commands.command(name="pity")
    @commands.guild_only()
    async def pity(self, ctx):
        counters = await asyncio.to_thread(
            get_pity,
            ctx.author.id
        )

        embed = discord.Embed(
            title="🥟 BaoBot Pity Progress",
            description=(
                f"**{ctx.author.display_name}'s "
                "rarity guarantees**"
            ),
            color=discord.Color.purple()
        )

        icons = {
            "rare": "🔵",
            "epic": "🟣",
            "legendary": "🟡",
            "mythical": "🔴"
        }

        for tier, threshold in PITY_THRESHOLDS.items():
            progress = counters[tier]
            remaining = max(0, threshold - progress)

            filled = min(
                10,
                int(progress / threshold * 10)
            )

            bar = (
                "🟩" * filled
                + "⬛" * (10 - filled)
            )

            embed.add_field(
                name=(
                    f"{icons[tier]} "
                    f"{tier.title()}+"
                ),
                value=(
                    f"{bar}\n"
                    f"**{progress:,}/{threshold:,}** "
                    f"unsuccessful pulls\n"
                    f"Guaranteed within "
                    f"**{remaining:,}** rolls"
                ),
                inline=False
            )

        embed.set_footer(
            text=(
                "Higher rarities reset lower pity tiers. "
                "Divine and Peebing Cool have no pity."
            )
        )

        await ctx.send(embed=embed)




async def setup(bot):
    await bot.add_cog(Gacha(bot))
