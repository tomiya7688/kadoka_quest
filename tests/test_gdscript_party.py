"""Current-party drafts, real Godot controls and failure-safe state-only persistence."""
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


def key(name, **modifiers):
    return {"kind": "key", "key": name, **modifiers}


def click(target, index=0):
    return {"kind": "click", "target": target, "index": index}


class GDScriptPartyBoundaryTests(unittest.TestCase):
    def test_rules_and_view_do_not_access_files_and_service_does_not_render(self):
        for relative in ("engine/party_selection.gd", "ui/party_view.gd"):
            source = (ROOT / "gdscript" / relative).read_text(encoding="utf-8")
            for forbidden in ("FileAccess.", "DirAccess.", "load_profile(", "save_profile("):
                self.assertNotIn(forbidden, source)
        source = (ROOT / "gdscript/application/party_editor.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess.", "DirAccess.", "Label.new", "Button.new", "Input."):
            self.assertNotIn(forbidden, source)


@unittest.skipUnless(GODOT, "Set KADOKA_GODOT_EXECUTABLE for real party/control probes")
class GDScriptPartyTests(unittest.TestCase):
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

    def write(self, relative, value):
        path = self.profile / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

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

    def files(self, omit_state=False):
        return {str(path.relative_to(self.profile)): path.read_bytes() for path in self.profile.rglob("*")
                if path.is_file() and not (omit_state and path.name == "state.json")}

    def add_c_keyboard(self):
        return [key("F6"), key("E"), key("DOWN"), key("DOWN"), key("TAB"), key("END"), key("ENTER")]

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

    def test_mouse_editor_entry_slot_assignment_clear_and_save(self):
        self.seed()
        actual = self.probe([key("F6"), click("edit"), click("slots", 2), click("owned", 2), click("assign"),
                             click("slots", 0), click("clear"), click("save")])["observations"][-1]
        self.assertFalse(actual["editing"])
        self.assertEqual(actual["state"]["current_party"], [None, "b", "c", None])

    def test_keyboard_focus_and_enter_can_activate_save_button(self):
        self.seed()
        actions = self.add_c_keyboard() + [key("TAB"), key("TAB"), key("TAB"), key("ENTER")]
        actual = self.probe(actions)["observations"][-1]
        self.assertFalse(actual["editing"])
        self.assertEqual(actual["state"]["current_party"], ["a", "b", "c", None])

    def test_party_save_keeps_unsaved_position_and_next_f5_preserves_party(self):
        state = self.seed()
        actions = [key("RIGHT")] + self.add_c_keyboard() + [key("S", ctrl=True), key("ESC"), key("F5")]
        actual = self.probe(actions)["observations"]
        party_saved = actual[-3]
        self.assertEqual(party_saved["x"], state["player"]["x"] + 1)
        self.assertEqual(party_saved["state"]["player"], state["player"])
        self.assertEqual(actual[-1]["state"]["player"]["x"], party_saved["x"])
        self.assertEqual(actual[-1]["state"]["current_party"], ["a", "b", "c", None])

    def test_unselected_broken_individual_warns_without_blocking_valid_party_save(self):
        self.seed()
        self.write("monsters/broken/monster.json", {"id": "broken", "species_id": "missing", "name": "不正個体"})
        before = self.files(omit_state=True)
        actual = self.probe(self.add_c_keyboard() + [key("S", ctrl=True)])["observations"]
        self.assertTrue(actual[2]["draft"]["warnings"])
        self.assertEqual(actual[-1]["state"]["current_party"], ["a", "b", "c", None])
        self.assertEqual(self.files(omit_state=True), before)

    def test_delete_and_reassign_to_change_order_with_empty_slots(self):
        self.seed(["a", "b", "c", None])
        actual = self.probe([key("F6"), key("E"), key("DELETE"), key("END"), key("TAB"), key("HOME"),
                             key("ENTER"), key("S", ctrl=True)])["observations"][-1]
        self.assertEqual(actual["state"]["current_party"], [None, "b", "c", "a"])

    def test_duplicate_assignment_rejected_without_changing_draft_or_files(self):
        self.seed()
        before = self.files()
        actual = self.probe([key("F6"), key("E"), key("END"), key("TAB"), key("ENTER")])["observations"][-1]
        self.assertIn("複数枠", actual["message"])
        self.assertFalse(actual["draft"]["dirty"])
        self.assertEqual([item["id"] for item in actual["draft"]["party"]], ["a", "b", None, None])
        self.assertEqual(self.files(), before)

    def test_cancel_by_escape_f6_and_button_keeps_all_bytes(self):
        self.seed()
        before = self.files()
        for cancel in (key("ESC"), key("F6"), click("cancel")):
            with self.subTest(cancel=cancel):
                actual = self.probe(self.add_c_keyboard() + [cancel])["observations"][-1]
                self.assertFalse(actual["editing"])
                self.assertTrue(actual["roster_visible"])
                self.assertEqual(self.files(), before)

    def test_no_change_save_does_not_reformat_short_legacy_party(self):
        self.seed()
        before = self.files()
        actual = self.probe([key("F6"), key("E"), key("S", ctrl=True)])["observations"][-1]
        self.assertFalse(actual["editing"])
        self.assertIn("変更はありません", actual["status"])
        self.assertEqual(self.files(), before)

    def test_field_movement_interaction_f5_f9_are_blocked_while_editing(self):
        self.seed()
        before = self.files()
        results = self.probe(self.add_c_keyboard() + [key("RIGHT"), key("F5"), key("F9"), key("SPACE")])["observations"]
        self.assertTrue(results[-1]["editing"])
        self.assertTrue(results[-1]["draft"]["dirty"])
        self.assertEqual((results[-1]["x"], results[-1]["y"]), (results[0]["x"], results[0]["y"]))
        self.assertEqual(self.files(), before)

    def test_tab_focus_cycles_and_shift_tab_returns_within_editor(self):
        self.seed()
        actual = self.probe([key("F6"), key("E")] + [key("TAB")] * 6 + [key("TAB", shift=True)])["observations"]
        initial = actual[2]["focus"]
        self.assertEqual(actual[-2]["focus"], initial)
        self.assertNotEqual(actual[-1]["focus"], initial)
        self.assertEqual(len({entry["focus"] for entry in actual[2:-1]}), 6)

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

    def test_external_corruption_refuses_save_and_preserves_corrupt_bytes(self):
        self.seed()
        actual = self.probe(self.add_c_keyboard() + [
            {"kind": "external_state", "raw": "{broken"}, key("S", ctrl=True),
        ])["observations"][-1]
        self.assertTrue(actual["editing"])
        self.assertIn("保存失敗", actual["message"])
        self.assertEqual((self.profile / "state.json").read_text(encoding="utf-8"), "{broken")

    def test_member_revalidated_if_ai_removed_after_opening(self):
        self.seed()
        state_before = (self.profile / "state.json").read_bytes()
        actions = self.add_c_keyboard() + [{"kind": "remove_ai", "id": "c"}, key("S", ctrl=True)]
        actual = self.probe(actions)["observations"][-1]
        self.assertTrue(actual["editing"])
        self.assertIn("読込できない", actual["message"])
        self.assertEqual((self.profile / "state.json").read_bytes(), state_before)

    def test_missing_member_can_be_explicitly_removed_but_not_silently_saved(self):
        self.seed(["missing", "b"])
        before = self.files()
        actual = self.probe([key("F6"), key("E"), key("S", ctrl=True)])["observations"][-1]
        self.assertIn("missing", actual["slots"][0])
        self.assertTrue(actual["editing"])
        self.assertEqual(self.files(), before)
        repaired = self.probe([key("F6"), key("E"), key("DELETE"), key("S", ctrl=True)])["observations"][-1]
        self.assertEqual(repaired["state"]["current_party"], [None, "b", None, None])

    def test_duplicate_legacy_member_must_be_explicitly_removed(self):
        self.seed(["a", "a"])
        actual = self.probe([key("F6"), key("E"), key("S", ctrl=True), key("DOWN"), key("DELETE"),
                             key("S", ctrl=True)])["observations"]
        self.assertTrue(actual[3]["editing"])
        self.assertIn("重複", actual[3]["message"])
        self.assertEqual(actual[-1]["state"]["current_party"], ["a", None, None, None])

    def test_malformed_and_overflow_party_refuse_open_without_truncation(self):
        for members in ({"bad": True}, ["a"] * 5, [False], [7], [""]):
            with self.subTest(members=members):
                self.seed(members)
                before = self.files()
                actual = self.probe([key("F6"), key("E")])["observations"][-1]
                self.assertFalse(actual["editing"])
                self.assertIn("編成を開けません", actual["status"])
                self.assertEqual(self.files(), before)

    def test_new_profile_editor_is_readonly_until_first_save(self):
        actual = self.probe([key("F6"), key("E")])["observations"][-1]
        self.assertFalse(actual["editing"])
        self.assertIn("編成を開けません", actual["status"])
        self.assertFalse(self.profile.exists())
        saved = self.probe([key("F5"), key("F6"), key("E")])["observations"][-1]
        self.assertTrue(saved["editing"])
        self.assertEqual(len(saved["draft"]["records"]), 2)

    def test_all_empty_party_is_allowed_and_individuals_remain_owned(self):
        self.seed()
        before = self.files(omit_state=True)
        actual = self.probe([key("F6"), key("E"), key("DELETE"), key("DOWN"), key("DELETE"),
                             key("S", ctrl=True)])["observations"][-1]
        self.assertEqual(actual["state"]["current_party"], [None] * 4)
        self.assertEqual(self.files(omit_state=True), before)

    def test_unicode_individual_id_can_be_assigned_and_roundtripped(self):
        self.seed([])
        self.write("monsters/まる一号/monster.json", {"id": "まる一号", "species_id": "maru", "name": "まる一号", "level": 42})
        self.write("monsters/まる一号/ai.json", default_ai("maru"))
        actual = self.probe([key("F6"), key("E"), key("TAB"), key("END"), key("ENTER"),
                             key("S", ctrl=True)])["observations"][-1]
        self.assertEqual(actual["state"]["current_party"], ["まる一号", None, None, None])

    def test_legacy_missing_level_uses_default_one_in_editor(self):
        # Old individual documents omit optional fields; the view must share the default Lv1.
        self.seed([])
        self.write("monsters/z_legacy/monster.json", {"id": "z_legacy", "species_id": "slime", "name": "旧形式"})
        self.write("monsters/z_legacy/ai.json", default_ai())
        actual = self.probe([key("F6"), key("E"), key("TAB"), key("END"), key("ENTER"),
                             key("S", ctrl=True)])["observations"]
        self.assertIn("Lv.1", actual[-2]["slots"][0])
        self.assertEqual(actual[-1]["state"]["current_party"], ["z_legacy", None, None, None])

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
