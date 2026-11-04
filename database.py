
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / (
    "baobot-dev.db"
    if os.getenv("BOT_ENV") == "development"
    else "baobot.db"
)
print(f"🥟 BaoBot database: {DB_PATH}")


MAX_FREE_ROLLS = 10
REGEN_SECONDS = 60
ROLL_PRICE = 100
SHINY_MULTIPLIER = 5

DAILY_REWARD = 200
WEEKLY_REWARD = 1000

DAILY_COOLDOWN = 24 * 60 * 60
WEEKLY_COOLDOWN = 7 * 24 * 60 * 60


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


PITY_THRESHOLDS = {
    "rare": 15,
    "epic": 50,
    "legendary": 150,
    "mythical": 1500
}

RARITY_ORDER = [
    "common",
    "uncommon",
    "rare",
    "epic",
    "legendary",
    "mythical",
    "divine",
    "peebing_cool"
]

PITY_COLUMNS = {
    "rare": "rare_pity",
    "epic": "epic_pity",
    "legendary": "legendary_pity",
    "mythical": "mythical_pity"
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
            "last_regen_at": "INTEGER NOT NULL DEFAULT 0",
            "last_daily_claim": "INTEGER NOT NULL DEFAULT 0",
            "last_weekly_claim": "INTEGER NOT NULL DEFAULT 0"

        }

        for column, definition in new_columns.items():
            if column not in player_columns:
                conn.execute(
                    f"ALTER TABLE players "
                    f"ADD COLUMN {column} {definition}"
                )

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

        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pity_counters (
                user_id INTEGER PRIMARY KEY,
                rare_pity INTEGER NOT NULL DEFAULT 0,
                epic_pity INTEGER NOT NULL DEFAULT 0,
                legendary_pity INTEGER NOT NULL DEFAULT 0,
                mythical_pity INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id)
                    REFERENCES players(user_id)
            )
        """)




def _ensure_player(conn, user_id, now):
    conn.execute("""
        INSERT OR IGNORE INTO players (
            user_id, last_regen_at
        )
        VALUES (?, ?)
    """, (user_id, now))

    
def _ensure_pity(conn, user_id):
    conn.execute("""
        INSERT OR IGNORE INTO pity_counters (user_id)
        VALUES (?)
    """, (user_id,))


def _get_pity_counters(conn, user_id):
    row = conn.execute("""
        SELECT
            rare_pity,
            epic_pity,
            legendary_pity,
            mythical_pity
        FROM pity_counters
        WHERE user_id = ?
    """, (user_id,)).fetchone()

    return {
        tier: row[column]
        for tier, column in PITY_COLUMNS.items()
    }


def _get_guarantee(counters):
    
    for tier in reversed(list(PITY_THRESHOLDS)):
        if counters[tier] >= PITY_THRESHOLDS[tier] - 1:
            return tier

    return None


def _update_pity(conn, user_id, counters, rarity):
    pulled_rank = RARITY_ORDER.index(rarity)

    for tier in PITY_THRESHOLDS:
        tier_rank = RARITY_ORDER.index(tier)

        if pulled_rank >= tier_rank:
            counters[tier] = 0
        else:
            counters[tier] += 1

    conn.execute("""
        UPDATE pity_counters
        SET rare_pity = ?,
            epic_pity = ?,
            legendary_pity = ?,
            mythical_pity = ?
        WHERE user_id = ?
    """, (
        counters["rare"],
        counters["epic"],
        counters["legendary"],
        counters["mythical"],
        user_id
    ))


def get_pity(user_id):
    now = int(time.time())

    with database() as conn:
        conn.execute("BEGIN IMMEDIATE")

        _ensure_player(conn, user_id, now)
        _ensure_pity(conn, user_id)

        return _get_pity_counters(conn, user_id)




def _refresh_rolls(conn, user_id, now):
    player = conn.execute("""
        SELECT free_rolls, last_regen_at
        FROM players
        WHERE user_id = ?
    """, (user_id,)).fetchone()

    free = player["free_rolls"]
    last = player["last_regen_at"]


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



def perform_roll(user_id, roll_factory):
    now = int(time.time())

    with database() as conn:
        conn.execute("BEGIN IMMEDIATE")

        _ensure_player(conn, user_id, now)
        _ensure_pity(conn, user_id)

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

        counters = _get_pity_counters(
            conn, user_id
        )

        guarantee = _get_guarantee(counters)

       
        card, rarity, shiny = roll_factory(guarantee)

        if rarity not in RARITY_ORDER:
            raise ValueError(
                f"Unknown rarity: {rarity}"
            )

       
        _update_pity(
            conn,
            user_id,
            counters,
            rarity
        )

        conn.execute("""
            UPDATE players
            SET free_rolls = ?,
                paid_rolls = ?,
                total_rolls = total_rolls + 1
            WHERE user_id = ?
        """, (free, paid, user_id))

        cursor = conn.execute("""
            INSERT INTO player_cards (
                user_id,
                card_id,
                rarity,
                is_shiny
            )
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            card["id"],
            rarity,
            int(shiny)
        ))

        return {
            "instance_id": cursor.lastrowid,
            "card": card,
            "rarity": rarity,
            "shiny": shiny,
            "guarantee": guarantee,
            "payment": payment,
            "free_rolls": free,
            "paid_rolls": paid,
            "pity": counters.copy()
        }




