from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_quest.apps.launcher import _perform_save_action
from kadoka_quest.data.savedata import SaveDataManager


class SaveNameValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.manager = SaveDataManager(Path(self.temporary.name) / "savedata")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_windows_reserved_device_names_are_rejected_case_insensitively(self) -> None:
        for name in ("CON", "nul", "PRN", "AUX", "COM1", "com9", "LPT1", "lpt9", "CON.txt"):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    self.manager.validate_name(name)

    def test_nonreserved_similar_names_remain_valid(self) -> None:
        for name in ("COM0", "COM10", "LPT10", "CONSOLE", "冒険その1", "save_01"):
            with self.subTest(name=name):
                self.assertEqual(self.manager.validate_name(name), name)

    def test_trailing_dot_or_outer_space_is_rejected_without_silent_normalization(self) -> None:
        for name in ("save.", "save ", " save", "冒険その1 "):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    self.manager.validate_name(name)

    def test_invalid_name_is_rejected_before_profile_directory_is_created(self) -> None:
        with self.assertRaises(ValueError):
            self.manager.create("CON")

        self.assertFalse((self.manager.root / "CON").exists())

    def test_normal_japanese_name_can_still_be_created(self) -> None:
        profile = self.manager.create("冒険その1")

        self.assertTrue((profile / "state.json").is_file())
        self.assertEqual(profile.name, "冒険その1")

    def test_launcher_save_action_converts_oserror_to_status_text(self) -> None:
        def fail() -> Path:
            raise OSError("ファイルシステムで作成できません")

        path, error = _perform_save_action(fail, "作成できませんでした。")

        self.assertIsNone(path)
        self.assertEqual(error, "ファイルシステムで作成できません")

    def test_launcher_save_action_uses_fallback_for_empty_oserror(self) -> None:
        def fail() -> Path:
            raise OSError()

        path, error = _perform_save_action(fail, "作成できませんでした。")

        self.assertIsNone(path)
        self.assertEqual(error, "作成できませんでした。")


if __name__ == "__main__":
    unittest.main()
