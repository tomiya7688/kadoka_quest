from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from kadoka_quest.developer.project_validator import ProjectValidator
from kadoka_quest.developer.workflow import DeveloperWorkflowService
from kadoka_quest.paths import PROJECT_ROOT


class _Process:
    def __init__(self) -> None:
        self.return_code = None

    def poll(self):
        return self.return_code


class DeveloperWorkflowTests(unittest.TestCase):
    def test_current_player_project_passes_data_validation(self) -> None:
        report = ProjectValidator(PROJECT_ROOT / "data", PROJECT_ROOT / "assets").validate()
        self.assertTrue(report.ok, "\n".join(item.compact() for item in report.messages))

    def test_source_preview_uses_player_runtime_entrypoint(self) -> None:
        calls = []

        def launcher(command, **kwargs):
            calls.append((command, kwargs))
            return _Process()

        service = DeveloperWorkflowService(
            PROJECT_ROOT,
            executable="python-test",
            frozen=False,
            launcher=launcher,
        )
        result = service.preview_player()

        self.assertTrue(result.ok)
        self.assertEqual(calls[0][0], ["python-test", str(PROJECT_ROOT / "launcher.py"), "--play"])
        self.assertEqual(calls[0][1]["cwd"], PROJECT_ROOT)

    def test_frozen_preview_reuses_developer_executable_player_runtime(self) -> None:
        calls = []

        def launcher(command, **kwargs):
            calls.append((command, kwargs))
            return _Process()

        service = DeveloperWorkflowService(
            Path("C:/KadokaQuestDeveloper"),
            executable="C:/KadokaQuestDeveloper/KadokaQuestDeveloper.exe",
            frozen=True,
            launcher=launcher,
        )
        result = service.preview_player()

        self.assertTrue(result.ok)
        self.assertEqual(
            calls[0][0],
            ["C:/KadokaQuestDeveloper/KadokaQuestDeveloper.exe", "--player-preview"],
        )

    def test_background_build_reports_completion_and_log(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            calls = []
            process = _Process()

            def launcher(command, **kwargs):
                calls.append((command, kwargs))
                return process

            service = DeveloperWorkflowService(
                root,
                executable="python-test",
                frozen=False,
                launcher=launcher,
            )
            started = service.start_player_build()
            self.assertTrue(started.ok)
            self.assertEqual(calls[0][0], ["python-test", str(root / "developer_launcher.py"), "--build-player"])
            self.assertIsNone(service.poll())

            process.return_code = 0
            completed = service.poll()
            self.assertIsNotNone(completed)
            self.assertTrue(completed.ok)
            self.assertEqual(completed.log_path, root / "build" / "developer" / "player-build.log")

    def test_player_entrypoint_does_not_import_developer_package(self) -> None:
        source = (PROJECT_ROOT / "launcher.py").read_text(encoding="utf-8")
        self.assertNotIn("kadoka_quest.developer", source)
        self.assertNotIn("developer_launcher", source)


if __name__ == "__main__":
    unittest.main()
