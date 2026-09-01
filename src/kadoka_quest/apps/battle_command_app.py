from __future__ import annotations

from typing import Any

from kadoka_quest.application.app_command import AppCommand


class BattleCommandApplication:
    """Owns the semantic command boundary for the battle screen."""

    def __init__(self, session: Any) -> None:
        self.session = session

    def handle(self, command: AppCommand) -> Any:
        payload = command.payload
        if command.action == "execute":
            return self.session.handle_battle_command(str(payload["command"]))
        if command.action == "execute.selected":
            return self.session.handle_battle_command(self.session.selected_battle_command())
        if command.action == "selection.move":
            self.session.battle_selection = (self.session.battle_selection + int(payload["amount"])) % 4
            return self.session.battle_selection
        if command.action == "selection.set":
            self.session.battle_selection = max(0, min(3, int(payload["index"])))
            return self.session.battle_selection
        if command.action == "auto.toggle":
            return self.session.toggle_auto_battle()
        if command.action == "cancel":
            self.session.auto_battle = False
            self.session.status = "戦闘中です。Aでオート戦闘を切り替えられます。"
            return True
        if command.action == "return":
            return self.session.return_to_field()
        if command.action == "tick":
            changed = self.session.update_battle_playback(int(payload["now"]))
            self.session.update_auto_battle()
            return changed
        raise ValueError(f"戦闘コマンド {command.action} は未対応です。")
