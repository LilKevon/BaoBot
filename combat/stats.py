
from dataclasses import dataclass


MAX_LEVEL = 20

# Initial proposed values. We will balance these later.
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


@dataclass(frozen=True)
class CombatStats:
    hp: int
    atk: int
    defense: int
    speed: int


# Example archetypes; these are not the final card catalogue.
ARCHETYPES = {
    "balanced": BaseStats(500, 75, 55, 50),
    "bruiser": BaseStats(650, 90, 65, 35),
    "tank": BaseStats(800, 55, 100, 25),
    "assassin": BaseStats(400, 110, 35, 85),
    "glass_cannon": BaseStats(350, 130, 25, 65),
}


def calculate_stats(
    rarity: str,
    archetype: str,
    level: int = 1,
) -> CombatStats:
    """
    Calculate deterministic combat stats from
    rarity, archetype, and level.
    """

    if rarity not in RARITY_MULTIPLIERS:
        raise ValueError(f"Unknown rarity: {rarity}")

    if archetype not in ARCHETYPES:
        raise ValueError(f"Unknown archetype: {archetype}")

    if not 1 <= level <= MAX_LEVEL:
        raise ValueError(
            f"Level must be between 1 and {MAX_LEVEL}"
        )

    base = ARCHETYPES[archetype]
    rarity_multiplier = RARITY_MULTIPLIERS[rarity]

    # 5% growth per level, applied to base stats.
    level_multiplier = 1 + (level - 1) * 0.05

    multiplier = rarity_multiplier * level_multiplier

    return CombatStats(
        hp=round(base.hp * multiplier),
        atk=round(base.atk * multiplier),
        defense=round(base.defense * multiplier),
        speed=round(base.speed * multiplier),
    )
