
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "baobot-dev.db"



def initialize_database():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                total_rolls INTEGER NOT NULL DEFAULT 0
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

        # Migrate existing databases
        columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(player_cards)"
            )
        }

        if "rarity" not in columns:
            conn.execute("""
                ALTER TABLE player_cards
                ADD COLUMN rarity TEXT NOT NULL DEFAULT 'common'
            """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_player_cards_user
            ON player_cards(user_id)
        """)




def save_pull(user_id, card_id, rarity, is_shiny):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO players (user_id)
            VALUES (?)
            """,
            (user_id,)
        )

        cursor = conn.execute(
    """
    INSERT INTO player_cards
        (user_id, card_id, rarity, is_shiny)
    VALUES (?, ?, ?, ?)
    """,
    (user_id, card_id, rarity, int(is_shiny))
)

        conn.execute(
            """
            UPDATE players
            SET total_rolls = total_rolls + 1
            WHERE user_id = ?
            """,
            (user_id,)
        )

        return cursor.lastrowid


def get_collection(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT
    card_id,
    rarity,
    is_shiny,
    COUNT(*) AS quantity
FROM player_cards
WHERE user_id = ?
GROUP BY card_id, rarity, is_shiny
ORDER BY card_id, rarity, is_shiny
            """,
            (user_id,)
        ).fetchall()

        return [dict(row) for row in rows]


def get_total_rolls(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        result = conn.execute(
            """
            SELECT total_rolls
            FROM players
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        return result[0] if result else 0
