"""Actual Godot clock/RNG parity and isolated production-scene fixed actor tests."""
# {
#   責務: [test_gdscript_fixed_mobs: Actual Godot clock/RNG parity and isolated production-scene fixed actor tests.]
#   フィールド: []
# }
from __future__ import annotations

import base64
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from kadoka_engine.field_engine import FieldEngine
from kadoka_engine.fixed_mob_controller import FixedMobController

ROOT = Path(__file__).resolve().parents[1]
GODOT = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")
BLOCKS = {"floor": {"player_walkable": True}, "wall": {"player_walkable": False}}


# {
#   責務: [TapeRandom: tape・乱数の状態と振る舞いを担当する]
#   フィールド: [
#     rolls: rolls
#     roll_index: roll・位置番号
#     shuffle_index: 並べ替え・位置番号
#   ]
# }
class TapeRandom:
    # {
    #   責務: [__init__: tape・乱数が利用する初期状態と依存を設定する]
    #   処理: [1: tape・乱数が利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     rolls: rolls（list[int]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, rolls: list[int]):
        self.rolls = rolls
        self.roll_index = self.shuffle_index = 0

    # {
    #   責務: [randrange: tape・乱数のrandrangeを求める]
    #   処理: [1: tape・乱数のrandrangeを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     limit: limit（int）
    #   ]
    #   戻り値: [result: 値（int）]
    # }
    def randrange(self, limit: int) -> int:
        value = self.rolls[self.roll_index % len(self.rolls)] % limit
        self.roll_index += 1
        return value

    # {
    #   責務: [shuffle: tape・乱数の並べ替えを求める]
    #   処理: [1: tape・乱数の並べ替えを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     values: 値一覧（list）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def shuffle(self, values: list) -> None:
        original = values[:]
        values[:] = [original[(i + self.shuffle_index) % len(values)] for i in range(len(values))]
        self.shuffle_index += 1


# {
#   責務: [world: test・gdscript・fixed・モブ一覧のマップ状態を求める]
#   処理: [1: test・gdscript・fixed・モブ一覧のマップ状態を求める]
#   引数: [
#     mobs: モブ一覧（list[dict]）
#     width: 幅（int）
#     height: 高さ（int）
#   ]
#   戻り値: [result: test・gdscript・fixed・モブ一覧のマップ状態を求めるための結果（dict）]
# }
def world(mobs: list[dict], width: int = 8, height: int = 8) -> dict:
    return {"id": "fixture", "width": width, "height": height, "start": {"x": 0, "y": 0},
            "tiles": [["floor"] * width for _ in range(height)], "events": [], "fixed_mobs": mobs}


# {
#   責務: [mob: test・gdscript・fixed・モブ一覧のモブを求める]
#   処理: [1: test・gdscript・fixed・モブ一覧のモブを求める]
#   引数: [
#     id: 識別子（str）
#     changes: changes
#   ]
#   戻り値: [result: test・gdscript・fixed・モブ一覧のモブを求めるための結果（dict）]
# }
def mob(id: str = "test", **changes) -> dict:
    return {"id": id, "species_id": "slime", "x": 3, "y": 3, "ai": "random", **changes}


