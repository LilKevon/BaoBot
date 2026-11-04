
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

SOURCE_DB = BASE_DIR / "baobot-dev.db"
TARGET_DB = BASE_DIR / "baobot.db"


def columns(conn, table):
    return [
        row["name"]
        for row in conn.execute(
            f"PRAGMA table_info({table})"
        )
    ]


def migrate_player(user_id):
    if not SOURCE_DB.is_file():
        raise FileNotFoundError(SOURCE_DB)

    if not TARGET_DB.is_file():
        raise FileNotFoundError(TARGET_DB)

    if SOURCE_DB.resolve() == TARGET_DB.resolve():
        raise ValueError("Source and target must differ.")

    with sqlite3.connect(SOURCE_DB) as source, \
         sqlite3.connect(TARGET_DB) as target:

        source.row_factory = sqlite3.Row
        target.row_factory = sqlite3.Row
        target.execute("PRAGMA foreign_keys = ON")

        player = source.execute(
            "SELECT * FROM players WHERE user_id = ?",
            (user_id,)
        ).fetchone()

        if player is None:
            print("❌ User not found in development.")
            return

        cards = source.execute("""
            SELECT card_id, rarity, is_shiny, obtained_at
            FROM player_cards
            WHERE user_id = ?
            ORDER BY instance_id
        """, (user_id,)).fetchall()

        source_fields = columns(source, "players")
        target_fields = columns(target, "players")

        missing = set(source_fields) - set(target_fields)

        if missing:
            raise RuntimeError(
                f"Production is missing player columns: "
                f"{sorted(missing)}"
            )

        pity_fields = [
            "rare_pity",
            "epic_pity",
            "legendary_pity",
            "mythical_pity"
        ]

        for conn in (source, target):
            if not set(pity_fields).issubset(
                columns(conn, "pity_counters")
            ):
                raise RuntimeError(
                    "Both databases need the pity schema."
                )

        pity = source.execute("""
            SELECT rare_pity, epic_pity,
                   legendary_pity, mythical_pity
            FROM pity_counters
            WHERE user_id = ?
        """, (user_id,)).fetchone()

        existing = target.execute(
            "SELECT 1 FROM players WHERE user_id = ?",
            (user_id,)
        ).fetchone()

        print(f"\nUser: {user_id}")
        print(f"Cards to import: {len(cards)}")
        print(f"BaoCoins: {player['bao_coins']:,}")
        print(f"Purchased rolls: {player['paid_rolls']}")

        if existing:
            print(
                "⚠️ Existing production account "
                "will be replaced."
            )

        confirmation = input(
            f"\nType REPLACE {user_id} to continue: "
        )

        if confirmation != f"REPLACE {user_id}":
            print("Cancelled.")
            return

        
        timestamp = datetime.now().strftime(
            "%Y%m%d-%H%M%S"
        )

        backup_path = BASE_DIR / (
            f"baobot-backup-{timestamp}.db"
        )

        with sqlite3.connect(backup_path) as backup:
            target.backup(backup)

        print(f"✅ Backup created: {backup_path.name}")

        fields = list(player.keys())
        placeholders = ", ".join("?" for _ in fields)
        column_sql = ", ".join(fields)

        updates = ", ".join(
            f"{field} = excluded.{field}"
            for field in fields
            if field != "user_id"
        )

        try:
            target.execute("BEGIN IMMEDIATE")

           
            target.execute(f"""
                INSERT INTO players ({column_sql})
                VALUES ({placeholders})
                ON CONFLICT(user_id) DO UPDATE SET
                {updates}
            """, tuple(player))

            
            target.execute(
                "DELETE FROM player_cards WHERE user_id = ?",
                (user_id,)
            )

            
            target.executemany("""
                INSERT INTO player_cards (
                    user_id, card_id, rarity,
                    is_shiny, obtained_at
                )
                VALUES (?, ?, ?, ?, ?)
            """, [
                (
                    user_id,
                    card["card_id"],
                    card["rarity"],
                    card["is_shiny"],
                    card["obtained_at"]
                )
                for card in cards
            ])

           
            target.execute(
                "DELETE FROM pity_counters WHERE user_id = ?",
                (user_id,)
            )

            if pity is not None:
                target.execute("""
                    INSERT INTO pity_counters (
                        user_id, rare_pity, epic_pity,
                        legendary_pity, mythical_pity
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    user_id,
                    *[pity[field] for field in pity_fields]
                ))

            target.commit()

        except Exception:
            target.rollback()
            raise

        print("\n✅ Migration complete!")
        print(f"Transferred {len(cards)} cards.")
        print("All other players remain unchanged.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: py migrate_player.py <discord_user_id>")
        sys.exit(1)

    migrate_player(int(sys.argv[1]))
