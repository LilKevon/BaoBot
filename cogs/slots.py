
import secrets
import sqlite3
import logging

import discord
from discord.ext import commands

from database import DB_PATH


logger = logging.getLogger(__name__)

MIN_BET = 10
MAX_BET = 2000
SPIN_COOLDOWN = 1

# 50% loss, 48% pair, 2% triple
LOSS_CHANCE = 50
PAIR_CHANCE = 48
TRIPLE_CHANCE = 2

SYMBOLS = [
    "<:bao1:1568193348223762504>",
    "<:bao2:1568193349184393238>",
    "<:bao3:1568193350098493460>",
    "<:bao4:1568193351029755925>",
    "<:bao5:1568193359657570435>",
    "<:bao6:1568193360814940271>",
    "<:bao7:1568193361897062461>",
    "<:bao8:1568193362991779940>",
]

TRIPLE_MULTIPLIERS = {
    SYMBOLS[0]: 7,
    SYMBOLS[1]: 5,
    SYMBOLS[2]: 4,
    SYMBOLS[3]: 3,
    SYMBOLS[4]: 3,
    SYMBOLS[5]: 3,
    SYMBOLS[6]: 3,
    SYMBOLS[7]: 3,
}


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_slots():
    """Create slot history table if needed."""
    conn = get_connection()

    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS slot_history (
                    spin_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    wager INTEGER NOT NULL,
                    symbols TEXT NOT NULL,
                    multiplier INTEGER NOT NULL,
                    payout INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_slot_history_user
                ON slot_history(user_id)
            """)
    finally:
        conn.close()


def generate_reels():
    """
    Generate an outcome with controlled probabilities.

    50%: Three different symbols
    48%: Exactly two matching symbols
     2%: Three matching symbols
    """
    outcome = secrets.randbelow(100)

    if outcome < LOSS_CHANCE:
        # Three different symbols: loss.
        return secrets.SystemRandom().sample(
            SYMBOLS, 3
        )

    if outcome < LOSS_CHANCE + PAIR_CHANCE:
        # Exactly two matching symbols.
        matching = secrets.choice(SYMBOLS)

        alternatives = [
            symbol for symbol in SYMBOLS
            if symbol != matching
        ]

        different = secrets.choice(alternatives)

        reels = [matching, matching, different]
        secrets.SystemRandom().shuffle(reels)

        return reels

    # Three matching symbols: jackpot.
    symbol = secrets.choice(SYMBOLS)
    return [symbol, symbol, symbol]


def calculate_multiplier(reels):
    """Return the total payout multiplier."""

    # Three matching symbols.
    if reels[0] == reels[1] == reels[2]:
        return TRIPLE_MULTIPLIERS[reels[0]]

    # Exactly two matching symbols.
    if len(set(reels)) == 2:
        return 1.5

    # No matching symbols.
    return 0


def spin_slots(user_id, wager):
    """
    Atomically:
    1. Verify and deduct wager.
    2. Generate slot result.
    3. Credit winnings.
    4. Save spin history.
    """

    if (
        wager < MIN_BET
        or wager > MAX_BET
        or wager % 10 != 0
    ):
        raise ValueError(
            "Wager must be a multiple of 10 "
            "within the permitted limits."
        )

    conn = get_connection()

    try:
        conn.execute("BEGIN IMMEDIATE")

        result = conn.execute("""
            UPDATE players
            SET bao_coins = bao_coins - ?
            WHERE user_id = ?
              AND bao_coins >= ?
        """, (wager, user_id, wager))

        if result.rowcount != 1:
            conn.rollback()
            return None

        # Generate the final reels.
        reels = generate_reels()

        # Calculate the reward.
        multiplier = calculate_multiplier(reels)

        # Multiples of 10 ensure integer payouts.
        payout = int(wager * multiplier)

        conn.execute("""
            UPDATE players
            SET bao_coins = bao_coins + ?
            WHERE user_id = ?
        """, (payout, user_id))

        conn.execute("""
            INSERT INTO slot_history (
                user_id,
                wager,
                symbols,
                multiplier,
                payout
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            wager,
            " ".join(reels),
            multiplier,
            payout
        ))

        balance = conn.execute("""
            SELECT bao_coins
            FROM players
            WHERE user_id = ?
        """, (user_id,)).fetchone()["bao_coins"]

        conn.commit()

        return {
            "reels": reels,
            "multiplier": multiplier,
            "payout": payout,
            "profit": payout - wager,
            "balance": balance
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_slot_stats(user_id):
    """Retrieve lifetime slot statistics."""

    conn = get_connection()

    try:
        return conn.execute("""
            SELECT
                COUNT(*) AS spins,
                COALESCE(SUM(wager), 0) AS wagered,
                COALESCE(SUM(payout), 0) AS won,
                COALESCE(MAX(payout), 0) AS biggest_win,
                COALESCE(
                    SUM(
                        CASE
                            WHEN multiplier >= 3 THEN 1
                            ELSE 0
                        END
                    ), 0
                ) AS jackpots
            FROM slot_history
            WHERE user_id = ?
        """, (user_id,)).fetchone()
    finally:
        conn.close()


class BaoSlots(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="slots", aliases=["slot"])
    @commands.cooldown(
        1,
        SPIN_COOLDOWN,
        commands.BucketType.user
    )
    async def slots(self, ctx, bet: int):
        if (
            bet < MIN_BET
            or bet > MAX_BET
            or bet % 10 != 0
        ):
            await ctx.send(
                f"❌ Bets must be multiples of 10 "
                f"between {MIN_BET:,} and "
                f"{MAX_BET:,} BaoCoins."
            )
            return

        try:
            result = spin_slots(ctx.author.id, bet)

        except sqlite3.Error:
            logger.exception("Slot transaction failed")
            await ctx.send(
                "❌ Casino error! Your spin could not "
                "be completed. Please try again later."
            )
            return

        if result is None:
            await ctx.send(
                "❌ You don't have enough BaoCoins "
                "for that bet! Check `!balance`."
            )
            return

        multiplier = result["multiplier"]
        profit = result["profit"]

        if multiplier >= 3:
            outcome = "OH MY DAYS..."
            color = discord.Color.gold()

        elif multiplier == 1.5:
            outcome = "✨ LUCKY AF!"
            color = discord.Color.green()

        else:
            outcome = "💀 BYE BYE GEORGE!"
            color = discord.Color.red()

        embed = discord.Embed(
            title="🎰 Bao Casino",
            description=(
                f"## {' | '.join(result['reels'])}\n\n"
                f"**{outcome}**"
            ),
            color=color
        )

        embed.add_field(
            name="Wager",
            value=f"{bet:,} BC",
            inline=True
        )

        embed.add_field(
            name="Multiplier",
            value=f"{multiplier:g}x",
            inline=True
        )

        embed.add_field(
            name="Payout",
            value=f"{result['payout']:,} BC",
            inline=True
        )

        embed.add_field(
            name="Net Result",
            value=f"{profit:+,} BC",
            inline=True
        )

        embed.add_field(
            name="New Balance",
            value=f"{result['balance']:,} BC",
            inline=True
        )

        embed.set_footer(
            text=f"Player: {ctx.author.display_name}"
        )

        await ctx.send(
            embed=embed,
            allowed_mentions=discord.AllowedMentions.none()
        )

    @commands.command(name="slotstats")
    async def slot_stats(self, ctx):
        stats = get_slot_stats(ctx.author.id)

        wagered = stats["wagered"]
        won = stats["won"]
        net_profit = won - wagered

        embed = discord.Embed(
            title="🎰 Bao Casino Statistics",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Total Spins",
            value=f"{stats['spins']:,}"
        )

        embed.add_field(
            name="Total Wagered",
            value=f"{wagered:,} BC"
        )

        embed.add_field(
            name="Total Payouts",
            value=f"{won:,} BC"
        )

        embed.add_field(
            name="Net Profit",
            value=f"{net_profit:+,} BC"
        )

        embed.add_field(
            name="Biggest Payout",
            value=f"{stats['biggest_win']:,} BC"
        )

        embed.add_field(
            name="Jackpots (3x+)",
            value=f"{stats['jackpots']:,}"
        )

        await ctx.send(embed=embed)


async def setup(bot):
    initialize_slots()
    await bot.add_cog(BaoSlots(bot))
