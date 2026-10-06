# {
#   責務: [test_engine_boundaries: test・ルール処理・boundariesの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import ast
from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_engine.data_validator import DataValidator
from kadoka_engine.field_engine import FieldEngine
from kadoka_engine.fixed_mob_controller import FixedMobController
from kadoka_engine.grid_movement import GridMovement
from kadoka_engine.hidden_enemy_controller import HiddenEnemyController
from kadoka_engine.player_field_controller import PlayerFieldController
from kadoka_quest.data.data_validator import DataValidator as LegacyDataValidator
from kadoka_quest.core.field_engine import FieldEngine as LegacyFieldEngine
from kadoka_quest.core.fixed_mob_controller import FixedMobController as LegacyFixedMobController
from kadoka_quest.core.grid_movement import GridMovement as LegacyGridMovement
from kadoka_quest.core.hidden_enemy_controller import HiddenEnemyController as LegacyHiddenEnemyController
from kadoka_quest.core.player_field_controller import PlayerFieldController as LegacyPlayerFieldController


# {
#   責務: [EngineBoundaryTests: ルール処理・boundary・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class EngineBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_engine_package_does_not_import_game_or_pygame: 検証: engine package does not import game or pygame]
    #   処理: [1: 検証: engine package does not import game or pygame]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_engine_package_does_not_import_game_or_pygame(self) -> None:
        engine_root = PROJECT_ROOT / "src" / "kadoka_engine"
        imported_roots: set[str] = set()
        for path in engine_root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported_roots.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported_roots.add(node.module.split(".")[0])
        self.assertNotIn("kadoka_quest", imported_roots)
        self.assertNotIn("pygame", imported_roots)

    # {
    #   責務: [test_engine_validator_requires_project_data_from_caller: 検証: engine validator requires project data from caller]
    #   処理: [1: 検証: engine validator requires project data from caller]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_engine_validator_requires_project_data_from_caller(self) -> None:
        validator = DataValidator(PROJECT_ROOT / "data")
        self.assertEqual(validator.root, PROJECT_ROOT / "data")
        self.assertEqual(validator.validate(), [])

    # {
    #   責務: [test_legacy_game_import_keeps_default_data_root: 検証: legacy game import keeps default data root]
    #   処理: [1: 検証: legacy game import keeps default data root]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_legacy_game_import_keeps_default_data_root(self) -> None:
        self.assertEqual(LegacyDataValidator().validate(), [])

    # {
    #   責務: [test_legacy_field_imports_are_exact_engine_types: 検証: legacy field imports are exact engine types]
    #   処理: [1: 検証: legacy field imports are exact engine types]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_legacy_field_imports_are_exact_engine_types(self) -> None:
        self.assertIs(LegacyFieldEngine, FieldEngine)
        self.assertIs(LegacyFixedMobController, FixedMobController)
        self.assertIs(LegacyGridMovement, GridMovement)
        self.assertIs(LegacyHiddenEnemyController, HiddenEnemyController)
        self.assertIs(LegacyPlayerFieldController, PlayerFieldController)


if __name__ == "__main__":
    unittest.main()
