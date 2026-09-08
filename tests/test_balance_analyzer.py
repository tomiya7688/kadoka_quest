from __future__ import annotations

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_quest.data.repository import GameRepository
from kadoka_quest.devtools.balance_analyzer import BalanceAnalyzer, BalanceSettings


class BalanceAnalyzerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = GameRepository(PROJECT_ROOT / "data")

    def test_same_seed_produces_the_same_non_learning_report(self) -> None:
        settings = BalanceSettings(levels=(10,), battles_per_pair=4, seed=123, max_rounds=40)
        first = BalanceAnalyzer(self.repository, settings).analyze(["ghost", "slime"])
        second = BalanceAnalyzer(self.repository, settings).analyze(["ghost", "slime"])

        self.assertEqual(first, second)
        self.assertFalse(first["learning_enabled"])
        self.assertEqual(len(first["matchups"]), 1)
        self.assertEqual(first["matchups"][0]["battles"], 4)
        self.assertEqual(len(first["matchups"][0]["history"]), 4)
        self.assertEqual(first["matchups"][0]["history"][0]["battle_index"], 1)
        self.assertEqual(sum(row["matches"] for row in first["rankings"]), 8)

    def test_recommendations_use_level_100_as_the_tuning_anchor(self) -> None:
        settings = BalanceSettings(levels=(100,), battles_per_pair=20, seed=5, max_rounds=40)
        report = BalanceAnalyzer(self.repository, settings).analyze(["metal_slime", "slime"])

        self.assertTrue(report["level_100_anchor"])
        self.assertTrue(report["recommendations"])
        for recommendation in report["recommendations"]:
            self.assertEqual(recommendation["anchor_level"], 100)
            self.assertIn(recommendation["confidence"], {"low", "medium", "high"})
            self.assertIn(recommendation["stat_candidate"]["direction"], {"increase", "decrease"})

    def test_invalid_settings_and_unknown_species_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            BalanceSettings(levels=(0,))
        with self.assertRaises(ValueError):
            BalanceAnalyzer(self.repository).analyze(["slime", "missing"])


if __name__ == "__main__":
    unittest.main()
