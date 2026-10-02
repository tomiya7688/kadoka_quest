"""Execute the real Godot port against the Python reference; never substitute results."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import unittest

from kadoka_engine.field_engine import FieldEngine
from kadoka_quest.data.field_data import FieldDataLoader
from kadoka_quest.data.repository import GameRepository

ROOT = Path(__file__).resolve().parents[1]
GODOT = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")


def content_digest(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for directory in ("data", "assets", "savedata")
        for path in (root / directory).rglob("*")
        if path.is_file()
    }


def run_godot(script: str, content_root: Path, fixture: Path | None = None) -> dict:
    command = [str(GODOT), "--headless", "--path", str(ROOT / "gdscript"), "--script", script]
    if fixture is not None:
        command.extend(["--", str(fixture)])
    environment = dict(os.environ, KADOKA_CONTENT_ROOT=str(content_root), KADOKA_SAVE_DIR=str(content_root / "savedata"))
    completed = subprocess.run(
        command, cwd=content_root, env=environment, text=True, encoding="utf-8",
        errors="replace", capture_output=True, timeout=30, check=False,
    )
    if completed.returncode or "SCRIPT ERROR" in completed.stderr or "ERROR:" in completed.stderr:
        raise AssertionError(f"Godot failed ({completed.returncode}):\n{completed.stdout[-1000:]}\n{completed.stderr}")
    prefix = "KADOKA_SCENE_RESULT=" if "scene" in script else "KADOKA_CONTRACT_RESULT="
    for line in completed.stdout.splitlines():
        if line.startswith(prefix):
            # Windows Godot console output can use the active ANSI codepage.
            # The engine emits an ASCII envelope around UTF-8 JSON, not lossy text.
            return json.loads(base64.b64decode(line[len(prefix):]).decode("utf-8"))
    raise AssertionError(f"No real-engine result: {completed.stdout}\n{completed.stderr}")


class GDScriptLayoutTests(unittest.TestCase):
    def test_language_boundaries_and_launchable_scene_exist(self) -> None:
        for relative in (
            "python/README.md", "unity/README.md", "gdscript/README.md",
            "gdscript/project.godot", "gdscript/scenes/field.tscn",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)
        settings = (ROOT / "gdscript/project.godot").read_text(encoding="utf-8")
        self.assertIn('run/main_scene="res://scenes/field.tscn"', settings)

    def test_rules_do_not_access_files_input_or_rendering(self) -> None:
        source = (ROOT / "gdscript/engine/field_engine.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess.", "DirAccess.", "Input.", "draw_", "get_tree(", "extends Node"):
            self.assertNotIn(forbidden, source)
        self.assertIn("extends RefCounted", source)


@unittest.skipUnless(GODOT, "Set KADOKA_GODOT_EXECUTABLE to execute the real GDScript port")
class GDScriptRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="kadoka-gdscript-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.content = Path(cls.temporary.name)
        shutil.copytree(ROOT / "data", cls.content / "data")
        shutil.copytree(ROOT / "assets", cls.content / "assets")
        (cls.content / "savedata").mkdir()
        (cls.content / "savedata/sentinel.json").write_text('{"untouched": true}', encoding="utf-8")
        cls.before = content_digest(cls.content)
        cls.repository = GameRepository(cls.content / "data")
        cls.loader = FieldDataLoader(cls.repository)
        cls.blocks = cls.loader.blocks()
        cls.map_ids = cls.repository.list_maps()
        cls.maps = {map_id: cls.loader.load_map(map_id)["map"] for map_id in cls.map_ids}
        cls.cases: list[dict] = []
        cls.expected: list[dict] = []
        cls.groups: dict[str, list[int]] = {}

        def add(
            group: str, world: dict, operation: str, args: list,
            visible: list | None = None, hidden: list | None = None,
        ) -> None:
            rules = FieldEngine(world, cls.blocks)
            operations = {
                "move": lambda: rules.resolve_player_move(*args, visible or [], hidden or []),
                "front": lambda: list(rules.front_position(*args)),
                "transition": lambda: rules.step_transition_at(*args),
                "nearby": lambda: rules.nearby_event(*args),
                "tile": lambda: rules.tile_allows(*args),
                "path": lambda: rules.has_clear_axis_path(*args),
            }
            cls.groups.setdefault(group, []).append(len(cls.cases))
            cls.expected.append({"value": operations[operation](), "mutated": False})
            cls.cases.append({
                "map": world, "blocks": cls.blocks, "operation": operation,
                "args": args, "visible": visible or [], "hidden": hidden or [],
            })

        world = {"width": 3, "height": 3, "tiles": [["path"] * 3 for _ in range(3)], "events": []}
        add("collision", world, "move", [0, 0, -1, 0, "front"])
        add("collision", world, "move", [0, 0, 1, 0, "front"])
        character = {"id": "mob", "x": 1, "y": 0}
        add("collision", world, "move", [0, 0, 1, 0, "front"], [character])
        add("collision", world, "move", [0, 0, 1, 0, "front"], [character], [dict(character, id="hidden")])
        wall = dict(world, tiles=[["path", "wall", "missing"]] + world["tiles"][1:])
        add("collision", wall, "move", [0, 0, 1, 0, "front"])
        add("collision", wall, "move", [1, 0, 1, 0, "front"])
        blocked = dict(world, events=[{
            "id": "rock", "x": 1, "y": 0, "blocking": True,
            "type": "transition", "activation": "interact",
        }])
        add("collision", blocked, "move", [0, 0, 1, 0, "front"])
        add("collision", blocked, "move", [0, 0, 1, 0, "front"], [character])
        rng = random.Random(111)
        for map_data in cls.maps.values():
            for _ in range(48):
                x, y = rng.randrange(map_data["width"]), rng.randrange(map_data["height"])
                dx, dy = rng.choice([(-1, 0), (1, 0), (0, -1), (0, 1)])
                add("maps", map_data, "move", [x, y, dx, dy, "front"], map_data.get("fixed_mobs", []))
            for event in map_data.get("events", []):
                add("events", map_data, "transition", [event["x"], event["y"]])
                add("events", map_data, "nearby", [event["x"], event["y"]])
            add("events", map_data, "nearby", [-100, -100])
        for direction in ("front", "left", "right", "back", "unknown"):
            add("queries", world, "front", [1, 1, direction])
        for args in ((0, 0, "player_walkable"), (1, 0, "player_walkable"), (-1, 0, "enemy_walkable"), (0, 1, "missing")):
            add("queries", wall, "tile", list(args))
        for start, target in (
            ([0, 0], [2, 0]), ([0, 1], [2, 1]), ([0, 0], [0, 2]),
            ([0, 0], [2, 2]), ([0, 0], [0, 0]), ([2, 1], [0, 1]),
        ):
            add("queries", wall, "path", [start, target, "player_walkable"])
        fixture = cls.content / "contracts.json"
        payload = {"root": str(cls.content).replace("\\", "/"), "cases": cls.cases, "map_ids": cls.map_ids}
        fixture.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        cls.actual = run_godot("res://tests/run_contracts.gd", cls.content, fixture)
        cls.scene = run_godot("res://tests/run_scene_smoke.gd", cls.content)

    def assert_group(self, group: str) -> None:
        for index in self.groups[group]:
            with self.subTest(case=index, operation=self.cases[index]["operation"]):
                self.assertEqual(self.actual["results"][index], self.expected[index])

    def test_collision_priority_matches_python(self) -> None:
        self.assert_group("collision")

    def test_sampled_moves_on_every_canonical_map_match_python(self) -> None:
        self.assert_group("maps")

    def test_event_activation_and_nearby_selection_match_python(self) -> None:
        self.assert_group("events")

    def test_front_tile_and_axis_path_queries_match_python(self) -> None:
        self.assert_group("queries")

    def test_json_blocks_maps_extra_events_and_species_match_python(self) -> None:
        self.assertEqual(self.actual["blocks"], self.blocks)
        self.assertEqual(self.actual["maps"], self.maps)
        self.assertEqual(self.actual["hero"], self.repository.get_species("hero").definition)

    def test_repository_rejects_path_traversal(self) -> None:
        for result in self.actual["invalid_ids"]:
            self.assertEqual(result["value"], {})
            self.assertTrue(result["error"].startswith("Invalid map id"))

    def test_session_preserves_step_interact_and_mob_blocking(self) -> None:
        sessions = self.actual["sessions"]
        self.assertEqual(sessions["edge"]["event"]["target"]["map_id"], "greenwood")
        self.assertEqual(sessions["rock"]["reason"], "blocking_event")
        self.assertEqual(sessions["rock_interaction"]["target"]["map_id"], "ghost_home")
        self.assertEqual(sessions["mob"]["reason"], "visible_character")

    def test_real_keyboard_press_repeat_release(self) -> None:
        self.assertEqual(self.actual["repeats"], [[1, 0], [0, 0], [1, 0], [0, 0]])

    def test_production_scene_moves_and_transitions_through_input(self) -> None:
        self.assertEqual(self.scene["initial"], "starting_town")
        self.assertEqual(self.scene["start"], [18, 14])
        self.assertEqual(self.scene["moved"], [19, 14, "right"])
        self.assertEqual(self.scene["crossed"], "greenwood")
        self.assertEqual(self.scene["interacted"], "ghost_home")
        self.assertEqual(self.scene["image_width"], 64)
        self.assertEqual(self.scene["filter"], 1)  # CanvasItem.TEXTURE_FILTER_NEAREST

    def test_invalid_transition_keeps_world_and_displays_error(self) -> None:
        self.assertFalse(self.scene["invalid_success"])
        self.assertTrue(self.scene["stable_world"])
        self.assertTrue(self.scene["error_visible"])

    def test_readonly_content_and_save_sentinel_unchanged(self) -> None:
        self.assertEqual(content_digest(self.content), self.before)


if __name__ == "__main__":
    unittest.main()
