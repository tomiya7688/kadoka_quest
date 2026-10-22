# {
#   責務: [test_balance_analyzer: test・balance・analyzerの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_quest.data.repository import GameRepository
from kadoka_quest.devtools.balance_analyzer import BalanceAnalyzer, BalanceSettings


# {
#   責務: [BalanceAnalyzerTests: balance・analyzer・testsの状態と振る舞いを担当する]
#   フィールド: [repository: データ取得先]
# }
class BalanceAnalyzerTests(unittest.TestCase):
    # {
    #   責務: [setUp: 検証に必要な専用fixtureと依存を準備する]
    #   処理: [1: 検証に必要な専用fixtureと依存を準備する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def setUp(self) -> None:
        self.repository = GameRepository(PROJECT_ROOT / "data")

    # {
    #   責務: [test_same_seed_produces_the_same_non_learning_report: 検証: same seed produces the same non learning report]
    #   処理: [1: 検証: same seed produces the same non learning report]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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

    # {
    #   責務: [test_recommendations_use_level_100_as_the_tuning_anchor: 検証: recommendations use level 100 as the tuning anchor]
    #   処理: [1: 検証: recommendations use level 100 as the tuning anchor]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_recommendations_use_level_100_as_the_tuning_anchor(self) -> None:
        settings = BalanceSettings(levels=(100,), battles_per_pair=20, seed=5, max_rounds=40)
        report = BalanceAnalyzer(self.repository, settings).analyze(["metal_slime", "slime"])

        self.assertTrue(report["level_100_anchor"])
        self.assertTrue(report["recommendations"])
        for recommendation in report["recommendations"]:
            self.assertEqual(recommendation["anchor_level"], 100)
            self.assertIn(recommendation["confidence"], {"low", "medium", "high"})
            self.assertIn(recommendation["stat_candidate"]["direction"], {"increase", "decrease"})

    # {
    #   責務: [test_invalid_settings_and_unknown_species_are_rejected: 検証: invalid settings and unknown species are rejected]
    #   処理: [1: 検証: invalid settings and unknown species are rejected]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_invalid_settings_and_unknown_species_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            BalanceSettings(levels=(0,))
        with self.assertRaises(ValueError):
            BalanceAnalyzer(self.repository).analyze(["slime", "missing"])


if __name__ == "__main__":
    unittest.main()
