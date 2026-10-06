# {
#   責務: [test_distribution_paths: test・distribution・パス一覧の公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from kadoka_quest import paths


# {
#   責務: [DistributionPathTests: distribution・パス・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class DistributionPathTests(unittest.TestCase):
    # {
    #   責務: [test_project_root_override_has_priority: 検証: project root override has priority]
    #   処理: [1: 検証: project root override has priority]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_project_root_override_has_priority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with patch.dict(os.environ, {"KADOKA_PROJECT_ROOT": temporary}):
                self.assertEqual(paths.runtime_root(), Path(temporary).resolve())

    # {
    #   責務: [test_frozen_runtime_root_is_executable_directory: 検証: frozen runtime root is executable directory]
    #   処理: [1: 検証: frozen runtime root is executable directory]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_frozen_runtime_root_is_executable_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "KadokaQuest.exe"
            environment = os.environ.copy()
            environment.pop("KADOKA_PROJECT_ROOT", None)
            with patch.dict(os.environ, environment, clear=True):
                with patch.object(sys, "frozen", True, create=True):
                    with patch.object(sys, "executable", str(executable)):
                        self.assertEqual(paths.runtime_root(), Path(temporary).resolve())


if __name__ == "__main__":
    unittest.main()
