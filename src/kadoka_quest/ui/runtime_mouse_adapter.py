# {
#   責務: [runtime_mouse_adapter: 画面内の左クリックを既存runtimeへ渡す意味コマンドへ変換します]
#   フィールド: []
# }
from __future__ import annotations

from collections.abc import Iterable, Mapping

import pygame


# {
#   責務: [RuntimeMouseAdapter: Translates screen-specific left clicks into semantic command requests.]
#   フィールド: [
#     password_keys: 暗号の各文字とクリック領域
#     password_actions: 暗号の操作名とクリック領域
#     battle_buttons: 戦闘コマンド名とクリック領域
#   ]
# }
class RuntimeMouseAdapter:
    """Translates screen-specific left clicks into semantic command requests."""

    # {
    #   責務: [__init__: 暗号と戦闘の操作矩形を独立コピーして保持します]
    #   処理: [1: 暗号と戦闘の操作矩形を独立コピーして保持します]
    #   引数: [
    #     self: 処理対象インスタンス
    #     password_keys: 暗号の各文字とクリック領域（Iterable[tuple[str, pygame.Rect]]）
    #     password_actions: 暗号の操作名とクリック領域（Mapping[str, pygame.Rect]）
    #     battle_buttons: 戦闘コマンド名とクリック領域（Iterable[tuple[str, pygame.Rect]]）
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
    #   責務: [translate: 現在の画面と操作可能状態に合う左クリックだけをコマンドへ変換します]
    #   処理: [1: 現在の画面と操作可能状態に合う左クリックだけをコマンドへ変換します]
    #   引数: [
    #     self: 処理対象インスタンス
    #     event: イベント（pygame.event.Event）
    #     mode: field・battle・passwordの画面識別子（str）
    #     battle_enabled: 戦闘コマンドを実行できるか（bool）
    #     now: 演出開始へ渡すミリ秒時刻（int | None）
    #   ]
    #   戻り値: [result: クリック位置に対応する意味コマンド列。対象外なら空列]
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
    #   責務: [_password_click: クリック位置から暗号の文字キーまたは操作ボタンを特定します]
    #   処理: [1: クリック位置から暗号の文字キーまたは操作ボタンを特定します]
    #   引数: [
    #     self: 処理対象インスタンス
    #     position: 座標（tuple[int, int]）
    #   ]
    #   戻り値: [result: 文字追加・一文字消去・決定・取消のいずれか一つの要求、または空列]
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
    #   責務: [_battle_click: 押した戦闘ボタンを選択してから、そのコマンドの実行要求を返します]
    #   処理: [1: 共有矩形から押された項目を探し、選択更新とコマンド実行を順に返します]
    #   引数: [
    #     self: 処理対象インスタンス
    #     position: 座標（tuple[int, int]）
    #     now: 演出開始へ渡すミリ秒時刻（int | None）
    #   ]
    #   戻り値: [result: 実行時・mouse・adapterの戦闘・clickを求めるための結果（list[dict]）]
    # }
    def _battle_click(self, position: tuple[int, int], now: int | None) -> list[dict]:
        # マウス決定後も、キーボードの選択表示を実行したコマンドへ合わせます。
        for index, (command, rect) in enumerate(self.battle_buttons):
            if not rect.collidepoint(position):
                continue
            payload: dict[str, object] = {"command": command}
            if now is not None:
                payload["now"] = int(now)
            return [self._command("battle", "selection.set", index=index), self._command("battle", "execute", **payload)]
        return []

    # {
    #   責務: [_command: 宛先と操作名と引数を意味コマンドの辞書へまとめます]
    #   処理: [1: 宛先と操作名と引数を意味コマンドの辞書へまとめます]
    #   引数: [
    #     target: 対象（str）
    #     action: コマンドの操作名（str）
    #     payload: 要求データ（object）
    #   ]
    #   戻り値: [result: kind・target・action・payloadを持つ意味コマンド辞書]
    # }
    @staticmethod
    def _command(target: str, action: str, **payload: object) -> dict:
        return {"kind": "command", "target": target, "action": action, "payload": payload}
