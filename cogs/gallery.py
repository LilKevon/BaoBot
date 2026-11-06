import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import discord
from discord.ext import commands

from database import DB_PATH

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent.parent
CATALOGUE_PATH = BASE_DIR / "data" / "cards.json"
MAX_FAVOURITES = 5
LOCK_ERROR = "GALLERY_LOCKED"


@contextmanager
def db_connection():
    connection = sqlite3.connect(str(DB_PATH), timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_gallery():
    with db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS favourite_cards (
                gallery_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                instance_id INTEGER NOT NULL,
                added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (user_id, instance_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_favourite_cards_user
            ON favourite_cards(user_id, gallery_id)
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS gallery_prevent_card_delete
            BEFORE DELETE ON player_cards
            FOR EACH ROW
            WHEN EXISTS (
                SELECT 1 FROM favourite_cards AS fav
                WHERE fav.instance_id = OLD.instance_id
                  AND fav.user_id = OLD.user_id
            )
            BEGIN
                SELECT RAISE(ABORT, 'GALLERY_LOCKED');
            END
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS gallery_prevent_card_transfer
            BEFORE UPDATE OF user_id, instance_id ON player_cards
            FOR EACH ROW
            WHEN (NEW.user_id != OLD.user_id OR NEW.instance_id != OLD.instance_id)
             AND EXISTS (
                SELECT 1 FROM favourite_cards AS fav
                WHERE fav.instance_id = OLD.instance_id
                  AND fav.user_id = OLD.user_id
            )
            BEGIN
                SELECT RAISE(ABORT, 'GALLERY_LOCKED');
            END
        """)


def get_favourites(user_id):
    with db_connection() as conn:
        rows = conn.execute("""
            SELECT fav.gallery_id, fav.instance_id,
                   card.card_id, card.rarity, card.is_shiny
            FROM favourite_cards AS fav
            JOIN player_cards AS card
              ON card.instance_id = fav.instance_id
             AND card.user_id = fav.user_id
            WHERE fav.user_id = ?
            ORDER BY fav.gallery_id ASC
            LIMIT ?
        """, (user_id, MAX_FAVOURITES)).fetchall()
    return [dict(row) for row in rows]


def add_favourite(user_id, instance_id):
    with db_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")

        conn.execute("""
            DELETE FROM favourite_cards
            WHERE user_id = ? AND NOT EXISTS (
                SELECT 1 FROM player_cards AS c
                WHERE c.user_id = favourite_cards.user_id
                  AND c.instance_id = favourite_cards.instance_id
            )
        """, (user_id,))

        owned = conn.execute("""
            SELECT 1 FROM player_cards
            WHERE user_id = ? AND instance_id = ?
        """, (user_id, instance_id)).fetchone()
        if not owned:
            return False, "You don't own that card instance."

        exists = conn.execute("""
            SELECT 1 FROM favourite_cards
            WHERE user_id = ? AND instance_id = ?
        """, (user_id, instance_id)).fetchone()
        if exists:
            return False, "That card is already in your gallery."

        count = conn.execute("""
            SELECT COUNT(*) FROM favourite_cards WHERE user_id = ?
        """, (user_id,)).fetchone()[0]
        if count >= MAX_FAVOURITES:
            return False, "Your gallery is full (5/5). Remove a card first."

        conn.execute("""
            INSERT INTO favourite_cards (user_id, instance_id)
            VALUES (?, ?)
        """, (user_id, instance_id))
        return True, "Added to your gallery and locked from selling/trading."


def remove_favourite(user_id, instance_id):
    with db_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        result = conn.execute("""
            DELETE FROM favourite_cards
            WHERE user_id = ? AND instance_id = ?
        """, (user_id, instance_id))
        return result.rowcount > 0


def load_catalogue():
    with CATALOGUE_PATH.open(encoding="utf-8") as f:
        records = json.load(f)
    return {record["id"]: record for record in records}


def build_embed(member, cards, index, catalogue):
    selected = cards[index]
    card = catalogue.get(selected["card_id"], {})
    name = card.get("name", selected["card_id"])
    rarity = selected["rarity"].replace("_", " ").title()
    shiny = bool(selected["is_shiny"])

    embed = discord.Embed(
        title=f"🖼️ {member.display_name}'s Bao Gallery",
        description=(
            f"**{name}** {'✨ Shiny' if shiny else ''}\n"
            f"**Rarity:** {rarity}\n"
            f"**Instance:** `#{selected['instance_id']}` 🔒\n\n"
            f"*{card.get('description', 'A treasured Bao card.')}*"
        ),
        color=discord.Color.gold() if shiny else discord.Color.blurple(),
    )
    embed.set_footer(text=f"Favourite {index + 1}/{len(cards)} • 5 slots maximum")

    image = card.get("image")
    if not image:
        return embed, None

    allowed_dir = (BASE_DIR / "files" / "cards").resolve()
    path = (BASE_DIR / image).resolve()
    if not path.is_relative_to(allowed_dir) or not path.is_file():
        logger.warning("Invalid or missing gallery image for card %s: %s", selected["card_id"], image)
        return embed, None

    attachment = discord.File(path, filename=path.name)
    embed.set_image(url=f"attachment://{path.name}")
    return embed, attachment


class GalleryView(discord.ui.View):
    def __init__(self, viewer_id, member, catalogue):
        super().__init__(timeout=180)
        self.viewer_id = viewer_id
        self.member = member
        self.catalogue = catalogue
        self.index = 0
        self.message = None
        self.sync_buttons()

    def sync_buttons(self):
        count = len(get_favourites(self.member.id))
        self.previous_button.disabled = (count < 2 or self.index <= 0)
        self.next_button.disabled = (count < 2 or self.index >= count - 1)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.viewer_id:
            await interaction.response.send_message(
                "🥟 Use `!gallery` to open your own viewer.", ephemeral=True
            )
            return False
        return True

    async def display_current(self, interaction: discord.Interaction):
        cards = get_favourites(self.member.id)
        if not cards:
            embed = discord.Embed(
                title=f"🖼️ {self.member.display_name}'s Bao Gallery",
                description="No favourite cards to display.",
                color=discord.Color.blurple(),
            )
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(
                embed=embed, attachments=[], view=self
            )
            return

        self.index = max(0, min(self.index, len(cards) - 1))
        self.sync_buttons()
        embed, attachment = build_embed(self.member, cards, self.index, self.catalogue)
        try:
            await interaction.response.edit_message(
                embed=embed,
                attachments=[attachment] if attachment else [],
                view=self,
            )
        finally:
            if attachment:
                attachment.close()

    @discord.ui.button(label="Previous", emoji="◀️", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index -= 1
        await self.display_current(interaction)

    @discord.ui.button(label="Next", emoji="▶️", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index += 1
        await self.display_current(interaction)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class BaoGallery(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        initialize_gallery()

    @commands.command(name="favadd", aliases=["favoriteadd", "favouriteadd"])
    @commands.guild_only()
    async def favadd(self, ctx, instance_id: int):
        if instance_id <= 0:
            await ctx.send("❌ Card instance IDs must be positive integers.")
            return
        success, message = add_favourite(ctx.author.id, instance_id)
        if not success:
            await ctx.send(f"❌ {message}")
            return
        count = len(get_favourites(ctx.author.id))
        await ctx.send(f"🔒 Card `#{instance_id}` {message}\n**Gallery:** {count}/5")

    @commands.command(name="favremove", aliases=["favoriteremove", "favouriteremove"])
    @commands.guild_only()
    async def favremove(self, ctx, instance_id: int):
        if instance_id <= 0:
            await ctx.send("❌ Card instance IDs must be positive integers.")
            return
        if not remove_favourite(ctx.author.id, instance_id):
            await ctx.send("❌ That card isn't in your gallery.")
            return
        await ctx.send(f"🔓 Card `#{instance_id}` removed from your gallery and unlocked.")

    @commands.command(name="gallery", aliases=["favourites", "favorites"])
    @commands.guild_only()
    async def gallery(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        cards = get_favourites(member.id)
        if not cards:
            await ctx.send(
                f"🖼️ **{member.display_name}'s Gallery** is empty.\n"
                "Use `!favadd <instance_id>` to showcase a card."
            )
            return

        catalogue = load_catalogue()
        view = GalleryView(ctx.author.id, member, catalogue)
        embed, attachment = build_embed(member, cards, 0, catalogue)
        kwargs = {"embed": embed, "view": view}
        if attachment:
            kwargs["file"] = attachment
        try:
            view.message = await ctx.send(**kwargs)
        finally:
            if attachment:
                attachment.close()


async def setup(bot):
    await bot.add_cog(BaoGallery(bot))
