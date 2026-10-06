# {
#   責務: [runtime_mouse_adapter: 実行時・mouse・adapterの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from collections.abc import Iterable, Mapping

import pygame


# {
#   責務: [RuntimeMouseAdapter: Translates screen-specific left clicks into semantic command requests.]
#   フィールド: [
#     password_keys: 暗号・キー一覧
#     password_actions: 暗号・actions
#     battle_buttons: 戦闘・buttons
#   ]
# }
class RuntimeMouseAdapter:
    """Translates screen-specific left clicks into semantic command requests."""

    # {
    #   責務: [__init__: 実行時・mouse・adapterが利用する初期状態と依存を設定する]
    #   処理: [1: 実行時・mouse・adapterが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     password_keys: 暗号・キー一覧（Iterable[tuple[str, pygame.Rect]]）
    #     password_actions: 暗号・actions（Mapping[str, pygame.Rect]）
    #     battle_buttons: 戦闘・buttons（Iterable[tuple[str, pygame.Rect]]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(
        self,
        password_keys: Iterable[tuple[str, pygame.Rect]],
        password_actions: Mapping[str, pygame.Rect],
        battle_buttons: Iterable[tuple[str, pygame.Rect]],
    ) -> None:
        self.password_keys = [(character, rect.copy()) for character, rect in password_keys]
        self.password_actions = {action: rect.copy() for action, rect in password_actions.items()}
        self.battle_buttons = [(command, rect.copy()) for command, rect in battle_buttons]

    # {
    #   責務: [translate: 実行時・mouse・adapterを変換する]
    #   処理: [1: 実行時・mouse・adapterを変換する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     event: イベント（pygame.event.Event）
    #     mode: mode（str）
    #     battle_enabled: 戦闘・enabled（bool）
    #     now: 現在時刻（int | None）
    #   ]
    #   戻り値: [result: 実行時・mouse・adapterを変換するための結果（list[dict]）]
    # }
    def translate(
        self,
        event: pygame.event.Event,
        mode: str,
        *,
        battle_enabled: bool = True,
        now: int | None = None,
    ) -> list[dict]:
        if event.type != pygame.MOUSEBUTTONDOWN or getattr(event, "button", None) != 1:
            return []
        position = tuple(event.pos)
        if mode == "password":
            return self._password_click(position)
        if mode == "battle" and battle_enabled:
            return self._battle_click(position, now)
        return []

    # {
    #   責務: [_password_click: 実行時・mouse・adapterの暗号・clickを求める]
    #   処理: [1: 実行時・mouse・adapterの暗号・clickを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     position: 座標（tuple[int, int]）
    #   ]
    #   戻り値: [result: 実行時・mouse・adapterの暗号・clickを求めるための結果（list[dict]）]
    # }
    def _password_click(self, position: tuple[int, int]) -> list[dict]:
        for character, rect in self.password_keys:
            if rect.collidepoint(position):
                return [self._command("password", "append", character=character)]
        for action in ("backspace", "submit", "cancel"):
            rect = self.password_actions.get(action)
            if rect is not None and rect.collidepoint(position):
                return [self._command("password", action)]
        return []

    # {
    #   責務: [_battle_click: 実行時・mouse・adapterの戦闘・clickを求める]
    #   処理: [1: 実行時・mouse・adapterの戦闘・clickを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     position: 座標（tuple[int, int]）
    #     now: 現在時刻（int | None）
    #   ]
    #   戻り値: [result: 実行時・mouse・adapterの戦闘・clickを求めるための結果（list[dict]）]
    # }
    def _battle_click(self, position: tuple[int, int], now: int | None) -> list[dict]:
        for command, rect in self.battle_buttons:
            if not rect.collidepoint(position):
                continue
            payload: dict[str, object] = {"command": command}
            if now is not None:
                payload["now"] = int(now)
            return [self._command("battle", "execute", **payload)]
        return []

    # {
    #   責務: [_command: 実行時・mouse・adapterのコマンドを求める]
    #   処理: [1: 実行時・mouse・adapterのコマンドを求める]
    #   引数: [
    #     target: 対象（str）
    #     action: action（str）
    #     payload: 要求データ（object）
    #   ]
    #   戻り値: [result: 実行時・mouse・adapterのコマンドを求めるための結果（dict）]
    # }
    @staticmethod
    def _command(target: str, action: str, **payload: object) -> dict:
        return {"kind": "command", "target": target, "action": action, "payload": payload}
