"""Real Godot bounded input parity and isolated spring Scene/native/virtual modal tests."""
# {
#   責務: [test_gdscript_password: Real Godot bounded input parity and isolated spring Scene/native/virtual modal tests.]
#   フィールド: []
# }
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import unittest

from kadoka_quest.apps.password_session import PasswordSession

ROOT = Path(__file__).resolve().parents[1]
GODOT = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")
PASSWORD = "へいわなすみか"
KANA_KEYS = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"
OPEN = [{"kind": "open"}, {"kind": "key", "key": "E"}]


# {
#   責務: [GDScriptPasswordTests: gdscript・暗号・testsの状態と振る舞いを担当する]
#   フィールド: [
#     temporary: temporary
#     content: content
#   ]
# }
@unittest.skipUnless(GODOT, "Set KADOKA_GODOT_EXECUTABLE for real password probes")
class GDScriptPasswordTests(unittest.TestCase):
    # {
    #   責務: [setUp: 検証に必要な専用fixtureと依存を準備する]
    #   処理: [1: 検証に必要な専用fixtureと依存を準備する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="kadoka-password-")
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
    #   責務: [probe: gdscript・暗号・testsのprobeを求める]
    #   処理: [1: gdscript・暗号・testsのprobeを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     request: 要求（dict）
    #   ]
    #   戻り値: [result: gdscript・暗号・testsのprobeを求めるための結果（list）]
    # }
    def probe(self, request: dict) -> list:
        if request.get("scene"):
            self.prepare_scene()
        fixture = self.content / "request.json"
        fixture.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
        environment = dict(os.environ, KADOKA_CONTENT_ROOT=str(self.content),
                           KADOKA_GDSCRIPT_SAVE_ROOT=str(self.content / "saves"), KADOKA_GDSCRIPT_SAVE_NAME="default",
                           KADOKA_SAVE_DIR=str(self.content / "python-never"))
        result = subprocess.run([str(GODOT), "--headless", "--path", str(ROOT / "gdscript"), "--script",
                                 "res://tests/run_password_probe.gd", "--", str(fixture)], cwd=self.content,
                                env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=40, check=False)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout[-1000:])
        self.assertNotIn("SCRIPT ERROR", result.stderr)
        self.assertNotIn("ERROR:", result.stderr)
        for line in result.stdout.splitlines():
            if line.startswith("KADOKA_PASSWORD="):
                return json.loads(base64.b64decode(line.split("=", 1)[1]))
        self.fail(result.stderr + result.stdout[-1000:])

    # {
    #   責務: [scene: gdscript・暗号・testsのsceneを求める]
    #   処理: [1: gdscript・暗号・testsのsceneを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     actions: actions（list）
    #   ]
    #   戻り値: [result: gdscript・暗号・testsのsceneを求めるための結果（list）]
    # }
    def scene(self, actions: list) -> list:
        return self.probe({"scene": True, "actions": actions})

    # {
    #   責務: [snapshot: gdscript・暗号・testsを状態を複製する]
    #   処理: [1: gdscript・暗号・testsを状態を複製する]
    #   引数: [session: セッション（PasswordSession）]
    #   戻り値: [result: gdscript・暗号・testsを状態を複製するための結果（dict）]
    # }
    @staticmethod
    def snapshot(session: PasswordSession) -> dict:
        return {key: getattr(session, key) for key in ("input_text", "message", "active", "maximum_length")}

    # {
    #   責務: [test_operation_sequences_match_python_including_empty_invalid_full_and_closed: 検証: operation sequences match python including empty invalid full and closed]
    #   処理: [1: 検証: operation sequences match python including empty invalid full and closed]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_operation_sequences_match_python_including_empty_invalid_full_and_closed(self) -> None:
        basic = [{"kind": "submit"}, {"kind": "append", "value": "へ"}, {"kind": "backspace"},
                 {"kind": "cancel"}, {"kind": "open"}, {"kind": "backspace"}, {"kind": "submit"}]
        basic += [{"kind": "append", "value": value} for value in ("", "x", "が", "平和", "へい", "😀", "\n", " ")]
        basic += [{"kind": "append", "value": char} for char in PASSWORD + "あ"]
        basic += [{"kind": "submit"}, {"kind": "append", "value": "へ"}, {"kind": "backspace"},
                  {"kind": "submit"}, {"kind": "open"}, {"kind": "append", "value": "あ"},
                  {"kind": "submit"}, {"kind": "cancel"}, {"kind": "open"}]
        rng = random.Random(224)
        choices = [{"kind": kind} for kind in ("open", "cancel", "submit", "backspace")]
        choices += [{"kind": "append", "value": value} for value in KANA_KEYS + "😀aが"]
        cases = [{"operations": basic}]
        for secret, keys in ((PASSWORD, KANA_KEYS), ("😀あ", "😀あ"), ("", ""), ("a", "ab")):
            cases.append({"secret": secret, "keys": keys, "operations": [rng.choice(choices) for _ in range(500)]})
        results = self.probe({"cases": cases})
        for case, observations in zip(cases, results):
            session = PasswordSession(case.get("secret", PASSWORD), case.get("keys", KANA_KEYS))
            self.assertEqual(observations[0]["state"], self.snapshot(session))
            for index, (operation, observation) in enumerate(zip(case["operations"], observations[1:])):
                with self.subTest(secret=session.secret, index=index, operation=operation):
                    method = getattr(session, operation["kind"])
                    expected = method(operation["value"]) if operation["kind"] == "append" else method()
                    self.assertEqual(observation, {"result": expected, "state": self.snapshot(session)})

    # {
    #   責務: [test_canonical_constants_and_ui_do_not_own_secret_or_rule: 検証: canonical constants and ui do not own secret or rule]
    #   処理: [1: 検証: canonical constants and ui do not own secret or rule]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_canonical_constants_and_ui_do_not_own_secret_or_rule(self) -> None:
        source = (ROOT / "src/kadoka_quest/apps/game.py").read_text(encoding="utf-8")
        self.assertIn(f'PASSWORD = "{PASSWORD}"', source)
        self.assertIn(f'KANA_KEYS = tuple("{KANA_KEYS}")', source)
        view = (ROOT / "gdscript/ui/password_view.gd").read_text(encoding="utf-8")
        for forbidden in (PASSWORD, "FileAccess", "SaveStore", "secret", "maximum_length"):
            self.assertNotIn(forbidden, view)

    # {
    #   責務: [test_spring_opens_real_seven_slots_and_full_kana_keyboard: 検証: spring opens real seven slots and full kana keyboard]
    #   処理: [1: 検証: spring opens real seven slots and full kana keyboard]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_spring_opens_real_seven_slots_and_full_kana_keyboard(self) -> None:
        result = self.scene(OPEN)[-1]
        self.assertTrue(result["visible"])
        self.assertTrue(result["state"]["active"])
        self.assertEqual(result["slots"], ["＿"] * 7)
        self.assertEqual(set(result["keys"]), set(KANA_KEYS) | {"submit", "cancel", "backspace"})
        self.assertEqual(result["state"]["maximum_length"], 7)
        self.assertTrue(result["bounds_ok"], (result["panel_rect"], result["window_size"]))
        self.assertFalse((self.content / "saves").exists())

    # {
    #   責務: [test_native_unicode_limit_backspace_and_keypad_enter_match_without_fake_acquisition: 検証: native unicode limit backspace and keypad enter match without fake acquisition]
    #   処理: [1: 検証: native unicode limit backspace and keypad enter match without fake acquisition]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_native_unicode_limit_backspace_and_keypad_enter_match_without_fake_acquisition(self) -> None:
        result = self.scene(OPEN + [
            {"kind": "type", "value": PASSWORD + "あx😀"},
            {"kind": "key", "key": "Backspace"}, {"kind": "type", "value": "か"},
            {"kind": "key", "key": "KPEnter"},
        ])
        self.assertEqual(result[2]["state"]["input_text"], PASSWORD)
        self.assertEqual(result[2]["slots"], list(PASSWORD))
        self.assertEqual(result[2]["native_text"], "")
        self.assertEqual(result[3]["state"]["input_text"], PASSWORD[:-1])
        self.assertFalse(result[-1]["visible"])
        self.assertEqual(result[-1]["result"], {"kind": "password_matched"})
        self.assertEqual(result[-1]["signals"], [{"kind": "password_matched"}])
        self.assertIn("先にF5", result[-1]["status"])
        self.assertFalse(result[-1]["acquisition"]["ok"])
        self.assertNotIn("仲間にな", result[-1]["status"])
        self.assertFalse((self.content / "saves").exists())

    # {
    #   責務: [test_virtual_key_clicks_erase_and_submit_through_real_controls: 検証: virtual key clicks erase and submit through real controls]
    #   処理: [1: 検証: virtual key clicks erase and submit through real controls]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_virtual_key_clicks_erase_and_submit_through_real_controls(self) -> None:
        actions = OPEN + [{"kind": "click", "target": char} for char in PASSWORD[:-1] + "あ"]
        actions += [{"kind": "click", "target": "backspace"}, {"kind": "click", "target": "か"},
                    {"kind": "click", "target": "submit"}]
        result = self.scene(actions)[-1]
        self.assertEqual(result["state"]["input_text"], PASSWORD)
        self.assertEqual(result["signals"], [{"kind": "password_matched"}])
        self.assertFalse(result["visible"])

    # {
    #   責務: [test_empty_and_wrong_submit_stay_open_cancel_and_reopen_reset_input: 検証: empty and wrong submit stay open cancel and reopen reset input]
    #   処理: [1: 検証: empty and wrong submit stay open cancel and reopen reset input]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_empty_and_wrong_submit_stay_open_cancel_and_reopen_reset_input(self) -> None:
        result = self.scene(OPEN + [
            {"kind": "key", "key": "Enter"}, {"kind": "click", "target": "あ"},
            {"kind": "key", "key": "Enter"}, {"kind": "key", "key": "Escape"},
            {"kind": "key", "key": "E"},
        ])
        for observation in (result[2], result[4]):
            self.assertEqual(observation["message"], "あいことばが違います。")
            self.assertTrue(observation["state"]["active"])
            self.assertEqual(observation["signals"], [])
        self.assertEqual(result[5]["result"], {"kind": "password_cancelled"})
        self.assertEqual(result[-1]["state"]["input_text"], "")
        self.assertEqual(result[-1]["message"], "7文字のあいことばを入力してください。")
        self.assertTrue(result[-1]["visible"])

    # {
    #   責務: [test_virtual_cancel_and_confirm_echo_do_not_duplicate_a_result: 検証: virtual cancel and confirm echo do not duplicate a result]
    #   処理: [1: 検証: virtual cancel and confirm echo do not duplicate a result]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_virtual_cancel_and_confirm_echo_do_not_duplicate_a_result(self) -> None:
        result = self.scene(OPEN + [
            {"kind": "type", "value": PASSWORD}, {"kind": "key", "key": "Enter", "echo": True},
            {"kind": "click", "target": "cancel"},
        ])
        self.assertTrue(result[-2]["visible"])
        self.assertEqual(result[-2]["signals"], [])
        self.assertEqual(result[-1]["signals"], [{"kind": "password_cancelled"}])
        self.assertFalse(result[-1]["visible"])

    # {
    #   責務: [test_committed_text_signal_and_unicode_with_virtual_button_focus_do_not_double_append: 検証: committed text signal and unicode with virtual button focus do not double append]
    #   処理: [1: 検証: committed text signal and unicode with virtual button focus do not double append]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_committed_text_signal_and_unicode_with_virtual_button_focus_do_not_double_append(self) -> None:
        result = self.scene(OPEN + [
            {"kind": "commit_signal", "value": "へいx😀わなすみかあ"},
            {"kind": "key", "key": "Backspace"}, {"kind": "focus", "target": "あ"},
            {"kind": "type", "value": "か"}, {"kind": "key", "key": "Enter"},
        ])
        self.assertEqual(result[2]["state"]["input_text"], PASSWORD)
        self.assertEqual(result[2]["native_text"], "")
        self.assertEqual(result[-1]["state"]["input_text"], PASSWORD)
        self.assertEqual(result[-1]["signals"], [{"kind": "password_matched"}])

    # {
    #   責務: [test_modal_freezes_clock_actor_positions_keyboard_and_direct_save_load_until_resumed: 検証: modal freezes clock actor positions keyboard and direct save load until resumed]
    #   処理: [1: 検証: modal freezes clock actor positions keyboard and direct save load until resumed]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_modal_freezes_clock_actor_positions_keyboard_and_direct_save_load_until_resumed(self) -> None:
        actions = OPEN + [{"kind": "tick", "delta": 30}, {"kind": "key", "key": "Right"}]
        actions += [{"kind": "key", "key": key} for key in ("F5", "F9", "F6")]
        actions += [{"kind": "save"}, {"kind": "load"}, {"kind": "roster"}, {"kind": "party"},
                    {"kind": "tick", "delta": 30}, {"kind": "key", "key": "Escape"},
                    {"kind": "tick", "delta": 0.449}, {"kind": "tick", "delta": 0.001}]
        result = self.scene(actions)
        for observation in result[1:13]:
            self.assertEqual(observation["clock"], 0)
            self.assertEqual(observation["player"], [17, 8])
            self.assertEqual(observation["npcs"], result[1]["npcs"])
            self.assertEqual(observation["keyboard_elapsed"], 0)
            self.assertFalse(observation["roster"])
            self.assertFalse(observation["party"])
        self.assertIs(result[7]["outcome"], False)
        self.assertIs(result[8]["outcome"], False)
        self.assertAlmostEqual(result[-2]["clock"], 449)
        self.assertEqual(result[-2]["npcs"][0]["move_count"], 0)
        self.assertAlmostEqual(result[-1]["clock"], 450)
        self.assertLessEqual(result[-1]["npcs"][0]["move_count"], 1)
        self.assertEqual(result[-1]["npcs"][1]["move_count"], 0)
        self.assertFalse((self.content / "saves").exists())

    # {
    #   責務: [test_tab_space_virtual_navigation_and_wrong_full_length_stay_modal: 検証: tab space virtual navigation and wrong full length stay modal]
    #   処理: [1: 検証: tab space virtual navigation and wrong full length stay modal]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_tab_space_virtual_navigation_and_wrong_full_length_stay_modal(self) -> None:
        result = self.scene(OPEN + [
            {"kind": "key", "key": "Tab"}, {"kind": "key", "key": "Space"},
            {"kind": "type", "value": "あ" * 6}, {"kind": "key", "key": "Enter"},
        ])
        self.assertEqual(result[3]["state"]["input_text"], "あ")
        self.assertEqual(result[-1]["state"]["input_text"], "あ" * 7)
        self.assertEqual(result[-1]["message"], "あいことばが違います。")
        self.assertTrue(result[-1]["visible"])
        self.assertEqual(result[-1]["signals"], [])
        self.assertEqual(result[-1]["player"], [17, 8])

    # {
    #   責務: [test_cancel_and_already_complete_match_keep_json_and_ghosts_unchanged: 検証: cancel and already complete match keep json and ghosts unchanged]
    #   処理: [1: 検証: cancel and already complete match keep json and ghosts unchanged]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_cancel_and_already_complete_match_keep_json_and_ghosts_unchanged(self) -> None:
        self.prepare_scene()
        profile = self.content / "saves/default"
        profile.mkdir(parents=True)
        for name in ("items/items.json", "parties/keep.json", "meta.json"):
            target = profile / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('{"mod_keep": "unmodified"}', encoding="utf-8")
        for acquired in (False, True):
            state = {"schema_version": 1, "map_id": "ghost_home", "player": {"x": 17, "y": 8, "direction": "back"},
                     "flags": {"ghost_entrance_open": acquired}, "current_party": [], "mod_keep": {"value": 7}}
            (profile / "state.json").write_text(json.dumps(state), encoding="utf-8")
            for id in (("maru_01", "kadoka_01") if acquired else ()):
                folder = profile / "monsters" / id
                folder.mkdir(parents=True, exist_ok=True)
                (folder / "ai.json").write_text('{"learning":"keep"}', encoding="utf-8")
                record = {"id": id, "species_id": id[:-3], "level": 1, "name": id, "plus_choices": []}
                (folder / "monster.json").write_text(json.dumps(record), encoding="utf-8")
            before = self.content_bytes()
            actions = [{"kind": "key", "key": "E"}, {"kind": "type", "value": PASSWORD}]
            if acquired:
                actions += [{"kind": "key", "key": "Enter"}, {"kind": "key", "key": "E"}]
            actions.append({"kind": "key", "key": "Escape"})
            result = self.scene(actions)
            if acquired:
                self.assertEqual(result[2]["result"], {"kind": "password_matched"})
                self.assertTrue(result[2]["acquisition"]["ok"])
            self.assertEqual(result[-1]["result"], {"kind": "password_cancelled"})
            self.assertEqual([n["species_id"] for n in result[-1]["npcs"]], ["maru", "kadoka"])
            self.assertEqual(self.content_bytes(), before)
        self.assertFalse((self.content / "python-never").exists())

    # {
    #   責務: [content_bytes: gdscript・暗号・testsのcontent・bytesを求める]
    #   処理: [1: gdscript・暗号・testsのcontent・bytesを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: gdscript・暗号・testsのcontent・bytesを求めるための結果（dict）]
    # }
    def content_bytes(self) -> dict:
        return {p.relative_to(self.content): p.read_bytes() for parent in ("data", "assets", "saves")
                for p in (self.content / parent).rglob("*") if p.is_file()}
