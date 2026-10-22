"""Current-party drafts, real Godot controls and failure-safe state-only persistence."""
# {
#   責務: [test_gdscript_party: Current-party drafts, real Godot controls and failure-safe state-only persistence.]
#   フィールド: []
# }
from __future__ import annotations

import base64
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from kadoka_quest.core.ai import default_ai
from kadoka_quest.data.state import DEFAULT_STATE, StateStore

ROOT = Path(__file__).resolve().parents[1]
GODOT = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")


# {
#   責務: [key: test・gdscript・パーティのキーを求める]
#   処理: [1: test・gdscript・パーティのキーを求める]
#   引数: [
#     name: 名前
#     modifiers: modifiers
#   ]
#   戻り値: [result: test・gdscript・パーティのキーを求めるための結果（型注釈なし）]
# }
def key(name, **modifiers):
    return {"kind": "key", "key": name, **modifiers}


# {
#   責務: [click: test・gdscript・パーティのclickを求める]
#   処理: [1: test・gdscript・パーティのclickを求める]
#   引数: [
#     target: 対象
#     index: 位置番号
#   ]
#   戻り値: [result: test・gdscript・パーティのclickを求めるための結果（型注釈なし）]
# }
def click(target, index=0):
    return {"kind": "click", "target": target, "index": index}


# {
#   責務: [GDScriptPartyBoundaryTests: gdscript・パーティ・boundary・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class GDScriptPartyBoundaryTests(unittest.TestCase):
    # {
    #   責務: [test_rules_and_view_do_not_access_files_and_service_does_not_render: 検証: rules and view do not access files and service does not render]
    #   処理: [1: 検証: rules and view do not access files and service does not render]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_rules_and_view_do_not_access_files_and_service_does_not_render(self):
        for relative in ("engine/party_selection.gd", "ui/party_view.gd"):
            source = (ROOT / "gdscript" / relative).read_text(encoding="utf-8")
            for forbidden in ("FileAccess.", "DirAccess.", "load_profile(", "save_profile("):
                self.assertNotIn(forbidden, source)
        source = (ROOT / "gdscript/application/party_editor.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess.", "DirAccess.", "Label.new", "Button.new", "Input."):
            self.assertNotIn(forbidden, source)


