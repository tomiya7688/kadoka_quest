from __future__ import annotations

from typing import Any

from kadoka_quest.application.app_command import AppCommand


class ManagerCommandApplication:
    """Own semantic commands for the external monster-management screen."""

    def __init__(self, session: Any) -> None:
        self.session = session

    def handle(self, command: AppCommand) -> Any:
        if command.action == "open":
            return self.session.open_manager()
        if command.action == "refresh":
            return self.session.refresh_manager_if_closed()
        raise ValueError(f"管理画面コマンド {command.action} は未対応です。")
