from __future__ import annotations

from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PlayerDistributionBoundaryTests(unittest.TestCase):
    def test_player_entrypoint_uses_ranch_manager_not_developer_manager(self) -> None:
        source = (PROJECT_ROOT / "launcher.py").read_text(encoding="utf-8")
        self.assertIn("kadoka_quest.apps.ranch_manager", source)
        self.assertNotIn("kadoka_quest.apps.manage", source)
        self.assertNotIn("block_editor", source)
        self.assertNotIn("map_editor", source)
        self.assertNotIn("monster_editor", source)
        self.assertNotIn("data_creator", source)

    def test_player_ranch_has_no_creation_import_or_simulation_dependencies(self) -> None:
        source = (PROJECT_ROOT / "src/kadoka_quest/apps/ranch_manager.py").read_text(encoding="utf-8")
        for forbidden in ("BattleEngine", "IMPORT_ROOT", "discover_external", "acquire_from_scan", "def create("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
