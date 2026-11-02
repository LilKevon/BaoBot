
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "baobot-dev.db"

MAX_FREE_ROLLS = 5
REGEN_SECONDS = 60
ROLL_PRICE = 100
SHINY_MULTIPLIER = 5

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

PROTECTED_RARITIES = {
    "legendary",
    "mythical",
    "divine",
    "peebing_cool"
}


@contextmanager
def database():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        with conn:
            yield conn
    finally:
        conn.close()


def initialize_database():
    with database() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                total_rolls INTEGER NOT NULL DEFAULT 0,
                bao_coins INTEGER NOT NULL DEFAULT 0,
                free_rolls INTEGER NOT NULL DEFAULT 5,
                paid_rolls INTEGER NOT NULL DEFAULT 0,
                last_regen_at INTEGER NOT NULL DEFAULT 0
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS player_cards (
                instance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                card_id TEXT NOT NULL,
                rarity TEXT NOT NULL DEFAULT 'common',
                is_shiny INTEGER NOT NULL DEFAULT 0
                    CHECK (is_shiny IN (0, 1)),
                obtained_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id)
                    REFERENCES players(user_id)
            )
        """)

        # Migrate existing player databases
        player_columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(players)"
            )
        }

        new_columns = {
            "bao_coins": "INTEGER NOT NULL DEFAULT 0",
            "free_rolls": "INTEGER NOT NULL DEFAULT 5",
            "paid_rolls": "INTEGER NOT NULL DEFAULT 0",
            "last_regen_at": "INTEGER NOT NULL DEFAULT 0"
        }

        for column, definition in new_columns.items():
            if column not in player_columns:
                conn.execute(
                    f"ALTER TABLE players "
                    f"ADD COLUMN {column} {definition}"
                )

        # Preserve compatibility with older card databases
        card_columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(player_cards)"
            )
        }

        if "rarity" not in card_columns:
            conn.execute("""
                ALTER TABLE player_cards
                ADD COLUMN rarity TEXT NOT NULL
                DEFAULT 'common'
            """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_player_cards_user
            ON player_cards(user_id)
        """)


def _ensure_player(conn, user_id, now):
    conn.execute("""
        INSERT OR IGNORE INTO players (
            user_id, last_regen_at
        )
        VALUES (?, ?)
    """, (user_id, now))


def _refresh_rolls(conn, user_id, now):
    player = conn.execute("""
        SELECT free_rolls, last_regen_at
        FROM players
        WHERE user_id = ?
    """, (user_id,)).fetchone()

    free = player["free_rolls"]
    last = player["last_regen_at"]

    # Initialize timer for users from an older database
    if last == 0:
        last = now

    if free >= MAX_FREE_ROLLS:
        free = MAX_FREE_ROLLS
        last = now
    else:
        elapsed = max(0, now - last)
        restored = elapsed // REGEN_SECONDS

        if restored > 0:
            free = min(
                MAX_FREE_ROLLS,
                free + restored
            )

            if free == MAX_FREE_ROLLS:
                last = now
            else:
                last += restored * REGEN_SECONDS

    conn.execute("""
        UPDATE players
        SET free_rolls = ?,
            last_regen_at = ?
        WHERE user_id = ?
    """, (free, last, user_id))

    return free, last


def get_balance(user_id):
    now = int(time.time())

    with database() as conn:
        conn.execute("BEGIN IMMEDIATE")
        _ensure_player(conn, user_id, now)
        free, last = _refresh_rolls(
            conn, user_id, now
        )

        player = conn.execute("""
            SELECT bao_coins, paid_rolls, total_rolls
            FROM players
            WHERE user_id = ?
        """, (user_id,)).fetchone()

        next_roll = (
            max(1, REGEN_SECONDS - (now - last))
            if free < MAX_FREE_ROLLS
            else 0
        )

        return {
            "coins": player["bao_coins"],
            "free_rolls": free,
            "paid_rolls": player["paid_rolls"],
            "total_rolls": player["total_rolls"],
            "next_roll": next_roll
        }


