
from pathlib import Path
from utils.shiny import get_card_file
import discord
from collections import Counter 

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

SELL_VALUES = {
    "common": 10,
    "uncommon": 20,
    "rare": 40,
    "epic": 100,
    "legendary": 500,
    "mythical": 2000,
    "divine": 10000,
    "peebing_cool": 100000
}


def build_card_display(instance, card_lookup, base_dir):
    """Build an embed and optional image attachment."""
    card = card_lookup.get(instance["card_id"], {})

    name = card.get("name", instance["card_id"])
    rarity = instance["rarity"]
    shiny = bool(instance["is_shiny"])

    icon = RARITY_ICONS.get(rarity, "❔")
    rarity_name = rarity.replace("_", " ").title()

    value = SELL_VALUES.get(rarity, 0)
    if shiny:
        value *= 5

    title = (
        f"✨ {icon} Shiny {name}"
        if shiny else f"{icon} {name}"
    )

    embed = discord.Embed(
        title=title,
        description=card.get("description", ""),
        color=RARITY_COLORS.get(
            rarity, discord.Color.default()
        )
    )

    embed.add_field(
        name="💎 Rarity",
        value=rarity_name,
        inline=True
    )

    embed.add_field(
        name="✨ Variant",
        value="Shiny" if shiny else "Normal",
        inline=True
    )

    embed.add_field(
        name="🪙 Sell Value",
        value=f"{value:,} BC",
        inline=True
    )

    embed.add_field(
        name="🆔 Instance ID",
        value=f"`#{instance['instance_id']}`",
        inline=True
    )

    embed.add_field(
        name="📅 Obtained",
        value=instance["obtained_at"],
        inline=True
    )

    embed.set_footer(
        text=(
            f"Use !sell {instance['instance_id']} "
            "to sell this card"
        )
    )

    
    image_file = None
    image_name = card.get("image")

    if image_name:
        image_path = base_dir / image_name

        if image_path.is_file():
            image_file = get_card_file(
                image_path,
                bool(instance["is_shiny"])
            )

            embed.set_image(
                url=f"attachment://{image_file.filename}"
            )

    return embed, image_file



class CardSelect(discord.ui.Select):
    def __init__(self, inventory_view):
        self.inventory_view = inventory_view

        super().__init__(
            placeholder="Jump to a card...",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label="Loading cards...",
                    value="0"
                )
            ],
            row=0
        )

    def refresh_options(self):
        view = self.inventory_view

        
        group_start = view.page * 25
        group_end = min(
            group_start + 25,
            len(view.instances)
        )

        options = []

        for index in range(group_start, group_end):
            instance = view.instances[index]

            card = view.card_lookup.get(
                instance["card_id"], {}
            )

            name = card.get(
                "name",
                instance["card_id"]
            )

            rarity = instance["rarity"]
            shiny = bool(instance["is_shiny"])

            icon = RARITY_ICONS.get(rarity, "❔")

            label = (
                f"{name} "
                f"(#{instance['instance_id']})"
            )

            description = (
                f"{rarity.replace('_', ' ').title()}"
                f" • {'Shiny' if shiny else 'Normal'}"
            )

            options.append(
                discord.SelectOption(
                    label=label[:100],
                    description=description[:100],
                    value=str(index),
                    emoji="✨" if shiny else icon,
                    default=index == view.index
                )
            )

        self.options = options

        group_number = group_start // 25 + 1
        total_groups = (
            len(view.instances) + 24
        ) // 25

        self.placeholder = (
            f"Select card • Group "
            f"{group_number}/{total_groups}"
        )

    async def callback(self, interaction):
        selected_index = int(self.values[0])

        await self.inventory_view.show_card(
            interaction,
            selected_index
        )



