from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from kadoka_quest.data.savedata import SaveDataManager


class DistributionSaveDataTests(unittest.TestCase):
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

    def test_create_still_rejects_an_existing_profile_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "UserData"
            manager = SaveDataManager(root)
            manager.ensure_profile("default")

            with self.assertRaises(FileExistsError):
                manager.create("default")


if __name__ == "__main__":
    unittest.main()
