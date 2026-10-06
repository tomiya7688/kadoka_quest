# {
#   責務: [test_simulation_manager: test・simulation・managerの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))


# {
#   責務: [SimulationManagerTests: simulation・manager・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class SimulationManagerTests(unittest.TestCase):
    # {
    #   責務: [test_player_ui_uses_the_isolated_facility_service: 検証: player ui uses the isolated facility service]
    #   処理: [1: 検証: player ui uses the isolated facility service]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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
