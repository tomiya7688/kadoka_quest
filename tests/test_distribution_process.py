# {
#   責務: [test_distribution_process: test・distribution・processの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from pathlib import Path
import unittest

from kadoka_quest.apps.manager_process_service import ManagerProcessService


# {
#   責務: [_Process: processの状態と振る舞いを担当する]
#   フィールド: []
# }
class _Process:
    # {
    #   責務: [poll: processのpollを求める]
    #   処理: [1: processのpollを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: processのpollを求めるための結果（型注釈なし）]
    # }
    def poll(self):
        return None


# {
#   責務: [DistributionProcessTests: distribution・process・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class DistributionProcessTests(unittest.TestCase):
    # {
    #   責務: [test_frozen_ranch_manager_relaunches_player_executable: 検証: frozen ranch manager relaunches player executable]
    #   処理: [1: 検証: frozen ranch manager relaunches player executable]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_frozen_ranch_manager_relaunches_player_executable(self) -> None:
        calls = []

        # {
        #   責務: [launcher: distribution・process・testsのlauncherを求める]
        #   処理: [1: distribution・process・testsのlauncherを求める]
        #   引数: [
        #     command: コマンド
        #     kwargs: kwargs
        #   ]
        #   戻り値: [result: distribution・process・testsのlauncherを求めるための結果（型注釈なし）]
        # }
        def launcher(command, **kwargs):
            calls.append((command, kwargs))
            return _Process()

        service = ManagerProcessService(
            Path("C:/KadokaQuest/manage.py"),
            python_executable="C:/KadokaQuest/KadokaQuest.exe",
            launcher=launcher,
            frozen=True,
        )

        self.assertEqual(service.open(), "started")
        self.assertEqual(
            calls[0][0],
            ["C:/KadokaQuest/KadokaQuest.exe", "--manager"],
        )
        self.assertEqual(calls[0][1]["cwd"], Path("C:/KadokaQuest"))


if __name__ == "__main__":
    unittest.main()
