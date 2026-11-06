
from combat.engine import Fighter, Battle
from combat.stats import calculate_stats


crazy_bao = Fighter(
    instance_id=101,
    name="Crazy Bao",
    stats=calculate_stats(
        rarity="epic",
        archetype="glass_cannon",
        level=5,
    ),
)

cow_bao = Fighter(
    instance_id=102,
    name="Cow Bao",
    stats=calculate_stats(
        rarity="epic",
        archetype="tank",
        level=5,
    ),
)

battle = Battle(crazy_bao, cow_bao)

print("\n🥟 BAO BATTLES 🥟")
print(battle.log[-1])

while battle.status == "active":
    current = battle.current_turn
    fighter = battle.fighters[current]

    # Very basic AI: Cow Bao defends on its first turn.
    if fighter.name == "Cow Bao" and battle.turn_count == 1:
        action = "defend"
    else:
        action = "attack"

    state = battle.take_action(current, action)

    print(battle.log[-1])

    for f in state["fighters"]:
        print(f"  {f['name']}: {f['hp']}/{f['max_hp']} HP")

    print()

print("Final result:", battle.status)

if battle.winner is not None:
    print("Winner:", battle.fighters[battle.winner].name)

import unittest

from combat.engine import Battle, Fighter
from combat.stats import CombatStats


def fighter(instance_id, name, hp, atk, defense, speed):
    return Fighter(
        instance_id=instance_id,
        name=name,
        stats=CombatStats(
            hp=hp,
            atk=atk,
            defense=defense,
            speed=speed,
        ),
    )


class TestBattle(unittest.TestCase):

    def setUp(self):
        self.fast = fighter(1, "Fast Bao", 200, 100, 0, 80)
        self.slow = fighter(2, "Slow Bao", 200, 50, 0, 30)
        self.battle = Battle(self.fast, self.slow)

    def test_speed_determines_first_turn(self):
        self.assertEqual(self.battle.current_turn, 0)

    def test_attack_reduces_hp(self):
        state = self.battle.take_action(0, "attack")
        self.assertEqual(state["fighters"][1]["hp"], 100)

    def test_turns_alternate(self):
        self.battle.take_action(0, "attack")
        self.assertEqual(self.battle.current_turn, 1)

    def test_cannot_act_out_of_turn(self):
        with self.assertRaises(ValueError):
            self.battle.take_action(1, "attack")

    def test_defend_reduces_next_hit(self):
        self.battle.take_action(0, "defend")
        state = self.battle.take_action(1, "attack")

        self.assertEqual(state["fighters"][0]["hp"], 175)
        self.assertFalse(state["fighters"][0]["defending"])

    def test_victory(self):
        self.battle.take_action(0, "attack")
        self.battle.take_action(1, "attack")
        state = self.battle.take_action(0, "attack")

        self.assertEqual(state["status"], "finished")
        self.assertEqual(state["winner"], 0)

    def test_no_actions_after_victory(self):
        self.battle.take_action(0, "attack")
        self.battle.take_action(1, "attack")
        self.battle.take_action(0, "attack")

        with self.assertRaises(ValueError):
            self.battle.take_action(1, "attack")

    def test_original_fighters_unchanged(self):
        self.battle.take_action(0, "attack")
        self.assertEqual(self.slow.current_hp, 200)


if __name__ == "__main__":
    unittest.main()
