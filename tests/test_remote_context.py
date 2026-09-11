from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
from unittest.mock import patch
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPOSITORY_ROOT / "tools" / "remote-context" / "script" / "sync_remote_context.py"
SPEC = importlib.util.spec_from_file_location("remote_context", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
remote_context = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(remote_context)


class RemoteContextTests(unittest.TestCase):
    def test_run_git_decodes_utf8_output_independent_of_windows_console_locale(self) -> None:
        completed = subprocess.CompletedProcess(
            args=("git", "diff"), returncode=0, stdout="日本語の差分", stderr=""
        )
        with patch.object(remote_context, "git_executable", return_value="git.exe"), patch.object(
            remote_context.subprocess, "run", return_value=completed
        ) as run:
            result = remote_context.run_git("diff", "--stat")

        self.assertEqual("日本語の差分", result)
        self.assertEqual("utf-8", run.call_args.kwargs["encoding"])
        self.assertEqual("replace", run.call_args.kwargs["errors"])
