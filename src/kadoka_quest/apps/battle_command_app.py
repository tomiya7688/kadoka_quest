from __future__ import annotations

from typing import Any

from kadoka_quest.application.app_command import AppCommand
from kadoka_quest.apps.battle_flow_dependencies import BattleFlowDependencies
from kadoka_quest.apps.battle_flow_service import BattleFlowService


class BattleCommandApplication:
    """Owns the semantic command boundary for the battle screen."""

    def __init__(self, session: Any) -> None:
        self.session = session
        self._flow: BattleFlowService | None = None

    def _battle_flow(self) -> BattleFlowService | None:
        if self._flow is not None:
            return self._flow
        required = ("battle_session", "monsters", "states", "state")
        if not all(hasattr(self.session, name) for name in required):
            return None
        self._flow = BattleFlowService(
            BattleFlowDependencies(
                session=self.session.battle_session,
                monsters=self.session.monsters,
                states=self.session.states,
                state_provider=lambda: self.session.state,
            )
        )
        return self._flow

    def _now(self, payload: dict) -> int:
        if "now" in payload:
            return int(payload["now"])
        battle_session = getattr(self.session, "battle_session", None)
        return int(getattr(battle_session, "last_auto_tick", 0))

    def handle(self, command: AppCommand) -> Any:
        payload = command.payload
        flow = self._battle_flow()
        if command.action == "start.wild":
            self.session.start_wild_battle(
                dict(payload["spawn"]),
                fixed_mob_id=str(payload["fixed_mob_id"]),
            )
            return self.session.battle
        if command.action == "execute":
            if flow is None:
                return self.session.handle_battle_command(str(payload["command"]))
            return flow.execute(str(payload["command"]), self._now(payload))
        if command.action == "execute.selected":
            if flow is None:
                return self.session.handle_battle_command(self.session.selected_battle_command())
            return flow.execute(flow.selected_command(), self._now(payload))
        if command.action == "selection.move":
            if flow is None:
                return self.session.move_battle_selection(int(payload["amount"]))
            return flow.move_selection(int(payload["amount"]))
        if command.action == "selection.set":
            if flow is None:
                return self.session.set_battle_selection(int(payload["index"]))
            return flow.set_selection(int(payload["index"]))
        if command.action == "auto.toggle":
            if flow is None:
                return self.session.toggle_auto_battle()
            message = flow.toggle_auto(self._now(payload))
            if message is not None:
                self.session.status = message
            return message
        if command.action == "cancel":
            if flow is None:
                self.session.stop_auto_battle()
            else:
                flow.stop_auto()
            self.session.status = "戦闘中です。Aでオート戦闘を切り替えられます。"
            return True
        if command.action == "return":
            return self.session.return_to_field()
        if command.action == "tick":
            now = int(payload["now"])
            if flow is None:
                changed = self.session.update_battle_playback(now)
                self.session.update_auto_battle(now)
                return changed
            changed = flow.update_playback(now)
            flow.update_auto(now, battle_mode=self.session.mode == "battle")
            return changed
        raise ValueError(f"戦闘コマンド {command.action} は未対応です。")
