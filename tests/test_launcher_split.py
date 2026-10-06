# {
#   責務: [test_launcher_split: test・launcher・splitの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import unittest

from kadoka_quest.apps.launcher_config import DEVELOPER_LAUNCH_TARGETS, PLAYER_LAUNCH_TARGETS


# {
#   責務: [LauncherSplitTests: launcher・split・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class LauncherSplitTests(unittest.TestCase):
    # {
    #   責務: [test_player_launcher_only_exposes_game_entrypoint: 検証: player launcher only exposes game entrypoint]
    #   処理: [1: 検証: player launcher only exposes game entrypoint]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_player_launcher_only_exposes_game_entrypoint(self) -> None:
        self.assertEqual(PLAYER_LAUNCH_TARGETS, (("ゲームを開始", "game.py"),))

    # {
    #   責務: [test_developer_targets_are_not_exposed_by_player_launcher: 検証: developer targets are not exposed by player launcher]
    #   処理: [1: 検証: developer targets are not exposed by player launcher]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_developer_targets_are_not_exposed_by_player_launcher(self) -> None:
        player_scripts = {script for _, script in PLAYER_LAUNCH_TARGETS}
        developer_scripts = {script for _, script in DEVELOPER_LAUNCH_TARGETS}

        self.assertTrue(developer_scripts)
        self.assertTrue(player_scripts.isdisjoint(developer_scripts))
        self.assertIn("manage.py", developer_scripts)
        self.assertIn("data_creator.py", developer_scripts)


if __name__ == "__main__":
    unittest.main()
