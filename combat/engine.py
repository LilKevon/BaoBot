
from dataclasses import dataclass
from typing import Optional

from combat.stats import CombatStats


MAX_TURNS = 100


@dataclass
class Fighter:
    instance_id: int
    name: str
    stats: CombatStats
    current_hp: Optional[int] = None
    defending: bool = False

    def __post_init__(self):
        if self.current_hp is None:
            self.current_hp = self.stats.hp

        if self.stats.hp <= 0:
            raise ValueError("Maximum HP must be positive.")

        if not 0 <= self.current_hp <= self.stats.hp:
            raise ValueError("Invalid starting HP.")


class Battle:
    def __init__(self, fighter1: Fighter, fighter2: Fighter):
        if fighter1.instance_id == fighter2.instance_id:
            raise ValueError("A card cannot fight itself.")

  
        self.fighters = [
            Fighter(
                instance_id=f.instance_id,
                name=f.name,
                stats=f.stats,
                current_hp=f.current_hp,
                defending=f.defending,
            )
            for f in (fighter1, fighter2)
        ]


        self.current_turn = (
            0 if fighter1.stats.speed >= fighter2.stats.speed
            else 1
        )

        self.turn_count = 0
        self.status = "active"
        self.winner = None
        self.log = []

        first = self.fighters[self.current_turn]
        self.log.append(f"⚔️ {first.name} moves first!")

    def _calculate_damage(self, attacker, defender):
        """
        Defense reduces incoming damage with
        diminishing returns.
        """
        attack = max(0, attacker.stats.atk)
        defense = max(0, defender.stats.defense)

        damage = round(
            attack * 100 / (100 + defense)
        )

        if defender.defending:
            damage = round(damage * 0.5)

        return max(1, damage)

    def take_action(self, fighter_index: int, action: str):
        if self.status != "active":
            raise ValueError("This battle has already ended.")

        if fighter_index not in (0, 1):
            raise ValueError("Invalid fighter index.")

        if fighter_index != self.current_turn:
            raise ValueError("It is not this fighter's turn.")

        if action not in ("attack", "defend"):
            raise ValueError("Unknown combat action.")

        attacker = self.fighters[fighter_index]
        defender_index = 1 - fighter_index
        defender = self.fighters[defender_index]

        if action == "attack":
            damage = self._calculate_damage(
                attacker,
                defender
            )

            defender.current_hp = max(
                0,
                defender.current_hp - damage
            )


            defender.defending = False

            self.log.append(
                f"⚔️ {attacker.name} attacks "
                f"{defender.name} for {damage} damage!"
            )

        elif action == "defend":
            attacker.defending = True

            self.log.append(
                f"🛡️ {attacker.name} braces for an attack!"
            )

        self.turn_count += 1

        if defender.current_hp == 0:
            self.status = "finished"
            self.winner = fighter_index

            self.log.append(
                f"🏆 {attacker.name} wins the battle!"
            )

        elif self.turn_count >= MAX_TURNS:
            self.status = "draw"
            self.log.append(
                "🤝 Battle ended in a draw "
                "(turn limit reached)."
            )

        else:
            self.current_turn = defender_index

        return self.get_state()

    def get_state(self):
        return {
            "status": self.status,
            "current_turn": (
                self.current_turn
                if self.status == "active"
                else None
            ),
            "turn_count": self.turn_count,
            "winner": self.winner,
            "fighters": [
                {
                    "instance_id": f.instance_id,
                    "name": f.name,
                    "hp": f.current_hp,
                    "max_hp": f.stats.hp,
                    "atk": f.stats.atk,
                    "defense": f.stats.defense,
                    "speed": f.stats.speed,
                    "defending": f.defending,
                }
                for f in self.fighters
            ],
            "log": self.log.copy(),
        }
