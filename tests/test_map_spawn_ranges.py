# {
#   責務: [test_map_spawn_ranges: test・マップ・出現・rangesの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from pathlib import Path
import sys
import unittest

import pygame


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_quest.apps.map_editor import MapEditor


# {
#   責務: [MapSpawnRangeTests: マップ・出現・range・testsの状態と振る舞いを担当する]
#   フィールド: [editor: editor]
# }
class MapSpawnRangeTests(unittest.TestCase):
    # {
    #   責務: [setUpClass: 検証に必要な専用fixtureと依存を準備する]
    #   処理: [1: 検証に必要な専用fixtureと依存を準備する]
    #   引数: [cls: 対象クラス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((1, 1))

    # {
    #   責務: [tearDownClass: 検証用fixtureと一時的な変更を後始末する]
    #   処理: [1: 検証用fixtureと一時的な変更を後始末する]
    #   引数: [cls: 対象クラス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    # {
    #   責務: [setUp: 検証に必要な専用fixtureと依存を準備する]
    #   処理: [1: 検証に必要な専用fixtureと依存を準備する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def setUp(self) -> None:
        self.editor = MapEditor()

    # {
    #   責務: [select_species: 種族を選択する]
    #   処理: [1: 種族を選択する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     species_id: 種族・識別子（str）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def select_species(self, species_id: str) -> None:
        self.editor.select_species(self.editor.species_ids.index(species_id))

    # {
    #   責務: [test_editing_existing_spawn_range_updates_the_same_entry: 検証: editing existing spawn range updates the same entry]
    #   処理: [1: 検証: editing existing spawn range updates the same entry]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_editing_existing_spawn_range_updates_the_same_entry(self) -> None:
        spawn = next(item for item in self.editor.map_data["spawns"] if item["species_id"] != "ball_slime")
        self.select_species(spawn["species_id"])
        self.editor.open_spawn_dialog()

        self.assertEqual(self.editor.spawn_min_level.value, str(spawn["min_level"]))
        self.assertEqual(self.editor.spawn_max_level.value, str(spawn["max_level"]))
        self.editor.spawn_min_level.value = "7"
        self.editor.spawn_max_level.value = "12"

        self.assertTrue(self.editor.apply_spawn_range())
        self.assertEqual(spawn["min_level"], 7)
        self.assertEqual(spawn["max_level"], 12)
        self.assertTrue(self.editor.dirty)

    # {
    #   責務: [test_range_can_add_missing_species_and_reject_invalid_order: 検証: range can add missing species and reject invalid order]
    #   処理: [1: 検証: range can add missing species and reject invalid order]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_range_can_add_missing_species_and_reject_invalid_order(self) -> None:
        existing = {item["species_id"] for item in self.editor.map_data["spawns"]}
        species_id = next(species for species in self.editor.species_ids if species not in existing and species != "ball_slime")
        self.select_species(species_id)
        self.editor.open_spawn_dialog()
        self.editor.spawn_min_level.value = "20"
        self.editor.spawn_max_level.value = "30"

        self.assertTrue(self.editor.apply_spawn_range())
        spawn = self.editor.current_spawn
        self.assertEqual(spawn, {"species_id": species_id, "weight": 10, "min_level": 20, "max_level": 30})

        self.editor.spawn_min_level.value = "31"
        self.editor.spawn_max_level.value = "30"
        self.assertFalse(self.editor.apply_spawn_range())
        self.assertEqual(self.editor.current_spawn["min_level"], 20)
        self.assertEqual(self.editor.current_spawn["max_level"], 30)

    # {
    #   責務: [test_ball_slime_cannot_be_added_from_level_range_dialog: 検証: ball slime cannot be added from level range dialog]
    #   処理: [1: 検証: ball slime cannot be added from level range dialog]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_ball_slime_cannot_be_added_from_level_range_dialog(self) -> None:
        self.select_species("ball_slime")
        self.editor.open_spawn_dialog()
        self.editor.spawn_min_level.value = "1"
        self.editor.spawn_max_level.value = "100"

        self.assertFalse(self.editor.apply_spawn_range())
        self.assertIsNone(self.editor.current_spawn)


if __name__ == "__main__":
    unittest.main()
