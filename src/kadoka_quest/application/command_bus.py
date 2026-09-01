from __future__ import annotations

from typing import Any, Callable

from kadoka_quest.application.app_command import AppCommand


class CommandBus:
    """Routes a command to exactly one independent application."""

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[[AppCommand], Any]] = {}

    def register(self, target: str, handler: Callable[[AppCommand], Any]) -> None:
        key = str(target).strip()
        if not key:
            raise ValueError("コマンドの対象名は空にできません。")
        if key in self._handlers:
            raise ValueError(f"コマンド対象 {key} は登録済みです。")
        self._handlers[key] = handler

    def dispatch(self, command: AppCommand) -> Any:
        handler = self._handlers.get(command.target)
        if handler is None:
            raise ValueError(f"コマンド対象 {command.target} は登録されていません。")
        return handler(command)
