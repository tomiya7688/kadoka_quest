from __future__ import annotations

from typing import Any

from kadoka_quest.application.app_command import AppCommand
from kadoka_quest.apps.battle_flow_dependencies import BattleFlowDependencies
from kadoka_quest.apps.battle_flow_service import BattleFlowService
from kadoka_quest.apps.legacy_battle_command_adapter import LegacyBattleCommandAdapter


class BattleCommandApplication:
    """Owns the semantic command boundary for the battle screen."""

    def __init__(self, session: Any) -> None:
        self.session = session
        self._flow: BattleFlowService | None = None
        self._legacy: LegacyBattleCommandAdapter | None = None

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

    def _legacy_adapter(self) -> LegacyBattleCommandAdapter:
        if self._legacy is None:
            self._legacy = LegacyBattleCommandAdapter(self.session)
        return self._legacy

    def _now(self, payload: dict) -> int:
        if "now" in payload:
            return int(payload["now"])
        battle_session = getattr(self.session, "battle_session", None)
        return int(getattr(battle_session, "runtime_tick", 0))

    def handle(self, command: AppCommand) -> Any:
        payload = command.payload
        if command.action == "start.wild":
            self.session.start_wild_battle(
                dict(payload["spawn"]),
                fixed_mob_id=str(payload["fixed_mob_id"]),
            )
            return self.session.battle

        flow = self._battle_flow()
        if flow is None:
            return self._legacy_adapter().handle(command)

        if command.action == "execute":
            return flow.execute(str(payload["command"]), self._now(payload))
        if command.action == "execute.selected":
            return flow.execute(flow.selected_command(), self._now(payload))
        if command.action == "selection.move":
            return flow.move_selection(int(payload["amount"]))
        if command.action == "selection.set":
            return flow.set_selection(int(payload["index"]))
        if command.action == "auto.toggle":
            message = flow.toggle_auto(self._now(payload))
            if message is not None:
                self.session.status = message
            return message
        if command.action == "cancel":
            flow.stop_auto()
            self.session.status = "戦闘中です。Aでオート戦闘を切り替えられます。"
            return True
        if command.action == "return":
            return self.session.return_to_field()
        if command.action == "tick":
            now = int(payload["now"])
            changed = flow.update_playback(now)
            flow.update_auto(now, battle_mode=self.session.mode == "battle")
            return changed
        raise ValueError(f"戦闘コマンド {command.action} は未対応です。")
