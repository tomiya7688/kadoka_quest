# {
#   責務: [test_battle_decision_explanation: test・戦闘・decision・explanationの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_quest.core.battle_decision_explanation import BattleDecisionExplanation


# {
#   責務: [BattleDecisionExplanationTests: 戦闘・decision・explanation・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class BattleDecisionExplanationTests(unittest.TestCase):
    # {
    #   責務: [test_includes_only_active_learning_reasons_for_selected_skill: 検証: includes only active learning reasons for selected skill]
    #   処理: [1: 検証: includes only active learning reasons for selected skill]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_includes_only_active_learning_reasons_for_selected_skill(self) -> None:
        ai = {
            "tactic": "careful",
            "action_preferences": {"heal": 0.4, "attack": 0.9},
            "context_preferences": {"self:hurt": {"heal": 0.5}, "mp:low": {"heal": -0.2}},
        }
        explanation = BattleDecisionExplanation.describe(
            ai, {"id": "heal"}, ("self:hurt", "numbers:even")
        )
        self.assertIn("戦術:careful", explanation)
        self.assertIn("習熟:+0.40", explanation)
        self.assertIn("状況:self:hurt +0.50", explanation)
        self.assertNotIn("mp:low", explanation)

    # {
    #   責務: [test_default_ai_has_a_safe_non_learning_explanation: 検証: default ai has a safe non learning explanation]
    #   処理: [1: 検証: default ai has a safe non learning explanation]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_default_ai_has_a_safe_non_learning_explanation(self) -> None:
        self.assertEqual(
            BattleDecisionExplanation.describe({}, {"id": "attack"}, ()),
            "AI判断 戦術:balanced",
        )


if __name__ == "__main__":
    unittest.main()