class InventoryView(discord.ui.View):
    def __init__(
        self,
        owner_id,
        instances,
        card_lookup,
        base_dir,
        total_rolls=0,
        inventory_owner_name=None,
    read_only=False
        
    ):
        super().__init__(timeout=180)

        self.owner_id = owner_id
        self.instances = instances
        self.card_lookup = card_lookup
        self.base_dir = base_dir
        self.total_rolls = total_rolls
        self.inventory_owner_name = inventory_owner_name
        self.read_only = read_only

        self.index = 0
        self.page = 0
        self.showing_overview = True
        self.message = None

        self.card_select = CardSelect(self)
        self.add_item(self.card_select)

        self.update_controls()

    def update_controls(self):
        self.previous_button.disabled = (
            self.showing_overview or self.index == 0
        )

        self.next_button.disabled = (
            self.showing_overview
            or self.index == len(self.instances) - 1
        )

        self.overview_button.label = (
            "View Card"
            if self.showing_overview
            else "Overview"
        )
        total_pages = (len(self.instances) + 24) // 25

        self.previous_page_button.disabled = self.page == 0
        self.next_page_button.disabled = self.page >= total_pages - 1

        self.card_select.refresh_options()

    def overview_display(self):
        total_cards = len(self.instances)

        shiny_count = sum(
            bool(card["is_shiny"])
            for card in self.instances
        )

        unique_variants = len({
            (card["card_id"], card["rarity"])
            for card in self.instances
        })

        rarity_counts = Counter(
            card["rarity"]
            for card in self.instances
        )

        rarity_order = [
            "peebing_cool",
            "divine",
            "mythical",
            "legendary",
            "epic",
            "rare",
            "uncommon",
            "common"
        ]

        rarest = next(
            (
                rarity
                for rarity in rarity_order
                if rarity_counts[rarity] > 0
            ),
            "common"
        )

        embed = discord.Embed(
    title=(
        f"🥟 {self.inventory_owner_name}'s Inventory"
        if self.inventory_owner_name
        else "🥟 Bao Inventory Overview"
    ),
            description="Your personal Bao collection",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="📦 Total Cards",
            value=f"**{total_cards:,}**",
            inline=True
        )

        embed.add_field(
            name="📚 Unique Variants",
            value=f"**{unique_variants:,}**",
            inline=True
        )

        embed.add_field(
            name="✨ Shinies",
            value=f"**{shiny_count:,}**",
            inline=True
        )

        embed.add_field(
            name="🎲 Lifetime Rolls",
            value=f"**{self.total_rolls:,}**",
            inline=True
        )

        embed.add_field(
            name="🏆 Highest Rarity",
            value=(
                f"{RARITY_ICONS.get(rarest, '❔')} "
                f"{rarest.replace('_', ' ').title()}"
            ),
            inline=True
        )

        rarity_lines = []

        for rarity in rarity_order:
            count = rarity_counts[rarity]

            if count > 0:
                icon = RARITY_ICONS.get(rarity, "❔")
                name = rarity.replace("_", " ").title()

                rarity_lines.append(
                    f"{icon} **{name}:** {count:,}"
                )

        embed.add_field(
            name="📊 Rarity Breakdown",
            value="\n".join(rarity_lines),
            inline=False
        )

        embed.set_footer(
            text="Select a card from the dropdown to inspect it."
        )

        return embed

    def current_display(self):
        if self.showing_overview:
            return self.overview_display(), None

        instance = self.instances[self.index]

        embed, image = build_card_display(
            instance,
            self.card_lookup,
            self.base_dir
        )

        footer = (
    f"Card {self.index + 1}/{len(self.instances)} • "
    f"Instance #{instance['instance_id']}"
)

        if not self.read_only:
            footer += f" • !sell {instance['instance_id']}"

        embed.set_footer(text=footer)

        return embed, image

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "🥟 This isn't your inventory! "
                "Use `!inventory` to open your own.",
                ephemeral=True
            )
            return False

        return True

    async def show_card(self, interaction, index):
        self.index = max(
            0,
            min(index, len(self.instances) - 1)
        )
        self.page = self.index // 25

        self.showing_overview = False
        await self.refresh_message(interaction)

    
    async def refresh_message(self, interaction):
        self.update_controls()

        embed, image = self.current_display()

        try:
            await interaction.response.edit_message(
                embed=embed,
                attachments=[image] if image else [],
                view=self
            )
        finally:
            if image:
                image.close()


    @discord.ui.button(
        label="Previous",
        emoji="◀️",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def previous_button(self, interaction, button):
        await self.show_card(
            interaction,
            self.index - 1
        )

    @discord.ui.button(
        label="Overview",
        emoji="📊",
        style=discord.ButtonStyle.primary,
        row=1
    )
    async def overview_button(self, interaction, button):
        self.showing_overview = (
            not self.showing_overview
        )

        await self.refresh_message(interaction)

    @discord.ui.button(
        label="Next",
        emoji="▶️",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def next_button(self, interaction, button):
        await self.show_card(
            interaction,
            self.index + 1
        )

    @discord.ui.button(
    label="Previous 25",
    emoji="⏪",
    style=discord.ButtonStyle.secondary,
    row=2
)
    async def previous_page_button(self, interaction, button):
        self.page = max(0, self.page - 1)
        await self.refresh_message(interaction)


    @discord.ui.button(
        label="Next 25",
        emoji="⏩",
        style=discord.ButtonStyle.secondary,
        row=2
    )
    async def next_page_button(self, interaction, button):
        total_pages = (len(self.instances) + 24) // 25

        self.page = min(
            total_pages - 1,
            self.page + 1
        )

        await self.refresh_message(interaction)
        

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass
