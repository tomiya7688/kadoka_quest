from __future__ import annotations

import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))


class SimulationManagerTests(unittest.TestCase):
    def test_player_ui_uses_the_isolated_facility_service(self) -> None:
        source = (PROJECT_ROOT / "src/kadoka_quest/apps/simulation_manager.py").read_text(encoding="utf-8")
        self.assertIn("SimulationRosterService", source)
        self.assertIn("IMPORT_ROOT / \"simulation\"", source)
        self.assertIn("SAVE_ROOT / \"simulation\"", source)
        self.assertNotIn("StateStore", source)
        self.assertNotIn("PartyStore", source)
        self.assertNotIn("MonsterStore", source)


if __name__ == "__main__":
    unittest.main()
