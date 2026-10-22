"""公開のゲーム内合言葉の入力規則と、専用保存先でのGodot入力画面を検証します。"""
# {
#   責務: [test_gdscript_password: 公開の湧き場の合言葉について、Pythonとの入力結果一致とGodot画面の入力停止・保存保護を検証します]
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
# 公開のゲーム内合言葉です。アカウントの認証情報や利用者の秘密情報ではありません。
SPRING_PUZZLE_ANSWER = "へいわなすみか"
KANA_KEYS = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"
OPEN = [{"kind": "open"}, {"kind": "key", "key": "E"}]


# {
#   責務: [GDScriptPasswordTests: 実Godotで湧き場の合言葉入力を検証する専用一時領域と検証入口を所有します]
#   フィールド: [
#     temporary: テスト終了時に除去する専用TemporaryDirectory
#     content: data・assets・検証専用savesを置く一時領域のPath
#   ]
# }
@unittest.skipUnless(GODOT, "Set KADOKA_GODOT_EXECUTABLE for real password probes")
class GDScriptPasswordTests(unittest.TestCase):
    # {
    #   責務: [setUp: 暗号入力の検証で実コンテンツや実セーブを変更しないための専用一時領域を用意します]
    #   処理: [
    #     1: 一時領域の自動片付けを登録し、fixtureの保存先を保持します
    #   ]
    #   引数: [
    #     self: 専用一時領域とGodot検証入口を所有するGDScriptPasswordTests
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def setUp(self) -> None:
        # 一時領域の寿命をテストケースへ結び付け、成功・失敗のどちらでも片付けます。
        self.temporary = tempfile.TemporaryDirectory(prefix="kadoka-password-")
        self.addCleanup(self.temporary.cleanup)
        self.content = Path(self.temporary.name)

    # {
    #   責務: [prepare_scene: GodotのScene検証に必要なdataとassetsを、未準備の場合だけ専用領域へ複製します]
    #   処理: [
    #     1: 正規データを読取元として専用領域へコピーし、既に準備済みなら変更しません
    #   ]
    #   引数: [
    #     self: 専用一時領域とGodot検証入口を所有するGDScriptPasswordTests
    #   ]
    #   戻り値: [result: なし（None）。正規data/assetsは変更しません]
    # }
    def prepare_scene(self) -> None:
        # Sceneの読込を専用領域へ向けるため、正規data/assetsのコピーを一度だけ作ります。
        if not (self.content / "data").exists():
            shutil.copytree(ROOT / "data", self.content / "data")
            shutil.copytree(ROOT / "assets", self.content / "assets")

    # {
    #   責務: [probe: 公開の合言葉を含む検証シナリオを専用JSONで実Godotへ渡し、診断と観測結果を確認します]
    #   処理: [
    #     1: 必要なScene用データを専用領域に準備して要求JSONを書きます
    #     2: 保存先を専用領域へ隔離してGodotを起動し、終了コードと診断を検査します
    #     3: 標準出力の結果を復号し、結果がなければ検証を失敗させます
    #   ]
    #   引数: [
    #     self: 専用一時領域とGodot検証入口を所有するGDScriptPasswordTests
    #     request: 操作列またはScene操作を持つ検証要求。認証情報ではなく公開のゲーム用文字列です（dict）
    #   ]
    #   戻り値: [result: Godotが返した状態・イベントの観測一覧（list）]
    # }
    def probe(self, request: dict) -> list:
        # 公開のゲーム用シナリオだけを専用fixtureへ保存し、アカウントの認証情報を扱いません。
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
    #   責務: [scene: フィールドSceneを使う合言葉入力の検証要求を、共用のGodot検証入口へ渡します]
    #   処理: [
    #     1: Scene区分と操作列をprobeへ渡し、実Godotの観測一覧を返します
    #   ]
    #   引数: [
    #     self: 専用一時領域とGodot検証入口を所有するGDScriptPasswordTests
    #     actions: 湧き場を調べる・文字入力・確定・取消などの再現操作列（list）
    #   ]
    #   戻り値: [result: Scene操作後の状態とイベントの観測一覧（list）]
    # }
    def scene(self, actions: list) -> list:
        # Scene操作もprobeの起動・診断検査を共用し、観測結果の代替値を作りません。
        return self.probe({"scene": True, "actions": actions})

    # {
    #   責務: [snapshot: Pythonの合言葉入力状態から、Godotと比較する四つのスカラー値だけを複製します]
    #   処理: [
    #     1: 入力文字列・案内文・表示状態・文字数上限を新しい辞書へ取り出します
    #   ]
    #   引数: [
    #     session: 比較するPython版の合言葉入力セッション（PasswordSession）
    #   ]
    #   戻り値: [result: input_text/message/active/maximum_lengthの比較用辞書（dict）]
    # }
    @staticmethod
    def snapshot(session: PasswordSession) -> dict:
        # Godotとの比較に必要な四値だけを取り出し、Pythonセッションの実状態を変更しません。
        return {key: getattr(session, key) for key in ("input_text", "message", "active", "maximum_length")}

    # {
    #   責務: [test_operation_sequences_match_python_including_empty_invalid_full_and_closed: 境界入力と固定seedの操作列について、Godotの結果・入力状態がPythonと一致することを検証します]
    #   処理: [
    #     1: 専用の入力・画面操作を再現し、期待する観測と保存ファイルの保護を確認します
    #   ]
    #   引数: [
    #     self: 専用一時領域とGodot検証入口を所有するGDScriptPasswordTests
    #   ]
    #   戻り値: [result: なし（None）。実セーブは使用しません]
    # }
    def test_operation_sequences_match_python_including_empty_invalid_full_and_closed(self) -> None:
        # 操作列の乱数を固定し、Python/Godotの実装差と抽選差を混同しないようにします。
        basic = [{"kind": "submit"}, {"kind": "append", "value": "へ"}, {"kind": "backspace"},
                 {"kind": "cancel"}, {"kind": "open"}, {"kind": "backspace"}, {"kind": "submit"}]
        basic += [{"kind": "append", "value": value} for value in ("", "x", "が", "平和", "へい", "😀", "\n", " ")]
        basic += [{"kind": "append", "value": char} for char in SPRING_PUZZLE_ANSWER + "あ"]
        basic += [{"kind": "submit"}, {"kind": "append", "value": "へ"}, {"kind": "backspace"},
                  {"kind": "submit"}, {"kind": "open"}, {"kind": "append", "value": "あ"},
                  {"kind": "submit"}, {"kind": "cancel"}, {"kind": "open"}]
        rng = random.Random(224)
        choices = [{"kind": kind} for kind in ("open", "cancel", "submit", "backspace")]
        choices += [{"kind": "append", "value": value} for value in KANA_KEYS + "😀aが"]
        cases = [{"operations": basic}]
        for secret, keys in ((SPRING_PUZZLE_ANSWER, KANA_KEYS), ("😀あ", "😀あ"), ("", ""), ("a", "ab")):
            cases.append({"secret": secret, "keys": keys, "operations": [rng.choice(choices) for _ in range(500)]})
        results = self.probe({"cases": cases})
        for case, observations in zip(cases, results):
            session = PasswordSession(case.get("secret", SPRING_PUZZLE_ANSWER), case.get("keys", KANA_KEYS))
            self.assertEqual(observations[0]["state"], self.snapshot(session))
            for index, (operation, observation) in enumerate(zip(case["operations"], observations[1:])):
                with self.subTest(secret=session.secret, index=index, operation=operation):
                    method = getattr(session, operation["kind"])
                    expected = method(operation["value"]) if operation["kind"] == "append" else method()
                    self.assertEqual(observation, {"result": expected, "state": self.snapshot(session)})

    # {
    #   責務: [test_canonical_constants_and_ui_do_not_own_secret_or_rule: 公開の正規合言葉とかな一覧がPythonに一致し、Godot表示層が合言葉・保存・入力規則を所有しないことを検証します]
    #   処理: [
    #     1: 専用の入力・画面操作を再現し、期待する観測と保存ファイルの保護を確認します
    #   ]
    #   引数: [
    #     self: 専用一時領域とGodot検証入口を所有するGDScriptPasswordTests
    #   ]
    #   戻り値: [result: なし（None）。実セーブは使用しません]
    # }
    def test_canonical_constants_and_ui_do_not_own_secret_or_rule(self) -> None:
        # 描画層へ入力判定や保存が漏れていないことを、正規値の一致と禁止依存から確認します。
        source = (ROOT / "src/kadoka_quest/apps/game.py").read_text(encoding="utf-8")
        self.assertIn(f'PASSWORD = "{SPRING_PUZZLE_ANSWER}"', source)
        self.assertIn(f'KANA_KEYS = tuple("{KANA_KEYS}")', source)
        view = (ROOT / "gdscript/ui/password_view.gd").read_text(encoding="utf-8")
        for forbidden in (SPRING_PUZZLE_ANSWER, "FileAccess", "SaveStore", "secret", "maximum_length"):
            self.assertNotIn(forbidden, view)

    # {
    #   責務: [test_spring_opens_real_seven_slots_and_full_kana_keyboard: 湧き場を調べると七枠とかなキーボードが表示され、表示だけではセーブを作らないことを検証します]
    #   処理: [
    #     1: 専用の入力・画面操作を再現し、期待する観測と保存ファイルの保護を確認します
    #   ]
    #   引数: [
    #     self: 専用一時領域とGodot検証入口を所有するGDScriptPasswordTests
    #   ]
    #   戻り値: [result: なし（None）。実セーブは使用しません]
    # }
    def test_spring_opens_real_seven_slots_and_full_kana_keyboard(self) -> None:
        # 表示だけで進行データを作らず、入力文字数とかな一覧を実Sceneから観測します。
        result = self.scene(OPEN)[-1]
        self.assertTrue(result["visible"])
        self.assertTrue(result["state"]["active"])
        self.assertEqual(result["slots"], ["＿"] * 7)
        self.assertEqual(set(result["keys"]), set(KANA_KEYS) | {"submit", "cancel", "backspace"})
        self.assertEqual(result["state"]["maximum_length"], 7)
        self.assertTrue(result["bounds_ok"], (result["panel_rect"], result["window_size"]))
        self.assertFalse((self.content / "saves").exists())

    # {
    #   責務: [test_native_unicode_limit_backspace_and_keypad_enter_match_without_fake_acquisition: 直接入力の七文字制限・削除・テンキー確定が働き、未保存プロフィールで仲間加入を成功表示しないことを検証します]
    #   処理: [
    #     1: 専用の入力・画面操作を再現し、期待する観測と保存ファイルの保護を確認します
    #   ]
    #   引数: [
    #     self: 専用一時領域とGodot検証入口を所有するGDScriptPasswordTests
    #   ]
    #   戻り値: [result: なし（None）。実セーブは使用しません]
    # }
    def test_native_unicode_limit_backspace_and_keypad_enter_match_without_fake_acquisition(self) -> None:
        # 未保存プロフィールでは暗号一致と仲間加入の成功を分け、未取得を成功扱いにしないことを確認します。
        result = self.scene(OPEN + [
            {"kind": "type", "value": SPRING_PUZZLE_ANSWER + "あx😀"},
            {"kind": "key", "key": "Backspace"}, {"kind": "type", "value": "か"},
            {"kind": "key", "key": "KPEnter"},
        ])
        self.assertEqual(result[2]["state"]["input_text"], SPRING_PUZZLE_ANSWER)
        self.assertEqual(result[2]["slots"], list(SPRING_PUZZLE_ANSWER))
        self.assertEqual(result[2]["native_text"], "")
        self.assertEqual(result[3]["state"]["input_text"], SPRING_PUZZLE_ANSWER[:-1])
        self.assertFalse(result[-1]["visible"])
        self.assertEqual(result[-1]["result"], {"kind": "password_matched"})
        self.assertEqual(result[-1]["signals"], [{"kind": "password_matched"}])
        self.assertIn("先にF5", result[-1]["status"])
        self.assertFalse(result[-1]["acquisition"]["ok"])
        self.assertNotIn("仲間にな", result[-1]["status"])
        self.assertFalse((self.content / "saves").exists())

    # {
    #   責務: [test_virtual_key_clicks_erase_and_submit_through_real_controls: 仮想かなボタンで誤字を削除して正規合言葉を確定すると、一回だけ一致イベントが出ることを検証します]
    #   処理: [
    #     1: 専用の入力・画面操作を再現し、期待する観測と保存ファイルの保護を確認します
    #   ]
    #   引数: [
    #     self: 専用一時領域とGodot検証入口を所有するGDScriptPasswordTests
    #   ]
    #   戻り値: [result: なし（None）。実セーブは使用しません]
    # }
    def test_virtual_key_clicks_erase_and_submit_through_real_controls(self) -> None:
        # 末尾の誤字修正を実ボタンで再現し、入力状態と一回だけの確定イベントを確認します。
        actions = OPEN + [{"kind": "click", "target": char} for char in SPRING_PUZZLE_ANSWER[:-1] + "あ"]
        actions += [{"kind": "click", "target": "backspace"}, {"kind": "click", "target": "か"},
                    {"kind": "click", "target": "submit"}]
        result = self.scene(actions)[-1]
        self.assertEqual(result["state"]["input_text"], SPRING_PUZZLE_ANSWER)
        self.assertEqual(result["signals"], [{"kind": "password_matched"}])
        self.assertFalse(result["visible"])

    # {
    #   責務: [test_empty_and_wrong_submit_stay_open_cancel_and_reopen_reset_input: 空文字と誤った合言葉は入力画面を閉じず、取消後の再表示で入力を消すことを検証します]
    #   処理: [
    #     1: 専用の入力・画面操作を再現し、期待する観測と保存ファイルの保護を確認します
    #   ]
    #   引数: [
    #     self: 専用一時領域とGodot検証入口を所有するGDScriptPasswordTests
    #   ]
    #   戻り値: [result: なし（None）。実セーブは使用しません]
    # }
    def test_empty_and_wrong_submit_stay_open_cancel_and_reopen_reset_input(self) -> None:
        # 仮想かな入力と送信操作を分離し、誤入力で入力画面が消える回帰を防ぎます。
        # 仮想かなボタンのEnterは文字入力なので、暗号の判定は確定ボタンから要求します。
        result = self.scene(OPEN + [
            {"kind": "key", "key": "Enter"}, {"kind": "click", "target": "あ"},
            {"kind": "focus", "target": "submit"},
            {"kind": "key", "key": "Enter"}, {"kind": "key", "key": "Escape"},
            {"kind": "key", "key": "E"},
        ])
        for observation in (result[2], result[5]):
            self.assertEqual(observation["message"], "あいことばが違います。")
            self.assertTrue(observation["state"]["active"])
            self.assertEqual(observation["signals"], [])
        self.assertEqual(result[6]["result"], {"kind": "password_cancelled"})
        self.assertEqual(result[-1]["state"]["input_text"], "")
        self.assertEqual(result[-1]["message"], "7文字のあいことばを入力してください。")
        self.assertTrue(result[-1]["visible"])

    # {
    #   責務: [test_virtual_cancel_and_confirm_echo_do_not_duplicate_a_result: 確定キーのリピートを無視し、仮想取消ボタンが一回だけ取消イベントを出すことを検証します]
    #   処理: [
    #     1: 専用の入力・画面操作を再現し、期待する観測と保存ファイルの保護を確認します
    #   ]
    #   引数: [
    #     self: 専用一時領域とGodot検証入口を所有するGDScriptPasswordTests
    #   ]
    #   戻り値: [result: なし（None）。実セーブは使用しません]
    # }
    def test_virtual_cancel_and_confirm_echo_do_not_duplicate_a_result(self) -> None:
        # 押しっぱなしの確定リピートで暗号判定を二重発火させないことを確認します。
        result = self.scene(OPEN + [
            {"kind": "type", "value": SPRING_PUZZLE_ANSWER}, {"kind": "key", "key": "Enter", "echo": True},
            {"kind": "click", "target": "cancel"},
        ])
        self.assertTrue(result[-2]["visible"])
        self.assertEqual(result[-2]["signals"], [])
        self.assertEqual(result[-1]["signals"], [{"kind": "password_cancelled"}])
        self.assertFalse(result[-1]["visible"])

    # {
    #   責務: [test_committed_text_signal_and_unicode_with_virtual_button_focus_do_not_double_append: 確定テキストと仮想ボタン選択中の直接入力が重複せず、正規合言葉を一回だけ確定できることを検証します]
    #   処理: [
    #     1: 専用の入力・画面操作を再現し、期待する観測と保存ファイルの保護を確認します
    #   ]
    #   引数: [
    #     self: 専用一時領域とGodot検証入口を所有するGDScriptPasswordTests
    #   ]
    #   戻り値: [result: なし（None）。実セーブは使用しません]
    # }
    def test_committed_text_signal_and_unicode_with_virtual_button_focus_do_not_double_append(self) -> None:
        # 日本語の確定入力が文字入力イベントと重なっても、文字を二重追加しないことを確認します。
        # 日本語入力は仮想キーへフォーカスがある場合も受け付け、送信だけは明示操作に分けます。
        result = self.scene(OPEN + [
            {"kind": "commit_signal", "value": "へいx😀わなすみかあ"},
            {"kind": "key", "key": "Backspace"}, {"kind": "focus", "target": "あ"},
            {"kind": "type", "value": "か"}, {"kind": "focus", "target": "submit"},
            {"kind": "key", "key": "Enter"},
        ])
        self.assertEqual(result[2]["state"]["input_text"], SPRING_PUZZLE_ANSWER)
        self.assertEqual(result[2]["native_text"], "")
        self.assertEqual(result[-1]["state"]["input_text"], SPRING_PUZZLE_ANSWER)
        self.assertEqual(result[-1]["signals"], [{"kind": "password_matched"}])

    # {
    #   責務: [test_modal_freezes_clock_actor_positions_keyboard_and_direct_save_load_until_resumed: 合言葉入力中は移動・モブ時計・保存読込・管理画面を止め、取消後に通常の移動周期へ戻ることを検証します]
    #   処理: [
    #     1: 専用の入力・画面操作を再現し、期待する観測と保存ファイルの保護を確認します
    #   ]
    #   引数: [
    #     self: 専用一時領域とGodot検証入口を所有するGDScriptPasswordTests
    #   ]
    #   戻り値: [result: なし（None）。実セーブは使用しません]
    # }
    def test_modal_freezes_clock_actor_positions_keyboard_and_direct_save_load_until_resumed(self) -> None:
        # 入力画面の経過時間を探索へ流さず、再開時のモブがまとめて動かないことを確認します。
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
    #   責務: [test_tab_space_virtual_navigation_and_wrong_full_length_stay_modal: Tabで選ぶかなをSpace/Enterで入力でき、誤った七文字を確定しても入力画面を保持することを検証します]
    #   処理: [
    #     1: 専用の入力・画面操作を再現し、期待する観測と保存ファイルの保護を確認します
    #   ]
    #   引数: [
    #     self: 専用一時領域とGodot検証入口を所有するGDScriptPasswordTests
    #   ]
    #   戻り値: [result: なし（None）。実セーブは使用しません]
    # }
    def test_tab_space_virtual_navigation_and_wrong_full_length_stay_modal(self) -> None:
        # 仮想かなの選択と確定ボタンの送信を別々に通し、誤った七文字の扱いを確認します。
        # Enterによる仮想かな入力と、確定ボタンによる暗号判定を別の操作として検証します。
        result = self.scene(OPEN + [
            {"kind": "key", "key": "Tab"}, {"kind": "key", "key": "Space"},
            {"kind": "key", "key": "Enter"}, {"kind": "type", "value": "あ" * 5},
            {"kind": "focus", "target": "submit"}, {"kind": "key", "key": "Enter"},
        ])
        self.assertEqual(result[3]["state"]["input_text"], "あ")
        self.assertEqual(result[4]["state"]["input_text"], "ああ")
        self.assertEqual(result[4]["signals"], [])
        self.assertEqual(result[-1]["state"]["input_text"], "あ" * 7)
        self.assertEqual(result[-1]["message"], "あいことばが違います。")
        self.assertTrue(result[-1]["visible"])
        self.assertEqual(result[-1]["signals"], [])
        self.assertEqual(result[-1]["player"], [17, 8])

    # {
    #   責務: [test_cancel_and_already_complete_match_keep_json_and_ghosts_unchanged: 取消と既取得の合言葉一致は、専用保存先のJSON・AI・コンテンツと住処の二匹を変更しないことを検証します]
    #   処理: [
    #     1: 専用の入力・画面操作を再現し、期待する観測と保存ファイルの保護を確認します
    #   ]
    #   引数: [
    #     self: 専用一時領域とGodot検証入口を所有するGDScriptPasswordTests
    #   ]
    #   戻り値: [result: なし（None）。実セーブは使用しません]
    # }
    def test_cancel_and_already_complete_match_keep_json_and_ghosts_unchanged(self) -> None:
        # 取得済みの合言葉再入力と取消では、ファイルの書換えや二体の消去を行わないことを確認します。
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
            actions = [{"kind": "key", "key": "E"}, {"kind": "type", "value": SPRING_PUZZLE_ANSWER}]
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
    #   責務: [content_bytes: 専用領域のコンテンツと保存ファイルを、操作前後の不変比較に使うバイト列として読み取ります]
    #   処理: [
    #     1: data・assets・saves配下のファイルを相対パスで索引化します
    #   ]
    #   引数: [
    #     self: 専用一時領域とGodot検証入口を所有するGDScriptPasswordTests
    #   ]
    #   戻り値: [result: 専用領域の相対Pathからファイル内容bytesへの辞書（dict）]
    # }
    def content_bytes(self) -> dict:
        # 専用領域内のファイル内容だけを比較用に読み、検査対象を書き戻しません。
        return {p.relative_to(self.content): p.read_bytes() for parent in ("data", "assets", "saves")
                for p in (self.content / parent).rglob("*") if p.is_file()}
