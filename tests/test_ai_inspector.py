from __future__ import annotations

from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_quest.apps.ai_inspector import AiInspector


class AiInspectorTests(unittest.TestCase):
    def test_summary_orders_strongest_learned_preferences_without_mutating_ai(self) -> None:
        ai = {
            "profile": "normal", "tactic": "aggressive", "battles": 4, "actions": 12,
            "action_preferences": {"heal": 0.2, "attack": -0.8, "zap": 0.6},
            "context_preferences": {"self:hurt": {"heal": 0.5, "guard": -0.7}},
            "context_actions": {"self:hurt": 8},
        }
        summary = AiInspector.summarize(ai, limit=2)
        self.assertEqual(summary["action_preferences"][0], {"skill_id": "attack", "score": -0.8})
        self.assertEqual(summary["context_preferences"][0]["skill_id"], "guard")
        self.assertEqual(summary["context_preferences"][0]["actions"], 8)
        self.assertEqual(ai["action_preferences"]["attack"], -0.8)

    def test_empty_or_malformed_learning_data_is_safe(self) -> None:
        summary = AiInspector.summarize({"context_preferences": {"broken": []}})
        self.assertEqual(summary["action_preferences"], [])
        self.assertEqual(summary["context_preferences"], [])


if __name__ == "__main__":
    unittest.main()
