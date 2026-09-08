from __future__ import annotations

from pathlib import Path
import sys
import unittest

import pygame


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_quest.apps.map_editor import MapEditor


class MapSpawnRangeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def setUp(self) -> None:
        self.editor = MapEditor()

    def select_species(self, species_id: str) -> None:
        self.editor.select_species(self.editor.species_ids.index(species_id))

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

    def test_ball_slime_cannot_be_added_from_level_range_dialog(self) -> None:
        self.select_species("ball_slime")
        self.editor.open_spawn_dialog()
        self.editor.spawn_min_level.value = "1"
        self.editor.spawn_max_level.value = "100"

        self.assertFalse(self.editor.apply_spawn_range())
        self.assertIsNone(self.editor.current_spawn)


if __name__ == "__main__":
    unittest.main()
