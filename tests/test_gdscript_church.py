"""Private real-Scene checkpoint saves, Python compatibility, refusal and readback safety."""
# {
#   責務: [test_gdscript_church: Private real-Scene checkpoint saves, Python compatibility, refusal and readback safety.]
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

from kadoka_quest.data.field_progress import FieldProgressStore
from kadoka_quest.data.state import StateStore

ROOT = Path(__file__).resolve().parents[1]
GODOT = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")
TOWN = {"map_id": "starting_town", "x": 18, "y": 11, "name": "はじまりの街の教会"}
VILLAGE = {"map_id": "rokuta_village", "x": 14, "y": 10, "name": "ロクター教会"}
OPEN = {"kind": "open"}
KEY = {"kind": "key", "key": "E"}


# {
#   責務: [GDScriptChurchTests: gdscript・教会・testsの状態と振る舞いを担当する]
#   フィールド: [
#     temporary: temporary
#     content: content
#     name: 名前
#   ]
# }
@unittest.skipUnless(GODOT, "Set KADOKA_GODOT_EXECUTABLE for real church probes")
class GDScriptChurchTests(unittest.TestCase):
    # {
    #   責務: [setUp: 検証に必要な専用fixtureと依存を準備する]
    #   処理: [1: 検証に必要な専用fixtureと依存を準備する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="kadoka-church-")
        self.addCleanup(self.temporary.cleanup)
        self.content = Path(self.temporary.name)
        shutil.copytree(ROOT / "data", self.content / "data")
        shutil.copytree(ROOT / "assets", self.content / "assets")
        self.name = "default"

    # {
    #   責務: [profile: gdscript・教会・testsのプロファイルを求める]
    #   処理: [1: gdscript・教会・testsのプロファイルを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: gdscript・教会・testsのプロファイルを求めるための結果（Path）]
    # }
    @property
    def profile(self) -> Path:
        return self.content / "saves" / self.name

    # {
    #   責務: [write: gdscript・教会・testsを書き込む]
    #   処理: [1: gdscript・教会・testsを書き込む]
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
    #   責務: [seed: gdscript・教会・testsのseedを求める]
    #   処理: [1: gdscript・教会・testsのseedを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     changes: changes
    #   ]
    #   戻り値: [result: gdscript・教会・testsのseedを求めるための結果（dict）]
    # }
    def seed(self, **changes) -> dict:
        state = {"schema_version": 1, "map_id": "starting_town",
                 "player": {"x": 18, "y": 14, "direction": "left", "custom": "keep"},
                 "current_party": ["old", None, "missing", None], "flags": {"mod_flag": "keep"},
                 "revive_point": {"map_id": "ghost_home", "x": 17, "y": 8, "name": "以前の場所", "mod": True},
                 "mod_state": {"unknown": [3, "値", True]}}
        state.update(changes)
        self.write("state.json", state)
        self.write("monsters/old/monster.json", {"schema_version": 1, "id": "old", "species_id": "maru",
                   "name": "昔からのまる", "level": 77, "plus_choices": ["maru_hp"], "equipment_id": None})
        self.write("monsters/old/ai.json", {"schema_version": 1, "profile": "normal", "battles": 71,
                   "actions": 222, "action_preferences": {"attack": 0.72}, "mod_ai": [1, 2]})
        self.write("items/items.json", {"schema_version": 1, "items": {"orange": 9}, "mod_item": "keep"})
        self.write("parties/custom.json", {"schema_version": 1, "name": "保存済み", "members": ["old"]})
        self.write("meta.json", {"schema_version": 1, "name": self.name, "mod_meta": "keep"})
        return copy.deepcopy(state)

    # {
    #   責務: [files: gdscript・教会・testsのfilesを求める]
    #   処理: [1: gdscript・教会・testsのfilesを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: gdscript・教会・testsのfilesを求めるための結果（dict）]
    # }
    def files(self) -> dict:
        return {str(path.relative_to(self.content)): path.read_bytes() for path in self.content.rglob("*")
                if path.is_file() and path.parts[len(self.content.parts)] in {"data", "assets", "saves"}}

    # {
    #   責務: [state: gdscript・教会・testsの状態を求める]
    #   処理: [1: gdscript・教会・testsの状態を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: gdscript・教会・testsの状態を求めるための結果（dict）]
    # }
    def state(self) -> dict:
        return json.loads((self.profile / "state.json").read_text(encoding="utf-8"))

    # {
    #   責務: [probe: gdscript・教会・testsのprobeを求める]
    #   処理: [1: gdscript・教会・testsのprobeを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     actions: actions（list | None）
    #     cases: cases（list | None）
    #   ]
    #   戻り値: [result: gdscript・教会・testsのprobeを求めるための結果（list）]
    # }
    def probe(self, actions: list | None = None, cases: list | None = None) -> list:
        fixture = self.content / "request.json"
        fixture.write_text(json.dumps({"cases": cases} if cases is not None else {"actions": actions or []},
                                      ensure_ascii=False), encoding="utf-8")
        environment = dict(os.environ, KADOKA_CONTENT_ROOT=str(self.content),
                           KADOKA_GDSCRIPT_SAVE_ROOT=str(self.content / "saves"), KADOKA_GDSCRIPT_SAVE_NAME=self.name,
                           KADOKA_SAVE_DIR=str(self.content / "python-never"))
        result = subprocess.run([str(GODOT), "--headless", "--path", str(ROOT / "gdscript"), "--script",
                                 "res://tests/run_church_probe.gd", "--", str(fixture)], cwd=self.content,
                                env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=60, check=False)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout[-1500:])
        self.assertNotIn("SCRIPT ERROR", result.stderr)
        for line in result.stdout.splitlines():
            if line.startswith("KADOKA_CHURCH="):
                return json.loads(base64.b64decode(line.split("=", 1)[1]))
        self.fail(result.stderr + result.stdout[-1500:])

    # {
    #   責務: [assert_files_kept: gdscript・教会・testsのassert・files・keptを求める]
    #   処理: [1: gdscript・教会・testsのassert・files・keptを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     before: before（dict）
    #     state_change: 状態・change（bool）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def assert_files_kept(self, before: dict, *, state_change: bool = False) -> None:
        after = self.files()
        state_name = str((self.profile / "state.json").relative_to(self.content))
        if state_change:
            before = {name: value for name, value in before.items() if name != state_name}
            after = {name: value for name, value in after.items() if name != state_name}
        self.assertEqual(before, after)
        self.assertFalse((self.content / "python-never").exists())

    # {
    #   責務: [test_pure_point_types_one_key_plan_and_input_preservation: 検証: pure point types one key plan and input preservation]
    #   処理: [1: 検証: pure point types one key plan and input preservation]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_pure_point_types_one_key_plan_and_input_preservation(self) -> None:
        cases = [{"point": TOWN, "state": {"unknown": [1], "revive_point": TOWN}},
                 {"point": dict(VILLAGE, x=14.0, extra={"keep": True}), "state": {"player": {"x": 2}}}]
        invalid = [None, [], "point", True, {}, *[
            dict(TOWN, **{key: value}) for key, values in {
                "map_id": [None, 1, ""], "name": [None, 1, "", "  "],
                "x": [None, True, "18", 1.5, []], "y": [None, False, "11", 1.5, {}],
            }.items() for value in values
        ]]
        cases.extend({"point": point, "state": {"unknown": [1]}} for point in invalid)
        result = self.probe(cases=cases)
        for index, (case, observation) in enumerate(zip(cases, result)):
            with self.subTest(index=index):
                self.assertEqual(observation["input"], case)
                self.assertEqual(observation["result"]["ok"], index < 2)
                if index < 2:
                    expected = dict(case["state"], revive_point=case["point"])
                    self.assertEqual(observation["result"]["plan"]["state"], expected)
                    self.assertEqual(observation["result"]["plan"]["changed"], index == 1)

    # {
    #   責務: [test_real_church_keys_save_restart_and_python_read_preserve_other_data: 検証: real church keys save restart and python read preserve other data]
    #   処理: [1: 検証: real church keys save restart and python read preserve other data]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_real_church_keys_save_restart_and_python_read_preserve_other_data(self) -> None:
        for key in ("E", "Enter", "Space"):
            with self.subTest(key=key):
                self.name = key
                baseline = self.seed()
                before = self.files()
                result = self.probe([OPEN, {"kind": "key", "key": key}])
                self.assertTrue(result[-1]["result"]["ok"], result[-1])
                self.assertEqual(self.state(), dict(baseline, revive_point=TOWN))
                self.assertEqual(result[-1]["player"], result[1]["player"])
                self.assertEqual(result[-1]["npcs"], result[1]["npcs"])
                self.assertEqual(result[-1]["clock"], result[1]["clock"])
                self.assertIn("HP回復・敗北復活", result[-1]["status"])
                self.assertEqual(self.probe()[0]["state"]["revive_point"], TOWN)
                python_state = StateStore(self.profile / "state.json").load()
                self.assertEqual(FieldProgressStore.revive_point(python_state), TOWN)
                self.assertEqual(python_state["inventory"], {"orange": 9})
                self.assert_files_kept(before, state_change=True)

    # {
    #   責務: [test_two_canonical_churches_same_noop_and_no_teleport: 検証: two canonical churches same noop and no teleport]
    #   処理: [1: 検証: two canonical churches same noop and no teleport]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_two_canonical_churches_same_noop_and_no_teleport(self) -> None:
        baseline = self.seed()
        result = self.probe([OPEN, KEY,
                             {"kind": "open", "map_id": "rokuta_village", "entry": {"x": 14, "y": 9, "direction": "back"}},
                             KEY, KEY])
        self.assertEqual(result[2]["result"]["point"], TOWN)
        self.assertEqual(result[4]["result"]["point"], VILLAGE)
        self.assertTrue(result[4]["result"]["saved"])
        self.assertFalse(result[5]["result"]["saved"])
        self.assertEqual(result[4]["player"], result[3]["player"])
        self.assertEqual(self.state(), dict(baseline, revive_point=VILLAGE))
        before = self.files()
        self.probe([{"kind": "register", "revive": VILLAGE}])
        self.assert_files_kept(before)

    # {
    #   責務: [test_old_missing_schema_direction_and_revive_only_adds_requested_key: 検証: old missing schema direction and revive only adds requested key]
    #   処理: [1: 検証: old missing schema direction and revive only adds requested key]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_old_missing_schema_direction_and_revive_only_adds_requested_key(self) -> None:
        baseline = self.seed()
        for key in ("schema_version", "revive_point"):
            baseline.pop(key)
        baseline["player"].pop("direction")
        self.write("state.json", baseline)
        point = dict(TOWN, mod_point={"unknown": [1, "値"]})
        result = self.probe([{"kind": "register", "revive": point}])[-1]["outcome"]
        self.assertTrue(result["ok"], result)
        self.assertEqual(self.state(), dict(baseline, revive_point=point))
        reference = StateStore(self.content / "reference" / "state.json")
        expected = copy.deepcopy(baseline)
        expected["inventory"] = {"orange": 9}
        FieldProgressStore(reference).register_church(expected, point)
        self.assertEqual(reference.load()["revive_point"], self.state()["revive_point"])

    # {
    #   責務: [test_no_save_refuses_without_bootstrapping: 検証: no save refuses without bootstrapping]
    #   処理: [1: 検証: no save refuses without bootstrapping]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_no_save_refuses_without_bootstrapping(self) -> None:
        before = self.files()
        result = self.probe([OPEN, KEY])[-1]
        self.assertFalse(result["result"]["ok"])
        self.assertIn("先にF5", result["status"])
        self.assertFalse(self.profile.exists())
        self.assert_files_kept(before)

    # {
    #   責務: [test_missing_malformed_unsafe_out_of_range_or_blocked_revive_refuses: 検証: missing malformed unsafe out of range or blocked revive refuses]
    #   処理: [1: 検証: missing malformed unsafe out of range or blocked revive refuses]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_missing_malformed_unsafe_out_of_range_or_blocked_revive_refuses(self) -> None:
        self.seed()
        points = [None, {}, dict(TOWN, map_id="../escape"), dict(TOWN, map_id="missing_map"),
                  dict(TOWN, x=True), dict(TOWN, y="11"), dict(TOWN, x=1.5), dict(TOWN, name=None),
                  dict(TOWN, x=-1), dict(TOWN, x=999), dict(TOWN, x=0, y=0), dict(TOWN, x=25, y=14)]
        before = self.files()
        result = self.probe([{"kind": "register", "revive": point} for point in points])
        for observation in result[1:]:
            with self.subTest(point=observation["outcome"]):
                self.assertFalse(observation["outcome"]["ok"])
        self.assert_files_kept(before)

    # {
    #   責務: [test_invalid_target_map_shape_and_tile_definition_refuse_without_script_error: 検証: invalid target map shape and tile definition refuse without script error]
    #   処理: [1: 検証: invalid target map shape and tile definition refuse without script error]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_invalid_target_map_shape_and_tile_definition_refuse_without_script_error(self) -> None:
        self.seed()
        path = self.content / "data/maps/rokuta_village/map.json"
        original = json.loads(path.read_text(encoding="utf-8"))
        mutations = [{"id": "wrong"}, {"width": True}, {"height": "24"}, {"events": {}},
                     {"events": ["bad"]}, {"events": [{"x": "14", "y": 10}]}, {"tiles": []}]
        broken_tile = copy.deepcopy(original["tiles"])
        broken_tile[10][14] = "missing_block"
        mutations.append({"tiles": broken_tile})
        for change in mutations:
            with self.subTest(change=next(iter(change))):
                path.write_text(json.dumps(dict(original, **change)), encoding="utf-8")
                before = self.files()
                result = self.probe([{"kind": "register", "revive": VILLAGE}])[-1]["outcome"]
                self.assertFalse(result["ok"], result)
                self.assert_files_kept(before)

    # {
    #   責務: [test_corrupt_or_unsupported_state_is_not_repaired: 検証: corrupt or unsupported state is not repaired]
    #   処理: [1: 検証: corrupt or unsupported state is not repaired]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_corrupt_or_unsupported_state_is_not_repaired(self) -> None:
        baseline = self.seed()
        path = self.profile / "state.json"
        values = [b'{"bad":', b'[]', json.dumps(dict(baseline, schema_version=99)).encode(),
                  json.dumps(dict(baseline, player={"x": 0, "y": 0})).encode()]
        for value in values:
            with self.subTest(value=value[:20]):
                path.write_bytes(value)
                before = self.files()
                result = self.probe([OPEN, KEY])[-1]["result"]
                self.assertFalse(result["ok"], result)
                self.assert_files_kept(before)

    # {
    #   責務: [test_external_change_after_begin_is_kept_and_retry_uses_latest: 検証: external change after begin is kept and retry uses latest]
    #   処理: [1: 検証: external change after begin is kept and retry uses latest]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_external_change_after_begin_is_kept_and_retry_uses_latest(self) -> None:
        baseline = self.seed()
        result = self.probe([{"kind": "begin", "revive": TOWN},
                             {"kind": "change_state", "changes": {"external_update": "kept"}}, {"kind": "commit"}])
        self.assertEqual(result[-1]["outcome"]["error"], "changed")
        self.assertEqual(self.state(), dict(baseline, external_update="kept"))
        result = self.probe([OPEN, KEY])[-1]["result"]
        self.assertTrue(result["ok"], result)
        self.assertEqual(self.state(), dict(baseline, external_update="kept", revive_point=TOWN))

    # {
    #   責務: [test_store_digest_race_and_postwrite_verification_do_not_fake_success: 検証: store digest race and postwrite verification do not fake success]
    #   処理: [1: 検証: store digest race and postwrite verification do not fake success]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_store_digest_race_and_postwrite_verification_do_not_fake_success(self) -> None:
        for mode in ("before_write", "false_success", "after_write"):
            with self.subTest(mode=mode):
                self.name = mode
                baseline = self.seed()
                before = self.files()
                result = self.probe([{"kind": "fault", "mode": mode}, OPEN, KEY])[-1]["result"]
                self.assertFalse(result["ok"], result)
                self.assertEqual(result["error"], "changed")
                if mode == "false_success":
                    self.assertEqual(self.state(), baseline)
                    self.assert_files_kept(before)
                else:
                    expected = dict(baseline, external_update="kept")
                    if mode == "after_write":
                        expected["revive_point"] = TOWN
                        self.assertTrue(result["saved"])
                    self.assertEqual(self.state(), expected)
                    self.assert_files_kept(before, state_change=True)

    # {
    #   責務: [test_modal_and_echo_do_not_register_via_keys_or_direct_scene_call: 検証: modal and echo do not register via keys or direct scene call]
    #   処理: [1: 検証: modal and echo do not register via keys or direct scene call]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_modal_and_echo_do_not_register_via_keys_or_direct_scene_call(self) -> None:
        self.seed()
        before = self.files()
        for modal in ("password", "roster", "party", "presets"):
            with self.subTest(modal=modal):
                actions = [OPEN]
                if modal == "presets":
                    actions.append({"kind": "party"})
                actions += [{"kind": modal}, KEY, {"kind": "register", "revive": TOWN}]
                result = self.probe(actions)[-1]
                self.assertEqual(result["outcome"]["error"], "modal_active")
                self.assertEqual(result["result"], {})
                self.assert_files_kept(before)
        result = self.probe([OPEN, dict(KEY, echo=True)])[-1]
        self.assertEqual(result["result"], {})
        self.assert_files_kept(before)

    # {
    #   責務: [test_windows_replace_lock_keeps_files_noop_and_retry_after_release: 検証: windows replace lock keeps files noop and retry after release]
    #   処理: [1: 検証: windows replace lock keeps files noop and retry after release]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @unittest.skipUnless(os.name == "nt", "Windows sharing violation probe")
    def test_windows_replace_lock_keeps_files_noop_and_retry_after_release(self) -> None:
        self.seed()
        before = self.files()
        path = self.profile / "state.json"
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [
            ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
            ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
        ]
        kernel.CreateFileW.restype = ctypes.c_void_p
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.CreateFileW(str(path), 0x80000000, 3, None, 3, 0, None)
        self.assertNotEqual(handle, ctypes.c_void_p(-1).value, ctypes.get_last_error())
        try:
            result = self.probe([OPEN, KEY])[-1]["result"]
            self.assertFalse(result["ok"], result)
            self.assertEqual(result["error"], "replace_failed")
            self.assert_files_kept(before)
            self.assertEqual(list(self.profile.glob("*.tmp")), [])
        finally:
            kernel.CloseHandle(handle)
        self.assertTrue(self.probe([OPEN, KEY])[-1]["result"]["ok"])
        before = self.files()
        handle = kernel.CreateFileW(str(path), 0x80000000, 3, None, 3, 0, None)
        self.assertNotEqual(handle, ctypes.c_void_p(-1).value, ctypes.get_last_error())
        try:
            result = self.probe([OPEN, KEY])[-1]["result"]
            self.assertTrue(result["ok"], result)
            self.assertFalse(result["saved"])
            self.assert_files_kept(before)
        finally:
            kernel.CloseHandle(handle)

    # {
    #   責務: [test_linked_profile_refuses_and_never_writes_target: 検証: linked profile refuses and never writes target]
    #   処理: [1: 検証: linked profile refuses and never writes target]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @unittest.skipUnless(os.name == "nt", "Windows directory junction probe")
    def test_linked_profile_refuses_and_never_writes_target(self) -> None:
        self.seed()
        target = self.profile
        self.name = "linked"
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(self.profile), str(target)],
                                capture_output=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        # The setup-created alias is included in the baseline; it is not a game write.
        before = self.files()
        result = self.probe([OPEN, KEY])[-1]["result"]
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["error"], "linked_profile")
        # Both the real target and its private alias must remain unchanged.
        self.name = "default"
        self.assert_files_kept(before)
