# {
#   責務: [password_command_app: 暗号・コマンド・appの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from typing import Any

from kadoka_quest.application.app_command import AppCommand


# {
#   責務: [PasswordCommandApplication: Owns virtual-keyboard commands independently from pygame input.]
#   フィールド: [session: セッション]
# }
class PasswordCommandApplication:
    """Owns virtual-keyboard commands independently from pygame input."""

    # {
    #   責務: [__init__: 暗号・コマンド・applicationが利用する初期状態と依存を設定する]
    #   処理: [1: 暗号・コマンド・applicationが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     session: セッション（Any）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, session: Any) -> None:
        self.session = session

    # {
    #   責務: [handle: 暗号・コマンド・applicationを入力を処理する]
    #   処理: [1: 暗号・コマンド・applicationを入力を処理する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     command: コマンド（AppCommand）
    #   ]
    #   戻り値: [result: 暗号・コマンド・applicationを入力を処理するための結果（Any）]
    # }
    def handle(self, command: AppCommand) -> Any:
        if command.action == "open":
            return self.session.open_password_input()
        if command.action == "append":
            return self.session.append_password(str(command.payload["character"]))
        if command.action == "backspace":
            return self.session.backspace_password()
        if command.action == "submit":
            return self.session.submit_password()
        if command.action == "cancel":
            return self.session.cancel_password()
        raise ValueError(f"暗号入力コマンド {command.action} は未対応です。")