# {
#   責務: [GDScriptPartyTests: gdscript・パーティ・testsの状態と振る舞いを担当する]
#   フィールド: [
#     content: content
#     saves: saves
#     profile: プロファイル
#     legacy: legacy
#   ]
# }
@unittest.skipUnless(GODOT, "Set KADOKA_GODOT_EXECUTABLE for real party/control probes")
class GDScriptPartyTests(unittest.TestCase):
    # {
    #   責務: [setUp: 検証に必要な専用fixtureと依存を準備する]
    #   処理: [1: 検証に必要な専用fixtureと依存を準備する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="kadoka-gdscript-party-")
        self.addCleanup(temporary.cleanup)
        self.content = Path(temporary.name)
        shutil.copytree(ROOT / "data", self.content / "data")
        shutil.copytree(ROOT / "assets", self.content / "assets")
        self.saves = self.content / "gd-saves"
        self.profile = self.saves / "default"
        self.legacy = self.content / "python-saves"
        self.legacy.mkdir()
        (self.legacy / "sentinel.json").write_text('{"keep":true}', encoding="utf-8")

    # {
    #   責務: [probe: gdscript・パーティ・testsのprobeを求める]
    #   処理: [1: gdscript・パーティ・testsのprobeを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     actions: actions
    #     contracts: contracts
    #   ]
    #   戻り値: [result: gdscript・パーティ・testsのprobeを求めるための結果（型注釈なし）]
    # }
    def probe(self, actions=(), **contracts):
        fixture = self.content / "probe.json"
        fixture.write_text(json.dumps({"actions": list(actions), **contracts}, ensure_ascii=False), encoding="utf-8")
        environment = dict(os.environ, KADOKA_CONTENT_ROOT=str(self.content), KADOKA_SAVE_DIR=str(self.legacy),
                           KADOKA_GDSCRIPT_SAVE_ROOT=str(self.saves), KADOKA_GDSCRIPT_SAVE_NAME="default")
        result = subprocess.run(
            [str(GODOT), "--headless", "--path", str(ROOT / "gdscript"), "--script",
             "res://tests/run_party_probe.gd", "--", str(fixture)],
            cwd=self.content, env=environment, text=True, encoding="utf-8", errors="replace",
            capture_output=True, timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout[-1200:])
        self.assertNotIn("SCRIPT ERROR", result.stderr)
        for line in result.stdout.splitlines():
            if line.startswith("KADOKA_PARTY_RESULT="):
                return json.loads(base64.b64decode(line.split("=", 1)[1]).decode("utf-8"))
        self.fail(result.stdout[-1200:] + result.stderr)

    # {
    #   責務: [write: gdscript・パーティ・testsを書き込む]
    #   処理: [1: gdscript・パーティ・testsを書き込む]
    #   引数: [
    #     self: 処理対象インスタンス
    #     relative: relative
    #     value: 値
    #   ]
    #   戻り値: [result: パス（型注釈なし）]
    # }
    def write(self, relative, value):
        path = self.profile / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    # {
    #   責務: [seed: gdscript・パーティ・testsのseedを求める]
    #   処理: [1: gdscript・パーティ・testsのseedを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     members: 個体一覧
    #     changes: changes
    #   ]
    #   戻り値: [result: 状態（型注釈なし）]
    # }
    def seed(self, members=None, **changes):
        state = json.loads(json.dumps(DEFAULT_STATE, ensure_ascii=False))
        state.pop("inventory")
        state.update(current_party=["a", "b"] if members is None else members)
        state.update(changes)
        for index, identifier in enumerate(("a", "b", "c")):
            monster = {"schema_version": 1, "id": identifier, "species_id": "slime", "name": f"仲間{identifier}",
                       "level": index + 1, "experience": 17, "plus_choices": [], "equipment_id": None}
            self.write(f"monsters/{identifier}/monster.json", monster)
            self.write(f"monsters/{identifier}/ai.json", {**default_ai(), "battles": 77, "mod_ai": [1, 2, 3]})
        self.write("items/items.json", {"schema_version": 1, "items": {"orange": 27}, "mod_item": True})
        self.write("parties/existing.json", {"schema_version": 1, "name": "既存編成", "members": ["b", None, "a", None]})
        self.write("meta.json", {"schema_version": 1, "name": "default", "mod_meta": True})
        self.write("state.json", state)
        return state

    # {
    #   責務: [files: gdscript・パーティ・testsのfilesを求める]
    #   処理: [1: gdscript・パーティ・testsのfilesを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     omit_state: omit・状態
    #   ]
    #   戻り値: [result: gdscript・パーティ・testsのfilesを求めるための結果（型注釈なし）]
    # }
    def files(self, omit_state=False):
        return {str(path.relative_to(self.profile)): path.read_bytes() for path in self.profile.rglob("*")
                if path.is_file() and not (omit_state and path.name == "state.json")}

    # {
    #   責務: [add_c_keyboard: c・keyboardを追加する]
    #   処理: [1: c・keyboardを追加する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: c・keyboardを追加するための結果（型注釈なし）]
    # }
    def add_c_keyboard(self):
        return [key("F6"), key("E"), key("DOWN"), key("DOWN"), key("TAB"), key("END"), key("ENTER")]

    # {
    #   責務: [test_keyboard_add_save_restart_and_python_format_preserve_other_documents: 検証: keyboard add save restart and python format preserve other documents]
    #   処理: [1: 検証: keyboard add save restart and python format preserve other documents]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_keyboard_add_save_restart_and_python_format_preserve_other_documents(self):
        state = self.seed(mod_state={"keep": [1, "日本語"]}, flags={"custom_flag": True})
        state["player"]["custom"] = 123
        self.write("state.json", state)
        before = self.files(omit_state=True)
        content_before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                          for folder in ("data", "assets", "python-saves")
                          for path in (self.content / folder).rglob("*") if path.is_file()}
        observations = self.probe(self.add_c_keyboard() + [key("S", ctrl=True)])["observations"]
        self.assertEqual([item["id"] for item in observations[-2]["draft"]["party"]], ["a", "b", "c", None])
        self.assertTrue(observations[-2]["draft"]["dirty"])
        self.assertFalse(observations[-1]["editing"])
        expected = {**state, "current_party": ["a", "b", "c", None]}
        self.assertEqual(observations[-1]["state"], expected)
        self.assertEqual(self.files(omit_state=True), before)
        restarted = self.probe()["observations"][0]
        self.assertEqual(restarted["state"], expected)
        self.assertEqual(StateStore(self.profile / "state.json").load()["current_party"], expected["current_party"])
        content_after = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                         for folder in ("data", "assets", "python-saves")
                         for path in (self.content / folder).rglob("*") if path.is_file()}
        self.assertEqual(content_before, content_after)

    # {
    #   責務: [test_mouse_editor_entry_slot_assignment_clear_and_save: 検証: mouse editor entry slot assignment clear and save]
    #   処理: [1: 検証: mouse editor entry slot assignment clear and save]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_mouse_editor_entry_slot_assignment_clear_and_save(self):
        self.seed()
        actual = self.probe([key("F6"), click("edit"), click("slots", 2), click("owned", 2), click("assign"),
                             click("slots", 0), click("clear"), click("save")])["observations"][-1]
        self.assertFalse(actual["editing"])
        self.assertEqual(actual["state"]["current_party"], [None, "b", "c", None])

    # {
    #   責務: [test_keyboard_focus_and_enter_can_activate_save_button: 検証: keyboard focus and enter can activate save button]
    #   処理: [1: 検証: keyboard focus and enter can activate save button]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_keyboard_focus_and_enter_can_activate_save_button(self):
        self.seed()
        actions = self.add_c_keyboard() + [key("TAB"), key("TAB"), key("TAB"), key("ENTER")]
        actual = self.probe(actions)["observations"][-1]
        self.assertFalse(actual["editing"])
        self.assertEqual(actual["state"]["current_party"], ["a", "b", "c", None])

    # {
    #   責務: [test_party_save_keeps_unsaved_position_and_next_f5_preserves_party: 検証: party save keeps unsaved position and next f5 preserves party]
    #   処理: [1: 検証: party save keeps unsaved position and next f5 preserves party]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_party_save_keeps_unsaved_position_and_next_f5_preserves_party(self):
        state = self.seed()
        actions = [key("RIGHT")] + self.add_c_keyboard() + [key("S", ctrl=True), key("ESC"), key("F5")]
        actual = self.probe(actions)["observations"]
        party_saved = actual[-3]
        self.assertEqual(party_saved["x"], state["player"]["x"] + 1)
        self.assertEqual(party_saved["state"]["player"], state["player"])
        self.assertEqual(actual[-1]["state"]["player"]["x"], party_saved["x"])
        self.assertEqual(actual[-1]["state"]["current_party"], ["a", "b", "c", None])

    # {
    #   責務: [test_unselected_broken_individual_warns_without_blocking_valid_party_save: 検証: unselected broken individual warns without blocking valid party save]
    #   処理: [1: 検証: unselected broken individual warns without blocking valid party save]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_unselected_broken_individual_warns_without_blocking_valid_party_save(self):
        self.seed()
        self.write("monsters/broken/monster.json", {"id": "broken", "species_id": "missing", "name": "不正個体"})
        before = self.files(omit_state=True)
        actual = self.probe(self.add_c_keyboard() + [key("S", ctrl=True)])["observations"]
        self.assertTrue(actual[2]["draft"]["warnings"])
        self.assertEqual(actual[-1]["state"]["current_party"], ["a", "b", "c", None])
        self.assertEqual(self.files(omit_state=True), before)

    # {
    #   責務: [test_delete_and_reassign_to_change_order_with_empty_slots: 検証: delete and reassign to change order with empty slots]
    #   処理: [1: 検証: delete and reassign to change order with empty slots]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_delete_and_reassign_to_change_order_with_empty_slots(self):
        self.seed(["a", "b", "c", None])
        actual = self.probe([key("F6"), key("E"), key("DELETE"), key("END"), key("TAB"), key("HOME"),
                             key("ENTER"), key("S", ctrl=True)])["observations"][-1]
        self.assertEqual(actual["state"]["current_party"], [None, "b", "c", "a"])

    # {
    #   責務: [test_duplicate_assignment_rejected_without_changing_draft_or_files: 検証: duplicate assignment rejected without changing draft or files]
    #   処理: [1: 検証: duplicate assignment rejected without changing draft or files]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_duplicate_assignment_rejected_without_changing_draft_or_files(self):
        self.seed()
        before = self.files()
        actual = self.probe([key("F6"), key("E"), key("END"), key("TAB"), key("ENTER")])["observations"][-1]
        self.assertIn("複数枠", actual["message"])
        self.assertFalse(actual["draft"]["dirty"])
        self.assertEqual([item["id"] for item in actual["draft"]["party"]], ["a", "b", None, None])
        self.assertEqual(self.files(), before)

    # {
    #   責務: [test_cancel_by_escape_f6_and_button_keeps_all_bytes: 検証: cancel by escape f6 and button keeps all bytes]
    #   処理: [1: 検証: cancel by escape f6 and button keeps all bytes]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_cancel_by_escape_f6_and_button_keeps_all_bytes(self):
        self.seed()
        before = self.files()
        for cancel in (key("ESC"), key("F6"), click("cancel")):
            with self.subTest(cancel=cancel):
                actual = self.probe(self.add_c_keyboard() + [cancel])["observations"][-1]
                self.assertFalse(actual["editing"])
                self.assertTrue(actual["roster_visible"])
                self.assertEqual(self.files(), before)

    # {
    #   責務: [test_no_change_save_does_not_reformat_short_legacy_party: 検証: no change save does not reformat short legacy party]
    #   処理: [1: 検証: no change save does not reformat short legacy party]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_no_change_save_does_not_reformat_short_legacy_party(self):
        self.seed()
        before = self.files()
        actual = self.probe([key("F6"), key("E"), key("S", ctrl=True)])["observations"][-1]
        self.assertFalse(actual["editing"])
        self.assertIn("変更はありません", actual["status"])
        self.assertEqual(self.files(), before)

    # {
    #   責務: [test_field_movement_interaction_f5_f9_are_blocked_while_editing: 検証: field movement interaction f5 f9 are blocked while editing]
    #   処理: [1: 検証: field movement interaction f5 f9 are blocked while editing]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_field_movement_interaction_f5_f9_are_blocked_while_editing(self):
        self.seed()
        before = self.files()
        results = self.probe(self.add_c_keyboard() + [key("RIGHT"), key("F5"), key("F9"), key("SPACE")])["observations"]
        self.assertTrue(results[-1]["editing"])
        self.assertTrue(results[-1]["draft"]["dirty"])
        self.assertEqual((results[-1]["x"], results[-1]["y"]), (results[0]["x"], results[0]["y"]))
        self.assertEqual(self.files(), before)

    # {
    #   責務: [test_tab_focus_cycles_and_shift_tab_returns_within_editor: 編成画面の七つの操作対象をTabで巡回し、逆順の末尾からプリセットを開けることを検証します。]
    #   処理: [1: 七回のTabで初期フォーカスへ戻し、Shift+TabとEnterでプリセットボタンを作動させます。]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_tab_focus_cycles_and_shift_tab_returns_within_editor(self):
        # プリセットボタンを含む全操作対象が、画面外へ抜けずに巡回できることを確認します。
        self.seed()
        actual = self.probe([key("F6"), key("E")] + [key("TAB")] * 7 +
                            [key("TAB", shift=True), key("ENTER")])["observations"]
        initial = actual[2]["focus"]
        self.assertEqual(actual[-3]["focus"], initial)
        self.assertNotEqual(actual[-2]["focus"], initial)
        self.assertEqual(len({entry["focus"] for entry in actual[2:-2]}), 7)
        self.assertTrue(actual[-1]["preset_visible"])

    # {
    #   責務: [test_large_owned_list_keyboard_end_scrolls_and_selects_last: 検証: large owned list keyboard end scrolls and selects last]
    #   処理: [1: 検証: large owned list keyboard end scrolls and selects last]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_large_owned_list_keyboard_end_scrolls_and_selects_last(self):
        self.seed([])
        for index in range(120):
            identifier = f"m{index:03}"
            self.write(f"monsters/{identifier}/monster.json", {
                "id": identifier, "species_id": "slime", "name": f"長い名前のスライム{index}", "level": 1,
            })
            self.write(f"monsters/{identifier}/ai.json", default_ai())
        actual = self.probe([key("F6"), key("E"), key("TAB"), key("END"), key("PAGEUP"), key("HOME"),
                             key("PAGEDOWN"), key("END"), key("ENTER"),
                             key("S", ctrl=True)])["observations"]
        self.assertGreater(actual[4]["owned_scroll"], 0)
        self.assertLess(actual[5]["owned_selection"][0], actual[4]["owned_selection"][0])
        self.assertEqual(actual[6]["owned_selection"], [0])
        self.assertGreater(actual[7]["owned_selection"][0], 0)
        self.assertEqual(actual[-1]["state"]["current_party"], ["m119", None, None, None])

    # {
    #   責務: [test_external_state_update_refuses_save_and_retains_draft: 検証: external state update refuses save and retains draft]
    #   処理: [1: 検証: external state update refuses save and retains draft]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_external_state_update_refuses_save_and_retains_draft(self):
        self.seed()
        protected = self.files(omit_state=True)
        actual = self.probe(self.add_c_keyboard() + [
            {"kind": "external_state", "changes": {"mod_external": "keep", "current_party": ["b"]}}, key("S", ctrl=True),
        ])["observations"][-1]
        self.assertTrue(actual["editing"])
        self.assertTrue(actual["draft"]["dirty"])
        self.assertIn("外部で変更", actual["message"])
        self.assertEqual(actual["state"]["current_party"], ["b"])
        self.assertEqual(actual["state"]["mod_external"], "keep")
        self.assertEqual(self.files(omit_state=True), protected)

    # {
    #   責務: [test_external_corruption_refuses_save_and_preserves_corrupt_bytes: 検証: external corruption refuses save and preserves corrupt bytes]
    #   処理: [1: 検証: external corruption refuses save and preserves corrupt bytes]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_external_corruption_refuses_save_and_preserves_corrupt_bytes(self):
        self.seed()
        actual = self.probe(self.add_c_keyboard() + [
            {"kind": "external_state", "raw": "{broken"}, key("S", ctrl=True),
        ])["observations"][-1]
        self.assertTrue(actual["editing"])
        self.assertIn("保存失敗", actual["message"])
        self.assertEqual((self.profile / "state.json").read_text(encoding="utf-8"), "{broken")

    # {
    #   責務: [test_member_revalidated_if_ai_removed_after_opening: 検証: member revalidated if ai removed after opening]
    #   処理: [1: 検証: member revalidated if ai removed after opening]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_member_revalidated_if_ai_removed_after_opening(self):
        self.seed()
        state_before = (self.profile / "state.json").read_bytes()
        actions = self.add_c_keyboard() + [{"kind": "remove_ai", "id": "c"}, key("S", ctrl=True)]
        actual = self.probe(actions)["observations"][-1]
        self.assertTrue(actual["editing"])
        self.assertIn("読込できない", actual["message"])
        self.assertEqual((self.profile / "state.json").read_bytes(), state_before)

    # {
    #   責務: [test_missing_member_can_be_explicitly_removed_but_not_silently_saved: 検証: missing member can be explicitly removed but not silently saved]
    #   処理: [1: 検証: missing member can be explicitly removed but not silently saved]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_missing_member_can_be_explicitly_removed_but_not_silently_saved(self):
        self.seed(["missing", "b"])
        before = self.files()
        actual = self.probe([key("F6"), key("E"), key("S", ctrl=True)])["observations"][-1]
        self.assertIn("missing", actual["slots"][0])
        self.assertTrue(actual["editing"])
        self.assertEqual(self.files(), before)
        repaired = self.probe([key("F6"), key("E"), key("DELETE"), key("S", ctrl=True)])["observations"][-1]
        self.assertEqual(repaired["state"]["current_party"], [None, "b", None, None])

    # {
    #   責務: [test_duplicate_legacy_member_must_be_explicitly_removed: 検証: duplicate legacy member must be explicitly removed]
    #   処理: [1: 検証: duplicate legacy member must be explicitly removed]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_duplicate_legacy_member_must_be_explicitly_removed(self):
        self.seed(["a", "a"])
        actual = self.probe([key("F6"), key("E"), key("S", ctrl=True), key("DOWN"), key("DELETE"),
                             key("S", ctrl=True)])["observations"]
        self.assertTrue(actual[3]["editing"])
        self.assertIn("重複", actual[3]["message"])
        self.assertEqual(actual[-1]["state"]["current_party"], ["a", None, None, None])

    # {
    #   責務: [test_malformed_and_overflow_party_refuse_open_without_truncation: 検証: malformed and overflow party refuse open without truncation]
    #   処理: [1: 検証: malformed and overflow party refuse open without truncation]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_malformed_and_overflow_party_refuse_open_without_truncation(self):
        for members in ({"bad": True}, ["a"] * 5, [False], [7], [""]):
            with self.subTest(members=members):
                self.seed(members)
                before = self.files()
                actual = self.probe([key("F6"), key("E")])["observations"][-1]
                self.assertFalse(actual["editing"])
                self.assertIn("編成を開けません", actual["status"])
                self.assertEqual(self.files(), before)

    # {
    #   責務: [test_new_profile_editor_is_readonly_until_first_save: 検証: new profile editor is readonly until first save]
    #   処理: [1: 検証: new profile editor is readonly until first save]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_new_profile_editor_is_readonly_until_first_save(self):
        actual = self.probe([key("F6"), key("E")])["observations"][-1]
        self.assertFalse(actual["editing"])
        self.assertIn("編成を開けません", actual["status"])
        self.assertFalse(self.profile.exists())
        saved = self.probe([key("F5"), key("F6"), key("E")])["observations"][-1]
        self.assertTrue(saved["editing"])
        self.assertEqual(len(saved["draft"]["records"]), 2)

    # {
    #   責務: [test_all_empty_party_is_allowed_and_individuals_remain_owned: 検証: all empty party is allowed and individuals remain owned]
    #   処理: [1: 検証: all empty party is allowed and individuals remain owned]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_all_empty_party_is_allowed_and_individuals_remain_owned(self):
        self.seed()
        before = self.files(omit_state=True)
        actual = self.probe([key("F6"), key("E"), key("DELETE"), key("DOWN"), key("DELETE"),
                             key("S", ctrl=True)])["observations"][-1]
        self.assertEqual(actual["state"]["current_party"], [None] * 4)
        self.assertEqual(self.files(omit_state=True), before)

    # {
    #   責務: [test_unicode_individual_id_can_be_assigned_and_roundtripped: 検証: unicode individual id can be assigned and roundtripped]
    #   処理: [1: 検証: unicode individual id can be assigned and roundtripped]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_unicode_individual_id_can_be_assigned_and_roundtripped(self):
        self.seed([])
        self.write("monsters/まる一号/monster.json", {"id": "まる一号", "species_id": "maru", "name": "まる一号", "level": 42})
        self.write("monsters/まる一号/ai.json", default_ai("maru"))
        actual = self.probe([key("F6"), key("E"), key("TAB"), key("END"), key("ENTER"),
                             key("S", ctrl=True)])["observations"][-1]
        self.assertEqual(actual["state"]["current_party"], ["まる一号", None, None, None])

    # {
    #   責務: [test_legacy_missing_level_uses_default_one_in_editor: 検証: legacy missing level uses default one in editor]
    #   処理: [1: 検証: legacy missing level uses default one in editor]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_legacy_missing_level_uses_default_one_in_editor(self):
        # Old individual documents omit optional fields; the view must share the default Lv1.
        self.seed([])
        self.write("monsters/z_legacy/monster.json", {"id": "z_legacy", "species_id": "slime", "name": "旧形式"})
        self.write("monsters/z_legacy/ai.json", default_ai())
        actual = self.probe([key("F6"), key("E"), key("TAB"), key("END"), key("ENTER"),
                             key("S", ctrl=True)])["observations"]
        self.assertIn("Lv.1", actual[-2]["slots"][0])
        self.assertEqual(actual[-1]["state"]["current_party"], ["z_legacy", None, None, None])

    # {
    #   責務: [test_pure_selection_invalid_slots_ids_and_four_slot_contract: 検証: pure selection invalid slots ids and four slot contract]
    #   処理: [1: 検証: pure selection invalid slots ids and four slot contract]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_pure_selection_invalid_slots_ids_and_four_slot_contract(self):
        cases = [
            {"members": [], "records": {"a": {}}, "assignments": [{"slot": 3, "id": "a"}]},
            {"members": ["a"], "records": {"a": {}}, "assignments": [{"slot": -1, "id": "a"}]},
            {"members": ["a"], "records": {"a": {}}, "assignments": [{"slot": 4, "id": None}]},
            {"members": [], "records": {}, "assignments": [{"slot": 0, "id": "../other"}]},
            {"members": [], "records": {}, "assignments": [{"slot": 0, "id": 3}]},
            {"members": ["a"], "records": {"a": {}}, "assignments": [{"slot": 1, "id": "a"}]},
            {"members": ["a", "a"], "records": {"a": {}}},
            {"members": ["missing"], "records": {}},
            {"members": [None] * 4, "records": {}},
        ]
        results = self.probe(cases=cases)["cases"]
        for index, result in enumerate(results):
            with self.subTest(index=index):
                self.assertTrue(result["start_ok"])
                self.assertEqual(len(result["members"]), 4)
                self.assertEqual(result["result"]["ok"], index not in (1, 2, 3, 4, 5))
                self.assertEqual(result["valid"]["ok"], index not in (6, 7))
                self.assertEqual(result["dirty"], index == 0)

    # {
    #   責務: [test_real_state_lock_retains_draft_previous_state_and_cleans_temporary: 検証: real state lock retains draft previous state and cleans temporary]
    #   処理: [1: 検証: real state lock retains draft previous state and cleans temporary]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @unittest.skipUnless(os.name == "nt", "Windows sharing violation probe")
    def test_real_state_lock_retains_draft_previous_state_and_cleans_temporary(self):
        self.seed()
        path = self.profile / "state.json"
        before = self.files()
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
                                       ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
        kernel.CreateFileW.restype = ctypes.c_void_p
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.CreateFileW(str(path), 0x80000000, 3, None, 3, 0, None)
        self.assertNotEqual(handle, ctypes.c_void_p(-1).value, ctypes.get_last_error())
        try:
            actual = self.probe(self.add_c_keyboard() + [key("S", ctrl=True)])["observations"][-1]
            self.assertTrue(actual["editing"])
            self.assertTrue(actual["draft"]["dirty"])
            self.assertIn("保存失敗", actual["message"])
        finally:
            kernel.CloseHandle(handle)
        self.assertEqual(self.files(), before)
        self.assertEqual(list(self.profile.glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
