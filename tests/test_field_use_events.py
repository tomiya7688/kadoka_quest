from __future__ import annotations

import unittest
from pathlib import Path
import sys
import shutil
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_quest.apps.field_event_app import FieldEventApplication
from kadoka_quest.apps.map_editor import MapEditor
from kadoka_quest.data.repository import GameRepository


class FieldUseEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.events = [
            {
                "id": "sealed_spring",
                "type": "use_requirement",
                "x": 4,
                "y": 5,
                "radius": 1,
                "required": {"kind": "item", "id": "spring_key"},
                "effect": {"kind": "gain_item", "item": "clear_water", "status": "水が手に入った。"},
            }
        ]

    def test_only_matching_item_at_the_configured_range_triggers(self) -> None:
        app = FieldEventApplication()
        matched = app.resolve_use(self.events, (3, 5), "item", "spring_key")
        self.assertEqual(matched["kind"], "gain_item")
        self.assertEqual(matched["item"], "clear_water")
        self.assertEqual(app.resolve_use(self.events, (3, 5), "skill", "spring_key")["kind"], "none")
        self.assertEqual(app.resolve_use(self.events, (1, 5), "item", "spring_key")["kind"], "none")

    def test_map_editor_adds_edits_and_deletes_plain_event_data(self) -> None:
        editor = MapEditor()
        self.assertTrue(editor.add_use_event_at(1, 1))
        editor.use_event_id.value = "test_use"
        editor.use_required_id.value = "spring_key"
        editor.use_effect_text.value = "開いた。"
        self.assertTrue(editor.apply_use_event())
        event = editor.current_use_event
        self.assertEqual(event["required"], {"kind": "item", "id": "spring_key"})
        self.assertEqual(event["effect"]["kind"], "message")
        editor.delete_use_event()
        self.assertEqual(editor.use_events, [])

    def test_map_editor_save_and_reload_keeps_use_event(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "data"
            shutil.copytree(PROJECT_ROOT / "data", root)
            repository = GameRepository(root)
            editor = MapEditor(repository)
            self.assertTrue(editor.add_use_event_at(1, 1))
            editor.use_event_id.value = "saved_use"
            editor.use_required_id.value = "spring_key"
            self.assertTrue(editor.apply_use_event())
            editor.save()
            saved = GameRepository(root).get_map(editor.map_id)
            event = next(item for item in saved["events"] if item["id"] == "saved_use")
            self.assertEqual(event["required"]["id"], "spring_key")


if __name__ == "__main__":
    unittest.main()
