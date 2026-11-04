
import discord
from discord.ext import commands


COMMAND_CATEGORIES = {
    "home": {
        "title": "🥟 BaoBot Command Center",
        "description": (
            "Welcome to BaoBot!\n\n"
            "Choose a category below to explore commands."
        ),
        "commands": {
            "🎰 Gacha": "Roll cards and track pity.",
            "🪙 Economy": "Manage BaoCoins and roll purchases.",
            "🃏 Inventory": "Browse your personal collection.",
            "🤝 Trading": "Exchange cards with other players.",
            "🎭 Fun": "Classic BaoBot commands."
        }
    },
    "gacha": {
        "title": "🎰 Gacha Commands",
        "description": "Roll for the ultimate Bao.",
        "commands": {
            "!roll": "Pull a random Bao card.",
            "!pity": "Check your rarity guarantees."
        }
    },
    "economy": {
        "title": "🪙 Economy Commands",
        "description": "Earn and spend your BaoCoins.",
        "commands": {
            "!balance / !bal": "Check coins and available rolls.",
            "!buyroll <amount>": "Purchase extra rolls for 100 BC each.",
            "!sell <instance_id>": "Sell an owned card.",
            "!sell <id> confirm": "Confirm selling a valuable card."
        }
    },
    "inventory": {
        "title": "🃏 Inventory Commands",
        "description": "Browse and manage your collection.",
        "commands": {
            "!inventory / !inv": "Browse cards using buttons and dropdowns.",
            "!inspect <id>": "Inspect an individual card.",
            "!collection / !cards": "Shortcut to inventory."
        }
    },
    "trading": {
        "title": "🤝 Trading Commands",
        "description": "Trade Bao cards with other players.",
        "commands": {
            "!trade @player <your_id> <their_id>":
                "Offer one card in exchange for another.",
            "!inventory": "Find card instance IDs.",
            "!inspect <id>": "Inspect an owned card."
        }
    },
    "fun": {
        "title": "🎭 Fun Commands",
        "description": "The original BaoBot experience.",
        "commands": {
            "!diff @user1 @user2": "Who diffs whom?",
            "!triangle": "Generate an emoji triangle.",
            "!circle": "Generate an emoji circle.",
            "!stack": "Stack emojis.",
            "!pyramid": "Generate an emoji pyramid.",
            "!buttboy": "Classic BaoBot response.",
            "!performance": "Send the performance picture.",
            "!join": "Join your voice channel.",
            "!leave": "Leave the voice channel.",
            "!sound": "Play a Bao soundbite."
        }
    }
}


class HelpView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.message = None

    def build_embed(self, category="home"):
        info = COMMAND_CATEGORIES[category]

        embed = discord.Embed(
            title=info["title"],
            description=info["description"],
            color=discord.Color.blurple()
        )

        for name, description in info["commands"].items():
            embed.add_field(
                name=name,
                value=description,
                inline=False
            )

        embed.set_footer(
            text="BaoBot • Prefix: ! • Menu expires after 3 minutes"
        )

        return embed

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "🥟 Use `!help` to open your own command menu.",
                ephemeral=True
            )
            return False

        return True

    async def change_category(self, interaction, category):
        await interaction.response.edit_message(
            embed=self.build_embed(category),
            view=self
        )

    @discord.ui.button(
        label="Home",
        emoji="🏠",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def home_button(self, interaction, button):
        await self.change_category(interaction, "home")

    @discord.ui.button(
        label="Gacha",
        emoji="🎰",
        style=discord.ButtonStyle.primary,
        row=0
    )
    async def gacha_button(self, interaction, button):
        await self.change_category(interaction, "gacha")

    @discord.ui.button(
        label="Economy",
        emoji="🪙",
        style=discord.ButtonStyle.primary,
        row=0
    )
    async def economy_button(self, interaction, button):
        await self.change_category(interaction, "economy")

    @discord.ui.button(
        label="Inventory",
        emoji="🃏",
        style=discord.ButtonStyle.primary,
        row=0
    )
    async def inventory_button(self, interaction, button):
        await self.change_category(interaction, "inventory")

    @discord.ui.button(
        label="Trading",
        emoji="🤝",
        style=discord.ButtonStyle.primary,
        row=1
    )
    async def trading_button(self, interaction, button):
        await self.change_category(interaction, "trading")

    @discord.ui.button(
        label="Fun",
        emoji="🎭",
        style=discord.ButtonStyle.primary,
        row=1
    )
    async def fun_button(self, interaction, button):
        await self.change_category(interaction, "fun")

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class HelpMenu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    @commands.guild_only()
    async def show_help(self, ctx):
        view = HelpView(ctx.author.id)

        message = await ctx.send(
            embed=view.build_embed(),
            view=view
        )

        view.message = message


async def setup(bot):
    await bot.add_cog(HelpMenu(bot))
