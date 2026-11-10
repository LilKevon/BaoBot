
import asyncio
import json
import random
from pathlib import Path
from database import get_pity, PITY_THRESHOLDS
from cogs.card_sale import CardSaleView
from utils.shiny import get_card_file



import discord
from discord.ext import commands
from database import (
    perform_roll,
    get_balance,
    buy_rolls,
    sell_card,
    get_collection,
    get_total_rolls,
    preview_multi_sale,
    execute_multi_sale,
    get_inventory,
    get_card_instance,
    perform_multi_roll

)



from cogs.inventory import (
    InventoryView,
    build_card_display
)



BASE_DIR = Path(__file__).resolve().parent.parent
CARDS_FILE = BASE_DIR / "data" / "cards.json"


RARITY_WEIGHTS = {
    "common": 58922,
    "uncommon": 21500,
    "rare": 11500,
    "epic": 5200,
    "legendary": 2200,
    "mythical": 520,
    "divine": 142,
    "peebing_cool": 16
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

    
    @commands.command(
        name="multiroll",
        aliases=["multi", "rollmulti", "mult"]
    )
    @commands.guild_only()
    @commands.cooldown(
        1, 2, commands.BucketType.user
    )
    async def multiroll(self, ctx, quantity: int = 10):

        if not 2 <= quantity <= 10:
            await ctx.send(
                "❌ Multi-roll quantity must be "
                "between 2 and 10.\n"
                "Example: `!multiroll 10`"
            )
            return

        def generate_roll(guarantee):
            card, rarity, shiny = self.roll_card(
                minimum_rarity=guarantee
            )

            image_path = BASE_DIR / card["image"]

            if not image_path.is_file():
                raise FileNotFoundError(
                    f"Missing artwork: {image_path}"
                )

            return card, rarity, shiny

        try:
            result = await asyncio.to_thread(
                perform_multi_roll,
                ctx.author.id,
                quantity,
                generate_roll
            )

        except FileNotFoundError as exc:
            print(f"❌ Gacha image error: {exc}", flush=True)
            await ctx.send(
                f"❌ Missing image: `{exc}`\n"
                "Your roll was not consumed."
            )
            return

        if result["status"] == "insufficient":
            await ctx.send(
                "❌ **Not enough rolls!**\n"
                f"You requested **{quantity}**, "
                f"but have **{result['available']}**.\n"
                "Use `!balance` to check your rolls "
                "or `!buyroll` to purchase more."
            )
            return

        if result["status"] != "success":
            await ctx.send(
                "❌ Unable to complete multi-roll."
            )
            return

        icons = {
            "common": "⚪",
            "uncommon": "🟢",
            "rare": "🔵",
            "epic": "🟣",
            "legendary": "🟡",
            "mythical": "🔴",
            "divine": "💎",
            "peebing_cool": "🥟"
        }

        lines = []

        for index, pull in enumerate(
            result["results"], start=1
        ):
            card = pull["card"]
            rarity = pull["rarity"]
            shiny = pull["shiny"]

            icon = icons.get(rarity, "❔")
            name = discord.utils.escape_markdown(
                card["name"]
            )
            rarity_name = rarity.replace(
                "_", " "
            ).title()

            shiny_label = " ✨" if shiny else ""
            pity_label = (
                " 🎯" if pull["guarantee"]
                else ""
            )

            lines.append(
                f"**{index}.** {icon} **{name}**"
                f"{shiny_label}\n"
                f"   {rarity_name}{pity_label} "
                f"• `#{pull['instance_id']}`"
            )

        embed = discord.Embed(
            title=f"🎰 BaoBot {quantity}× Multi-Roll",
            description="\n".join(lines),
            color=discord.Color.gold()
        )

        embed.add_field(
            name="🎟️ Free Rolls Used",
            value=str(result["free_spent"]),
            inline=True
        )

        embed.add_field(
            name="🎫 Purchased Rolls Used",
            value=str(result["paid_spent"]),
            inline=True
        )

        shiny_count = sum(
            pull["shiny"]
            for pull in result["results"]
        )

        embed.add_field(
            name="✨ Shinies",
            value=str(shiny_count),
            inline=True
        )

        embed.set_footer(
            text=(
                "🎯 = Pity guarantee • "
                "Use !inventory to view your cards"
            )
        )

        await ctx.send(embed=embed)

    
    @commands.command(name="multisell", aliases=["multsell", "msell"])
    @commands.guild_only()
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def multisell(self, ctx, *arguments: str):
        if not arguments:
            await ctx.send(
                "❌ Usage: `!multisell 101 102 103`\n"
                "Separate card instance IDs with spaces."
            )
            return

        confirmed = arguments[-1].lower() == "confirm"

        tokens = (
            arguments[:-1]
            if confirmed
            else arguments
        )

        try:
            instance_ids = [int(x) for x in tokens]
        except ValueError:
            await ctx.send(
                "❌ Use numeric card IDs separated by spaces.\n"
                "Example: `!multisell 101 102 103`"
            )
            return

        if not 2 <= len(instance_ids) <= 25:
            await ctx.send(
                "❌ Select between 2 and 25 cards."
            )
            return

        preview = await asyncio.to_thread(
            preview_multi_sale,
            ctx.author.id,
            instance_ids
        )

        if preview["status"] != "valid":
            errors = {
                "duplicate_ids":
                    "You entered the same card ID twice.",
                "missing_cards":
                    "One or more cards don't belong to you.",
                "unknown_rarity":
                    "One card has an unknown rarity.",
                "invalid_quantity":
                    "Select between 2 and 25 cards."
            }

            await ctx.send(
                "❌ " + errors.get(
                    preview["status"],
                    "Unable to prepare sale."
                )
            )
            return

        lines = []

        for card in preview["cards"]:
            info = self.card_lookup.get(
                card["card_id"], {}
            )

            name = discord.utils.escape_markdown(
                info.get("name", card["card_id"])
            )

            rarity = card["rarity"].replace(
                "_", " "
            ).title()

            shiny = "✨ " if card["is_shiny"] else ""

            lines.append(
                f"**#{card['instance_id']}** "
                f"{shiny}{name} ({rarity}) "
                f"— {card['value']:,} BC"
            )

        embed = discord.Embed(
            title="🪙 BaoBot Multi-Sell",
            description="\n".join(lines),
            color=discord.Color.gold()
        )

        embed.add_field(
            name="Cards Selected",
            value=str(len(instance_ids)),
            inline=True
        )

        embed.add_field(
            name="Total Payout",
            value=f"**{preview['total']:,} BC**",
            inline=True
        )

        
        if preview["protected"] and not confirmed:
            ids = " ".join(map(str, instance_ids))

            embed.add_field(
                name="⚠️ Confirmation Required",
                value=(
                    "This batch contains a shiny or "
                    "Legendary+ card.\n\n"
                    "Confirm with:\n"
                    f"`!multisell {ids} confirm`"
                ),
                inline=False
            )

            await ctx.send(embed=embed)
            return

        result = await asyncio.to_thread(
            execute_multi_sale,
            ctx.author.id,
            instance_ids,
            confirmed
        )

        if result["status"] != "success":
            await ctx.send(
                "❌ Sale failed. One or more cards "
                "may no longer be available.\n"
                "No partial sale was completed."
            )
            return

        embed.title = "✅ Multi-Sell Complete!"
        embed.color = discord.Color.green()
        embed.description = (
            f"Sold **{result['cards_sold']} cards** "
            f"for **{result['total']:,} BaoCoins!**"
        )

        embed.clear_fields()

        embed.set_footer(
            text="Use !balance to check your BaoCoins."
        )

        await ctx.send(embed=embed)



    @commands.command(name="roll")
    @commands.guild_only()
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def roll(self, ctx):
        def generate_roll(guarantee):
            card, rarity, shiny = self.roll_card(
                  minimum_rarity=guarantee
            )

           
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

        
        image_path = BASE_DIR / card["image"]
        file = get_card_file(image_path, shiny)

        embed.set_image(
            url=f"attachment://{file.filename}"
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
    file=file,
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
            value=f"**{account['free_rolls']}/10**",
            inline=True
        )

        embed.add_field(
            name="🎫 Purchased Rolls",
            value=f"**{account['paid_rolls']}**",
            inline=True
        )

        if account["free_rolls"] == 10:
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
    async def inventory(
        self,
        ctx,
        member: discord.User = None
    ):
    
        target = member or ctx.author

        instances = await asyncio.to_thread(
            get_inventory,
            target.id
        )

        total_rolls = await asyncio.to_thread(
            get_total_rolls,
            target.id
        )

        if not instances:
            await ctx.send(
                f"🥟 **{discord.utils.escape_markdown(target.display_name)}** "
                "has no cards in their inventory!"
            )
            return

  
        view = InventoryView(
            owner_id=ctx.author.id,
            instances=instances,
            card_lookup=self.card_lookup,
            base_dir=BASE_DIR,
            total_rolls=total_rolls,
            inventory_owner_name=target.display_name,
    read_only=target.id != ctx.author.id

        )

        embed, image = view.current_display()

        
        embed.title = (
            f"🥟 {target.display_name}'s Inventory"
            if view.showing_overview
            else embed.title
        )

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
