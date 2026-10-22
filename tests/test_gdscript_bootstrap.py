"""Execute the real Godot port against the Python reference; never substitute results."""
# {
#   責務: [test_gdscript_bootstrap: Execute the real Godot port against the Python reference; never substitute results.]
#   フィールド: []
# }
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


# {
#   責務: [content_digest: test・gdscript・bootstrapのcontent・digestを求める]
#   処理: [1: test・gdscript・bootstrapのcontent・digestを求める]
#   引数: [root: 基準ディレクトリ（Path）]
#   戻り値: [result: test・gdscript・bootstrapのcontent・digestを求めるための結果（dict[str, str]）]
# }
def content_digest(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for directory in ("data", "assets", "savedata")
        for path in (root / directory).rglob("*")
        if path.is_file()
    }


# {
#   責務: [run_godot: godotを実行する]
#   処理: [1: godotを実行する]
#   引数: [
#     script: script（str）
#     content_root: content・基準ディレクトリ（Path）
#     fixture: fixture（Path | None）
#   ]
#   戻り値: [result: godotを実行するための結果（dict）]
# }
def run_godot(script: str, content_root: Path, fixture: Path | None = None) -> dict:
    command = [str(GODOT), "--headless", "--path", str(ROOT / "gdscript"), "--script", script]
    if fixture is not None:
        command.extend(["--", str(fixture)])
    environment = dict(
        os.environ, KADOKA_CONTENT_ROOT=str(content_root), KADOKA_SAVE_DIR=str(content_root / "savedata"),
        KADOKA_GDSCRIPT_SAVE_ROOT=str(content_root / "savedata"), KADOKA_GDSCRIPT_SAVE_NAME="default",
    )
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


# {
#   責務: [GDScriptLayoutTests: gdscript・layout・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class GDScriptLayoutTests(unittest.TestCase):
    # {
    #   責務: [test_language_boundaries_and_launchable_scene_exist: 検証: language boundaries and launchable scene exist]
    #   処理: [1: 検証: language boundaries and launchable scene exist]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_language_boundaries_and_launchable_scene_exist(self) -> None:
        for relative in (
            "python/README.md", "unity/README.md", "gdscript/README.md",
            "gdscript/project.godot", "gdscript/scenes/field.tscn",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)
        settings = (ROOT / "gdscript/project.godot").read_text(encoding="utf-8")
        self.assertIn('run/main_scene="res://scenes/field.tscn"', settings)

    # {
    #   責務: [test_rules_do_not_access_files_input_or_rendering: 検証: rules do not access files input or rendering]
    #   処理: [1: 検証: rules do not access files input or rendering]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_rules_do_not_access_files_input_or_rendering(self) -> None:
        source = (ROOT / "gdscript/engine/field_engine.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess.", "DirAccess.", "Input.", "draw_", "get_tree(", "extends Node"):
            self.assertNotIn(forbidden, source)
        self.assertIn("extends RefCounted", source)


