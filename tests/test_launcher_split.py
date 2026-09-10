from __future__ import annotations

import unittest

from kadoka_quest.apps.launcher_config import DEVELOPER_LAUNCH_TARGETS, PLAYER_LAUNCH_TARGETS


class LauncherSplitTests(unittest.TestCase):
    def test_player_launcher_only_exposes_game_entrypoint(self) -> None:
        self.assertEqual(PLAYER_LAUNCH_TARGETS, (("ゲームを開始", "game.py"),))

    def test_developer_targets_are_not_exposed_by_player_launcher(self) -> None:
        player_scripts = {script for _, script in PLAYER_LAUNCH_TARGETS}
        developer_scripts = {script for _, script in DEVELOPER_LAUNCH_TARGETS}

        self.assertTrue(developer_scripts)
        self.assertTrue(player_scripts.isdisjoint(developer_scripts))
        self.assertIn("manage.py", developer_scripts)
        self.assertIn("data_creator.py", developer_scripts)


if __name__ == "__main__":
    unittest.main()
