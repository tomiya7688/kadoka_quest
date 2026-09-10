from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from kadoka_quest import paths


class DistributionPathTests(unittest.TestCase):
    def test_project_root_override_has_priority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with patch.dict(os.environ, {"KADOKA_PROJECT_ROOT": temporary}):
                self.assertEqual(paths.runtime_root(), Path(temporary).resolve())

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
