# {
#   責務: [workflow: workflowの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable

from kadoka_quest.developer.project_validator import ProjectValidator
from kadoka_quest.paths import PROJECT_ROOT, is_frozen


# {
#   責務: [WorkflowResult: workflow・処理結果の状態と振る舞いを担当する]
#   フィールド: [
#     ok: ok（bool）
#     message: message（str）
#     log_path: ログ・パス（Path | None）
#   ]
# }
@dataclass(frozen=True)
class WorkflowResult:
    ok: bool
    message: str
    log_path: Path | None = None


# {
#   責務: [RunningTask: running・taskの状態と振る舞いを担当する]
#   フィールド: [
#     label: 表示名（str）
#     process: process（Any）
#     log_path: ログ・パス（Path）
#   ]
# }
@dataclass
class RunningTask:
    label: str
    process: Any
    log_path: Path


# {
#   責務: [DeveloperWorkflowService: Orchestrate Developer actions without owning editor or build implementation.]
#   フィールド: [
#     project_root: project・基準ディレクトリ
#     executable: executable
#     frozen: frozen
#     launcher: launcher
#     running_task: running・task
#   ]
# }
class DeveloperWorkflowService:
    """Orchestrate Developer actions without owning editor or build implementation."""

    # {
    #   責務: [__init__: developer・workflow・serviceが利用する初期状態と依存を設定する]
    #   処理: [1: developer・workflow・serviceが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     project_root: project・基準ディレクトリ（Path | None）
    #     executable: executable（str | None）
    #     frozen: frozen（bool | None）
    #     launcher: launcher（Callable[..., Any]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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

    # {
    #   責務: [log_root: developer・workflow・serviceのログ・基準ディレクトリを求める]
    #   処理: [1: developer・workflow・serviceのログ・基準ディレクトリを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: developer・workflow・serviceのログ・基準ディレクトリを求めるための結果（Path）]
    # }
    @property
    def log_root(self) -> Path:
        if self.frozen:
            return self.project_root / "UserData" / "developer"
        return self.project_root / "build" / "developer"

    # {
    #   責務: [validate_project: projectを妥当性を検査する]
    #   処理: [1: projectを妥当性を検査する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: projectを妥当性を検査するための結果（WorkflowResult）]
    # }
    def validate_project(self) -> WorkflowResult:
        report = ProjectValidator(self.project_root / "data", self.project_root / "assets").validate()
        return WorkflowResult(report.ok, report.summary(detail_limit=3))

    # {
    #   責務: [preview_player: 主人公をプレビューする]
    #   処理: [1: 主人公をプレビューする]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 主人公をプレビューするための結果（WorkflowResult）]
    # }
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

    # {
    #   責務: [start_player_build: 主人公・buildを開始する]
    #   処理: [1: 主人公・buildを開始する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 主人公・buildを開始するための結果（WorkflowResult）]
    # }
    def start_player_build(self) -> WorkflowResult:
        return self._start_task("Player Build", "--build-player", "player-build.log")

    # {
    #   責務: [start_player_smoke: 主人公・smokeを開始する]
    #   処理: [1: 主人公・smokeを開始する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 主人公・smokeを開始するための結果（WorkflowResult）]
    # }
    def start_player_smoke(self) -> WorkflowResult:
        return self._start_task("Player Distribution Smoke", "--smoke-player-build", "player-smoke.log")

    # {
    #   責務: [poll: developer・workflow・serviceのpollを求める]
    #   処理: [1: developer・workflow・serviceのpollを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: developer・workflow・serviceのpollを求めるための結果（WorkflowResult | None）]
    # }
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

    # {
    #   責務: [_start_task: taskを開始する]
    #   処理: [1: taskを開始する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     label: 表示名（str）
    #     flag: フラグ（str）
    #     log_name: ログ・名前（str）
    #   ]
    #   戻り値: [result: taskを開始するための結果（WorkflowResult）]
    # }
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

    # {
    #   責務: [_developer_command: developer・workflow・serviceのdeveloper・コマンドを求める]
    #   処理: [1: developer・workflow・serviceのdeveloper・コマンドを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     flag: フラグ（str）
    #   ]
    #   戻り値: [result: developer・workflow・serviceのdeveloper・コマンドを求めるための結果（list[str]）]
    # }
    def _developer_command(self, flag: str) -> list[str]:
        if self.frozen:
            return [self.executable, flag]
        return [self.executable, str(self.project_root / "developer_launcher.py"), flag]

    # {
    #   責務: [_environment: developer・workflow・serviceのenvironmentを求める]
    #   処理: [1: developer・workflow・serviceのenvironmentを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: environment（dict[str, str]）]
    # }
    def _environment(self) -> dict[str, str]:
        environment = os.environ.copy()
        environment["KADOKA_PROJECT_ROOT"] = str(self.project_root)
        environment["KADOKA_DEVELOPER_TOOLS"] = "1"
        return environment
