
import sqlite3

import discord
from discord.ext import commands

from database import DB_PATH


MAX_TERM_LENGTH = 60
MAX_DEFINITION_LENGTH = 1000


def get_connection():
    """Open the database selected by the active bot environment."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_dictionary():
    """Create the dictionary table if it doesn't exist."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS server_dictionary (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                term TEXT NOT NULL COLLATE NOCASE,
                definition TEXT NOT NULL,
                author_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT,
                UNIQUE(guild_id, term)
            )
        """)


def parse_entry(text):
    """Split 'term | definition' into two validated values."""
    if "|" not in text:
        raise ValueError(
            "Use the format: `term | definition`"
        )

    term, definition = text.split("|", 1)
    term = term.strip()
    definition = definition.strip()

    if not term or not definition:
        raise ValueError(
            "Both the term and definition are required."
        )

    if len(term) > MAX_TERM_LENGTH:
        raise ValueError("That term is too long.")

    if len(definition) > MAX_DEFINITION_LENGTH:
        raise ValueError("That definition is too long.")

    return term, definition



# Maximum number of entries shown in one dropdown
DROPDOWN_PAGE_SIZE = 25


class DictionarySelect(discord.ui.Select):
    def __init__(self, dictionary_view):
        self.dictionary_view = dictionary_view

        entries = dictionary_view.entries
        page = dictionary_view.index // DROPDOWN_PAGE_SIZE

        start = page * DROPDOWN_PAGE_SIZE
        end = min(start + DROPDOWN_PAGE_SIZE, len(entries))

        options = []

        for index in range(start, end):
            entry = entries[index]

            options.append(
                discord.SelectOption(
                    label=entry["term"][:100],
                    value=str(index),
                    description=(
                        entry["definition"]
                        .replace("\n", " ")[:100]
                    ),
                    default=(index == dictionary_view.index)
                )
            )

        super().__init__(
            placeholder="📖 Select a dictionary entry...",
            min_values=1,
            max_values=1,
            options=options,
            row=0
        )

    async def callback(self, interaction):
        view = self.dictionary_view

        # The selected value is the entry's list index.
        view.index = int(self.values[0])

        view.update_controls()

        await interaction.response.edit_message(
            embed=view.create_embed(),
            view=view
        )


class DictionarySearchModal(discord.ui.Modal, title="Search Dictionary"):
    keyword = discord.ui.TextInput(
        label="Search term",
        placeholder="Search words or definitions...",
        required=True,
        min_length=1,
        max_length=100
    )

    def __init__(self, dictionary_view):
        super().__init__()
        self.dictionary_view = dictionary_view

    async def on_submit(self, interaction: discord.Interaction):
        view = self.dictionary_view
        keyword = self.keyword.value.strip()

        if not keyword:
            await interaction.response.send_message(
                "❌ Please enter a search term.",
                ephemeral=True
            )
            return

        # Fetch the latest matching entries from SQLite.
        with get_connection() as conn:
            results = conn.execute("""
                SELECT *
                FROM server_dictionary
                WHERE guild_id = ?
                  AND (
                    instr(lower(term), lower(?)) > 0
                    OR instr(lower(definition), lower(?)) > 0
                  )
                ORDER BY term COLLATE NOCASE ASC
                LIMIT 250
            """, (
                view.guild_id,
                keyword,
                keyword
            )).fetchall()

        if not results:
            await interaction.response.send_message(
                f"🔍 No results found for "
                f"**{discord.utils.escape_markdown(keyword)}**.",
                ephemeral=True
            )
            return

        view.entries = results
        view.index = 0
        view.search_query = keyword
        view.update_controls()

        # A modal submission is a separate interaction.
        # Update the original dictionary message.
        await interaction.response.edit_message(
            embed=view.create_embed(),
            view=view
        )


class DictionaryView(discord.ui.View):
    
    def __init__(self, entries, owner_id, guild_id, title="Server Dictionary"):
        super().__init__(timeout=180)

        self.entries = entries
        self.owner_id = owner_id
        self.guild_id = guild_id
        self.title = title
        self.search_query = None
        self.index = 0
        self.dropdown = None

        self.update_controls()


    def update_controls(self):
        # Remove the old dropdown before creating a new one.
        if self.dropdown is not None:
            self.remove_item(self.dropdown)

        self.dropdown = DictionarySelect(self)
        self.add_item(self.dropdown)

        current_page = self.index // DROPDOWN_PAGE_SIZE
        total_pages = (
            (len(self.entries) - 1) // DROPDOWN_PAGE_SIZE
        ) + 1

        self.previous_entry.disabled = self.index == 0
        self.next_entry.disabled = (
            self.index == len(self.entries) - 1
        )

        self.previous_page.disabled = current_page == 0
        self.next_page.disabled = (
            current_page >= total_pages - 1
        )

        self.clear_search_button.disabled = self.search_query is None

    def create_embed(self):
        entry = self.entries[self.index]

        page = self.index // DROPDOWN_PAGE_SIZE + 1
        total_pages = (
            (len(self.entries) - 1) // DROPDOWN_PAGE_SIZE
        ) + 1

        display_title = (
    f"🔍 Search: {self.search_query}"
    if self.search_query
    else "📖 Server Dictionary"
)

        display_title = (
    f"🔍 Search: {self.search_query}"
    if self.search_query
    else "📖 Server Dictionary"
)

        embed = discord.Embed(
            title=f"{display_title}\n{entry['term']}",
            description=entry["definition"],
            color=discord.Color.green()
)

        embed.add_field(
            name="Added by",
            value=f"<@{entry['author_id']}>",
            inline=True
        )

        embed.add_field(
            name="Dictionary",
            value=self.title,
            inline=True
        )

        embed.set_footer(
            text=(
                f"Entry {self.index + 1}/{len(self.entries)}"
                f" • Dropdown page {page}/{total_pages}"
                f" • ID #{entry['entry_id']}"
            )
        )

        return embed

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ Open your own dictionary using !dict.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="Previous",
        emoji="◀️",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def previous_entry(self, interaction, button):
        self.index -= 1
        self.update_controls()

        await interaction.response.edit_message(
            embed=self.create_embed(),
            view=self
        )

    @discord.ui.button(
        label="Next",
        emoji="▶️",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def next_entry(self, interaction, button):
        self.index += 1
        self.update_controls()

        await interaction.response.edit_message(
            embed=self.create_embed(),
            view=self
        )

    @discord.ui.button(
        label="-25",
        style=discord.ButtonStyle.primary,
        row=1
    )
    async def previous_page(self, interaction, button):
        current_page = self.index // DROPDOWN_PAGE_SIZE

        self.index = (
            current_page - 1
        ) * DROPDOWN_PAGE_SIZE

        self.update_controls()

        await interaction.response.edit_message(
            embed=self.create_embed(),
            view=self
        )

    @discord.ui.button(
        label="+25",
        style=discord.ButtonStyle.primary,
        row=1
    )
    async def next_page(self, interaction, button):
        current_page = self.index // DROPDOWN_PAGE_SIZE

        self.index = (
            current_page + 1
        ) * DROPDOWN_PAGE_SIZE

        self.update_controls()

        await interaction.response.edit_message(
            embed=self.create_embed(),
            view=self
        )


    @discord.ui.button(
        label="Search",
        emoji="🔍",
        style=discord.ButtonStyle.success,
        row=2
    )
    async def search_button(self, interaction, button):
        await interaction.response.send_modal(
            DictionarySearchModal(self)
        )

    @discord.ui.button(
        label="Clear Search",
        emoji="❌",
        style=discord.ButtonStyle.secondary,
        row=2
    )
    async def clear_search_button(self, interaction, button):
        with get_connection() as conn:
            self.entries = conn.execute("""
                SELECT *
                FROM server_dictionary
                WHERE guild_id = ?
                ORDER BY term COLLATE NOCASE ASC
            """, (self.guild_id,)).fetchall()

        if not self.entries:
            await interaction.response.send_message(
                "📖 The server dictionary is empty.",
                ephemeral=True
            )
            return

        self.index = 0
        self.search_query = None
        self.update_controls()

        await interaction.response.edit_message(
            embed=self.create_embed(),
            view=self
        )




class Dictionary(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.command(name="dictadd")
    @commands.guild_only()
    @commands.cooldown(3, 60, commands.BucketType.user)
    async def dict_add(self, ctx, *, entry: str):
        try:
            term, definition = parse_entry(entry)
        except ValueError as error:
            await ctx.send(str(error))
            return

        try:
            with get_connection() as conn:
                conn.execute("""
                    INSERT INTO server_dictionary
                        (guild_id, term, definition, author_id)
                    VALUES (?, ?, ?, ?)
                """, (
                    ctx.guild.id,
                    term,
                    definition,
                    ctx.author.id
                ))

        except sqlite3.IntegrityError:
            await ctx.send(
                "❌ That term already exists in this server."
            )
            return

        await ctx.send(
            f"📖 Added **{discord.utils.escape_markdown(term)}** "
            "to the server dictionary!",
            allowed_mentions=discord.AllowedMentions.none()
        )

    @commands.command(name="define")
    @commands.guild_only()
    async def define(self, ctx, *, term: str):
        term = term.strip()

        with get_connection() as conn:
            entry = conn.execute("""
                SELECT *
                FROM server_dictionary
                WHERE guild_id = ? AND term = ?
            """, (ctx.guild.id, term)).fetchone()

        if entry is None:
            await ctx.send(
                "❌ That term isn't in this server's dictionary."
            )
            return

        embed = discord.Embed(
            title=f"📖 {entry['term']}",
            description=entry["definition"],
            color=discord.Color.green()
        )

        embed.add_field(
            name="Added by",
            value=f"<@{entry['author_id']}>",
            inline=True
        )

        embed.set_footer(
            text=f"Dictionary Entry #{entry['entry_id']}"
        )

        await ctx.send(
            embed=embed,
            allowed_mentions=discord.AllowedMentions.none()
        )

    @commands.command(name="dictedit")
    @commands.guild_only()
    async def dict_edit(self, ctx, *, entry: str):
        try:
            term, definition = parse_entry(entry)
        except ValueError as error:
            await ctx.send(str(error))
            return

        with get_connection() as conn:
            existing = conn.execute("""
                SELECT entry_id, author_id
                FROM server_dictionary
                WHERE guild_id = ? AND term = ?
            """, (ctx.guild.id, term)).fetchone()

            if existing is None:
                await ctx.send("❌ That term doesn't exist.")
                return

            is_author = existing["author_id"] == ctx.author.id
            is_moderator = ctx.author.guild_permissions.manage_messages

            if not (is_author or is_moderator):
                await ctx.send(
                    "❌ Only the author or a server moderator "
                    "can edit this definition."
                )
                return

            conn.execute("""
                UPDATE server_dictionary
                SET definition = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE entry_id = ? AND guild_id = ?
            """, (
                definition,
                existing["entry_id"],
                ctx.guild.id
            ))

        await ctx.send("✅ Dictionary entry updated!")

    
    @commands.command(name="dictionary", aliases=["dict"])
    @commands.guild_only()
    async def dictionary(self, ctx):
        with get_connection() as conn:
            entries = conn.execute("""
                SELECT *
                FROM server_dictionary
                WHERE guild_id = ?
                ORDER BY term COLLATE NOCASE ASC
            """, (ctx.guild.id,)).fetchall()

        if not entries:
            await ctx.send(
                "📖 This server's dictionary is empty! "
                "Add a word using `!dictadd term | definition`."
            )
            return

        view = DictionaryView(
    entries=entries,
    owner_id=ctx.author.id,
    guild_id=ctx.guild.id
)

        await ctx.send(
            embed=view.create_embed(),
            view=view,
            allowed_mentions=discord.AllowedMentions.none()
        )

    
    @commands.command(name="dictsearch")
    @commands.guild_only()
    @commands.cooldown(3, 30, commands.BucketType.user)
    async def dict_search(self, ctx, *, keyword: str):
        keyword = keyword.strip()

        if not keyword:
            await ctx.send(
                "❌ Please provide a search keyword."
            )
            return

        if len(keyword) > 100:
            await ctx.send(
                "❌ Search queries must be 100 characters or less."
            )
            return

        with get_connection() as conn:
            entries = conn.execute("""
                SELECT *
                FROM server_dictionary
                WHERE guild_id = ?
                  AND (
                    instr(lower(term), lower(?)) > 0
                    OR instr(lower(definition), lower(?)) > 0
                  )
                ORDER BY term COLLATE NOCASE ASC
                LIMIT 250
            """, (
                ctx.guild.id,
                keyword,
                keyword
            )).fetchall()

        if not entries:
            await ctx.send(
                "🔍 No dictionary entries found matching "
                f"**{discord.utils.escape_markdown(keyword)}**.",
                allowed_mentions=discord.AllowedMentions.none()
            )
            return

        view = DictionaryView(
            entries=entries,
            owner_id=ctx.author.id,
            title=f"Search: {keyword}"
        )

        await ctx.send(
            embed=view.create_embed(),
            view=view,
            allowed_mentions=discord.AllowedMentions.none()
        )



    @commands.command(name="dictremove")
    @commands.guild_only()
    async def dict_remove(self, ctx, *, term: str):
        with get_connection() as conn:
            existing = conn.execute("""
                SELECT entry_id, author_id
                FROM server_dictionary
                WHERE guild_id = ? AND term = ?
            """, (ctx.guild.id, term.strip())).fetchone()

            if existing is None:
                await ctx.send("❌ That term doesn't exist.")
                return

            is_author = existing["author_id"] == ctx.author.id
            is_moderator = ctx.author.guild_permissions.manage_messages

            if not (is_author or is_moderator):
                await ctx.send(
                    "❌ You cannot remove this entry."
                )
                return

            conn.execute("""
                DELETE FROM server_dictionary
                WHERE entry_id = ? AND guild_id = ?
            """, (
                existing["entry_id"],
                ctx.guild.id
            ))

        await ctx.send("🗑️ Dictionary entry removed!")

    @commands.command(name="dictrandom")
    @commands.guild_only()
    async def dict_random(self, ctx):
        with get_connection() as conn:
            entry = conn.execute("""
                SELECT *
                FROM server_dictionary
                WHERE guild_id = ?
                ORDER BY RANDOM()
                LIMIT 1
            """, (ctx.guild.id,)).fetchone()

        if entry is None:
            await ctx.send(
                "📖 This server's dictionary is empty!"
            )
            return

        embed = discord.Embed(
            title=f"📖 {entry['term']}",
            description=entry["definition"],
            color=discord.Color.green()
        )

        embed.set_footer(text="Random Server Definition")

        await ctx.send(
            embed=embed,
            allowed_mentions=discord.AllowedMentions.none()
        )


async def setup(bot):
    initialize_dictionary()
    await bot.add_cog(Dictionary(bot))
