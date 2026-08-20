from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec("pygame"), "pygame-ce is not installed")
class AppSmokeTests(unittest.TestCase):
    def test_all_apps_open_and_close_headlessly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            environment = os.environ.copy()
            environment["SDL_VIDEODRIVER"] = "dummy"
            environment["SDL_AUDIODRIVER"] = "dummy"
            environment["KADOKA_SAVE_DIR"] = str(Path(temporary) / "save")
            environment["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
            for script in ("launcher.py", "block_editor.py", "map_editor.py", "monster_editor.py", "manage.py", "game.py"):
                completed = subprocess.run(
                    [sys.executable, str(PROJECT_ROOT / script), "--smoke", "2"],
                    cwd=PROJECT_ROOT,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                self.assertEqual(completed.returncode, 0, f"{script}\n{completed.stdout}\n{completed.stderr}")


if __name__ == "__main__":
    unittest.main()


