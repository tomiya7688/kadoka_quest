# {
#   責務: [test_distribution_savedata: test・distribution・セーブデータの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from kadoka_quest.data.savedata import SaveDataManager


# {
#   責務: [DistributionSaveDataTests: distribution・保存・データ・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class DistributionSaveDataTests(unittest.TestCase):
    # {
    #   責務: [test_bootstrap_profile_completes_precreated_user_data_folder: 検証: bootstrap profile completes precreated user data folder]
    #   処理: [1: 検証: bootstrap profile completes precreated user data folder]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_bootstrap_profile_completes_precreated_user_data_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "UserData"
            incomplete = root / "default"
            (incomplete / "monsters").mkdir(parents=True)

            manager = SaveDataManager(root)
            profile = manager.ensure_profile("default")

            self.assertEqual(profile, incomplete)
            self.assertTrue((profile / "state.json").is_file())
            self.assertTrue((profile / "items" / "items.json").is_file())
            self.assertTrue((profile / "parties").is_dir())
            self.assertTrue((profile / "monsters").is_dir())
            self.assertTrue((profile / "meta.json").is_file())
            self.assertEqual(manager.active_name(), "default")
            self.assertTrue((root / "active.json").is_file())

    # {
    #   責務: [test_create_still_rejects_an_existing_profile_directory: 検証: create still rejects an existing profile directory]
    #   処理: [1: 検証: create still rejects an existing profile directory]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_create_still_rejects_an_existing_profile_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "UserData"
            manager = SaveDataManager(root)
            manager.ensure_profile("default")

            with self.assertRaises(FileExistsError):
                manager.create("default")


if __name__ == "__main__":
    unittest.main()
