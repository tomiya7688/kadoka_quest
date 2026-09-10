from __future__ import annotations

from pathlib import Path
import unittest

from kadoka_quest.apps.manager_process_service import ManagerProcessService


class _Process:
    def poll(self):
        return None


class DistributionProcessTests(unittest.TestCase):
    def test_frozen_ranch_manager_relaunches_player_executable(self) -> None:
        calls = []

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