# {
#   責務: [GDScriptRuntimeTests: gdscript・実行時・testsの状態と振る舞いを担当する]
#   フィールド: [
#     temporary: temporary
#     content: content
#     before: before
#     repository: データ取得先
#     loader: loader
#     blocks: ブロック定義
#     map_ids: マップ・識別子一覧
#     maps: マップ一覧
#     cases: cases（list[dict]）
#     expected: expected（list[dict]）
#     groups: groups（dict[str, list[int]]）
#     actual: actual
#     scene: scene
#   ]
# }
@unittest.skipUnless(GODOT, "Set KADOKA_GODOT_EXECUTABLE to execute the real GDScript port")
class GDScriptRuntimeTests(unittest.TestCase):
    # {
    #   責務: [setUpClass: 検証に必要な専用fixtureと依存を準備する]
    #   処理: [1: 検証に必要な専用fixtureと依存を準備する]
    #   引数: [cls: 対象クラス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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

        # {
        #   責務: [add: gdscript・実行時・testsを追加する]
        #   処理: [1: gdscript・実行時・testsを追加する]
        #   引数: [
        #     group: group（str）
        #     world: マップ状態（dict）
        #     operation: operation（str）
        #     args: args（list）
        #     visible: visible（list | None）
        #     hidden: 非表示（list | None）
        #   ]
        #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
        # }
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

    # {
    #   責務: [assert_group: gdscript・実行時・testsのassert・groupを求める]
    #   処理: [1: gdscript・実行時・testsのassert・groupを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     group: group（str）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def assert_group(self, group: str) -> None:
        for index in self.groups[group]:
            with self.subTest(case=index, operation=self.cases[index]["operation"]):
                self.assertEqual(self.actual["results"][index], self.expected[index])

    # {
    #   責務: [test_collision_priority_matches_python: 検証: collision priority matches python]
    #   処理: [1: 検証: collision priority matches python]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_collision_priority_matches_python(self) -> None:
        self.assert_group("collision")

    # {
    #   責務: [test_sampled_moves_on_every_canonical_map_match_python: 検証: sampled moves on every canonical map match python]
    #   処理: [1: 検証: sampled moves on every canonical map match python]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_sampled_moves_on_every_canonical_map_match_python(self) -> None:
        self.assert_group("maps")

    # {
    #   責務: [test_event_activation_and_nearby_selection_match_python: 検証: event activation and nearby selection match python]
    #   処理: [1: 検証: event activation and nearby selection match python]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_event_activation_and_nearby_selection_match_python(self) -> None:
        self.assert_group("events")

    # {
    #   責務: [test_front_tile_and_axis_path_queries_match_python: 検証: front tile and axis path queries match python]
    #   処理: [1: 検証: front tile and axis path queries match python]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_front_tile_and_axis_path_queries_match_python(self) -> None:
        self.assert_group("queries")

    # {
    #   責務: [test_json_blocks_maps_extra_events_and_species_match_python: 検証: json blocks maps extra events and species match python]
    #   処理: [1: 検証: json blocks maps extra events and species match python]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_json_blocks_maps_extra_events_and_species_match_python(self) -> None:
        self.assertEqual(self.actual["blocks"], self.blocks)
        self.assertEqual(self.actual["maps"], self.maps)
        self.assertEqual(self.actual["hero"], self.repository.get_species("hero").definition)

    # {
    #   責務: [test_repository_rejects_path_traversal: 検証: repository rejects path traversal]
    #   処理: [1: 検証: repository rejects path traversal]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_repository_rejects_path_traversal(self) -> None:
        for result in self.actual["invalid_ids"]:
            self.assertEqual(result["value"], {})
            self.assertTrue(result["error"].startswith("Invalid map id"))

    # {
    #   責務: [test_session_preserves_step_interact_and_mob_blocking: 検証: session preserves step interact and mob blocking]
    #   処理: [1: 検証: session preserves step interact and mob blocking]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_session_preserves_step_interact_and_mob_blocking(self) -> None:
        sessions = self.actual["sessions"]
        self.assertEqual(sessions["edge"]["event"]["target"]["map_id"], "greenwood")
        self.assertEqual(sessions["rock"]["reason"], "blocking_event")
        self.assertEqual(sessions["rock_interaction"]["target"]["map_id"], "ghost_home")
        self.assertEqual(sessions["mob"]["reason"], "visible_character")

    # {
    #   責務: [test_real_keyboard_press_repeat_release: 検証: real keyboard press repeat release]
    #   処理: [1: 検証: real keyboard press repeat release]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_real_keyboard_press_repeat_release(self) -> None:
        self.assertEqual(self.actual["repeats"], [[1, 0], [0, 0], [1, 0], [0, 0]])

    # {
    #   責務: [test_production_scene_moves_and_transitions_through_input: 検証: production scene moves and transitions through input]
    #   処理: [1: 検証: production scene moves and transitions through input]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_production_scene_moves_and_transitions_through_input(self) -> None:
        self.assertEqual(self.scene["initial"], "starting_town")
        self.assertEqual(self.scene["start"], [18, 14])
        self.assertEqual(self.scene["moved"], [19, 14, "right"])
        self.assertEqual(self.scene["crossed"], "greenwood")
        self.assertEqual(self.scene["interacted"], "ghost_home")
        self.assertEqual(self.scene["image_width"], 64)
        self.assertEqual(self.scene["filter"], 1)  # CanvasItem.TEXTURE_FILTER_NEAREST

    # {
    #   責務: [test_invalid_transition_keeps_world_and_displays_error: 検証: invalid transition keeps world and displays error]
    #   処理: [1: 検証: invalid transition keeps world and displays error]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_invalid_transition_keeps_world_and_displays_error(self) -> None:
        self.assertFalse(self.scene["invalid_success"])
        self.assertTrue(self.scene["stable_world"])
        self.assertTrue(self.scene["error_visible"])

    # {
    #   責務: [test_readonly_content_and_save_sentinel_unchanged: 検証: readonly content and save sentinel unchanged]
    #   処理: [1: 検証: readonly content and save sentinel unchanged]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_readonly_content_and_save_sentinel_unchanged(self) -> None:
        self.assertEqual(content_digest(self.content), self.before)


if __name__ == "__main__":
    unittest.main()
