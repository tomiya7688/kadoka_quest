# {
#   責務: [manager_command_app: manager・コマンド・appの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from typing import Any

from kadoka_quest.application.app_command import AppCommand


# {
#   責務: [ManagerCommandApplication: Own semantic commands for external player-management screens.]
#   フィールド: [session: セッション]
# }
class ManagerCommandApplication:
    """Own semantic commands for external player-management screens."""

    # {
    #   責務: [__init__: manager・コマンド・applicationが利用する初期状態と依存を設定する]
    #   処理: [1: manager・コマンド・applicationが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     session: セッション（Any）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, session: Any) -> None:
        self.session = session

    # {
    #   責務: [handle: manager・コマンド・applicationを入力を処理する]
    #   処理: [1: manager・コマンド・applicationを入力を処理する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     command: コマンド（AppCommand）
    #   ]
    #   戻り値: [result: manager・コマンド・applicationを入力を処理するための結果（Any）]
    # }
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
