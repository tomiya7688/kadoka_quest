from __future__ import annotations

from typing import Any

from kadoka_quest.application.app_command import AppCommand


class BattleCommandApplication:
    """Owns the semantic command boundary for the battle screen."""

    def __init__(self, session: Any) -> None:
        self.session = session

    def handle(self, command: AppCommand) -> Any:
        payload = command.payload
        if command.action == "start.wild":
            self.session.start_wild_battle(
                dict(payload["spawn"]),
                fixed_mob_id=str(payload["fixed_mob_id"]),
            )
            return self.session.battle
        if command.action == "execute":
            return self.session.handle_battle_command(str(payload["command"]))
        if command.action == "execute.selected":
            return self.session.handle_battle_command(self.session.selected_battle_command())
        if command.action == "selection.move":
            return self.session.move_battle_selection(int(payload["amount"]))
        if command.action == "selection.set":
            return self.session.set_battle_selection(int(payload["index"]))
        if command.action == "auto.toggle":
            return self.session.toggle_auto_battle()
        if command.action == "cancel":
            self.session.stop_auto_battle()
            self.session.status = "戦闘中です。Aでオート戦闘を切り替えられます。"
            return True
        if command.action == "return":
            return self.session.return_to_field()
        if command.action == "tick":
            now = int(payload["now"])
            changed = self.session.update_battle_playback(now)
            self.session.update_auto_battle(now)
            return changed
        raise ValueError(f"戦闘コマンド {command.action} は未対応です。")
