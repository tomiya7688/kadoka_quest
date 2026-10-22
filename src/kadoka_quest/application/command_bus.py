# {
#   責務: [command_bus: コマンド・busの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from typing import Any, Callable

from kadoka_quest.application.app_command import AppCommand


# {
#   責務: [CommandBus: Routes a command to exactly one independent application.]
#   フィールド: [_handlers: handlers（dict[str, Callable[[AppCommand], Any]]）]
# }
class CommandBus:
    """Routes a command to exactly one independent application."""

    # {
    #   責務: [__init__: コマンド・busが利用する初期状態と依存を設定する]
    #   処理: [1: コマンド・busが利用する初期状態と依存を設定する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self) -> None:
        self._handlers: dict[str, Callable[[AppCommand], Any]] = {}

    # {
    #   責務: [register: コマンド・busを登録する]
    #   処理: [1: コマンド・busを登録する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     target: 対象（str）
    #     handler: handler（Callable[[AppCommand], Any]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def register(self, target: str, handler: Callable[[AppCommand], Any]) -> None:
        key = str(target).strip()
        if not key:
            raise ValueError("コマンドの対象名は空にできません。")
        if key in self._handlers:
            raise ValueError(f"コマンド対象 {key} は登録済みです。")
        self._handlers[key] = handler

    # {
    #   責務: [dispatch: コマンド・busを配送する]
    #   処理: [1: コマンド・busを配送する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     command: コマンド（AppCommand）
    #   ]
    #   戻り値: [result: コマンド・busを配送するための結果（Any）]
    # }
    def dispatch(self, command: AppCommand) -> Any:
        handler = self._handlers.get(command.target)
        if handler is None:
            raise ValueError(f"コマンド対象 {command.target} は登録されていません。")
        return handler(command)
