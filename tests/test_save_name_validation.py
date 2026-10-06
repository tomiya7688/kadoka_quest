# {
#   責務: [test_save_name_validation: test・保存・名前・validationの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_quest.apps.launcher import _perform_save_action
from kadoka_quest.data.savedata import SaveDataManager


# {
#   責務: [SaveNameValidationTests: 保存・名前・validation・testsの状態と振る舞いを担当する]
#   フィールド: [
#     temporary: temporary
#     manager: manager
#   ]
# }
class SaveNameValidationTests(unittest.TestCase):
    # {
    #   責務: [setUp: 検証に必要な専用fixtureと依存を準備する]
    #   処理: [1: 検証に必要な専用fixtureと依存を準備する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.manager = SaveDataManager(Path(self.temporary.name) / "savedata")

    # {
    #   責務: [tearDown: 検証用fixtureと一時的な変更を後始末する]
    #   処理: [1: 検証用fixtureと一時的な変更を後始末する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def tearDown(self) -> None:
        self.temporary.cleanup()

    # {
    #   責務: [test_windows_reserved_device_names_are_rejected_case_insensitively: 検証: windows reserved device names are rejected case insensitively]
    #   処理: [1: 検証: windows reserved device names are rejected case insensitively]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_windows_reserved_device_names_are_rejected_case_insensitively(self) -> None:
        for name in ("CON", "nul", "PRN", "AUX", "COM1", "com9", "LPT1", "lpt9", "CON.txt"):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    self.manager.validate_name(name)

    # {
    #   責務: [test_nonreserved_similar_names_remain_valid: 検証: nonreserved similar names remain valid]
    #   処理: [1: 検証: nonreserved similar names remain valid]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_nonreserved_similar_names_remain_valid(self) -> None:
        for name in ("COM0", "COM10", "LPT10", "CONSOLE", "冒険その1", "save_01"):
            with self.subTest(name=name):
                self.assertEqual(self.manager.validate_name(name), name)

    # {
    #   責務: [test_trailing_dot_or_outer_space_is_rejected_without_silent_normalization: 検証: trailing dot or outer space is rejected without silent normalization]
    #   処理: [1: 検証: trailing dot or outer space is rejected without silent normalization]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_trailing_dot_or_outer_space_is_rejected_without_silent_normalization(self) -> None:
        for name in ("save.", "save ", " save", "冒険その1 "):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    self.manager.validate_name(name)

    # {
    #   責務: [test_invalid_name_is_rejected_before_profile_directory_is_created: 検証: invalid name is rejected before profile directory is created]
    #   処理: [1: 検証: invalid name is rejected before profile directory is created]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_invalid_name_is_rejected_before_profile_directory_is_created(self) -> None:
        with self.assertRaises(ValueError):
            self.manager.create("CON")

        # On Windows, exists("CON") may resolve the device even with no file.
        entries = list(self.manager.root.iterdir()) if self.manager.root.exists() else []
        self.assertNotIn("CON", [entry.name.upper() for entry in entries])

    # {
    #   責務: [test_normal_japanese_name_can_still_be_created: 検証: normal japanese name can still be created]
    #   処理: [1: 検証: normal japanese name can still be created]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_normal_japanese_name_can_still_be_created(self) -> None:
        profile = self.manager.create("冒険その1")

        self.assertTrue((profile / "state.json").is_file())
        self.assertEqual(profile.name, "冒険その1")

    # {
    #   責務: [test_launcher_save_action_converts_oserror_to_status_text: 検証: launcher save action converts oserror to status text]
    #   処理: [1: 検証: launcher save action converts oserror to status text]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_launcher_save_action_converts_oserror_to_status_text(self) -> None:
        # {
        #   責務: [fail: 保存・名前・validation・testsのfailを求める]
        #   処理: [1: 保存・名前・validation・testsのfailを求める]
        #   引数: []
        #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
        # }
        def fail() -> Path:
            raise OSError("ファイルシステムで作成できません")

        path, error = _perform_save_action(fail, "作成できませんでした。")

        self.assertIsNone(path)
        self.assertEqual(error, "ファイルシステムで作成できません")

    # {
    #   責務: [test_launcher_save_action_uses_fallback_for_empty_oserror: 検証: launcher save action uses fallback for empty oserror]
    #   処理: [1: 検証: launcher save action uses fallback for empty oserror]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_launcher_save_action_uses_fallback_for_empty_oserror(self) -> None:
        # {
        #   責務: [fail: 保存・名前・validation・testsのfailを求める]
        #   処理: [1: 保存・名前・validation・testsのfailを求める]
        #   引数: []
        #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
        # }
        def fail() -> Path:
            raise OSError()

        path, error = _perform_save_action(fail, "作成できませんでした。")

        self.assertIsNone(path)
        self.assertEqual(error, "作成できませんでした。")


if __name__ == "__main__":
    unittest.main()
