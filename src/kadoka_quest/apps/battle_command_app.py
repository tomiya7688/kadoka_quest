# {
#   責務: [battle_command_app: 戦闘・コマンド・appの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from typing import Any

from kadoka_quest.application.app_command import AppCommand
from kadoka_quest.apps.battle_flow_dependencies import BattleFlowDependencies
from kadoka_quest.apps.battle_flow_service import BattleFlowService
from kadoka_quest.apps.legacy_battle_command_adapter import LegacyBattleCommandAdapter


# {
#   責務: [BattleCommandApplication: Owns the semantic command boundary for the battle screen.]
#   フィールド: [
#     session: セッション
#     _flow: 進行
#     _legacy: legacy
#   ]
# }
class BattleCommandApplication:
    """Owns the semantic command boundary for the battle screen."""

    # {
    #   責務: [__init__: 戦闘・コマンド・applicationが利用する初期状態と依存を設定する]
    #   処理: [1: 戦闘・コマンド・applicationが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     session: セッション（Any）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, session: Any) -> None:
        self.session = session
        self._flow: BattleFlowService | None = None
        self._legacy: LegacyBattleCommandAdapter | None = None

    # {
    #   責務: [_battle_flow: 戦闘・コマンド・applicationの戦闘・進行を求める]
    #   処理: [1: 戦闘・コマンド・applicationの戦闘・進行を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 戦闘・コマンド・applicationの戦闘・進行を求めるための結果（BattleFlowService | None）]
    # }
    def _battle_flow(self) -> BattleFlowService | None:
        if self._flow is not None:
            return self._flow
        required = ("battle_session", "monsters", "states")
        if not all(hasattr(self.session, name) for name in required):
            return None
        if hasattr(self.session, "progress_session"):
            state_provider = lambda: self.session.progress_session.state
        elif hasattr(self.session, "state"):
            # Older external callers have no ProgressSession yet.
            state_provider = lambda: self.session.state
        else:
            return None
        self._flow = BattleFlowService(
            BattleFlowDependencies(
                session=self.session.battle_session,
                monsters=self.session.monsters,
                states=self.session.states,
                state_provider=state_provider,
            )
        )
        return self._flow

    # {
    #   責務: [_legacy_adapter: 戦闘・コマンド・applicationのlegacy・adapterを求める]
    #   処理: [1: 戦闘・コマンド・applicationのlegacy・adapterを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.・legacy（LegacyBattleCommandAdapter）]
    # }
    def _legacy_adapter(self) -> LegacyBattleCommandAdapter:
        if self._legacy is None:
            self._legacy = LegacyBattleCommandAdapter(self.session)
        return self._legacy

    # {
    #   責務: [_now: 戦闘・コマンド・applicationの現在時刻を求める]
    #   処理: [1: 戦闘・コマンド・applicationの現在時刻を求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     payload: 要求データ（dict）
    #   ]
    #   戻り値: [result: 戦闘・コマンド・applicationの現在時刻を求めるための結果（int）]
    # }
    def _now(self, payload: dict) -> int:
        if "now" in payload:
            return int(payload["now"])
        battle_session = getattr(self.session, "battle_session", None)
        return int(getattr(battle_session, "runtime_tick", 0))

    # {
    #   責務: [handle: 戦闘・コマンド・applicationを入力を処理する]
    #   処理: [1: 戦闘・コマンド・applicationを入力を処理する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     command: コマンド（AppCommand）
    #   ]
    #   戻り値: [result: 戦闘・コマンド・applicationを入力を処理するための結果（Any）]
    # }
    def handle(self, command: AppCommand) -> Any:
        payload = command.payload
        if command.action == "start.wild":
            self.session.start_wild_battle(
                dict(payload["spawn"]),
                fixed_mob_id=str(payload["fixed_mob_id"]),
            )
            if hasattr(self.session, "battle_session"):
                return self.session.battle_session.battle
            return self.session.battle  # Legacy external caller.

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
