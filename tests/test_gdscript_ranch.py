"""Canonical town/ranch events -> real Godot management controls, never a Python child app."""
# {
#   責務: [test_gdscript_ranch: Canonical town/ranch events -> real Godot management controls, never a Python child app.]
#   フィールド: []
# }
from __future__ import annotations

import hashlib
import json
import unittest

import test_gdscript_party as fixture

key = fixture.key


# {
#   責務: [GDScriptRanchTests: gdscript・ranch・testsの状態と振る舞いを担当する]
#   フィールド: [
#     setUp: set・up
#     probe: probe
#     seed: seed
#     write: write
#   ]
# }
@unittest.skipUnless(fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real ranch journeys")
class GDScriptRanchTests(unittest.TestCase):
    setUp = fixture.GDScriptPartyTests.setUp
    probe = fixture.GDScriptPartyTests.probe
    seed = fixture.GDScriptPartyTests.seed
    write = fixture.GDScriptPartyTests.write

    # {
    #   責務: [files: gdscript・ranch・testsのfilesを求める]
    #   処理: [1: gdscript・ranch・testsのfilesを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     omit_state: omit・状態
    #   ]
    #   戻り値: [result: gdscript・ranch・testsのfilesを求めるための結果（型注釈なし）]
    # }
    def files(self, omit_state=False):
        return {name.replace("\\", "/"): data
                for name, data in fixture.GDScriptPartyTests.files(self, omit_state).items()}

    # {
    #   責務: [seed_ranch: gdscript・ranch・testsのseed・ranchを求める]
    #   処理: [1: gdscript・ranch・testsのseed・ranchを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: gdscript・ranch・testsのseed・ranchを求めるための結果（型注釈なし）]
    # }
    def seed_ranch(self):
        return self.seed(map_id="starting_ranch", player={"x": 14, "y": 6, "direction": "back"})

    # {
    #   責務: [content_hashes: gdscript・ranch・testsのcontent・hashesを求める]
    #   処理: [1: gdscript・ranch・testsのcontent・hashesを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: gdscript・ranch・testsのcontent・hashesを求めるための結果（型注釈なし）]
    # }
    def content_hashes(self):
        return {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                for directory in ("data", "assets", "python-saves")
                for path in (self.content / directory).rglob("*") if path.is_file()}

    # {
    #   責務: [test_canonical_town_entrance_walk_to_table_collision_open_and_return: 検証: canonical town entrance walk to table collision open and return]
    #   処理: [1: 検証: canonical town entrance walk to table collision open and return]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_canonical_town_entrance_walk_to_table_collision_open_and_return(self):
        self.seed(map_id="starting_town", player={"x": 8, "y": 11, "direction": "back"})
        before = self.files()
        content_before = self.content_hashes()
        actions = [key("UP"), key("SPACE")] + [key("UP")] * 11 + [key("UP"), key("SPACE"), key("ESC")]
        actual = self.probe(actions)["observations"]
        self.assertEqual(actual[1]["map_id"], "starting_town")
        self.assertEqual(actual[2]["map_id"], "starting_ranch")
        self.assertEqual((actual[2]["x"], actual[2]["y"]), (14, 17))
        self.assertEqual((actual[-3]["x"], actual[-3]["y"]), (14, 6))  # The table at (14,5) is blocking.
        self.assertTrue(actual[-2]["roster_visible"])
        self.assertEqual(set(actual[-2]["owned_ids"]), {"a", "b", "c"})
        self.assertIn("パーティ", actual[-2]["roster_text"])
        self.assertIn("個体編集・AI変更は未移植", actual[-2]["status"])
        self.assertFalse(actual[-1]["roster_visible"])
        self.assertEqual((actual[-1]["x"], actual[-1]["y"], actual[-1]["direction"]), (14, 6, "back"))
        self.assertEqual(self.files(), before)
        self.assertEqual(self.content_hashes(), content_before)

    # {
    #   責務: [test_each_interaction_key_opens_only_roster_not_editor: 検証: each interaction key opens only roster not editor]
    #   処理: [1: 検証: each interaction key opens only roster not editor]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_each_interaction_key_opens_only_roster_not_editor(self):
        self.seed_ranch()
        before = self.files()
        for name in ("ENTER", "SPACE", "E"):
            with self.subTest(name=name):
                actual = self.probe([key(name)])["observations"][-1]
                self.assertTrue(actual["roster_visible"])
                self.assertFalse(actual["editing"])
                self.assertFalse(actual["preset_visible"])
                self.assertEqual((actual["x"], actual["y"], actual["direction"]), (14, 6, "back"))
                self.assertEqual(self.files(), before)

    # {
    #   責務: [test_roster_editor_and_presets_stop_held_movement_and_field_save_load: 検証: roster editor and presets stop held movement and field save load]
    #   処理: [1: 検証: roster editor and presets stop held movement and field save load]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_roster_editor_and_presets_stop_held_movement_and_field_save_load(self):
        self.seed_ranch()
        before = self.files()
        for stage in ([], [key("E")], [key("E"), key("P")]):
            with self.subTest(stage=stage):
                actions = [key("SPACE")] + stage + [
                    {"kind": "key_down", "key": "RIGHT"}, {"kind": "tick", "seconds": 1.0},
                    key("F5"), key("F9"), key("SPACE"), {"kind": "key_up", "key": "RIGHT"},
                ]
                actual = self.probe(actions)["observations"][-1]
                self.assertEqual((actual["x"], actual["y"], actual["direction"]), (14, 6, "back"))
                self.assertEqual(self.files(), before)

    # {
    #   責務: [test_ranch_preset_and_explicit_party_save_preserve_owned_files_and_restart: 検証: ranch preset and explicit party save preserve owned files and restart]
    #   処理: [1: 検証: ranch preset and explicit party save preserve owned files and restart]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_ranch_preset_and_explicit_party_save_preserve_owned_files_and_restart(self):
        self.seed_ranch()
        before = self.files()
        actions = [key("SPACE"), key("E"), key("P"), key("ENTER"), key("P"), key("TAB"),
                   {"kind": "text", "text": "牧場編成"}, key("ENTER"), key("ESC"),
                   key("S", ctrl=True), key("ESC")]
        actual = self.probe(actions)["observations"][-1]
        self.assertFalse(actual["roster_visible"])
        self.assertFalse(actual["editing"])
        self.assertEqual(actual["state"]["current_party"], ["b", None, "a", None])
        self.assertEqual((actual["x"], actual["y"], actual["direction"]), (14, 6, "back"))
        after = self.files()
        for name, value in before.items():
            if name != "state.json":
                self.assertEqual(after[name], value)
        self.assertEqual(json.loads(after["parties/party.json"])["members"], ["b", None, "a", None])
        restarted = self.probe()["observations"][0]
        self.assertEqual(restarted["state"], actual["state"])
        self.assertEqual((restarted["x"], restarted["y"], restarted["direction"]), (14, 6, "back"))

    # {
    #   責務: [test_ranch_loaded_draft_cancel_leaves_every_file_unchanged: 検証: ranch loaded draft cancel leaves every file unchanged]
    #   処理: [1: 検証: ranch loaded draft cancel leaves every file unchanged]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_ranch_loaded_draft_cancel_leaves_every_file_unchanged(self):
        self.seed_ranch()
        before = self.files()
        actual = self.probe([key("SPACE"), key("E"), key("P"), key("ENTER"), key("ESC"), key("ESC")])[
            "observations"][-1]
        self.assertFalse(actual["roster_visible"])
        self.assertFalse(actual["editing"])
        self.assertEqual(actual["state"]["current_party"], ["a", "b"])
        self.assertEqual(self.files(), before)

    # {
    #   責務: [test_new_profile_table_is_read_only_and_explains_initial_save: 検証: new profile table is read only and explains initial save]
    #   処理: [1: 検証: new profile table is read only and explains initial save]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_new_profile_table_is_read_only_and_explains_initial_save(self):
        # Modify only the copied map's start to reach the canonical entrance with real keys.
        path = self.content / "data/maps/starting_town/map.json"
        town = json.loads(path.read_text(encoding="utf-8"))
        town["start"] = {"x": 8, "y": 11}
        path.write_text(json.dumps(town, ensure_ascii=False), encoding="utf-8")
        content_before = self.content_hashes()
        actions = [key("UP"), key("SPACE")] + [key("UP")] * 11 + [key("SPACE"), key("E")]
        actual = self.probe(actions)["observations"][-1]
        self.assertTrue(actual["roster_visible"])
        self.assertFalse(actual["editing"])
        self.assertIn("F5", actual["roster_text"])
        self.assertIn("編成を開けません", actual["status"])
        self.assertFalse(self.profile.exists())
        self.assertEqual(self.content_hashes(), content_before)

    # {
    #   責務: [test_corrupt_save_refuses_edit_and_is_not_repaired: 検証: corrupt save refuses edit and is not repaired]
    #   処理: [1: 検証: corrupt save refuses edit and is not repaired]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_corrupt_save_refuses_edit_and_is_not_repaired(self):
        self.seed_ranch()
        before = self.files(omit_state=True)
        actual = self.probe([{"kind": "external_state", "raw": "{broken"}, key("SPACE"), key("E")])[
            "observations"][-1]
        self.assertTrue(actual["roster_visible"])
        self.assertFalse(actual["editing"])
        self.assertEqual(actual["owned_ids"], [])
        self.assertIn("壊れています", actual["roster_text"])
        self.assertIn("編成を開けません", actual["status"])
        self.assertEqual((self.profile / "state.json").read_text(encoding="utf-8"), "{broken")
        self.assertEqual(self.files(omit_state=True), before)

    # {
    #   責務: [test_reopening_table_rescans_individuals_without_deleting_bad_folder: 検証: reopening table rescans individuals without deleting bad folder]
    #   処理: [1: 検証: reopening table rescans individuals without deleting bad folder]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_reopening_table_rescans_individuals_without_deleting_bad_folder(self):
        self.seed_ranch()
        before = self.files()
        actual = self.probe([key("SPACE"), key("ESC"), {"kind": "remove_ai", "id": "c"}, key("SPACE")])[
            "observations"]
        self.assertEqual(set(actual[1]["owned_ids"]), {"a", "b", "c"})
        self.assertEqual(set(actual[-1]["owned_ids"]), {"a", "b"})
        self.assertIn("注意", actual[-1]["roster_text"])
        self.assertTrue((self.profile / "monsters/c/monster.json").is_file())
        self.assertEqual(self.files(), {name: value for name, value in before.items() if name != "monsters/c/ai.json"})

    # {
    #   責務: [test_escape_and_f6_return_in_place_then_movement_resumes: 検証: escape and f6 return in place then movement resumes]
    #   処理: [1: 検証: escape and f6 return in place then movement resumes]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_escape_and_f6_return_in_place_then_movement_resumes(self):
        self.seed_ranch()
        before = self.files()
        for closing in ("ESC", "F6"):
            with self.subTest(closing=closing):
                actual = self.probe([key("SPACE"), key(closing), key("RIGHT")])["observations"]
                self.assertFalse(actual[-2]["roster_visible"])
                self.assertEqual((actual[-2]["x"], actual[-2]["y"], actual[-2]["direction"]), (14, 6, "back"))
                self.assertEqual((actual[-1]["x"], actual[-1]["y"]), (15, 6))
                self.assertEqual(self.files(), before)


if __name__ == "__main__":
    unittest.main()