def perform_roll(user_id, card_id, rarity, is_shiny):
    now = int(time.time())

    with database() as conn:
        # Lock before checking/spending a roll
        conn.execute("BEGIN IMMEDIATE")

        _ensure_player(conn, user_id, now)
        free, last = _refresh_rolls(
            conn, user_id, now
        )

        player = conn.execute("""
            SELECT paid_rolls
            FROM players
            WHERE user_id = ?
        """, (user_id,)).fetchone()

        paid = player["paid_rolls"]

        if free > 0:
            free -= 1
            payment = "free"

        elif paid > 0:
            paid -= 1
            payment = "purchased"

        else:
            return None

        conn.execute("""
            UPDATE players
            SET free_rolls = ?,
                paid_rolls = ?,
                total_rolls = total_rolls + 1
            WHERE user_id = ?
        """, (free, paid, user_id))

        cursor = conn.execute("""
            INSERT INTO player_cards (
                user_id, card_id, rarity, is_shiny
            )
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            card_id,
            rarity,
            int(is_shiny)
        ))

        return {
            "instance_id": cursor.lastrowid,
            "payment": payment,
            "free_rolls": free,
            "paid_rolls": paid
        }


def buy_rolls(user_id, quantity):
    if not 1 <= quantity <= 100:
        return {"status": "invalid_quantity"}

    cost = quantity * ROLL_PRICE
    now = int(time.time())

    with database() as conn:
        conn.execute("BEGIN IMMEDIATE")
        _ensure_player(conn, user_id, now)

        player = conn.execute("""
            SELECT bao_coins
            FROM players
            WHERE user_id = ?
        """, (user_id,)).fetchone()

        if player["bao_coins"] < cost:
            return {
                "status": "insufficient",
                "cost": cost,
                "coins": player["bao_coins"]
            }

        conn.execute("""
            UPDATE players
            SET bao_coins = bao_coins - ?,
                paid_rolls = paid_rolls + ?
            WHERE user_id = ?
        """, (cost, quantity, user_id))

        return {
            "status": "success",
            "cost": cost,
            "quantity": quantity
        }


def sell_card(user_id, instance_id, confirmed=False):
    with database() as conn:
        conn.execute("BEGIN IMMEDIATE")

        card = conn.execute("""
            SELECT card_id, rarity, is_shiny
            FROM player_cards
            WHERE instance_id = ? AND user_id = ?
        """, (instance_id, user_id)).fetchone()

        if card is None:
            return {"status": "not_found"}

        rarity = card["rarity"]
        shiny = bool(card["is_shiny"])

        if rarity not in SELL_VALUES:
            return {"status": "unknown_rarity"}

        value = SELL_VALUES[rarity] * (
            SHINY_MULTIPLIER if shiny else 1
        )

        valuable = (
            shiny or rarity in PROTECTED_RARITIES
        )

        if valuable and not confirmed:
            return {
                "status": "confirmation_required",
                "value": value,
                "rarity": rarity,
                "shiny": shiny
            }

        conn.execute("""
            DELETE FROM player_cards
            WHERE instance_id = ? AND user_id = ?
        """, (instance_id, user_id))

        conn.execute("""
            UPDATE players
            SET bao_coins = bao_coins + ?
            WHERE user_id = ?
        """, (value, user_id))

        return {
            "status": "success",
            "card_id": card["card_id"],
            "rarity": rarity,
            "shiny": shiny,
            "value": value
        }


def get_collection(user_id):
    with database() as conn:
        rows = conn.execute("""
            SELECT
                card_id,
                rarity,
                is_shiny,
                COUNT(*) AS quantity
            FROM player_cards
            WHERE user_id = ?
            GROUP BY card_id, rarity, is_shiny
            ORDER BY card_id, rarity, is_shiny
        """, (user_id,)).fetchall()

        return [dict(row) for row in rows]


def get_total_rolls(user_id):
    with database() as conn:
        row = conn.execute("""
            SELECT total_rolls
            FROM players
            WHERE user_id = ?
        """, (user_id,)).fetchone()

        return row["total_rolls"] if row else 0


def get_inventory(user_id):
    """Return every card instance owned by a player."""
    with database() as conn:
        rows = conn.execute("""
            SELECT
                instance_id,
                card_id,
                rarity,
                is_shiny,
                obtained_at
            FROM player_cards
            WHERE user_id = ?
            ORDER BY
                is_shiny DESC,
                CASE rarity
                    WHEN 'peebing_cool' THEN 0
                    WHEN 'divine' THEN 1
                    WHEN 'mythical' THEN 2
                    WHEN 'legendary' THEN 3
                    WHEN 'epic' THEN 4
                    WHEN 'rare' THEN 5
                    WHEN 'uncommon' THEN 6
                    ELSE 7
                END,
                instance_id DESC
        """, (user_id,)).fetchall()

        return [dict(row) for row in rows]


def get_card_instance(user_id, instance_id):
    """Retrieve one card, verifying its owner."""
    with database() as conn:
        row = conn.execute("""
            SELECT
                instance_id,
                card_id,
                rarity,
                is_shiny,
                obtained_at
            FROM player_cards
            WHERE user_id = ?
              AND instance_id = ?
        """, (user_id, instance_id)).fetchone()

        return dict(row) if row else None

