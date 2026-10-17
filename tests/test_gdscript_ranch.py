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
    #   責務: [test_roster_editor_and_presets_stop_held_movement_and_field_save_load: 牧場の台帳・編成・プリセット操作で探索位置と向きが変わらず、探索の保存・読込も実行されないことを検証します。]
    #   処理: [1: 各画面で方向キーを長押しし、保存・読込・Spaceを入力して全観測時点の位置と保存ファイルを比較します。]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_roster_editor_and_presets_stop_held_movement_and_field_save_load(self):
        # Spaceが「探索へ戻る」を押した場合も、押下中の方向キーは探索へ持ち越しません。
        self.seed_ranch()
        before = self.files()
        for stage in ([], [key("E")], [key("E"), key("P")]):
            with self.subTest(stage=stage):
                actions = [key("SPACE")] + stage + [
                    {"kind": "key_down", "key": "RIGHT"}, {"kind": "tick", "seconds": 1.0},
                    key("F5"), key("F9"), key("SPACE"), {"kind": "key_up", "key": "RIGHT"},
                ]
                for actual in self.probe(actions)["observations"]:
                    self.assertEqual((actual["x"], actual["y"], actual["direction"]), (14, 6, "back"))
                self.assertEqual(self.files(), before)

    # {
    #   責務: [test_roster_close_requires_direction_release_before_field_movement_resumes: 台帳を閉じたときの方向長押しを無視し、方向キーを離して押し直すと探索を再開できることを検証します。]
    #   処理: [
    #     1: 方向キーで台帳の戻るボタンを選び、Spaceで台帳を閉じたまま長押しを続けます。
    #     2: 方向キーを離して再度押し、探索位置だけが一歩進み保存ファイルが変わらないことを確認します。
    #   ]
    #   引数: [self: 隔離した牧場データとGodotプローブを所有するテスト]
    #   戻り値: [result: なし]
    # }
    def test_roster_close_requires_direction_release_before_field_movement_resumes(self):
        self.seed_ranch()
        before = self.files()
        actions = [key("SPACE"), {"kind": "key_down", "key": "RIGHT"}, key("SPACE"),
                   {"kind": "tick", "seconds": 1.0}, {"kind": "key_up", "key": "RIGHT"}, key("RIGHT")]
        observations = self.probe(actions)["observations"]
        # 戻るボタンのネイティブ操作は有効なまま、解除前の位置と向きを保護します。
        self.assertFalse(observations[3]["roster_visible"])
        for actual in observations[:-1]:
            self.assertEqual((actual["x"], actual["y"], actual["direction"]), (14, 6, "back"))
        self.assertEqual((observations[-1]["x"], observations[-1]["y"], observations[-1]["direction"]),
                         (15, 6, "right"))
        self.assertEqual(self.files(), before)

    # {
    #   責務: [test_roster_close_accepts_same_frame_direction_release_and_repress: 台帳を閉じた後、同じフレーム内に方向キーを離して押し直すと探索移動を再開できることを検証します。]
    #   処理: [1: 右方向を保持して台帳を閉じ、探索更新を挟まない右方向の解放・再押下で一歩だけ進むことを確認します。]
    #   引数: [self: 隔離した牧場データとGodotプローブを所有するテスト]
    #   戻り値: [result: なし]
    # }
    def test_roster_close_accepts_same_frame_direction_release_and_repress(self):
        self.seed_ranch()
        before = self.files()
        # key_batchはキー間に_processやフレーム待ちを挟まず、通常の解放フレームに依存しません。
        actions = [key("SPACE"), {"kind": "key_down", "key": "RIGHT"}, key("SPACE"),
                   {"kind": "key_batch", "events": [
                       {"key": "RIGHT", "pressed": False}, {"key": "RIGHT", "pressed": True}]},
                   {"kind": "key_up", "key": "RIGHT"}]
        observations = self.probe(actions)["observations"]
        self.assertFalse(observations[3]["roster_visible"])
        for actual in observations[:4]:
            self.assertEqual((actual["x"], actual["y"], actual["direction"]), (14, 6, "back"))
        for actual in observations[4:]:
            self.assertEqual((actual["x"], actual["y"], actual["direction"]), (15, 6, "right"))
        self.assertEqual(self.files(), before)

    # {
    #   責務: [test_roster_close_waits_until_all_direction_keys_are_released: 台帳終了時に矢印とWASDを同時に保持していた場合、全方向キーを離すまで探索移動を抑止することを検証します。]
    #   処理: [
    #     1: 右矢印とAを保持して台帳を閉じ、右矢印だけの解放・再押下では位置と向きが変わらないことを確認します。
    #     2: 両方の方向キーを離して右矢印を押し直し、同一フレームでも探索を再開できることを確認します。
    #   ]
    #   引数: [self: 隔離した牧場データとGodotプローブを所有するテスト]
    #   戻り値: [result: なし]
    # }
    def test_roster_close_waits_until_all_direction_keys_are_released(self):
        self.seed_ranch()
        before = self.files()
        # 一方向のキー解放だけでは、別の方向キーによる持ち越し防止を解除しません。
        actions = [key("SPACE"), {"kind": "key_down", "key": "RIGHT"},
                   {"kind": "key_down", "key": "A"}, key("SPACE"),
                   {"kind": "key_batch", "events": [
                       {"key": "RIGHT", "pressed": False}, {"key": "RIGHT", "pressed": True}]},
                   {"kind": "tick", "seconds": 1.0},
                   {"kind": "key_batch", "events": [
                       {"key": "RIGHT", "pressed": False}, {"key": "A", "pressed": False},
                       {"key": "RIGHT", "pressed": True}]},
                   {"kind": "key_up", "key": "RIGHT"}]
        observations = self.probe(actions)["observations"]
        self.assertFalse(observations[4]["roster_visible"])
        for actual in observations[:7]:
            self.assertEqual((actual["x"], actual["y"], actual["direction"]), (14, 6, "back"))
        for actual in observations[7:]:
            self.assertEqual((actual["x"], actual["y"], actual["direction"]), (15, 6, "right"))
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
    #   責務: [test_new_profile_table_is_read_only_and_explains_initial_save: 未保存プロフィールの牧場台帳はメニューの初回保存導線を示し、参照だけでは保存ファイルを作成しないことを検証します。]
    #   処理: [1: 隔離マップの開始位置から牧場へ移動して台帳を開き、保存案内とファイル不変を確認します。]
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
        self.assertIn("メニューの「冒険を保存する」", actual["roster_text"])
        self.assertIn("初期仲間を作成します", actual["roster_text"])
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
