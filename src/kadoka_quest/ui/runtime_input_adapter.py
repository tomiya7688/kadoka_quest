# {
#   責務: [runtime_input_adapter: 実行時・入力・adapterの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import pygame


# {
#   責務: [RuntimeInputAdapter: Translates pygame keyboard events into plain semantic command requests.]
#   フィールド: [move_directions: move・directions]
# }
class RuntimeInputAdapter:
    """Translates pygame keyboard events into plain semantic command requests."""

    # {
    #   責務: [__init__: 実行時・入力・adapterが利用する初期状態と依存を設定する]
    #   処理: [1: 実行時・入力・adapterが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     move_directions: move・directions（dict[int, str]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, move_directions: dict[int, str]) -> None:
        self.move_directions = dict(move_directions)

    # {
    #   責務: [translate: 実行時・入力・adapterを変換する]
    #   処理: [1: 実行時・入力・adapterを変換する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     event: イベント（pygame.event.Event）
    #     mode: mode（str）
    #     now: 現在時刻（int）
    #     battle_finished: 戦闘・finished（bool）
    #     battle_playback: 戦闘・playback（bool）
    #   ]
    #   戻り値: [result: 実行時・入力・adapterを変換するための結果（list[dict]）]
    # }
    def translate(
        self,
        event: pygame.event.Event,
        mode: str,
        now: int,
        *,
        battle_finished: bool = False,
        battle_playback: bool = False,
    ) -> list[dict]:
        if event.type == pygame.QUIT:
            return [{"kind": "quit"}]
        if mode == "field" and event.type == pygame.JOYHATMOTION:
            return self._field_hat(event, now)
        if event.type == pygame.KEYUP:
            return self._key_up(event)
        if event.type != pygame.KEYDOWN:
            return []
        if event.key == pygame.K_ESCAPE:
            return self._escape(mode, battle_finished, battle_playback)
        if mode == "field":
            return self._field_key(event, now)
        if mode == "battle":
            return self._battle_key(event, battle_finished, battle_playback, now)
        if mode == "password":
            return self._password_key(event)
        return []

    # {
    #   責務: [_key_up: 実行時・入力・adapterのキー・upを求める]
    #   処理: [1: 実行時・入力・adapterのキー・upを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     event: イベント（pygame.event.Event）
    #   ]
    #   戻り値: [result: 実行時・入力・adapterのキー・upを求めるための結果（list[dict]）]
    # }
    def _key_up(self, event: pygame.event.Event) -> list[dict]:
        direction = self.move_directions.get(event.key)
        if direction is None:
            return []
        return [self._command("field", "move.stop", direction=direction)]

    # {
    #   責務: [_escape: 実行時・入力・adapterのescapeを求める]
    #   処理: [1: 実行時・入力・adapterのescapeを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     mode: mode（str）
    #     battle_finished: 戦闘・finished（bool）
    #     battle_playback: 戦闘・playback（bool）
    #   ]
    #   戻り値: [result: 実行時・入力・adapterのescapeを求めるための結果（list[dict]）]
    # }
    def _escape(self, mode: str, battle_finished: bool, battle_playback: bool) -> list[dict]:
        if mode == "password":
            return [self._command("password", "cancel")]
        if mode == "battle":
            action = "return" if battle_finished and not battle_playback else "cancel"
            return [self._command("battle", action)]
        return [{"kind": "quit"}]

    # {
    #   責務: [_field_key: フィールドの移動・決定・既存ショートカットを意味要求へ変換します]
    #   処理: [1: 移動の初回押下を変換し、その他のキーを調べる操作やパーティ操作へ対応付けます]
    #   引数: [
    #     self: 移動キー対応表を持つ入力アダプター
    #     event: フィールドで押されたキーのイベント
    #     now: 移動開始のタイマーへ渡す現在ミリ秒
    #   ]
    #   戻り値: [result: 実行時・入力・adapterのフィールド・キーを求めるための結果（list[dict]）]
    # }
    def _field_key(self, event: pygame.event.Event, now: int) -> list[dict]:
        # OSのキーリピートには頼らず、移動Sessionが長押し間隔を所有します。
        direction = self.move_directions.get(event.key)
        if direction is not None:
            if getattr(event, "repeat", False):
                return []
            return [self._command("field", "move.start", direction=direction, now=int(now))]
        actions = {
            pygame.K_SPACE: "interact",
            pygame.K_RETURN: "interact",
            pygame.K_KP_ENTER: "interact",
            pygame.K_l: "pickup",
            pygame.K_t: "tactic.cycle",
            pygame.K_r: "ai.reset",
            pygame.K_F5: "acquire.scan",
            pygame.K_F7: "party.save_preset",
            pygame.K_F8: "party.load_next_preset",
        }
        if event.key in actions:
            return [self._command("field", actions[event.key])]
        if pygame.K_1 <= event.key <= pygame.K_4:
            return [self._command("field", "party.select", index=event.key - pygame.K_1)]
        return []

    # {
    #   責務: [_field_hat: ゲームパッドの十字キー変更を移動停止と新方向の開始へ変換します]
    #   処理: [1: 保持中の方向を解除し、中立でなければ優先方向の移動を開始します]
    #   引数: [
    #     self: 意味要求を組み立てる入力アダプター
    #     event: 十字キーのX方向とY方向を持つpygameイベント
    #     now: 移動開始に渡す現在ミリ秒
    #   ]
    #   戻り値: [result: 移動停止の要求と、必要な場合の移動開始要求]
    # }
    def _field_hat(self, event: pygame.event.Event, now: int) -> list[dict]:
        # 中立の入力にはKEYUPが来ないため、方向を外すたびに長押しを解除します。
        requests = [self._command("field", "move.stop", direction=direction) for direction in ("left", "right", "back", "front")]
        x, y = event.value
        direction = None
        if y:
            direction = "back" if y > 0 else "front"
        elif x:
            direction = "right" if x > 0 else "left"
        if direction is not None:
            requests.append(self._command("field", "move.start", direction=direction, now=int(now)))
        return requests

    # {
    #   責務: [_battle_key: 実行時・入力・adapterの戦闘・キーを求める]
    #   処理: [1: 実行時・入力・adapterの戦闘・キーを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     event: イベント（pygame.event.Event）
    #     battle_finished: 戦闘・finished（bool）
    #     battle_playback: 戦闘・playback（bool）
    #     now: 現在時刻（int）
    #   ]
    #   戻り値: [result: 実行時・入力・adapterの戦闘・キーを求めるための結果（list[dict]）]
    # }
    def _battle_key(
        self,
        event: pygame.event.Event,
        battle_finished: bool,
        battle_playback: bool,
        now: int,
    ) -> list[dict]:
        confirm_keys = {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE}
        if battle_finished and not battle_playback and event.key in confirm_keys:
            return [self._command("battle", "return")]
        if event.key == pygame.K_a:
            return [self._command("battle", "auto.toggle", now=int(now))]
        if event.key in {pygame.K_LEFT, pygame.K_UP}:
            return [self._command("battle", "selection.move", amount=-1)]
        if event.key in {pygame.K_RIGHT, pygame.K_DOWN}:
            return [self._command("battle", "selection.move", amount=1)]
        if event.key in confirm_keys:
            return [self._command("battle", "execute.selected", now=int(now))]
        if pygame.K_1 <= event.key <= pygame.K_4:
            return [
                self._command("battle", "selection.set", index=event.key - pygame.K_1),
                self._command("battle", "execute.selected", now=int(now)),
            ]
        return []

    # {
    #   責務: [_password_key: 実行時・入力・adapterの暗号・キーを求める]
    #   処理: [1: 実行時・入力・adapterの暗号・キーを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     event: イベント（pygame.event.Event）
    #   ]
    #   戻り値: [result: 実行時・入力・adapterの暗号・キーを求めるための結果（list[dict]）]
    # }
    def _password_key(self, event: pygame.event.Event) -> list[dict]:
        if event.key == pygame.K_BACKSPACE:
            return [self._command("password", "backspace")]
        if event.key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
            return [self._command("password", "submit")]
        character = str(getattr(event, "unicode", ""))
        if character:
            return [self._command("password", "append", character=character)]
        return []

    # {
    #   責務: [_command: 実行時・入力・adapterのコマンドを求める]
    #   処理: [1: 実行時・入力・adapterのコマンドを求める]
    #   引数: [
    #     target: 対象（str）
    #     action: action（str）
    #     payload: 要求データ（object）
    #   ]
    #   戻り値: [result: 実行時・入力・adapterのコマンドを求めるための結果（dict）]
    # }
    @staticmethod
    def _command(target: str, action: str, **payload: object) -> dict:
        return {"kind": "command", "target": target, "action": action, "payload": payload}
