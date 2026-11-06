
import json
import shlex
import time
from pathlib import Path

import os
import sys
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

if len(sys.argv) != 2 or sys.argv[1].lower() not in {
    "dev", "prod"
}:
    print("Usage: py control.py <dev|prod>")
    sys.exit(1)

ENVIRONMENT = sys.argv[1].lower()

if ENVIRONMENT == "dev":
    env_file = BASE_DIR / ".env.dev"
    os.environ["BOT_ENV"] = "development"
else:
    env_file = BASE_DIR / ".env"
    os.environ["BOT_ENV"] = "production"

# Load the selected environment without allowing its
# BOT_ENV value to override our explicit selection.
load_dotenv(env_file, override=True)
os.environ["BOT_ENV"] = (
    "development" if ENVIRONMENT == "dev"
    else "production"
)

# Import only AFTER selecting the environment.
from database import DB_PATH

print(f"🥟 Control environment: {ENVIRONMENT.upper()}")
print(f"📂 Database: {DB_PATH}")

if ENVIRONMENT == "prod":
    confirmation = input(
        "\n⚠️ PRODUCTION DATABASE! "
        "Type PROD to continue: "
    )

    if confirmation != "PROD":
        print("Cancelled.")
        sys.exit(0)

CARDS_PATH = BASE_DIR / "data" / "cards.json"

from database import (
    database,
    initialize_database,
    get_balance,
    get_pity,
    RARITY_ORDER,
    PITY_COLUMNS
)



ADMIN_USER_ID = 1158232274349850724

if ADMIN_USER_ID == 1560027010347044934:
    print("BOT")

elif ADMIN_USER_ID == 1158232274349850724:
    print("LilKevon")


def require_admin_id():
    if ADMIN_USER_ID <= 0:
        raise RuntimeError(
            "Set ADMIN_USER_ID in control.py first."
        )


def give_coins(user_id, amount):
    if amount <= 0:
        raise ValueError("Amount must be positive.")

    with database() as conn:
        conn.execute("BEGIN IMMEDIATE")

        conn.execute("""
            INSERT OR IGNORE INTO players (
                user_id, last_regen_at
            )
            VALUES (?, ?)
        """, (user_id, int(time.time())))

        conn.execute("""
            UPDATE players
            SET bao_coins = bao_coins + ?
            WHERE user_id = ?
        """, (amount, user_id))

def del_coins(user_id, amount):
    if amount <= 0:
        raise ValueError("Amount must be positive.")

    with database() as conn:
        conn.execute("BEGIN IMMEDIATE")

        conn.execute("""
            INSERT OR IGNORE INTO players (
                user_id, last_regen_at
            )
            VALUES (?, ?)
        """, (user_id, int(time.time())))

        conn.execute("""
            UPDATE players
            SET bao_coins = bao_coins - ?
            WHERE user_id = ?
        """, (amount, user_id))


def give_rolls(user_id, amount):
    if amount <= 0:
        raise ValueError("Amount must be positive.")

    with database() as conn:
        conn.execute("BEGIN IMMEDIATE")

        conn.execute("""
            INSERT OR IGNORE INTO players (
                user_id, last_regen_at
            )
            VALUES (?, ?)
        """, (user_id, int(time.time())))

        conn.execute("""
            UPDATE players
            SET paid_rolls = paid_rolls + ?
            WHERE user_id = ?
        """, (amount, user_id))


