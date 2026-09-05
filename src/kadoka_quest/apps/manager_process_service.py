from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import subprocess
import sys
from typing import Any


class ManagerProcessService:
    """Owns launching and observing the external monster-management process."""

    def __init__(
        self,
        script_path: Path,
        *,
        python_executable: str | None = None,
        launcher: Callable[..., Any] = subprocess.Popen,
    ) -> None:
        self.script_path = Path(script_path)
        self.python_executable = str(python_executable or sys.executable)
        self.launcher = launcher
        self.process: Any | None = None

    def open(self) -> str:
        if self.is_running():
            return "already_running"
        self.process = self.launcher(
            [self.python_executable, str(self.script_path)],
            cwd=self.script_path.parent,
        )
        return "started"

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def consume_closed(self) -> bool:
        if self.process is None or self.process.poll() is None:
            return False
        self.process = None
        return True
