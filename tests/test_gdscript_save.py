"""Isolated real-Godot field persistence, old Python format compatibility and failure safety."""
from __future__ import annotations

import base64
import ctypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from kadoka_quest.data.savedata import SaveDataManager
from kadoka_quest.data.state import DEFAULT_STATE, StateStore

ROOT = Path(__file__).resolve().parents[1]
GODOT = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")


@unittest.skipUnless(GODOT, "Set KADOKA_GODOT_EXECUTABLE to run real save/load probes")
class GDScriptSaveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="kadoka-gdscript-save-")
        self.addCleanup(self.temporary.cleanup)
        self.content = Path(self.temporary.name)
        shutil.copytree(ROOT / "data", self.content / "data")
        shutil.copytree(ROOT / "assets", self.content / "assets")
        self.save_root = self.content / "gd-saves"
        self.save_root.mkdir()
        self.legacy_root = self.content / "python-saves"
        self.legacy_root.mkdir()
        (self.legacy_root / "sentinel.json").write_text('{"do_not_touch": true}', encoding="utf-8")

    def profile(self, name: str = "default") -> Path:
        return self.save_root / name

    def state(self, **changes) -> dict:
        state = json.loads(json.dumps(DEFAULT_STATE, ensure_ascii=False))
        state.pop("inventory")
        state.update(changes)
        return state

    def seed(self, state: dict, name: str = "default") -> Path:
        path = self.profile(name)
        path.mkdir(exist_ok=True)
        (path / "state.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        return path

    def probe(self, actions: list | None = None, name: str = "default", names: list | None = None) -> dict:
        fixture = self.content / "probe.json"
        fixture.write_text(json.dumps({"actions": actions or [], "names": names or []}), encoding="utf-8")
        environment = dict(
            os.environ, KADOKA_CONTENT_ROOT=str(self.content), KADOKA_SAVE_DIR=str(self.legacy_root),
            KADOKA_GDSCRIPT_SAVE_ROOT=str(self.save_root), KADOKA_GDSCRIPT_SAVE_NAME=name,
        )
        result = subprocess.run(
            [str(GODOT), "--headless", "--path", str(ROOT / "gdscript"),
             "--script", "res://tests/run_save_probe.gd", "--", str(fixture)],
            cwd=self.content, env=environment, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout[-1000:])
        self.assertNotIn("SCRIPT ERROR", result.stderr)
        for line in result.stdout.splitlines():
            if line.startswith("KADOKA_SAVE_RESULT="):
                return json.loads(base64.b64decode(line.split("=", 1)[1]).decode("utf-8"))
        self.fail(result.stdout[-1000:] + result.stderr)

    @staticmethod
    def pose(observation: dict) -> tuple:
        return tuple(observation[key] for key in ("map_id", "x", "y", "direction"))

    def test_f5_save_f9_reload_and_new_process_restore_position_and_direction(self) -> None:
        observations = self.probe([
            {"kind": "open", "map_id": "fresh_forest", "entry": {"x": 22, "y": 26, "direction": "left"}},
            {"kind": "key", "key": "F5"},
            {"kind": "open", "map_id": "starting_town"},
            {"kind": "key", "key": "F9"},
        ])["observations"]
        expected = ("fresh_forest", 22, 26, "left")
        self.assertEqual(self.pose(observations[-1]), expected)
        self.assertTrue(observations[2]["status"].startswith("保存しました"))
        self.assertTrue(observations[-1]["status"].startswith("読み込みました"))
        self.assertEqual(self.pose(self.probe()["observations"][0]), expected)
        loaded = StateStore(self.profile() / "state.json").load()
        self.assertEqual(loaded["player"], {"x": 22, "y": 26, "direction": "left"})
        self.assertEqual(loaded["inventory"], DEFAULT_STATE["inventory"])
        for folder in ("monsters", "items", "parties"):
            self.assertTrue((self.profile() / folder).is_dir())

    def test_existing_python_profile_unknown_fields_and_owned_files_are_preserved(self) -> None:
        state = self.state(
            current_party=["hero_01", "ball_01"],
            player={"x": 18, "y": 14, "mod_player": "保持"},
            flags={"quest_extra": True}, mod_state={"nested": [1, "残す", False]},
        )
        profile = self.seed(state)
        files = {
            "monsters/hero_01/monster.json": '{"name":"主人公","level":100,"plus":[1,2]}',
            "monsters/hero_01/ai.json": '{"q":0.125,"custom":"学習済み"}',
            "items/items.json": '{"schema_version":1,"items":{"orange":99},"mod":"残す"}',
            "parties/party_01.json": '{"members":["hero_01","ball_01"]}',
            "meta.json": '{"name":"既存","created_at":"original"}',
        }
        for relative, text in files.items():
            path = profile / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        before = {relative: (profile / relative).read_bytes() for relative in files}
        observations = self.probe([
            {"kind": "open", "map_id": "starting_town", "entry": {"x": 18, "y": 14, "direction": "left"}},
            {"kind": "key", "key": "F9"},
            {"kind": "open", "map_id": "greenwood", "entry": {"x": 1, "y": 6, "direction": "right"}},
            {"kind": "save"},
        ])["observations"]
        self.assertEqual(self.pose(observations[2]), ("starting_town", 18, 14, "front"))
        stored = json.loads((profile / "state.json").read_text(encoding="utf-8"))
        for key in ("current_party", "flags", "mod_state", "revive_point"):
            self.assertEqual(stored[key], state[key])
        self.assertEqual(stored["player"]["mod_player"], "保持")
        self.assertEqual(before, {relative: (profile / relative).read_bytes() for relative in files})

    def test_corrupt_json_is_not_overwritten_and_runtime_is_unchanged(self) -> None:
        path = self.seed(self.state()) / "state.json"
        broken = b'{"map_id": '
        path.write_bytes(broken)
        observations = self.probe([{"kind": "save"}, {"kind": "load"}])["observations"]
        for observation in observations:
            self.assertEqual(self.pose(observation), ("starting_town", 18, 14, "front"))
            self.assertIn("失敗", observation["status"])
        self.assertEqual(path.read_bytes(), broken)
        self.assertEqual(list(path.parent.glob("*.tmp")), [])

    def test_invalid_schema_map_and_coordinates_fail_without_overwrite(self) -> None:
        cases = [
            self.state(schema_version=99), self.state(map_id="missing_map"),
            self.state(player={"x": 1.5, "y": 14}), self.state(player={"x": True, "y": 14}),
            self.state(player={"x": 999, "y": 14}), self.state(player={"x": -1, "y": 14}),
            self.state(player={"x": 0, "y": 0}), self.state(player={"x": 25, "y": 14}),
            self.state(map_id="ghost_home", player={"x": 10, "y": 7}),
            self.state(player={"x": 18, "y": 14, "direction": "invalid"}),
        ]
        for index, state in enumerate(cases):
            with self.subTest(case=index):
                name = f"bad_{index}"
                path = self.seed(state, name) / "state.json"
                before = path.read_bytes()
                result = self.probe([{"kind": "save"}, {"kind": "load"}], name)["observations"]
                self.assertEqual(self.pose(result[-1]), ("starting_town", 18, 14, "front"))
                self.assertFalse(result[1]["outcome"])
                self.assertFalse(result[2]["outcome"])
                self.assertEqual(path.read_bytes(), before)

    def test_missing_profile_read_is_readonly_and_reports_missing_on_f9(self) -> None:
        result = self.probe([{"kind": "key", "key": "F9"}])["observations"]
        self.assertFalse(self.profile().exists())
        self.assertIn("セーブがありません", result[-1]["status"])

    def test_named_profiles_remain_independent_and_python_save_root_is_untouched(self) -> None:
        before = (self.legacy_root / "sentinel.json").read_bytes()
        self.probe([{"kind": "save"}], "一つ目")
        other = self.profile("一つ目") / "state.json"
        first = other.read_bytes()
        self.probe([
            {"kind": "open", "map_id": "greenwood", "entry": {"x": 1, "y": 6}}, {"kind": "save"},
        ], "二つ目")
        self.assertEqual(other.read_bytes(), first)
        self.assertEqual((self.legacy_root / "sentinel.json").read_bytes(), before)
        self.assertEqual(sorted(path.name for path in self.legacy_root.iterdir()), ["sentinel.json"])
        self.assertEqual(SaveDataManager(self.save_root).list_names(), ["一つ目", "二つ目"])

    def test_name_validation_matches_python_and_invalid_names_do_not_create_files(self) -> None:
        names = ["default", "日本語セーブ", "a" * 45, "", " ", "../other", "a/b", "a\\b", "CON", "nul.txt",
                 "COM1", "lpt9", " name", "name ", "name.", "a:b", "a?b", "a\n", ".."]
        manager = SaveDataManager(self.content / "name-reference")
        results = self.probe(names=names)["names"]
        for name, result in zip(names, results):
            with self.subTest(name=name):
                try:
                    clean = manager.validate_name(name)
                except ValueError:
                    self.assertFalse(result["ok"])
                else:
                    self.assertTrue(result["ok"])
                    self.assertEqual(result["name"], clean)
        self.probe([{"kind": "save"}], "../escape")
        self.assertEqual(list(self.save_root.iterdir()), [])
        self.assertFalse((self.content / "escape").exists())

    def test_stale_digest_does_not_overwrite_external_changes(self) -> None:
        path = self.seed(self.state()) / "state.json"
        before = path.read_bytes()
        result = self.probe([{"kind": "stale_write"}])["observations"][-1]["outcome"]
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "changed")
        self.assertEqual(path.read_bytes(), before)

    @unittest.skipUnless(os.name == "nt", "Windows sharing violation probe")
    def test_real_windows_lock_preserves_previous_state_and_removes_owned_temporary(self) -> None:
        path = self.seed(self.state()) / "state.json"
        before = path.read_bytes()
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [
            ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
            ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
        ]
        kernel.CreateFileW.restype = ctypes.c_void_p
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        # Reads are allowed; replacing/deleting this exact private fixture is denied.
        handle = kernel.CreateFileW(str(path), 0x80000000, 3, None, 3, 0, None)
        self.assertNotEqual(handle, ctypes.c_void_p(-1).value, ctypes.get_last_error())
        try:
            result = self.probe([
                {"kind": "open", "map_id": "greenwood", "entry": {"x": 1, "y": 6}}, {"kind": "save"},
            ])["observations"][-1]
            self.assertFalse(result["outcome"])
            self.assertIn("保存失敗", result["status"])
        finally:
            kernel.CloseHandle(handle)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(list(path.parent.glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
