# {
#   責務: [test_remote_context: test・remote・判断用コンテキストの公開機能・宣言を定義する]
#   フィールド: []
# }
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


# {
#   責務: [RemoteContextTests: remote・判断用コンテキスト・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class RemoteContextTests(unittest.TestCase):
    # {
    #   責務: [test_run_git_decodes_utf8_output_independent_of_windows_console_locale: 検証: run git decodes utf8 output independent of windows console locale]
    #   処理: [1: 検証: run git decodes utf8 output independent of windows console locale]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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
