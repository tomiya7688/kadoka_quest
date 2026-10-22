# {
#   責務: [test_player_distribution_boundary: test・主人公・distribution・boundaryの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


# {
#   責務: [PlayerDistributionBoundaryTests: 主人公・distribution・boundary・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class PlayerDistributionBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_player_entrypoint_uses_ranch_manager_not_developer_manager: 検証: player entrypoint uses ranch manager not developer manager]
    #   処理: [1: 検証: player entrypoint uses ranch manager not developer manager]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_player_entrypoint_uses_ranch_manager_not_developer_manager(self) -> None:
        source = (PROJECT_ROOT / "launcher.py").read_text(encoding="utf-8")
        self.assertIn("kadoka_quest.apps.ranch_manager", source)
        self.assertNotIn("kadoka_quest.apps.manage", source)
        self.assertNotIn("block_editor", source)
        self.assertNotIn("map_editor", source)
        self.assertNotIn("monster_editor", source)
        self.assertNotIn("data_creator", source)

    # {
    #   責務: [test_player_ranch_has_no_creation_import_or_simulation_dependencies: 検証: player ranch has no creation import or simulation dependencies]
    #   処理: [1: 検証: player ranch has no creation import or simulation dependencies]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_player_ranch_has_no_creation_import_or_simulation_dependencies(self) -> None:
        source = (PROJECT_ROOT / "src/kadoka_quest/apps/ranch_manager.py").read_text(encoding="utf-8")
        for forbidden in ("BattleEngine", "IMPORT_ROOT", "discover_external", "acquire_from_scan", "def create("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
