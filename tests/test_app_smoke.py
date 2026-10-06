# {
#   責務: [test_app_smoke: test・app・smokeの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


# {
#   責務: [AppSmokeTests: app・smoke・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
@unittest.skipUnless(importlib.util.find_spec("pygame"), "pygame-ce is not installed")
class AppSmokeTests(unittest.TestCase):
    # {
    #   責務: [test_all_apps_open_and_close_headlessly: 検証: all apps open and close headlessly]
    #   処理: [1: 検証: all apps open and close headlessly]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_all_apps_open_and_close_headlessly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            environment = os.environ.copy()
            environment["SDL_VIDEODRIVER"] = "dummy"
            environment["SDL_AUDIODRIVER"] = "dummy"
            environment["KADOKA_SAVE_DIR"] = str(Path(temporary) / "save")
            environment["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
            for script in (
                "launcher.py",
                "developer_launcher.py",
                "block_editor.py",
                "map_editor.py",
                "monster_editor.py",
                "data_creator.py",
                "data_validator.py",
                "manage.py",
                "simulation_manager.py",
                "game.py",
            ):
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
