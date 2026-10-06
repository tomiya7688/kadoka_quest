"""Real-Godot dialogue deck parity, front-cell key routing and read-only field progress."""
# {
#   責務: [test_gdscript_dialogue: Real-Godot dialogue deck parity, front-cell key routing and read-only field progress.]
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
from test_gdscript_fixed_mobs import BLOCKS, TapeRandom, mob, world

ROOT = Path(__file__).resolve().parents[1]
GODOT = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")


# {
#   責務: [GDScriptDialogueTests: gdscript・会話・testsの状態と振る舞いを担当する]
#   フィールド: [
#     temporary: temporary
#     content: content
#   ]
# }
@unittest.skipUnless(GODOT, "Set KADOKA_GODOT_EXECUTABLE for actual dialogue tests")
class GDScriptDialogueTests(unittest.TestCase):
    # {
    #   責務: [setUp: 検証に必要な専用fixtureと依存を準備する]
    #   処理: [1: 検証に必要な専用fixtureと依存を準備する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="kadoka-dialogue-")
        self.addCleanup(self.temporary.cleanup)
        self.content = Path(self.temporary.name)

    # {
    #   責務: [prepare_scene: sceneを準備する]
    #   処理: [1: sceneを準備する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def prepare_scene(self) -> None:
        if not (self.content / "data").exists():
            shutil.copytree(ROOT / "data", self.content / "data")
            shutil.copytree(ROOT / "assets", self.content / "assets")

    # {
    #   責務: [probe: gdscript・会話・testsのprobeを求める]
    #   処理: [1: gdscript・会話・testsのprobeを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     request: 要求（dict）
    #   ]
    #   戻り値: [result: gdscript・会話・testsのprobeを求めるための結果（list）]
    # }
    def probe(self, request: dict) -> list:
        if request.get("scene"):
            self.prepare_scene()
        fixture = self.content / "request.json"
        fixture.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
        env = dict(os.environ, KADOKA_CONTENT_ROOT=str(self.content),
                   KADOKA_GDSCRIPT_SAVE_ROOT=str(self.content / "saves"), KADOKA_GDSCRIPT_SAVE_NAME="default",
                   KADOKA_SAVE_DIR=str(self.content / "python-never"))
        process = subprocess.run([str(GODOT), "--headless", "--path", str(ROOT / "gdscript"), "--script",
                                  "res://tests/run_fixed_mobs_probe.gd", "--", str(fixture)],
                                 cwd=self.content, env=env, capture_output=True, text=True, encoding="utf-8",
                                 errors="replace", timeout=40, check=False)
        self.assertEqual(process.returncode, 0, process.stderr + process.stdout[-1000:])
        self.assertNotIn("SCRIPT ERROR", process.stderr)
        self.assertNotIn("ERROR:", process.stderr)
        for line in process.stdout.splitlines():
            if line.startswith("KADOKA_FIXED_MOBS="):
                return json.loads(base64.b64decode(line.split("=", 1)[1]))
        self.fail(process.stderr + process.stdout[-1000:])

    # {
    #   責務: [scene: gdscript・会話・testsのsceneを求める]
    #   処理: [1: gdscript・会話・testsのsceneを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     actions: actions（list）
    #   ]
    #   戻り値: [result: gdscript・会話・testsのsceneを求めるための結果（list）]
    # }
    def scene(self, actions: list) -> list:
        return self.probe({"scene": True, "actions": actions})

    # {
    #   責務: [test_card_order_refill_boundary_and_unicode_trim_match_python: 検証: card order refill boundary and unicode trim match python]
    #   処理: [1: 検証: card order refill boundary and unicode trim match python]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_card_order_refill_boundary_and_unicode_trim_match_python(self) -> None:
        home = json.loads((ROOT / "data/maps/ghost_home/map.json").read_text(encoding="utf-8"))
        sources = [copy.deepcopy(n) for n in home["fixed_mobs"]]
        decks = [["村の話", "天気の話", "森の話"], ["一言"], ["a", "b"], ["a", "a", "b"], ["a", "a"],
                 ["", "  ", "  前後  ", "途中 空白", "\u200b残す\ufeff"]]
        sources += [{"dialogue": cards} for cards in decks]
        whitespace = list(range(9, 14)) + list(range(28, 33)) + list(range(8192, 8203)) + [
            133, 160, 5760, 8232, 8233, 8239, 8287, 12288,
        ]
        sources += [{"dialogue": [chr(point), chr(point) + "台詞" + chr(point), "別の台詞"]} for point in whitespace]
        cases = [{"source": source, "count": 23} for source in sources]
        results = self.probe({"dialogue": True, "cases": cases})
        for case, result in zip(cases, results):
            controller = FixedMobController(FieldEngine({}, {}), TapeRandom([0]))
            npc = copy.deepcopy(case["source"])
            for index, observation in enumerate(result["selections"]):
                with self.subTest(source=case["source"]["dialogue"], choice=index):
                    expected = controller.next_dialogue(npc)
                    self.assertEqual(observation["result"], {"ok": True, "line": expected})
                    self.assertEqual(observation["remaining"], npc["dialogue_remaining"])
                    self.assertEqual(observation["last"], npc["last_dialogue"])
                    self.assertEqual(observation["shuffles"], controller.rng.shuffle_index)
            self.assertTrue(result["source_unchanged"])

    # {
    #   責務: [test_distinct_deck_visits_each_card_once_and_avoids_repeat_across_refills: 検証: distinct deck visits each card once and avoids repeat across refills]
    #   処理: [1: 検証: distinct deck visits each card once and avoids repeat across refills]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_distinct_deck_visits_each_card_once_and_avoids_repeat_across_refills(self) -> None:
        result = self.probe({"dialogue": True, "cases": [{"source": {"dialogue": ["a", "b", "c"]}, "count": 30}]})[0]
        lines = [n["result"]["line"] for n in result["selections"]]
        for start in range(0, 30, 3):
            self.assertEqual(set(lines[start:start + 3]), {"a", "b", "c"})
        self.assertTrue(all(a != b for a, b in zip(lines, lines[1:])))

    # {
    #   責務: [test_missing_invalid_empty_decks_report_reason_and_consume_no_rng: 検証: missing invalid empty decks report reason and consume no rng]
    #   処理: [1: 検証: missing invalid empty decks report reason and consume no rng]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_missing_invalid_empty_decks_report_reason_and_consume_no_rng(self) -> None:
        cases = [({}, "missing_deck"), ({"dialogue": None}, "invalid_deck"), ({"dialogue": "文字列"}, "invalid_deck"),
                 ({"dialogue": {}}, "invalid_deck"), ({"dialogue": []}, "empty_deck"),
                 ({"dialogue": [" ", "\u3000"]}, "empty_deck")]
        cases += [({"dialogue": ["正しい台詞", value]}, "invalid_card") for value in (3, False, None, {}, [])]
        results = self.probe({"dialogue": True, "cases": [{"source": source, "count": 2} for source, _ in cases]})
        for (_, error), result in zip(cases, results):
            for observation in result["selections"]:
                with self.subTest(error=error):
                    self.assertFalse(observation["result"]["ok"])
                    self.assertEqual(observation["result"]["error"], error)
                    self.assertTrue(observation["result"]["message"])
                    self.assertNotIn("line", observation["result"])
                    self.assertEqual(observation["shuffles"], 0)
            self.assertTrue(result["source_unchanged"])

    # {
    #   責務: [test_per_mob_decks_are_independent_and_reset_on_map_entry: 検証: per mob decks are independent and reset on map entry]
    #   処理: [1: 検証: per mob decks are independent and reset on map entry]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_per_mob_decks_are_independent_and_reset_on_map_entry(self) -> None:
        source = world([mob("one", ai="idle", dialogue=["a", "b", "c"]),
                        mob("two", x=5, ai="idle", dialogue=["x", "y"])])
        actions = [{"kind": "talk", "index": i} for i in (0, 1, 0, 1, 0)] + [
            {"kind": "reset", "now": 10}, {"kind": "talk", "index": 0},
        ]
        result = self.probe({"cases": [{"world": source, "blocks": BLOCKS, "player": [7, 7], "actions": actions}]})[0]
        controller = FixedMobController(FieldEngine({}, {}), TapeRandom([0]))
        controller.reset(source, BLOCKS, set(), (7, 7), 0, str)
        for action, observation in zip(actions, result[1:]):
            if action["kind"] == "reset":
                controller.reset(source, BLOCKS, set(), (7, 7), 10, str)
            else:
                expected = controller.next_dialogue(controller.npcs[action["index"]])
                self.assertEqual(observation["outcome"]["line"], expected)
            self.assertTrue(observation["source_unchanged"])

    # {
    #   責務: [test_real_enter_space_e_keys_talk_only_to_front_cell_and_ignore_echo: 検証: real enter space e keys talk only to front cell and ignore echo]
    #   処理: [1: 検証: real enter space e keys talk only to front cell and ignore echo]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_real_enter_space_e_keys_talk_only_to_front_cell_and_ignore_echo(self) -> None:
        result = self.scene([
            {"kind": "open", "entry": {"x": 9, "y": 7, "direction": "back"}},
            {"kind": "key", "key": "Enter"},
            {"kind": "place", "x": 9, "y": 7, "direction": "right"},
            {"kind": "key", "key": "E", "echo": True},
            {"kind": "key", "key": "Enter"}, {"kind": "key", "key": "Space"}, {"kind": "key", "key": "E"},
        ])
        self.assertEqual(result[1]["status"], "目の前に調べるものはありません。")
        self.assertEqual(result[3]["status"], result[1]["status"])
        self.assertEqual([r["status"] for r in result[4:]], [
            "まる『ここ、へいわ』", "まる『かどかもいっしょ』", "まる『きょうはいっぱい歩く』",
        ])
        self.assertEqual(result[-1]["npcs"][0]["direction"], "left")
        self.assertEqual(result[-1]["drawn"][0]["direction"], "left")
        self.assertFalse((self.content / "saves").exists())

    # {
    #   責務: [test_talking_turns_npc_towards_player_from_all_four_sides: 検証: talking turns npc towards player from all four sides]
    #   処理: [1: 検証: talking turns npc towards player from all four sides]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_talking_turns_npc_towards_player_from_all_four_sides(self) -> None:
        sides = [(9, 7, "right", "left"), (11, 7, "left", "right"),
                 (10, 6, "front", "back"), (10, 8, "back", "front")]
        for x, y, direction, opposite in sides:
            with self.subTest(direction=direction):
                result = self.scene([{"kind": "open", "entry": {"x": x, "y": y, "direction": direction}},
                                     {"kind": "key", "key": "E"}])[-1]
                self.assertTrue(result["status"].startswith("まる『"))
                self.assertEqual(result["npcs"][0]["direction"], opposite)

    # {
    #   責務: [test_talking_pauses_movement_keeps_occupancy_and_leaving_resumes_at_deadline: 検証: talking pauses movement keeps occupancy and leaving resumes at deadline]
    #   処理: [1: 検証: talking pauses movement keeps occupancy and leaving resumes at deadline]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_talking_pauses_movement_keeps_occupancy_and_leaving_resumes_at_deadline(self) -> None:
        result = self.scene([
            {"kind": "open", "entry": {"x": 9, "y": 7, "direction": "right"}}, {"kind": "key", "key": "E"},
            {"kind": "tick", "delta": 0.45}, {"kind": "tick", "delta": 20.0},
            {"kind": "move", "dx": 1, "dy": 0}, {"kind": "place", "x": 8, "y": 7},
            {"kind": "tick", "delta": 0.449}, {"kind": "tick", "delta": 0.001},
        ])
        for observation in result[:7]:
            self.assertEqual((observation["npcs"][0]["x"], observation["npcs"][0]["y"]), (10, 7))
            self.assertEqual(observation["npcs"][0]["move_count"], 0)
        self.assertEqual(result[4]["outcome"]["reason"], "visible_character")
        self.assertEqual(result[-1]["npcs"][0]["move_count"], 1)

    # {
    #   責務: [test_management_modals_do_not_consume_a_dialogue_card: 検証: management modals do not consume a dialogue card]
    #   処理: [1: 検証: management modals do not consume a dialogue card]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_management_modals_do_not_consume_a_dialogue_card(self) -> None:
        actions = [{"kind": "open", "entry": {"x": 9, "y": 7, "direction": "right"}}]
        for name in ("roster", "party", "preset"):
            actions += [{"kind": "modal", "name": name}, {"kind": "key", "key": "Enter"}]
        actions += [{"kind": "modal", "name": "none"}, {"kind": "key", "key": "E"}]
        result = self.scene(actions)
        self.assertTrue(all(r["npcs"][0]["direction"] == "front" for r in result[:-1]))
        self.assertEqual(result[-1]["status"], "まる『ここ、へいわ』")

    # {
    #   責務: [test_front_npc_takes_precedence_over_event_and_battle_is_not_faked: 検証: front npc takes precedence over event and battle is not faked]
    #   処理: [1: 検証: front npc takes precedence over event and battle is not faked]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_front_npc_takes_precedence_over_event_and_battle_is_not_faked(self) -> None:
        self.prepare_scene()
        path = self.content / "data/maps/ghost_home/map.json"
        source = json.loads(path.read_text(encoding="utf-8"))
        source["fixed_mobs"][0]["interaction"] = "battle"
        source["events"].append({"x": 10, "y": 7, "type": "message", "text": "重なったイベント"})
        path.write_text(json.dumps(source), encoding="utf-8")
        result = self.scene([{"kind": "open", "entry": {"x": 9, "y": 7, "direction": "right"}},
                             {"kind": "key", "key": "E"}])[-1]
        self.assertIn("未移植: battle", result["status"])
        self.assertNotIn("重なったイベント", result["status"])
        self.assertEqual(result["npcs"][0]["direction"], "left")
        self.assertFalse((self.content / "saves").exists())

    # {
    #   責務: [test_invalid_deck_is_visible_in_scene_and_not_replaced_by_fake_dialogue: 検証: invalid deck is visible in scene and not replaced by fake dialogue]
    #   処理: [1: 検証: invalid deck is visible in scene and not replaced by fake dialogue]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_invalid_deck_is_visible_in_scene_and_not_replaced_by_fake_dialogue(self) -> None:
        self.prepare_scene()
        path = self.content / "data/maps/ghost_home/map.json"
        source = json.loads(path.read_text(encoding="utf-8"))
        source["fixed_mobs"][0].pop("dialogue")
        path.write_text(json.dumps(source), encoding="utf-8")
        result = self.scene([{"kind": "open", "entry": {"x": 9, "y": 7, "direction": "right"}},
                             {"kind": "key", "key": "E"}])[-1]
        self.assertIn("会話デッキが設定されていません", result["status"])
        self.assertNotIn("『……』", result["status"])

    # {
    #   責務: [test_unported_despawn_is_explicit_without_removing_actor_or_saving: 検証: unported despawn is explicit without removing actor or saving]
    #   処理: [1: 検証: unported despawn is explicit without removing actor or saving]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_unported_despawn_is_explicit_without_removing_actor_or_saving(self) -> None:
        self.prepare_scene()
        path = self.content / "data/maps/ghost_home/map.json"
        source = json.loads(path.read_text(encoding="utf-8"))
        source["fixed_mobs"][0]["despawn_after_interaction"] = True
        path.write_text(json.dumps(source), encoding="utf-8")
        result = self.scene([{"kind": "open", "entry": {"x": 9, "y": 7, "direction": "right"}},
                             {"kind": "key", "key": "E"}])[-1]
        self.assertIn("まる『", result["status"])
        self.assertIn("未移植: 会話後の消滅", result["status"])
        self.assertEqual(len(result["npcs"]), 2)
        self.assertFalse((self.content / "saves").exists())

    # {
    #   責務: [test_acquisition_state_does_not_hide_home_mobs_or_modify_json_ai_assets: 検証: acquisition state does not hide home mobs or modify json ai assets]
    #   処理: [1: 検証: acquisition state does not hide home mobs or modify json ai assets]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_acquisition_state_does_not_hide_home_mobs_or_modify_json_ai_assets(self) -> None:
        self.prepare_scene()
        profile = self.content / "saves/default"
        profile.mkdir(parents=True)
        for acquired in (False, True):
            state = {"schema_version": 1, "map_id": "ghost_home", "player": {"x": 9, "y": 7, "direction": "right"},
                     "flags": {"ghost_entrance_open": acquired}, "current_party": [], "mod_keep": {"value": 7}}
            (profile / "state.json").write_text(json.dumps(state), encoding="utf-8")
            for id in (("maru_01", "kadoka_01") if acquired else ()):
                folder = profile / "monsters" / id
                folder.mkdir(parents=True, exist_ok=True)
                (folder / "ai.json").write_text('{"learning":"keep"}', encoding="utf-8")
                record = {"id": id, "species_id": id[:-3], "level": 1, "name": id, "plus_choices": []}
                (folder / "monster.json").write_text(json.dumps(record), encoding="utf-8")
            before = {p.relative_to(self.content): p.read_bytes() for parent in ("data", "assets", "saves")
                      for p in (self.content / parent).rglob("*") if p.is_file()}
            result = self.scene([{"kind": "key", "key": "E"},
                                 {"kind": "place", "x": 11, "y": 10, "direction": "right"},
                                 {"kind": "key", "key": "Space"}])[-1]
            self.assertEqual([n["species_id"] for n in result["npcs"]], ["maru", "kadoka"])
            self.assertTrue(result["status"].startswith("かどか『"))
            after = {p.relative_to(self.content): p.read_bytes() for parent in ("data", "assets", "saves")
                     for p in (self.content / parent).rglob("*") if p.is_file()}
            self.assertEqual(before, after)
        self.assertFalse((self.content / "python-never").exists())
