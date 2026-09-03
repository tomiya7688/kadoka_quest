from __future__ import annotations

from typing import Any

from kadoka_quest.application.app_command import AppCommand
from kadoka_quest.application.command_bus import CommandBus
from kadoka_quest.apps.battle_command_app import BattleCommandApplication
from kadoka_quest.apps.field_command_app import FieldCommandApplication
from kadoka_quest.apps.manager_command_app import ManagerCommandApplication
from kadoka_quest.apps.password_command_app import PasswordCommandApplication


class RuntimeOrchestrator:
    """Own screen mode and route semantic commands and cross-app effects."""

    MODES = {"field", "battle", "password"}

    def __init__(self, session: Any) -> None:
        self.session = session
        self.mode = "field"
        self.previous_mode: str | None = None
        self.bus = CommandBus()
        self.bus.register("field", FieldCommandApplication(session).handle)
        self.bus.register("battle", BattleCommandApplication(session).handle)
        self.bus.register("password", PasswordCommandApplication(session).handle)
        self.bus.register("manager", ManagerCommandApplication(session).handle)

    def transition_to(self, mode: str) -> str:
        target = str(mode)
        if target not in self.MODES:
            raise ValueError(f"画面モード {target} は未対応です。")
        if target != self.mode:
            self.previous_mode = self.mode
            self.mode = target
        return self.mode

    def dispatch(self, target: str, action: str, **payload: Any) -> Any:
        return self.bus.dispatch(AppCommand(str(target), str(action), payload))

    def apply_field_effect(self, effect: dict) -> Any:
        status = effect.get("status")
        if status is not None:
            self.session.status = str(status)
        kind = str(effect.get("kind", "none"))
        if kind in {"none", "message"}:
            return None
        if kind == "transition":
            target = effect["target"]
            return self.dispatch(
                "field",
                "map.change",
                map_id=str(target["map_id"]),
                x=int(target["x"]),
                y=int(target["y"]),
                message=str(status) if status else None,
            )
        if kind == "npc_battle":
            return self.dispatch(
                "battle",
                "start.wild",
                spawn=dict(effect["spawn"]),
                fixed_mob_id=str(effect["npc_id"]),
            )
        if kind == "npc_despawn":
            return self.dispatch("field", "mob.despawn", npc_id=str(effect["npc_id"]))
        if kind == "register_church":
            return self.dispatch("field", "church.register", revive=dict(effect["revive"]))
        if kind == "open_password":
            return self.dispatch("password", "open")
        if kind == "open_manager":
            return self.dispatch("manager", "open")
        if kind == "gain_item":
            return self.dispatch("field", "item.gain", item_id=str(effect["item"]))
        raise ValueError(f"フィールド効果 {kind} は未対応です。")
