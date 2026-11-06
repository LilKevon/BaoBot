
import unittest

from combat.stats import calculate_stats, MAX_LEVEL


class TestCombatStats(unittest.TestCase):

    def test_base_stats(self):
        stats = calculate_stats(
            rarity="common",
            archetype="balanced",
            level=1,
        )

        self.assertEqual(stats.hp, 500)
        self.assertEqual(stats.atk, 75)
        self.assertEqual(stats.defense, 55)
        self.assertEqual(stats.speed, 50)

    def test_rarity_increases_stats(self):
        common = calculate_stats(
            "common", "bruiser", 1
        )

        legendary = calculate_stats(
            "legendary", "bruiser", 1
        )

        self.assertGreater(legendary.hp, common.hp)
        self.assertGreater(legendary.atk, common.atk)

    def test_level_increases_stats(self):
        level_1 = calculate_stats(
            "rare", "assassin", 1
        )

        level_20 = calculate_stats(
            "rare", "assassin", MAX_LEVEL
        )

        self.assertGreater(level_20.hp, level_1.hp)
        self.assertGreater(level_20.atk, level_1.atk)

    def test_invalid_level(self):
        with self.assertRaises(ValueError):
            calculate_stats("common", "balanced", 21)

    def test_deterministic_stats(self):
        first = calculate_stats("epic", "tank", 10)
        second = calculate_stats("epic", "tank", 10)

        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
