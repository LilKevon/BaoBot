import json
from pathlib import Path
from dataclasses import dataclass

BASE_DIR = Path(__file__).resolve().parent.parent
CARDS_FILE = BASE_DIR / "data" / "stats.json"


MAX_LEVEL = 20

RARITY_MULTIPLIERS = {
    "common": 1.00,
    "uncommon": 1.10,
    "rare": 1.20,
    "epic": 1.35,
    "legendary": 1.50,
    "mythical": 1.65,
    "divine": 1.80,
    "peebing_cool": 2.00,
}


@dataclass(frozen=True)
class BaseStats:
    hp: int
    atk: int
    defense: int
    speed: int
    crit_rate: int


@dataclass(frozen=True)
class CombatStats:
    hp: int
    atk: int
    defense: int
    speed: int
    crit_rate: int


ARCHETYPES = {
    "balanced": BaseStats(500, 75, 55, 50, 10),
    "bruiser": BaseStats(650, 90, 65, 35, 10),
    "tank": BaseStats(800, 55, 100, 25, 5),
    "assassin": BaseStats(400, 110, 35, 85, 20),
    "glass_cannon": BaseStats(350, 130, 25, 65, 25),
}

def get_card_base_stats(card_id: str) -> BaseStats:
    with open(CARDS_FILE, "r", encoding="utf-8") as file:
        cards = json.load(file)

    for card in cards:
        if card["id"] == card_id:
            stats = card["combat"]

            return BaseStats(
                hp=stats["hp"],
                atk=stats["atk"],
                defense=stats["def"],
                speed=stats["spd"],
                crit_rate=stats["crit_rate"]
            )

    raise ValueError(
        f"No combat stats found for card: {card_id}"
    )


def calculate_stats(
    rarity: str,
    card_id: str,
    level: int = 1,
) -> CombatStats:

    if rarity not in RARITY_MULTIPLIERS:
        raise ValueError(f"Unknown rarity: {rarity}")

    if not 1 <= level <= MAX_LEVEL:
        raise ValueError(
            f"Level must be between 1 and {MAX_LEVEL}"
        )

    base = get_card_base_stats(card_id)

    rarity_multiplier = RARITY_MULTIPLIERS[rarity]

    level_multiplier = 1 + (level - 1) * 0.05

    multiplier = rarity_multiplier * level_multiplier

    return CombatStats(
        hp=round(base.hp * multiplier),
        atk=round(base.atk * multiplier),
        defense=round(base.defense * multiplier),
        speed=round(base.speed * multiplier),

        # Crit rate stays unchanged for now.
        crit_rate=base.crit_rate
    )
