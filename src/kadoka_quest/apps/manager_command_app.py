from __future__ import annotations

from typing import Any

from kadoka_quest.application.app_command import AppCommand


class ManagerCommandApplication:
    """Own semantic commands for external player-management screens."""

    def __init__(self, session: Any) -> None:
        self.session = session

    def handle(self, command: AppCommand) -> Any:
        if command.action == "open":
            return self.session.open_manager()
        if command.action == "simulation.open":
            return self.session.open_simulation_manager()
        if command.action == "refresh":
            result = self.session.refresh_manager_if_closed()
            refresh_simulation = getattr(self.session, "refresh_simulation_if_closed", None)
            if refresh_simulation is not None:
                refresh_simulation()
            return result
        raise ValueError(f"管理画面コマンド {command.action} は未対応です。")
