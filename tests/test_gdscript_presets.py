"""Real-Godot preset UI and state-independent, editable JSON persistence."""
from __future__ import annotations

import ctypes
import json
import os
import unittest

import test_gdscript_party as fixture
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.parties import PartyStore
from kadoka_quest.data.repository import GameRepository

key = fixture.key
click = fixture.click
OPEN = [key("F6"), key("E"), key("P")]


class GDScriptPresetBoundaryTests(unittest.TestCase):
    def test_contract_ui_and_service_boundaries(self):
        for relative in ("engine/party_preset_contract.gd", "ui/party_preset_view.gd"):
            source = (fixture.ROOT / "gdscript" / relative).read_text(encoding="utf-8")
            for forbidden in ("FileAccess.", "DirAccess.", "write_atomic(", "load_profile("):
                self.assertNotIn(forbidden, source)
        source = (fixture.ROOT / "gdscript/application/party_presets.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess.", "DirAccess.", "Button.new", "Label.new", "save_profile("):
            self.assertNotIn(forbidden, source)


@unittest.skipUnless(fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real preset probes")
class GDScriptPresetTests(unittest.TestCase):
    setUp = fixture.GDScriptPartyTests.setUp
    probe = fixture.GDScriptPartyTests.probe
    seed = fixture.GDScriptPartyTests.seed
    write = fixture.GDScriptPartyTests.write
    add_c_keyboard = fixture.GDScriptPartyTests.add_c_keyboard

    def files(self, omit_state=False):
        return {name.replace("\\", "/"): data
                for name, data in fixture.GDScriptPartyTests.files(self, omit_state).items()}

    def test_keyboard_save_duplicate_names_and_python_load_keep_existing_bytes(self):
        self.seed()
        before = self.files()
        actions = self.add_c_keyboard() + [
            key("P"), key("TAB"), {"kind": "text", "text": "対ボス"}, key("ENTER"), key("ENTER"),
        ]
        actual = self.probe(actions)["observations"][-1]
        self.assertEqual(actual["preset_name"], "対ボス")
        self.assertTrue(actual["preset_visible"])
        self.assertEqual(actual["preset_count"], 3)
        after = self.files()
        self.assertEqual({name: after[name] for name in before}, before)
        self.assertEqual(set(after) - set(before), {"parties/party.json", "parties/party_2.json"})
        document = json.loads(after["parties/party.json"])
        self.assertEqual(document, {"schema_version": 1, "name": "対ボス", "members": ["a", "b", "c", None]})
        store = PartyStore(self.profile / "parties")
        monsters = MonsterStore(self.profile / "monsters", GameRepository(self.content / "data"))
        loaded = store.load(self.profile / "parties/party.json", monsters)
        self.assertEqual([record.monster_id if record else None for record in loaded], document["members"])

    def test_mouse_entry_save_and_load_then_explicit_current_party_commit(self):
        self.seed()
        before = self.files()
        actual = self.probe([key("F6"), click("edit"), click("presets"), click("preset_name"),
                             {"kind": "text", "text": "Adventure"}, click("preset_save"),
                             click("preset_list", 1), click("preset_load"), key("S", ctrl=True)])["observations"]
        self.assertEqual(actual[-1]["state"]["current_party"], ["b", None, "a", None])
        after = self.files()
        for name, value in before.items():
            if name != "state.json":
                self.assertEqual(after[name], value)
        self.assertIn("parties/adventure.json", after)

    def test_loaded_preset_is_draft_only_and_escape_cancels_without_save(self):
        self.seed()
        before = self.files()
        actual = self.probe(OPEN + [key("ENTER"), key("ESC")])["observations"]
        self.assertEqual([row["id"] for row in actual[-2]["draft"]["party"]], ["b", None, "a", None])
        self.assertTrue(actual[-2]["draft"]["dirty"])
        self.assertEqual(self.files(), before)

    def test_saved_preset_remains_when_current_party_draft_is_cancelled(self):
        self.seed()
        before = (self.profile / "state.json").read_bytes()
        actions = self.add_c_keyboard() + [
            key("P"), key("TAB"), {"kind": "text", "text": "saved"}, key("ENTER"), key("ESC"), key("ESC"),
        ]
        actual = self.probe(actions)["observations"][-1]
        self.assertFalse(actual["editing"])
        self.assertEqual((self.profile / "state.json").read_bytes(), before)
        self.assertTrue((self.profile / "parties/saved.json").is_file())

    def test_restart_reads_saved_preset_and_can_apply_it(self):
        self.seed()
        self.probe(self.add_c_keyboard() + [key("P"), key("TAB"), {"kind": "text", "text": "new"}, key("ENTER")])
        actual = self.probe(OPEN + [key("END"), key("ENTER"), key("S", ctrl=True)])["observations"][-1]
        self.assertEqual(actual["state"]["current_party"], ["a", "b", "c", None])

    def test_missing_individual_becomes_empty_without_rewriting_preset(self):
        self.seed()
        document = {"schema_version": 1, "name": "古い編成",
                    "members": ["gone", "b", None, "also_gone"], "mod": {"keep": 1}}
        path = self.write("parties/existing.json", document)
        before = path.read_bytes()
        actual = self.probe(OPEN + [key("ENTER"), key("S", ctrl=True)])["observations"]
        self.assertIn("注意2件", actual[-2]["message"])
        self.assertEqual(actual[-1]["state"]["current_party"], [None, "b", None, None])
        self.assertEqual(path.read_bytes(), before)

    def test_duplicate_preset_refused_without_losing_existing_dirty_draft(self):
        self.seed()
        self.write("parties/existing.json", {"name": "重複", "members": ["a", "a"]})
        before = self.files()
        actual = self.probe(self.add_c_keyboard() + [key("P"), key("ENTER")])["observations"][-1]
        self.assertTrue(actual["preset_visible"])
        self.assertIn("重複", actual["preset_message"])
        self.assertEqual([row["id"] for row in actual["draft"]["party"]], ["a", "b", "c", None])
        self.assertEqual(self.files(), before)

    def test_corrupt_and_invalid_presets_warn_and_stay_untouched(self):
        self.seed()
        invalid = [[], {"schema_version": 2, "name": "x", "members": []}, {"name": "", "members": []},
                   {"name": "x", "members": ["a"] * 5}, {"name": "x", "members": [False]},
                   {"name": "x", "members": [2]}, {"name": "x", "members": {}}, {"name": "x"}]
        for index, value in enumerate(invalid):
            self.write(f"parties/bad{index}.json", value)
        (self.profile / "parties/broken.json").write_text("{broken", encoding="utf-8")
        before = self.files()
        actual = self.probe(OPEN)["observations"][-1]
        self.assertEqual(actual["preset_count"], 1)
        self.assertIn("注意9件", actual["preset_message"])
        self.assertEqual(self.files(), before)

    def test_changed_preset_is_reread_on_load_not_from_cached_catalog(self):
        self.seed()
        document = {"schema_version": 1, "name": "updated", "members": ["c", None, None, "a"]}
        actual = self.probe(OPEN + [
            {"kind": "preset_raw", "filename": "existing.json", "raw": json.dumps(document)}, key("ENTER"),
        ])["observations"][-1]
        self.assertEqual([row["id"] for row in actual["draft"]["party"]], document["members"])
        self.assertEqual(actual["state"]["current_party"], ["a", "b"])

    def test_corruption_after_catalog_refuses_load_and_retains_draft(self):
        self.seed()
        actions = self.add_c_keyboard() + [
            key("P"),
            {"kind": "preset_raw", "filename": "existing.json", "raw": "{broken"}, key("ENTER"),
        ]
        actual = self.probe(actions)["observations"][-1]
        self.assertTrue(actual["preset_visible"])
        self.assertIn("読込失敗", actual["preset_message"])
        self.assertEqual([row["id"] for row in actual["draft"]["party"]], ["a", "b", "c", None])

    def test_large_catalog_navigation_scroll_and_no_slot_limit(self):
        self.seed()
        for index in range(120):
            self.write(f"parties/z{index:03}.json", {"name": f"編成{index}", "members": ["c", None, None, None]})
        actions = OPEN + [key("END"), key("PAGEUP"), key("HOME"), key("PAGEDOWN"), key("END"), key("ENTER")]
        actual = self.probe(actions)["observations"]
        self.assertEqual(actual[3]["preset_count"], 121)
        self.assertGreater(actual[4]["preset_scroll"], 0)
        self.assertLess(actual[5]["preset_selection"][0], 120)
        self.assertEqual(actual[6]["preset_selection"], [0])
        self.assertGreater(actual[7]["preset_selection"][0], 0)
        self.assertEqual([row["id"] for row in actual[-1]["draft"]["party"]], ["c", None, None, None])

    def test_browser_back_by_escape_f6_and_button_keeps_dirty_draft(self):
        self.seed()
        before = self.files()
        for back in (key("ESC"), key("F6"), click("preset_back")):
            with self.subTest(back=back):
                actual = self.probe(self.add_c_keyboard() + [key("P"), back])["observations"][-1]
                self.assertTrue(actual["editing"])
                self.assertFalse(actual["preset_visible"])
                self.assertTrue(actual["draft"]["dirty"])
                self.assertEqual([row["id"] for row in actual["draft"]["party"]], ["a", "b", "c", None])
                self.assertEqual(self.files(), before)

    def test_name_field_home_end_and_delete_do_not_mutate_party(self):
        self.seed()
        actions = OPEN + [key("TAB"), {"kind": "text", "text": "abc"}, key("HOME"),
                          key("DELETE"), key("END"), {"kind": "text", "text": "d"}]
        actual = self.probe(actions)["observations"][-1]
        self.assertEqual(actual["preset_name"], "bcd")
        self.assertFalse(actual["draft"]["dirty"])

    def test_tab_focus_is_contained_and_name_submission_works_keyboard_only(self):
        self.seed()
        actual = self.probe(OPEN + [key("TAB")] * 6 + [key("TAB", shift=True)])["observations"]
        self.assertEqual(actual[3]["focus"], actual[-2]["focus"])
        self.assertNotEqual(actual[-1]["focus"], actual[3]["focus"])
        self.assertEqual(len({item["focus"] for item in actual[3:-1]}), 6)

    def test_f5_refresh_and_field_keys_are_modal_without_writing_state(self):
        self.seed()
        before = self.files()
        actual = self.probe(OPEN + [key("RIGHT"), key("F5"), key("F9"), key("SPACE")])["observations"]
        self.assertEqual((actual[-1]["x"], actual[-1]["y"]), (actual[0]["x"], actual[0]["y"]))
        self.assertEqual(self.files(), before)

    def test_empty_name_and_lost_selected_individual_refuse_creation(self):
        self.seed()
        before = self.files()
        actual = self.probe(OPEN + [key("TAB"), key("ENTER")])["observations"][-1]
        self.assertIn("追加保存失敗", actual["preset_message"])
        self.assertEqual(self.files(), before)
        actions = self.add_c_keyboard() + [
            key("P"), {"kind": "remove_ai", "id": "c"}, key("TAB"), {"kind": "text", "text": "test"}, key("ENTER"),
        ]
        actual = self.probe(actions)["observations"][-1]
        self.assertIn("読込できない", actual["preset_message"])
        self.assertFalse((self.profile / "parties/test.json").exists())

    def test_filename_traversal_and_reserved_names_refused_without_changes(self):
        self.seed()
        before = self.files()
        for filename in ("../state.json", "a/b.json", "a\\b.json", "CON.json", ".json", "existing.txt"):
            with self.subTest(filename=filename):
                actual = self.probe(OPEN + [{"kind": "load_preset", "filename": filename}])["observations"][-1]
                self.assertTrue(actual["preset_visible"])
                self.assertIn("不正な", actual["preset_message"])
                self.assertEqual(self.files(), before)

    def test_new_profile_cannot_create_presets_before_initial_field_save(self):
        actual = self.probe(OPEN)["observations"][-1]
        self.assertFalse(actual["preset_visible"])
        self.assertFalse(self.profile.exists())

    def test_parties_path_is_file_save_fails_without_removing_it(self):
        self.seed()
        # Replace only the private fixture's folder, never a user save.
        shutil_path = self.profile / "parties"
        (shutil_path / "existing.json").unlink()
        shutil_path.rmdir()
        shutil_path.write_text("do not replace", encoding="utf-8")
        before = self.files()
        actual = self.probe(OPEN + [key("TAB"), {"kind": "text", "text": "test"}, key("ENTER")])["observations"][-1]
        self.assertIn("追加保存失敗", actual["preset_message"])
        self.assertEqual(self.files(), before)

    def test_pure_documents_missing_members_and_portable_stems(self):
        names = ["対ボス", "Boss Fight", "___Boss___", "___", "CON", "nul.txt", "a" * 100, "../escape"]
        cases = [{"name": name, "document": {"name": name, "members": ["a", "missing"]}, "records": {"a": {}}}
                 for name in names]
        actual = self.probe(preset_cases=cases)["preset_cases"]
        for name, value in zip(names, actual):
            with self.subTest(name=name):
                stem = PartyStore._slug(name)[:80]
                if stem in ("con", "nul"):
                    stem = "party_" + stem
                self.assertEqual(value["stem"], stem)
                self.assertEqual(value["project"]["members"], ["a", None, None, None])
                self.assertEqual(len(value["project"]["warnings"]), 1)

    def test_pure_invalid_schema_types_and_duplicate_members_are_refused(self):
        documents = [
            {"schema_version": True, "name": "bad", "members": []},
            {"schema_version": 1.5, "name": "bad", "members": []},
            {"schema_version": 2, "name": "bad", "members": []},
            {"name": " ", "members": []}, {"name": 3, "members": []},
            {"name": "bad", "members": [False]}, {"name": "bad", "members": [3]},
            {"name": "bad", "members": {}}, {"name": "bad", "members": ["a"] * 5},
            {"name": "valid", "members": ["a", "a"]}, {"name": "valid", "members": []},
        ]
        cases = [{"document": document, "records": {"a": {}}} for document in documents]
        actual = self.probe(preset_cases=cases)["preset_cases"]
        for index, value in enumerate(actual):
            with self.subTest(index=index):
                self.assertEqual(value["valid"]["ok"], index >= 9)
                self.assertEqual(value["project"]["ok"], index == 10)

    @unittest.skipUnless(os.name == "nt", "Windows read-lock probe")
    def test_unreadable_preset_does_not_reset_draft_or_change_files(self):
        self.seed()
        path = self.profile / "parties/existing.json"
        before = self.files()
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
                                       ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
        kernel.CreateFileW.restype = ctypes.c_void_p
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.CreateFileW(str(path), 0x80000000, 0, None, 3, 0, None)
        self.assertNotEqual(handle, ctypes.c_void_p(-1).value, ctypes.get_last_error())
        try:
            actions = self.add_c_keyboard() + [
                key("P"),
                {"kind": "load_preset", "filename": "existing.json"},
            ]
            actual = self.probe(actions)["observations"][-1]
            self.assertTrue(actual["preset_visible"])
            self.assertEqual([row["id"] for row in actual["draft"]["party"]], ["a", "b", "c", None])
            self.assertIn("読込失敗", actual["preset_message"])
        finally:
            kernel.CloseHandle(handle)
        self.assertEqual(self.files(), before)


if __name__ == "__main__":
    unittest.main()
