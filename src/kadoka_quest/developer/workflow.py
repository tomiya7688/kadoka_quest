from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable

from kadoka_quest.developer.project_validator import ProjectValidator
from kadoka_quest.paths import PROJECT_ROOT, is_frozen


@dataclass(frozen=True)
class WorkflowResult:
    ok: bool
    message: str
    log_path: Path | None = None


@dataclass
class RunningTask:
    label: str
    process: Any
    log_path: Path


class DeveloperWorkflowService:
    """Orchestrate Developer actions without owning editor or build implementation."""

    def __init__(
        self,
        project_root: Path | None = None,
        *,
        executable: str | None = None,
        frozen: bool | None = None,
        launcher: Callable[..., Any] = subprocess.Popen,
    ) -> None:
        self.project_root = Path(project_root or PROJECT_ROOT)
        self.executable = str(executable or sys.executable)
        self.frozen = is_frozen() if frozen is None else bool(frozen)
        self.launcher = launcher
        self.running_task: RunningTask | None = None

    @property
    def log_root(self) -> Path:
        if self.frozen:
            return self.project_root / "UserData" / "developer"
        return self.project_root / "build" / "developer"

    def validate_project(self) -> WorkflowResult:
        report = ProjectValidator(self.project_root / "data", self.project_root / "assets").validate()
        return WorkflowResult(report.ok, report.summary(detail_limit=3))

    def preview_player(self) -> WorkflowResult:
        environment = self._environment()
        if self.frozen:
            command = [self.executable, "--player-preview"]
        else:
            command = [self.executable, str(self.project_root / "launcher.py"), "--play"]
        try:
            self.launcher(command, cwd=self.project_root, env=environment)
        except OSError as exc:
            return WorkflowResult(False, f"Player Preview failed to start: {exc}")
        return WorkflowResult(True, "Player Preview started with the Player runtime.")

    def start_player_build(self) -> WorkflowResult:
        return self._start_task("Player Build", "--build-player", "player-build.log")

    def start_player_smoke(self) -> WorkflowResult:
        return self._start_task("Player Distribution Smoke", "--smoke-player-build", "player-smoke.log")

    def poll(self) -> WorkflowResult | None:
        task = self.running_task
        if task is None:
            return None
        code = task.process.poll()
        if code is None:
            return None
        self.running_task = None
        if code == 0:
            return WorkflowResult(True, f"{task.label} completed successfully.", task.log_path)
        return WorkflowResult(False, f"{task.label} failed (exit {code}). See {task.log_path}", task.log_path)

    def _start_task(self, label: str, flag: str, log_name: str) -> WorkflowResult:
        if self.running_task is not None and self.running_task.process.poll() is None:
            return WorkflowResult(False, f"{self.running_task.label} is already running.", self.running_task.log_path)

        self.log_root.mkdir(parents=True, exist_ok=True)
        log_path = self.log_root / log_name
        command = self._developer_command(flag)
        try:
            if self.frozen:
                process = self.launcher(
                    command,
                    cwd=self.project_root,
                    env=self._environment(),
                )
            else:
                with log_path.open("w", encoding="utf-8") as log_file:
                    process = self.launcher(
                        command,
                        cwd=self.project_root,
                        env=self._environment(),
                        stdout=log_file,
                        stderr=subprocess.STDOUT,
                    )
        except OSError as exc:
            return WorkflowResult(False, f"{label} failed to start: {exc}", log_path)
        self.running_task = RunningTask(label, process, log_path)
        return WorkflowResult(True, f"{label} started. Log: {log_path}", log_path)

    def _developer_command(self, flag: str) -> list[str]:
        if self.frozen:
            return [self.executable, flag]
        return [self.executable, str(self.project_root / "developer_launcher.py"), flag]

    def _environment(self) -> dict[str, str]:
        environment = os.environ.copy()
        environment["KADOKA_PROJECT_ROOT"] = str(self.project_root)
        environment["KADOKA_DEVELOPER_TOOLS"] = "1"
        return environment
