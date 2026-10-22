"""Actual spring Scene acquisition, Python output compatibility and safe partial retry."""
# {
#   責務: [test_gdscript_ghost_acquisition: Actual spring Scene acquisition, Python output compatibility and safe partial retry.]
#   フィールド: []
# }
from __future__ import annotations

import base64
import copy
import ctypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from kadoka_quest.apps.game import KadokaQuest
from kadoka_quest.apps.progress_session import ProgressSession
from kadoka_quest.core.ai import default_ai
from kadoka_quest.data.field_progress import FieldProgressStore
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.data.state import StateStore

ROOT = Path(__file__).resolve().parents[1]
GODOT = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")
PASSWORD = "へいわなすみか"
OPEN = [{"kind": "open"}, {"kind": "key", "key": "E"}]
MATCH = [{"kind": "type", "value": PASSWORD}, {"kind": "key", "key": "Enter"}]


# {
#   責務: [GDScriptGhostAcquisitionTests: gdscript・おばけ・acquisition・testsの状態と振る舞いを担当する]
#   フィールド: [
#     temporary: temporary
#     content: content
#     name: 名前
#   ]
# }
@unittest.skipUnless(GODOT, "Set KADOKA_GODOT_EXECUTABLE for real acquisition probes")
class GDScriptGhostAcquisitionTests(unittest.TestCase):
    # {
    #   責務: [setUp: 検証に必要な専用fixtureと依存を準備する]
    #   処理: [1: 検証に必要な専用fixtureと依存を準備する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="kadoka-ghost-acquisition-")
        self.addCleanup(self.temporary.cleanup)
        self.content = Path(self.temporary.name)
        shutil.copytree(ROOT / "data", self.content / "data")
        shutil.copytree(ROOT / "assets", self.content / "assets")
        self.name = "default"

    # {
    #   責務: [profile: gdscript・おばけ・acquisition・testsのプロファイルを求める]
    #   処理: [1: gdscript・おばけ・acquisition・testsのプロファイルを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: gdscript・おばけ・acquisition・testsのプロファイルを求めるための結果（Path）]
    # }
    @property
    def profile(self) -> Path:
        return self.content / "saves" / self.name

    # {
    #   責務: [write: gdscript・おばけ・acquisition・testsを書き込む]
    #   処理: [1: gdscript・おばけ・acquisition・testsを書き込む]
    #   引数: [
    #     self: 処理対象インスタンス
    #     relative: relative（str）
    #     value: 値（dict）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def write(self, relative: str, value: dict) -> None:
        path = self.profile / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    # {
    #   責務: [seed: gdscript・おばけ・acquisition・testsのseedを求める]
    #   処理: [1: gdscript・おばけ・acquisition・testsのseedを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     changes: changes
    #   ]
    #   戻り値: [result: gdscript・おばけ・acquisition・testsのseedを求めるための結果（dict）]
    # }
    def seed(self, **changes) -> dict:
        state = {"schema_version": 1, "map_id": "ghost_home", "player": {"x": 17, "y": 8, "direction": "back"},
                 "flags": {"story_complete": False, "ghost_entrance_open": False, "mod_flag": "keep"},
                 "current_party": ["hero_01", None, "missing", None],
                 "revive_point": {"map_id": "starting_town", "x": 18, "y": 11, "custom": "keep"},
                 "mod_state": {"unknown": [3, "値", True]}}
        state.update(changes)
        self.write("state.json", state)
        self.write("items/items.json", {"schema_version": 1, "items": {"orange": 9}, "mod_item": "keep"})
        self.write("parties/custom.json", {"schema_version": 1, "name": "保存済み", "members": ["hero_01"]})
        self.write("meta.json", {"schema_version": 1, "name": self.name, "mod_meta": "keep"})
        self.record("hero_01", "hero")
        return copy.deepcopy(state)

    # {
    #   責務: [record: gdscript・おばけ・acquisition・testsの個体レコードを求める]
    #   処理: [1: gdscript・おばけ・acquisition・testsの個体レコードを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     id: 識別子（str）
    #     species: 種族（str）
    #     changes: changes
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def record(self, id: str, species: str, **changes) -> None:
        repository = GameRepository(self.content / "data")
        store = MonsterStore(self.profile / "monsters", repository)
        record = store.create(species, monster_id=id)
        record.monster.update(changes)
        record.ai.update(battles=71, actions=222, tactic="careful", mod_ai={"keep": [1, 2]},
                         action_preferences={"attack": 0.72})
        store.save(record)

    # {
    #   責務: [files: gdscript・おばけ・acquisition・testsのfilesを求める]
    #   処理: [1: gdscript・おばけ・acquisition・testsのfilesを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     parent: parent（Path | None）
    #   ]
    #   戻り値: [result: gdscript・おばけ・acquisition・testsのfilesを求めるための結果（dict）]
    # }
    def files(self, parent: Path | None = None) -> dict:
        root = parent or self.content
        return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()
                and (root != self.content or path.parts[len(root.parts)] in {"data", "assets", "saves"})}

    # {
    #   責務: [state: gdscript・おばけ・acquisition・testsの状態を求める]
    #   処理: [1: gdscript・おばけ・acquisition・testsの状態を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: gdscript・おばけ・acquisition・testsの状態を求めるための結果（dict）]
    # }
    def state(self) -> dict:
        return json.loads((self.profile / "state.json").read_text(encoding="utf-8"))

    # {
    #   責務: [probe: gdscript・おばけ・acquisition・testsのprobeを求める]
    #   処理: [1: gdscript・おばけ・acquisition・testsのprobeを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     actions: actions（list）
    #   ]
    #   戻り値: [result: gdscript・おばけ・acquisition・testsのprobeを求めるための結果（list）]
    # }
    def probe(self, actions: list) -> list:
        fixture = self.content / "request.json"
        fixture.write_text(json.dumps({"scene": True, "actions": actions}, ensure_ascii=False), encoding="utf-8")
        environment = dict(os.environ, KADOKA_CONTENT_ROOT=str(self.content),
                           KADOKA_GDSCRIPT_SAVE_ROOT=str(self.content / "saves"), KADOKA_GDSCRIPT_SAVE_NAME=self.name,
                           KADOKA_SAVE_DIR=str(self.content / "python-never"))
        result = subprocess.run([str(GODOT), "--headless", "--path", str(ROOT / "gdscript"), "--script",
                                 "res://tests/run_password_probe.gd", "--", str(fixture)], cwd=self.content,
                                env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=60, check=False)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout[-1000:])
        self.assertNotIn("SCRIPT ERROR", result.stderr)
        for line in result.stdout.splitlines():
            if line.startswith("KADOKA_PASSWORD="):
                return json.loads(base64.b64decode(line.split("=", 1)[1]))
        self.fail(result.stderr + result.stdout[-1000:])

    # {
    #   責務: [assert_old_files_kept: gdscript・おばけ・acquisition・testsのassert・old・files・keptを求める]
    #   処理: [1: gdscript・おばけ・acquisition・testsのassert・old・files・keptを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     before: before（dict）
    #     state_change: 状態・change（bool）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def assert_old_files_kept(self, before: dict, *, state_change: bool = True) -> None:
        after = self.files()
        state_path = str((self.profile / "state.json").relative_to(self.content))
        for name, value in before.items():
            if name != state_path or not state_change:
                self.assertEqual(after.get(name), value, name)

    # {
    #   責務: [test_missing_two_one_or_none_match_python_reacquire_preserve_ai_party_and_restart: 検証: missing two one or none match python reacquire preserve ai party and restart]
    #   処理: [1: 検証: missing two one or none match python reacquire preserve ai party and restart]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_missing_two_one_or_none_match_python_reacquire_preserve_ai_party_and_restart(self) -> None:
        for index, existing in enumerate(((), ("maru",), ("kadoka",), ("maru", "kadoka"))):
            with self.subTest(existing=existing):
                self.name = f"組{index}"
                baseline = self.seed(map_id="starting_town", player={"x": 18, "y": 14, "direction": "left"})
                for species in existing:
                    self.record(species + "_old", species, name="昔からの" + species, level=77,
                                plus_choices=[species + "_hp"], mod_record={"keep": True})
                before = self.files()
                result = self.probe(OPEN + MATCH + [{"kind": "key", "key": "F6"}])
                acquired = result[3]["acquisition"]
                self.assertTrue(acquired["ok"], acquired)
                self.assertEqual(len(acquired["created"]), 2 - len(existing))
                self.assertFalse(acquired["partial"])
                self.assertEqual([n["species_id"] for n in result[3]["npcs"]], ["maru", "kadoka"])
                self.assertEqual(result[3]["npcs"], result[1]["npcs"])
                owned = result[-1]["owned"]["records"]
                self.assertEqual({entry["monster"]["species_id"] for entry in owned.values()}, {"hero", "maru", "kadoka"})
                self.assertIn("まる", result[-1]["roster_text"])
                self.assertIn("かどか", result[-1]["roster_text"])
                self.assert_old_files_kept(before)
                expected = copy.deepcopy(baseline)
                expected["flags"]["ghost_entrance_open"] = True
                self.assertEqual(self.state(), expected)
                python_root = self.content / f"reference-{index}"
                python_monsters = MonsterStore(python_root / "monsters", GameRepository(self.content / "data"))
                for species in existing:
                    python_monsters.create(species, level=77, monster_id=species + "_old")
                game = KadokaQuest.__new__(KadokaQuest)
                game.monsters = python_monsters
                game.progress_session = ProgressSession(copy.deepcopy(baseline))
                game.field_progress = FieldProgressStore(StateStore(python_root / "state.json"))
                game.reacquire_ghosts()
                expected_new = {r.species_id: r for r in python_monsters.list_records()
                                if not r.monster_id.endswith("_old")}
                python_read = MonsterStore(self.profile / "monsters", GameRepository(self.content / "data"))
                self.assertEqual(len(python_read.list_records()), 3)
                for created in acquired["created"]:
                    actual = python_read.get(created["id"])
                    reference = expected_new[created["species_id"]]
                    value = dict(reference.monster, id=actual.monster_id)
                    self.assertEqual(actual.monster, value)
                    self.assertEqual(actual.ai, default_ai(created["species_id"]))
                    self.assertEqual(actual.ai, reference.ai)
                self.assertEqual(StateStore(self.profile / "state.json").load()["flags"], game.state["flags"])
                again_before = self.files()
                again = self.probe(OPEN + MATCH)[-1]
                self.assertTrue(again["acquisition"]["ok"])
                self.assertEqual(again["acquisition"]["created"], [])
                self.assertIn("2匹とも既に", again["status"])
                self.assertEqual(self.files(), again_before)
                restarted = self.probe([{"kind": "key", "key": "F6"}])[-1]
                self.assertEqual(set(restarted["owned"]["records"]), set(owned))
                self.assertEqual(restarted["player"], [18, 14])

    # {
    #   責務: [test_cancel_mismatch_and_missing_save_do_not_write_or_fake_acquisition: 検証: cancel mismatch and missing save do not write or fake acquisition]
    #   処理: [1: 検証: cancel mismatch and missing save do not write or fake acquisition]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_cancel_mismatch_and_missing_save_do_not_write_or_fake_acquisition(self) -> None:
        missing = self.probe(OPEN + MATCH)[-1]
        self.assertFalse(missing["acquisition"]["ok"])
        self.assertIn("先にF5", missing["status"])
        self.assertFalse((self.content / "saves").exists())
        self.seed()
        before = self.files()
        result = self.probe(OPEN + [{"kind": "type", "value": "あ" * 7}, {"kind": "key", "key": "Enter"},
                                    {"kind": "key", "key": "Escape"}])
        self.assertEqual(result[-1]["acquisition"], {})
        self.assertEqual(self.files(), before)
        self.assertFalse((self.content / "python-never").exists())

    # {
    #   責務: [test_external_state_update_during_input_is_rejected_before_creation: 検証: external state update during input is rejected before creation]
    #   処理: [1: 検証: external state update during input is rejected before creation]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_external_state_update_during_input_is_rejected_before_creation(self) -> None:
        self.seed()
        before = self.files()
        result = self.probe(OPEN + [{"kind": "change_state", "changes": {"external_update": {"keep": 91}}}] + MATCH)[-1]
        self.assertFalse(result["acquisition"]["ok"])
        self.assertEqual(result["acquisition"]["error"], "changed")
        self.assertEqual(result["acquisition"]["created"], [])
        self.assertFalse(self.state()["flags"]["ghost_entrance_open"])
        self.assertEqual(self.state()["external_update"], {"keep": 91})
        self.assert_old_files_kept(before)

    # {
    #   責務: [test_second_publication_failure_is_partial_then_retry_creates_only_missing: 検証: second publication failure is partial then retry creates only missing]
    #   処理: [1: 検証: second publication failure is partial then retry creates only missing]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_second_publication_failure_is_partial_then_retry_creates_only_missing(self) -> None:
        self.seed()
        before = self.files()
        result = self.probe([{"kind": "fault", "mode": "fail_second"}] + OPEN + MATCH)[-1]
        partial = result["acquisition"]
        self.assertFalse(partial["ok"])
        self.assertTrue(partial["partial"])
        self.assertEqual(len(partial["created"]), 1)
        self.assertEqual(partial["created"][0]["species_id"], "maru")
        self.assertIn("部分保存", result["status"])
        self.assertNotIn("牧場に", result["status"])
        self.assertFalse(self.state()["flags"]["ghost_entrance_open"])
        self.assert_old_files_kept(before, state_change=False)
        first_id = partial["created"][0]["id"]
        first_bytes = self.files(self.profile / "monsters" / first_id)
        retry = self.probe(OPEN + MATCH)[-1]["acquisition"]
        self.assertTrue(retry["ok"])
        self.assertEqual([n["species_id"] for n in retry["created"]], ["kadoka"])
        self.assertEqual(self.files(self.profile / "monsters" / first_id), first_bytes)
        self.assertTrue(self.state()["flags"]["ghost_entrance_open"])

    # {
    #   責務: [test_external_update_after_first_publication_keeps_partial_and_retries_against_latest: 検証: external update after first publication keeps partial and retries against latest]
    #   処理: [1: 検証: external update after first publication keeps partial and retries against latest]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_external_update_after_first_publication_keeps_partial_and_retries_against_latest(self) -> None:
        self.seed()
        result = self.probe([{"kind": "fault", "mode": "external_state"}] + OPEN + MATCH)[-1]
        self.assertFalse(result["acquisition"]["ok"])
        self.assertEqual(result["acquisition"]["error"], "changed")
        self.assertTrue(result["acquisition"]["partial"])
        self.assertEqual(len(result["acquisition"]["created"]), 1)
        self.assertEqual(self.state()["external_update"], "kept")
        self.assertFalse(self.state()["flags"]["ghost_entrance_open"])
        retry = self.probe(OPEN + MATCH)[-1]["acquisition"]
        self.assertTrue(retry["ok"])
        self.assertEqual(len(retry["created"]), 1)
        self.assertEqual(self.state()["external_update"], "kept")

    # {
    #   責務: [test_real_windows_lock_keeps_state_and_published_ghosts_then_retry_reuses_ids: 検証: real windows lock keeps state and published ghosts then retry reuses ids]
    #   処理: [1: 検証: real windows lock keeps state and published ghosts then retry reuses ids]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @unittest.skipUnless(os.name == "nt", "Actual Windows replacement lock")
    def test_real_windows_lock_keeps_state_and_published_ghosts_then_retry_reuses_ids(self) -> None:
        self.seed()
        before = self.files()
        state_bytes = (self.profile / "state.json").read_bytes()
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [
            ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
            ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
        ]
        kernel.CreateFileW.restype = ctypes.c_void_p
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.CreateFileW(str(self.profile / "state.json"), 0x80000000, 3, None, 3, 0, None)
        self.assertNotEqual(handle, ctypes.c_void_p(-1).value, ctypes.get_last_error())
        try:
            result = self.probe(OPEN + MATCH)[-1]
        finally:
            kernel.CloseHandle(handle)
        self.assertFalse(result["acquisition"]["ok"])
        self.assertEqual(result["acquisition"]["stage"], "save")
        self.assertTrue(result["acquisition"]["partial"])
        self.assertEqual(len(result["acquisition"]["created"]), 2)
        self.assertIn("部分保存", result["status"])
        self.assertEqual((self.profile / "state.json").read_bytes(), state_bytes)
        self.assert_old_files_kept(before, state_change=False)
        self.assertEqual(list(self.profile.glob(".*.tmp")), [])
        published = self.files(self.profile / "monsters")
        retry = self.probe(OPEN + MATCH)[-1]["acquisition"]
        self.assertTrue(retry["ok"])
        self.assertEqual(retry["created"], [])
        self.assertEqual(self.files(self.profile / "monsters"), published)
        self.assertTrue(self.state()["flags"]["ghost_entrance_open"])

    # {
    #   責務: [test_invalid_flags_or_existing_individuals_refuse_without_repair_or_duplicates: 検証: invalid flags or existing individuals refuse without repair or duplicates]
    #   処理: [1: 検証: invalid flags or existing individuals refuse without repair or duplicates]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_invalid_flags_or_existing_individuals_refuse_without_repair_or_duplicates(self) -> None:
        for index, flags in enumerate((None, [], "bad", True)):
            with self.subTest(flags=flags):
                self.name = f"不正{index}"
                self.seed(flags=flags)
                before = self.files()
                result = self.probe(OPEN + MATCH)[-1]["acquisition"]
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"], "invalid_flags")
                self.assertEqual(self.files(), before)
        self.name = "壊れたAI"
        self.seed()
        self.record("owned_maru", "maru")
        (self.profile / "monsters/owned_maru/ai.json").write_text("{broken", encoding="utf-8")
        before = self.files()
        result = self.probe(OPEN + MATCH)[-1]["acquisition"]
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "invalid_owned")
        self.assertEqual(self.files(), before)

    # {
    #   責務: [test_broken_new_species_stats_skills_or_plus_validate_all_before_any_publication: 検証: broken new species stats skills or plus validate all before any publication]
    #   処理: [1: 検証: broken new species stats skills or plus validate all before any publication]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_broken_new_species_stats_skills_or_plus_validate_all_before_any_publication(self) -> None:
        cases = [("species", {"id": "wrong"}), ("species", {"display_name": ""}),
                 ("species", {"ai_profile": 3}), ("species", {"schema_version": 99}),
                 ("stats", {"levels": {}}), ("skills", {"learnset": "bad"}), ("plus", {"schema_version": 99})]
        for index, (document, changes) in enumerate(cases):
            with self.subTest(document=document, changes=changes):
                self.name = f"定義{index}"
                self.seed()
                path = self.content / f"data/species/kadoka/{document}.json"
                original = path.read_bytes()
                value = json.loads(original)
                value.update(changes)
                path.write_text(json.dumps(value), encoding="utf-8")
                before = self.files()
                result = self.probe(OPEN + MATCH)[-1]["acquisition"]
                self.assertFalse(result["ok"])
                self.assertEqual(result["created"], [])
                self.assertFalse(result["partial"])
                self.assertEqual(self.files(), before)
                path.write_bytes(original)  # Restore this test's own private content, not canonical data.

    # {
    #   責務: [test_many_owned_and_named_slots_have_no_new_limit_and_only_selected_profile_changes: 検証: many owned and named slots have no new limit and only selected profile changes]
    #   処理: [1: 検証: many owned and named slots have no new limit and only selected profile changes]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_many_owned_and_named_slots_have_no_new_limit_and_only_selected_profile_changes(self) -> None:
        self.name = "選択中"
        self.seed()
        for index in range(125):
            self.record(f"slime_{index:03}", "slime")
        for index in range(125):
            self.name = f"別保存{index}"
            self.write("state.json", {"sentinel": index})
        self.name = "選択中"
        before = self.files()
        result = self.probe(OPEN + MATCH + [{"kind": "key", "key": "F6"}])[-1]
        self.assertTrue(result["acquisition"]["ok"])
        self.assertEqual(len(result["owned"]["records"]), 128)
        self.assert_old_files_kept(before)
        self.assertEqual(len(list((self.content / "saves").iterdir())), 126)

    # {
    #   責務: [test_already_open_flag_without_owned_ghosts_reacquires_without_rewriting_state: 検証: already open flag without owned ghosts reacquires without rewriting state]
    #   処理: [1: 検証: already open flag without owned ghosts reacquires without rewriting state]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_already_open_flag_without_owned_ghosts_reacquires_without_rewriting_state(self) -> None:
        self.seed(flags={"ghost_entrance_open": True, "story_complete": True, "unknown": []})
        before = self.files()
        result = self.probe(OPEN + MATCH)[-1]
        self.assertTrue(result["acquisition"]["ok"])
        self.assertEqual(len(result["acquisition"]["created"]), 2)
        self.assertFalse(result["acquisition"]["flag_saved"])
        self.assertEqual([n["species_id"] for n in result["npcs"]], ["maru", "kadoka"])
        self.assert_old_files_kept(before, state_change=False)

    # {
    #   責務: [test_corrupt_or_future_state_and_non_directory_monsters_are_not_repaired: 検証: corrupt or future state and non directory monsters are not repaired]
    #   処理: [1: 検証: corrupt or future state and non directory monsters are not repaired]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_corrupt_or_future_state_and_non_directory_monsters_are_not_repaired(self) -> None:
        for index, value in enumerate(("{broken", '{"schema_version":99}')):
            with self.subTest(value=value):
                self.name = f"壊れた保存{index}"
                self.seed()
                (self.profile / "state.json").write_text(value, encoding="utf-8")
                before = self.files()
                result = self.probe(OPEN + MATCH)[-1]["acquisition"]
                self.assertFalse(result["ok"])
                self.assertEqual(result["created"], [])
                self.assertEqual(self.files(), before)
        self.name = "所有フォルダ破損"
        self.write("state.json", {"schema_version": 1, "map_id": "ghost_home", "player": {"x": 17, "y": 8}})
        self.write("monsters", {"blocked": True})
        before = self.files()
        result = self.probe(OPEN + MATCH)[-1]["acquisition"]
        self.assertFalse(result["ok"])
        self.assertEqual(result["created"], [])
        self.assertEqual(self.files(), before)