def perform_multi_roll(user_id, quantity, roll_factory):
    if not 2 <= quantity <= 10:
        return {"status": "invalid_quantity"}

    now = int(time.time())

    with database() as conn:
        conn.execute("BEGIN IMMEDIATE")

        _ensure_player(conn, user_id, now)
        _ensure_pity(conn, user_id)

        free, _ = _refresh_rolls(conn, user_id, now)

        player = conn.execute("""
            SELECT paid_rolls
            FROM players
            WHERE user_id = ?
        """, (user_id,)).fetchone()

        paid = player["paid_rolls"]
        available = free + paid

        if available < quantity:
            return {
                "status": "insufficient",
                "requested": quantity,
                "available": available
            }

        free_spent = min(free, quantity)
        paid_spent = quantity - free_spent

        counters = _get_pity_counters(conn, user_id)
        results = []

        for _ in range(quantity):
        
            guarantee = _get_guarantee(counters)

            card, rarity, shiny = roll_factory(guarantee)

            if rarity not in RARITY_ORDER:
                raise ValueError(
                    f"Unknown rarity: {rarity}"
                )

            if "id" not in card:
                raise ValueError("Card is missing an ID")

          
            _update_pity(
                conn, user_id, counters, rarity
            )

            cursor = conn.execute("""
                INSERT INTO player_cards (
                    user_id, card_id, rarity, is_shiny
                )
                VALUES (?, ?, ?, ?)
            """, (
                user_id,
                card["id"],
                rarity,
                int(shiny)
            ))

            results.append({
                "instance_id": cursor.lastrowid,
                "card": card,
                "rarity": rarity,
                "shiny": shiny,
                "guarantee": guarantee
            })

        conn.execute("""
            UPDATE players
            SET free_rolls = free_rolls - ?,
                paid_rolls = paid_rolls - ?,
                total_rolls = total_rolls + ?
            WHERE user_id = ?
        """, (
            free_spent,
            paid_spent,
            quantity,
            user_id
        ))

        return {
            "status": "success",
            "results": results,
            "free_spent": free_spent,
            "paid_spent": paid_spent,
            "pity": counters.copy()
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


def _prepare_multi_sale(conn, user_id, instance_ids):
    """Validate cards and calculate the sale payout."""

    if not 2 <= len(instance_ids) <= 25:
        return {"status": "invalid_quantity"}

    if len(set(instance_ids)) != len(instance_ids):
        return {"status": "duplicate_ids"}

    placeholders = ",".join("?" for _ in instance_ids)

    rows = conn.execute(f"""
        SELECT instance_id, card_id, rarity, is_shiny
        FROM player_cards
        WHERE user_id = ?
          AND instance_id IN ({placeholders})
    """, (user_id, *instance_ids)).fetchall()

    if len(rows) != len(instance_ids):
        return {"status": "missing_cards"}

    by_id = {
        row["instance_id"]: dict(row)
        for row in rows
    }

    cards = []
    total = 0
    protected = False

    for instance_id in instance_ids:
        card = by_id[instance_id]
        rarity = card["rarity"]
        shiny = bool(card["is_shiny"])

        if rarity not in SELL_VALUES:
            return {"status": "unknown_rarity"}

        value = SELL_VALUES[rarity]

        if shiny:
            value *= SHINY_MULTIPLIER

        card["value"] = value
        cards.append(card)

        total += value

        if shiny or rarity in PROTECTED_RARITIES:
            protected = True

    return {
        "status": "valid",
        "cards": cards,
        "total": total,
        "protected": protected
    }


def preview_multi_sale(user_id, instance_ids):
    with database() as conn:
        return _prepare_multi_sale(
            conn,
            user_id,
            instance_ids
        )


def execute_multi_sale(
    user_id,
    instance_ids,
    confirmed=False,
    expected_total=None
):
    with database() as conn:
        conn.execute("BEGIN IMMEDIATE")

        result = _prepare_multi_sale(
            conn,
            user_id,
            instance_ids
        )

        if result["status"] != "valid":
            return result

        if result["protected"] and not confirmed:
            return {
                "status": "confirmation_required",
                **result

            }

        if expected_total is not None:
            if result["total"] != expected_total:
                return {"status": "sale_changed"}

        placeholders = ",".join("?" for _ in instance_ids)

        cursor = conn.execute(f"""
            DELETE FROM player_cards
            WHERE user_id = ?
              AND instance_id IN ({placeholders})
        """, (user_id, *instance_ids))

        if cursor.rowcount != len(instance_ids):
            raise RuntimeError(
                "Batch sale deleted an unexpected number of cards"
            )

        conn.execute("""
            UPDATE players
            SET bao_coins = bao_coins + ?
            WHERE user_id = ?
        """, (result["total"], user_id))

        return {
            "status": "success",
            "cards_sold": len(instance_ids),
            "total": result["total"]
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



def get_trade_preview(
    sender_id, receiver_id,
    sender_card_id, receiver_card_id
):
    """Validate both cards before creating an offer."""
    if sender_id == receiver_id:
        return {"status": "same_user"}

    if sender_card_id == receiver_card_id:
        return {"status": "same_card"}

    with database() as conn:
        sender_card = conn.execute("""
            SELECT instance_id, card_id, rarity, is_shiny
            FROM player_cards
            WHERE instance_id = ? AND user_id = ?
        """, (sender_card_id, sender_id)).fetchone()

        receiver_card = conn.execute("""
            SELECT instance_id, card_id, rarity, is_shiny
            FROM player_cards
            WHERE instance_id = ? AND user_id = ?
        """, (receiver_card_id, receiver_id)).fetchone()

        if sender_card is None:
            return {"status": "sender_missing"}

        if receiver_card is None:
            return {"status": "receiver_missing"}

        return {
            "status": "valid",
            "sender_card": dict(sender_card),
            "receiver_card": dict(receiver_card)
        }


def execute_trade(
    sender_id, receiver_id,
    sender_card_id, receiver_card_id
):
    """Atomically exchange two card instances."""
    if sender_id == receiver_id:
        return {"status": "same_user"}

    if sender_card_id == receiver_card_id:
        return {"status": "same_card"}

    with database() as conn:
        
        conn.execute("BEGIN IMMEDIATE")

        cards = conn.execute("""
            SELECT instance_id, user_id
            FROM player_cards
            WHERE instance_id IN (?, ?)
        """, (
            sender_card_id,
            receiver_card_id
        )).fetchall()

        owners = {
            row["instance_id"]: row["user_id"]
            for row in cards
        }

        if owners.get(sender_card_id) != sender_id:
            return {"status": "sender_missing"}

        if owners.get(receiver_card_id) != receiver_id:
            return {"status": "receiver_missing"}

        conn.execute("""
            UPDATE player_cards
            SET user_id = ?
            WHERE instance_id = ?
        """, (
            receiver_id,
            sender_card_id
        ))

        conn.execute("""
            UPDATE player_cards
            SET user_id = ?
            WHERE instance_id = ?
        """, (
            sender_id,
            receiver_card_id
        ))

        return {"status": "success"}



def claim_reward(user_id, reward_type):
    rewards = {
        "daily": (
            DAILY_REWARD,
            DAILY_COOLDOWN,
            "last_daily_claim"
        ),
        "weekly": (
            WEEKLY_REWARD,
            WEEKLY_COOLDOWN,
            "last_weekly_claim"
        )
    }

    if reward_type not in rewards:
        raise ValueError("Invalid reward type")

    amount, cooldown, column = rewards[reward_type]
    now = int(time.time())

    with database() as conn:
        conn.execute("BEGIN IMMEDIATE")
        _ensure_player(conn, user_id, now)

        player = conn.execute(f"""
            SELECT bao_coins, {column}
            FROM players
            WHERE user_id = ?
        """, (user_id,)).fetchone()

        last_claim = player[column]
        remaining = max(
            0,
            last_claim + cooldown - now
        ) if last_claim else 0

        if remaining > 0:
            return {
                "status": "cooldown",
                "remaining": remaining,
                "coins": player["bao_coins"]
            }

        conn.execute(f"""
            UPDATE players
            SET bao_coins = bao_coins + ?,
                {column} = ?
            WHERE user_id = ?
        """, (amount, now, user_id))

        return {
            "status": "success",
            "reward": amount,
            "coins": player["bao_coins"] + amount,
            "next_claim": now + cooldown
        }


def get_reward_cooldowns(user_id):
    now = int(time.time())

    with database() as conn:
        conn.execute("BEGIN IMMEDIATE")
        _ensure_player(conn, user_id, now)

        player = conn.execute("""
            SELECT last_daily_claim, last_weekly_claim
            FROM players
            WHERE user_id = ?
        """, (user_id,)).fetchone()

        def remaining(last_claim, cooldown):
            if not last_claim:
                return 0

            return max(
                0,
                last_claim + cooldown - now
            )

        return {
            "daily": remaining(
                player["last_daily_claim"],
                DAILY_COOLDOWN
            ),
            "weekly": remaining(
                player["last_weekly_claim"],
                WEEKLY_COOLDOWN
            )
        }




