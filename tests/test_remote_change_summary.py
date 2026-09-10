from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPOSITORY_ROOT / "scripts" / "remote_change_summary.py"
SPEC = importlib.util.spec_from_file_location("remote_change_summary", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
remote_change_summary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(remote_change_summary)


class RemoteChangeSummaryTests(unittest.TestCase):
    def test_git_executable_prefers_runner_captured_path(self) -> None:
        executable = remote_change_summary.git_executable(
            environment={"KADOKA_GIT_EXECUTABLE": "C:/tools/git.exe"}
        )

        self.assertEqual("C:/tools/git.exe", executable)

    def test_changed_paths_uses_destination_for_renamed_files(self) -> None:
        paths = remote_change_summary.changed_paths("M\tdocs/CODEMAP.md\nR100\told.py\tnew.py")

        self.assertEqual(["docs/CODEMAP.md", "new.py"], paths)

    def test_summary_groups_paths_and_warns_about_dirty_overlap(self) -> None:
        summary = remote_change_summary.render_summary(
            base="HEAD",
            remote="origin/main",
            merge_base="abcdef123456",
            total_remote_commits=3,
            remote_commits=["1234567 Add player launcher"],
            paths=["src/kadoka_quest/apps/launcher.py", "docs/配布.md"],
            dirty={"docs/配布.md", "game.py"},
        )

        self.assertIn("ゲームアプリ: 1件", summary)
        self.assertIn("ドキュメント: 1件", summary)
        self.assertIn("リモートコミット: 3件", summary)
        self.assertIn("最新コミット（表示 1件）", summary)
        self.assertIn("`docs/配布.md`", summary)
        self.assertIn("1234567 Add player launcher", summary)
