# {
#   責務: [legacy_battle_command_adapter: legacy・戦闘・コマンド・adapterの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from typing import Any

from kadoka_quest.application.app_command import AppCommand


# {
#   責務: [LegacyBattleCommandAdapter: Compatibility-only adapter for pre-BattleFlowService session APIs.]
#   フィールド: [session: セッション]
# }
class LegacyBattleCommandAdapter:
    """Compatibility-only adapter for pre-BattleFlowService session APIs.

    Normal Kadoka Quest runtime does not use this adapter. It exists only while
    older tests and external callers still provide the former battle methods.
    """

    # {
    #   責務: [__init__: legacy・戦闘・コマンド・adapterが利用する初期状態と依存を設定する]
    #   処理: [1: legacy・戦闘・コマンド・adapterが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     session: セッション（Any）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, session: Any) -> None:
        self.session = session

    # {
    #   責務: [handle: legacy・戦闘・コマンド・adapterを入力を処理する]
    #   処理: [1: legacy・戦闘・コマンド・adapterを入力を処理する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     command: コマンド（AppCommand）
    #   ]
    #   戻り値: [result: legacy・戦闘・コマンド・adapterを入力を処理するための結果（Any）]
    # }
    def handle(self, command: AppCommand) -> Any:
        payload = command.payload
        action = command.action

        if action == "execute":
            return self.session.handle_battle_command(str(payload["command"]))
        if action == "execute.selected":
            return self.session.handle_battle_command(self.session.selected_battle_command())
        if action == "selection.move":
            return self.session.move_battle_selection(int(payload["amount"]))
        if action == "selection.set":
            return self.session.set_battle_selection(int(payload["index"]))
        if action == "auto.toggle":
            return self.session.toggle_auto_battle()
        if action == "cancel":
            self.session.stop_auto_battle()
            self.session.status = "戦闘中です。Aでオート戦闘を切り替えられます。"
            return True
        if action == "return":
            return self.session.return_to_field()
        if action == "tick":
            now = int(payload["now"])
            changed = self.session.update_battle_playback(now)
            self.session.update_auto_battle(now)
            return changed
        raise ValueError(f"戦闘コマンド {action} は未対応です。")