def give_card(user_id, card_id, rarity, shiny=False):
    if rarity not in RARITY_ORDER:
        raise ValueError("Invalid rarity.")

    with CARDS_PATH.open(encoding="utf-8") as file:
        cards = json.load(file)

    valid_card_ids = {
        card["id"] for card in cards
    }

    if card_id not in valid_card_ids:
        raise ValueError(
            f"Unknown card ID: {card_id}"
        )

    with database() as conn:
        conn.execute("BEGIN IMMEDIATE")

        conn.execute("""
            INSERT OR IGNORE INTO players (
                user_id, last_regen_at
            )
            VALUES (?, ?)
        """, (user_id, int(time.time())))

        cursor = conn.execute("""
            INSERT INTO player_cards (
                user_id, card_id, rarity, is_shiny
            )
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            card_id,
            rarity,
            int(shiny)
        ))

        return cursor.lastrowid


def set_pity(user_id, rarity, value):
    if rarity not in PITY_COLUMNS:
        raise ValueError(
            "Pity tier must be rare, epic, "
            "legendary, or mythical."
        )

    if value < 0:
        raise ValueError(
            "Pity cannot be negative."
        )

    column = PITY_COLUMNS[rarity]

    with database() as conn:
        conn.execute("BEGIN IMMEDIATE")

        conn.execute("""
            INSERT OR IGNORE INTO players (
                user_id, last_regen_at
            )
            VALUES (?, ?)
        """, (user_id, int(time.time())))

        conn.execute("""
            INSERT OR IGNORE INTO pity_counters (
                user_id
            )
            VALUES (?)
        """, (user_id,))

        conn.execute(
            f"""
            UPDATE pity_counters
            SET {column} = ?
            WHERE user_id = ?
            """,
            (value, user_id)
        )


def reset_pity(user_id):
    with database() as conn:
        conn.execute("BEGIN IMMEDIATE")

        conn.execute("""
            INSERT OR IGNORE INTO players (
                user_id, last_regen_at
            )
            VALUES (?, ?)
        """, (user_id, int(time.time())))

        conn.execute("""
            INSERT OR IGNORE INTO pity_counters (
                user_id
            )
            VALUES (?)
        """, (user_id,))

        conn.execute("""
            UPDATE pity_counters
            SET rare_pity = 0,
                epic_pity = 0,
                legendary_pity = 0,
                mythical_pity = 0
            WHERE user_id = ?
        """, (user_id,))


def show_account(user_id):
    balance = get_balance(user_id)
    pity = get_pity(user_id)

    print("\n===== BaoBot Account =====")
    print(f"User ID: {user_id}")
    print(f"BaoCoins: {balance['coins']:,}")
    print(f"Free Rolls: {balance['free_rolls']}/5")
    print(f"Purchased Rolls: {balance['paid_rolls']:,}")
    print(f"Lifetime Rolls: {balance['total_rolls']:,}")

    print("\nPity:")
    for rarity, amount in pity.items():
        print(f"  {rarity.title()}: {amount}")

    print("==========================\n")



def main():
    initialize_database()
    require_admin_id()

    print("🥟 BaoBot Admin Control")
    print(f"Target account: {ADMIN_USER_ID}")
    print("Type 'help' for commands. 'exit' to quit.")

    while True:
        try:
            raw = input("admin> ").strip()
            if not raw:
                continue

            args = shlex.split(raw)
            command = args[0].lower()

            if command in ("exit", "quit"):
                break

            elif command == "help":
                print("""
Commands:
  inspect
  balance
  give coins <amount>
  give rolls <amount>
  give card <card_id> <rarity> [shiny]
  set pity <rarity> <value>
  reset pity
  exit
""")

            elif command in ("inspect", "balance"):
                show_account(ADMIN_USER_ID)

            elif command == "remove" and len(args) >= 3:
                kind = args[1].lower()
                if kind == "coins" and len(args) == 3:
                    del_coins(ADMIN_USER_ID, int(args[2]))
                    print("✅ BaoCoins removed.")
            elif command == "give" and len(args) >= 3:
                kind = args[1].lower()

                if kind == "coins" and len(args) == 3:
                    give_coins(ADMIN_USER_ID, int(args[2]))
                    print("✅ BaoCoins added.")

                elif kind == "rolls" and len(args) == 3:
                    give_rolls(ADMIN_USER_ID, int(args[2]))
                    print("✅ Purchased rolls added.")
                

                elif kind == "card" and len(args) in (4, 5):
                    shiny = (
                        len(args) == 5
                        and args[4].lower() == "shiny"
                    )

                    instance_id = give_card(
                        ADMIN_USER_ID,
                        args[2],
                        args[3].lower(),
                        shiny
                    )

                    print(
                        f"✅ Card created: #{instance_id}"
                    )

                else:
                    print("❌ Invalid give command.")

            elif (
                command == "set"
                and len(args) == 4
                and args[1] == "pity"
            ):
                set_pity(
                    ADMIN_USER_ID,
                    args[2].lower(),
                    int(args[3])
                )
                print("✅ Pity updated.")

            elif (
                command == "reset"
                and len(args) == 2
                and args[1] == "pity"
            ):
                reset_pity(ADMIN_USER_ID)
                print("✅ Pity reset.")

            else:
                print(
                    "❌ Unknown command. Type 'help'."
                )

        except (ValueError, OSError) as exc:
            print(f"❌ {exc}")

        except (KeyboardInterrupt, EOFError):
            print()
            break


if __name__ == "__main__":
    main()