# {
#   責務: [GDScriptFixedMobTests: gdscript・fixed・モブ・testsの状態と振る舞いを担当する]
#   フィールド: [
#     temporary: temporary
#     content: content
#   ]
# }
@unittest.skipUnless(GODOT, "Set KADOKA_GODOT_EXECUTABLE for actual fixed-mob probes")
class GDScriptFixedMobTests(unittest.TestCase):
    # {
    #   責務: [setUp: 検証に必要な専用fixtureと依存を準備する]
    #   処理: [1: 検証に必要な専用fixtureと依存を準備する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="kadoka-fixed-mobs-")
        self.addCleanup(self.temporary.cleanup)
        self.content = Path(self.temporary.name)

    # {
    #   責務: [probe: gdscript・fixed・モブ・testsのprobeを求める]
    #   処理: [1: gdscript・fixed・モブ・testsのprobeを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     request: 要求（dict）
    #     scene: scene（bool）
    #   ]
    #   戻り値: [result: gdscript・fixed・モブ・testsのprobeを求めるための結果（list）]
    # }
    def probe(self, request: dict, scene: bool = False) -> list:
        fixture = self.content / "request.json"
        fixture.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
        env = dict(os.environ)
        if scene:
            if not (self.content / "data").exists():
                shutil.copytree(ROOT / "data", self.content / "data")
                shutil.copytree(ROOT / "assets", self.content / "assets")
            env.update(KADOKA_CONTENT_ROOT=str(self.content), KADOKA_GDSCRIPT_SAVE_ROOT=str(self.content / "saves"),
                       KADOKA_SAVE_DIR=str(self.content / "never-python-saves"))
        process = subprocess.run([str(GODOT), "--headless", "--path", str(ROOT / "gdscript"), "--script",
                                  "res://tests/run_fixed_mobs_probe.gd", "--", str(fixture)],
                                 env=env, cwd=self.content, capture_output=True, text=True, encoding="utf-8",
                                 errors="replace", timeout=40, check=False)
        self.assertEqual(process.returncode, 0, process.stderr + process.stdout[-1000:])
        self.assertNotIn("SCRIPT ERROR", process.stderr)
        for line in process.stdout.splitlines():
            if line.startswith("KADOKA_FIXED_MOBS="):
                return json.loads(base64.b64decode(line.split("=", 1)[1]))
        self.fail(process.stderr + process.stdout[-1000:])

    # {
    #   責務: [engine: gdscript・fixed・モブ・testsのルール処理を求める]
    #   処理: [1: gdscript・fixed・モブ・testsのルール処理を求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     source: 元データ（dict）
    #     actions: actions（list）
    #     player: 主人公
    #     extra: extra
    #   ]
    #   戻り値: [result: gdscript・fixed・モブ・testsのルール処理を求めるための結果（list）]
    # }
    def engine(self, source: dict, actions: list, player=(7, 7), **extra) -> list:
        return self.probe({"cases": [{"world": source, "blocks": BLOCKS, "player": list(player),
                                      "actions": actions, **extra}]})[0]

    # {
    #   責務: [test_same_clock_and_rng_match_python_idle_random_chase_and_interpolation: 検証: same clock and rng match python idle random chase and interpolation]
    #   処理: [1: 検証: same clock and rng match python idle random chase and interpolation]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_same_clock_and_rng_match_python_idle_random_chase_and_interpolation(self) -> None:
        cases = []
        for ai in ("idle", "random", "chase", "unknown"):
            for chance in (-5, 0, 45, 100, 120):
                for interval in (0, 900):
                    source = world([mob(ai=ai, move_chance=chance, move_interval_ms=interval),
                                    mob("blocker", x=4, y=3, ai="idle")])
                    source["tiles"][3][2] = "wall"
                    cases.append({"world": source, "blocks": BLOCKS, "player": [7, 7],
                                  "rolls": [0, 44, 45, 99, 16], "actions": [{"now": n} for n in
                                  (0, 99, 100, 145, 180, 450, 540, 899, 900, 990, 1080, 2000, 2010, 2180, 5000)]})
        results = self.probe({"cases": cases})
        for case, observations in zip(cases, results):
            rng = TapeRandom(case["rolls"])
            controller = FixedMobController(FieldEngine({}, {}), rng)
            before = copy.deepcopy(case["world"])
            player = tuple(case["player"])
            controller.reset(case["world"], BLOCKS, set(), player, 0, str)
            for action, observation in zip(case["actions"], observations[1:]):
                now = action["now"]
                with self.subTest(ai=case["world"]["fixed_mobs"][0]["ai"], now=now,
                                  chance=case["world"]["fixed_mobs"][0]["move_chance"],
                                  interval=case["world"]["fixed_mobs"][0]["move_interval_ms"]):
                    self.assertEqual(controller.update(player, now), observation["moved"])
                    self.assertEqual(len(observation["npcs"]), len(controller.npcs))
                    for actual, expected in zip(observation["npcs"], controller.npcs):
                        for key in ("id", "x", "y", "direction", "move_count", "next_move_tick", "ai"):
                            self.assertEqual(actual[key], expected[key])
                        px, py = expected["_movement"].position(now)
                        self.assertAlmostEqual(actual["display_x"], px, places=5)
                        self.assertAlmostEqual(actual["display_y"], py, places=5)
                    self.assertEqual(observation["rolls_used"], rng.roll_index)
                    self.assertEqual(observation["shuffles_used"], rng.shuffle_index)
                    self.assertTrue(observation["source_unchanged"])
            self.assertEqual(case["world"], before)

    # {
    #   責務: [test_canonical_maru_is_more_active_and_reentry_restores_start_positions: 検証: canonical maru is more active and reentry restores start positions]
    #   処理: [1: 検証: canonical maru is more active and reentry restores start positions]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_canonical_maru_is_more_active_and_reentry_restores_start_positions(self) -> None:
        source = json.loads((ROOT / "data/maps/ghost_home/map.json").read_text(encoding="utf-8"))
        blocks = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (ROOT / "data/blocks").glob("*.json")}
        actions = [{"now": n} for n in range(450, 9001, 450)] + [{"kind": "reset", "now": 9100}]
        case = {"world": source, "blocks": blocks, "player": [1, 9], "rolls": [50], "actions": actions}
        result = self.probe({"cases": [case]})[0]
        self.assertGreater(result[-2]["npcs"][0]["move_count"], 10)
        self.assertEqual(result[-2]["npcs"][1]["move_count"], 0)
        for initial, reset in zip(source["fixed_mobs"], result[-1]["npcs"]):
            self.assertEqual((reset["x"], reset["y"]), (initial["x"], initial["y"]))
            self.assertEqual(reset["move_count"], 0)
            self.assertEqual(reset["next_move_tick"], 9100 + initial["move_interval_ms"])

    # {
    #   責務: [test_chase_fallback_avoids_terrain_player_other_mobs_and_blocking_event: 検証: chase fallback avoids terrain player other mobs and blocking event]
    #   処理: [1: 検証: chase fallback avoids terrain player other mobs and blocking event]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_chase_fallback_avoids_terrain_player_other_mobs_and_blocking_event(self) -> None:
        source = world([mob(ai="chase"), mob("idle", x=2, y=3, ai="idle")])
        source["tiles"][4][3] = "wall"
        source["events"] = [{"id": "rock", "x": 4, "y": 3, "blocking": True}]
        result = self.engine(source, [{"now": 900}, {"now": 990}, {"now": 1080}], player=(7, 3))
        npc = result[1]["npcs"][0]
        self.assertEqual((npc["x"], npc["y"]), (3, 2))
        self.assertEqual((npc["display_x"], npc["display_y"]), (3, 3))
        self.assertEqual(result[2]["npcs"][0]["display_y"], 2.5)
        self.assertEqual(result[3]["npcs"][0]["display_y"], 2)

    # {
    #   責務: [test_each_blocking_ledger_cell_stays_blocked_for_fixed_mobs: 検証: each blocking ledger cell stays blocked for fixed mobs]
    #   処理: [1: 検証: each blocking ledger cell stays blocked for fixed mobs]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_each_blocking_ledger_cell_stays_blocked_for_fixed_mobs(self) -> None:
        cases = []
        for path in (ROOT / "data/maps").glob("*/map.json"):
            source = json.loads(path.read_text(encoding="utf-8"))
            for event in source.get("events", []):
                if event.get("blocking"):
                    fixture = world([mob(ai="chase", x=2, y=3)])
                    fixture["events"] = [{**event, "x": 3, "y": 3}]
                    cases.append({"world": fixture, "blocks": BLOCKS, "player": [7, 3],
                                  "actions": [{"now": 900}]})
        self.assertGreaterEqual(len(cases), 3)
        for result in self.probe({"cases": cases}):
            self.assertNotEqual((result[-1]["npcs"][0]["x"], result[-1]["npcs"][0]["y"]), (3, 3))

    # {
    #   責務: [test_reset_skips_disabled_despawned_and_relocates_overlaps_or_invalid_cells: 検証: reset skips disabled despawned and relocates overlaps or invalid cells]
    #   処理: [1: 検証: reset skips disabled despawned and relocates overlaps or invalid cells]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_reset_skips_disabled_despawned_and_relocates_overlaps_or_invalid_cells(self) -> None:
        source = world([mob("disabled", enabled=False), mob("gone", respawn_on_map_enter=False),
                        mob("returns", respawn_on_map_enter=True), mob("overlap"), mob("invalid", x=-1)], 3, 2)
        source["fixed_mobs"][2].update(x=1, y=0)
        source["fixed_mobs"][3].update(x=1, y=0)
        source["events"] = [{"x": 0, "y": 0, "blocking": True}]
        source["tiles"][0][2] = "wall"
        result = self.engine(source, [], player=(1, 0), despawned=["fixture:gone", "fixture:returns"])[0]
        self.assertEqual([n["id"] for n in result["npcs"]], ["returns", "overlap", "invalid"])
        self.assertEqual([(n["x"], n["y"]) for n in result["npcs"]], [(0, 1), (1, 1), (2, 1)])

    # {
    #   責務: [test_no_free_cell_reports_warning_instead_of_overlapping: 検証: no free cell reports warning instead of overlapping]
    #   処理: [1: 検証: no free cell reports warning instead of overlapping]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_no_free_cell_reports_warning_instead_of_overlapping(self) -> None:
        result = self.engine(world([mob(x=0, y=0)], 1, 1), [], player=(0, 0))[0]
        self.assertEqual(result["npcs"], [])
        self.assertEqual(len(result["warnings"]), 1)

    # {
    #   責務: [test_one_attempt_per_deadline_and_front_facing_pause_use_no_extra_rng: 検証: one attempt per deadline and front facing pause use no extra rng]
    #   処理: [1: 検証: one attempt per deadline and front facing pause use no extra rng]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_one_attempt_per_deadline_and_front_facing_pause_use_no_extra_rng(self) -> None:
        source = world([mob(direction="right", move_interval_ms=100)])
        result = self.engine(source, [{"now": 10000}, {"now": 10099}, {"now": 10100, "player": [7, 7]}],
                             player=(4, 3))
        self.assertEqual(result[1]["npcs"][0]["next_move_tick"], 10100)
        self.assertEqual(result[1]["rolls_used"], 0)
        self.assertEqual(result[2]["rolls_used"], 0)
        self.assertEqual(result[3]["npcs"][0]["move_count"], 1)

    # {
    #   責務: [test_actual_scene_updates_while_player_idle_and_draw_snapshot_is_interpolated: 検証: actual scene updates while player idle and draw snapshot is interpolated]
    #   処理: [1: 検証: actual scene updates while player idle and draw snapshot is interpolated]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_actual_scene_updates_while_player_idle_and_draw_snapshot_is_interpolated(self) -> None:
        result = self.probe({"scene": True, "actions": [
            {"kind": "open"}, {"kind": "tick", "delta": 0.449}, {"kind": "tick", "delta": 0.001},
            {"kind": "tick", "delta": 0.09}, {"kind": "refresh"}, {"kind": "refresh"},
        ]}, scene=True)
        self.assertEqual(result[0]["player"], result[-1]["player"])
        self.assertEqual(result[1]["npcs"][0]["move_count"], 0)
        self.assertEqual(result[2]["npcs"][0]["move_count"], 1)
        self.assertEqual(result[3]["npcs"], result[3]["drawn"])
        self.assertNotEqual(result[3]["npcs"][0]["x"], result[3]["npcs"][0]["display_x"])
        self.assertEqual(result[3]["npcs"], result[5]["npcs"])
        self.assertEqual(result[3]["clock"], result[5]["clock"])
        self.assertFalse((self.content / "saves").exists())

    # {
    #   責務: [test_all_management_modals_freeze_clock_and_resume_without_catchup: 検証: all management modals freeze clock and resume without catchup]
    #   処理: [1: 検証: all management modals freeze clock and resume without catchup]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_all_management_modals_freeze_clock_and_resume_without_catchup(self) -> None:
        actions = [{"kind": "open"}, {"kind": "tick", "delta": 0.44}]
        for name in ("roster", "party", "preset"):
            actions.extend([{"kind": "modal", "name": name}, {"kind": "tick", "delta": 30.0}])
        actions.extend([{"kind": "modal", "name": "none"}, {"kind": "tick", "delta": 0.01}])
        result = self.probe({"scene": True, "actions": actions}, scene=True)
        for observation in result[1:-1]:
            self.assertEqual(observation["clock"], 440)
            self.assertEqual(observation["npcs"][0]["move_count"], 0)
        self.assertEqual(result[-1]["clock"], 450)
        self.assertEqual(result[-1]["npcs"][0]["move_count"], 1)

    # {
    #   責務: [test_player_cannot_enter_logical_destination_during_interpolation: 検証: player cannot enter logical destination during interpolation]
    #   処理: [1: 検証: player cannot enter logical destination during interpolation]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_player_cannot_enter_logical_destination_during_interpolation(self) -> None:
        result = self.probe({"scene": True, "actions": [
            {"kind": "open"}, {"kind": "tick", "delta": 0.45},
            {"kind": "place", "x": 8, "y": 7}, {"kind": "move", "dx": 1, "dy": 0},
        ]}, scene=True)
        self.assertEqual(result[-1]["outcome"]["reason"], "visible_character")
        self.assertEqual(result[-1]["player"], [8, 7])

    # {
    #   責務: [test_save_load_on_former_spawn_preserves_flags_and_never_writes_mob_runtime: 検証: save load on former spawn preserves flags and never writes mob runtime]
    #   処理: [1: 検証: save load on former spawn preserves flags and never writes mob runtime]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_save_load_on_former_spawn_preserves_flags_and_never_writes_mob_runtime(self) -> None:
        result = self.probe({"scene": True, "actions": [
            {"kind": "open"}, {"kind": "tick", "delta": 0.45},
            {"kind": "place", "x": 10, "y": 7}, {"kind": "save"}, {"kind": "load"},
        ]}, scene=True)
        self.assertTrue(result[-2]["outcome"])
        self.assertTrue(result[-1]["outcome"])
        self.assertEqual(result[-1]["player"], [10, 7])
        self.assertNotIn((10, 7), [(n["x"], n["y"]) for n in result[-1]["npcs"]])
        state_path = self.content / "saves/default/state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertNotIn("fixed_mobs", state)
        self.assertNotIn("clock_ms", state)
        self.assertNotIn("move_count", json.dumps(state))
        before = {p.relative_to(self.content): p.read_bytes() for p in self.content.rglob("*.json")
                  if p.name != "request.json"}
        loaded = self.probe({"scene": True, "actions": [{"kind": "refresh"}]}, scene=True)
        self.assertEqual(loaded[0]["player"], [10, 7])
        after = {p.relative_to(self.content): p.read_bytes() for p in self.content.rglob("*.json")
                 if p.name != "request.json"}
        self.assertEqual(before, after)
        self.assertFalse((self.content / "never-python-saves").exists())

    # {
    #   責務: [test_load_consumes_existing_despawn_flags_without_changing_save: 検証: load consumes existing despawn flags without changing save]
    #   処理: [1: 検証: load consumes existing despawn flags without changing save]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_load_consumes_existing_despawn_flags_without_changing_save(self) -> None:
        self.probe({"scene": True, "actions": [{"kind": "save"}]}, scene=True)
        path = self.content / "data/maps/ghost_home/map.json"
        source = json.loads(path.read_text(encoding="utf-8"))
        source["fixed_mobs"][0]["respawn_on_map_enter"] = False
        path.write_text(json.dumps(source), encoding="utf-8")
        state_path = self.content / "saves/default/state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state.update(map_id="ghost_home", player={"x": 1, "y": 9},
                     despawned_fixed_mobs=["ghost_home:maru_home", "ghost_home:kadoka_home"], mod={"keep": True})
        state_path.write_text(json.dumps(state), encoding="utf-8")
        before = state_path.read_bytes()
        result = self.probe({"scene": True, "actions": [{"kind": "refresh"}, {"kind": "open"}]}, scene=True)
        self.assertEqual([n["id"] for n in result[0]["npcs"]], ["kadoka_home"])
        self.assertEqual([n["id"] for n in result[1]["npcs"]], ["kadoka_home"])
        self.assertEqual(before, state_path.read_bytes())

    # {
    #   責務: [test_new_runtime_engine_remains_free_of_ui_and_file_dependencies: 検証: new runtime engine remains free of ui and file dependencies]
    #   処理: [1: 検証: new runtime engine remains free of ui and file dependencies]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_new_runtime_engine_remains_free_of_ui_and_file_dependencies(self) -> None:
        text = (ROOT / "gdscript/engine/fixed_mob_controller.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "OS.", "Time.", "Input.", "queue_redraw", "change_scene"):
            self.assertNotIn(forbidden, text)
