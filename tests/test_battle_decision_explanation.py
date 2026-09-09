from __future__ import annotations

from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_quest.core.battle_decision_explanation import BattleDecisionExplanation


class BattleDecisionExplanationTests(unittest.TestCase):
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

    def test_default_ai_has_a_safe_non_learning_explanation(self) -> None:
        self.assertEqual(
            BattleDecisionExplanation.describe({}, {"id": "attack"}, ()),
            "AI判断 戦術:balanced",
        )


if __name__ == "__main__":
    unittest.main()
