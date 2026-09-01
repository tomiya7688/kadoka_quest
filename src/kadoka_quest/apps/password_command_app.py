from __future__ import annotations

from typing import Any

from kadoka_quest.application.app_command import AppCommand


class PasswordCommandApplication:
    """Owns virtual-keyboard commands independently from pygame input."""

    def __init__(self, session: Any) -> None:
        self.session = session

    def handle(self, command: AppCommand) -> Any:
        if command.action == "append":
            return self.session.append_password(str(command.payload["character"]))
        if command.action == "backspace":
            return self.session.backspace_password()
        if command.action == "submit":
            return self.session.submit_password()
        if command.action == "cancel":
            return self.session.cancel_password()
        raise ValueError(f"暗号入力コマンド {command.action} は未対応です。")
