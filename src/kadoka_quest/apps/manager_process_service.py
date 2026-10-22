# {
#   責務: [manager_process_service: manager・process・serviceの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import subprocess
import sys
from typing import Any


# {
#   責務: [ManagerProcessService: Owns launching and observing one external player-management process.]
#   フィールド: [
#     script_path: script・パス
#     python_executable: python・executable
#     launcher: launcher
#     frozen: frozen
#     frozen_argument: frozen・argument
#     process: process
#   ]
# }
class ManagerProcessService:
    """Owns launching and observing one external player-management process."""

    # {
    #   責務: [__init__: manager・process・serviceが利用する初期状態と依存を設定する]
    #   処理: [1: manager・process・serviceが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     script_path: script・パス（Path）
    #     python_executable: python・executable（str | None）
    #     launcher: launcher（Callable[..., Any]）
    #     frozen: frozen（bool | None）
    #     frozen_argument: frozen・argument（str）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(
        self,
        script_path: Path,
        *,
        python_executable: str | None = None,
        launcher: Callable[..., Any] = subprocess.Popen,
        frozen: bool | None = None,
        frozen_argument: str = "--manager",
    ) -> None:
        self.script_path = Path(script_path)
        self.python_executable = str(python_executable or sys.executable)
        self.launcher = launcher
        self.frozen = bool(getattr(sys, "frozen", False)) if frozen is None else bool(frozen)
        self.frozen_argument = str(frozen_argument)
        self.process: Any | None = None

    # {
    #   責務: [open: manager・process・serviceを開く]
    #   処理: [1: manager・process・serviceを開く]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: manager・process・serviceを開くための結果（str）]
    # }
    def open(self) -> str:
        if self.is_running():
            return "already_running"
        command = (
            [self.python_executable, self.frozen_argument]
            if self.frozen
            else [self.python_executable, str(self.script_path)]
        )
        self.process = self.launcher(command, cwd=self.script_path.parent)
        return "started"

    # {
    #   責務: [is_running: runningを該当するか判定する]
    #   処理: [1: runningを該当するか判定する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: runningを該当するか判定するための結果（bool）]
    # }
    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    # {
    #   責務: [consume_closed: closedを消費する]
    #   処理: [1: closedを消費する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: closedを消費するための結果（bool）]
    # }
    def consume_closed(self) -> bool:
        if self.process is None or self.process.poll() is None:
            return False
        self.process = None
        return True
