# {
#   責務: [runtime_orchestrator: 実行時・orchestratorの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from typing import Any

from kadoka_quest.application.app_command import AppCommand
from kadoka_quest.application.command_bus import CommandBus
from kadoka_quest.apps.battle_command_app import BattleCommandApplication
from kadoka_quest.apps.field_command_app import FieldCommandApplication
from kadoka_quest.apps.manager_command_app import ManagerCommandApplication
from kadoka_quest.apps.password_command_app import PasswordCommandApplication


# {
#   責務: [RuntimeOrchestrator: Own screen mode and route semantic commands and cross-app effects.]
#   フィールド: [
#     MODES: modes
#     session: セッション
#     mode: mode
#     previous_mode: previous・mode
#     bus: bus
#   ]
# }
class RuntimeOrchestrator:
    """Own screen mode and route semantic commands and cross-app effects."""

    MODES = {"field", "battle", "password"}

    # {
    #   責務: [__init__: 実行時・orchestratorが利用する初期状態と依存を設定する]
    #   処理: [1: 実行時・orchestratorが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     session: セッション（Any）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, session: Any) -> None:
        self.session = session
        self.mode = "field"
        self.previous_mode: str | None = None
        self.bus = CommandBus()
        self.bus.register("field", FieldCommandApplication(session).handle)
        self.bus.register("battle", BattleCommandApplication(session).handle)
        self.bus.register("password", PasswordCommandApplication(session).handle)
        self.bus.register("manager", ManagerCommandApplication(session).handle)

    # {
    #   責務: [transition_to: 実行時・orchestratorの移動ポイント・toを求める]
    #   処理: [1: 実行時・orchestratorの移動ポイント・toを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     mode: mode（str）
    #   ]
    #   戻り値: [result: self.mode（str）]
    # }
    def transition_to(self, mode: str) -> str:
        target = str(mode)
        if target not in self.MODES:
            raise ValueError(f"画面モード {target} は未対応です。")
        if target != self.mode:
            self.previous_mode = self.mode
            self.mode = target
        return self.mode

    # {
    #   責務: [dispatch: 実行時・orchestratorを配送する]
    #   処理: [1: 実行時・orchestratorを配送する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     target: 対象（str）
    #     action: action（str）
    #     payload: 要求データ（Any）
    #   ]
    #   戻り値: [result: 実行時・orchestratorを配送するための結果（Any）]
    # }
    def dispatch(self, target: str, action: str, **payload: Any) -> Any:
        return self.bus.dispatch(AppCommand(str(target), str(action), payload))

    # {
    #   責務: [apply_field_effect: フィールド・効果を適用する]
    #   処理: [1: フィールド・効果を適用する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     effect: 効果（dict）
    #   ]
    #   戻り値: [result: フィールド・効果を適用するための結果（Any）]
    # }
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
        if kind == "open_simulation_manager":
            return self.dispatch("manager", "simulation.open")
        if kind == "gain_item":
            return self.dispatch("field", "item.gain", item_id=str(effect["item"]))
        raise ValueError(f"フィールド効果 {kind} は未対応です。")
