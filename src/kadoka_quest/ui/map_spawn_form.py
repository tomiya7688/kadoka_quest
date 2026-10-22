# {
#   責務: [map_spawn_form: マップ・出現・formの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import pygame

from kadoka_engine.field_ai import FIELD_AI_TYPES
from kadoka_engine.spawn_controls import map_ai_ratios, parse_map_spawn_controls
from kadoka_quest.ui.common import (
    GOOD, MUTED, WARN, Button, TextField, draw_text, handle_fields,
)


# {
#   責務: [MapSpawnForm: Map-level draft widgets, kept independent from the candidate-row draft.]
#   フィールド: [
#     rate: rate
#     weights: 重み一覧
#     inherit: inherit
#     baseline: baseline
#   ]
# }
class MapSpawnForm:
    """Map-level draft widgets, kept independent from the candidate-row draft."""

    # {
    #   責務: [__init__: マップ・出現・formが利用する初期状態と依存を設定する]
    #   処理: [1: マップ・出現・formが利用する初期状態と依存を設定する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self) -> None:
        self.rate = TextField(pygame.Rect(165, 240, 190, 42), "100")
        self.weights = {
            name: TextField(pygame.Rect(165 + index * 285, 415, 235, 42), value)
            for index, (name, value) in enumerate(zip(FIELD_AI_TYPES, ("70", "25", "5")))
        }
        self.inherit = True
        self.baseline = self.snapshot()

    # {
    #   責務: [snapshot: マップ・出現・formを状態を複製する]
    #   処理: [1: マップ・出現・formを状態を複製する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: マップ・出現・formを状態を複製するための結果（tuple）]
    # }
    def snapshot(self) -> tuple:
        return (self.rate.value, self.inherit, *(field.value for field in self.weights.values()))

    # {
    #   責務: [changed: マップ・出現・formのchangedを求める]
    #   処理: [1: マップ・出現・formのchangedを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: マップ・出現・formのchangedを求めるための結果（bool）]
    # }
    @property
    def changed(self) -> bool:
        return self.snapshot() != self.baseline

    # {
    #   責務: [draft: マップ・出現・formの下書きを求める]
    #   処理: [1: マップ・出現・formの下書きを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: マップ・出現・formの下書きを求めるための結果（dict）]
    # }
    @property
    def draft(self) -> dict:
        return {"rate": self.rate.value,
                "weights": None if self.inherit else {name: field.value for name, field in self.weights.items()}}

    # {
    #   責務: [load: マップ・出現・formを読み込む]
    #   処理: [1: マップ・出現・formを読み込む]
    #   引数: [
    #     self: 処理対象インスタンス
    #     document: 文書（dict）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def load(self, document: dict) -> None:
        self.rate.value = str(document.get("pop_rate", 100))
        weights = document.get("field_ai_weights")
        self.inherit = weights is None
        for name, field in self.weights.items():
            field.value = str(weights.get(name, 0)) if isinstance(weights, dict) else {"random": "70", "chase": "25", "idle": "5"}[name]
        self.deactivate()
        self.baseline = self.snapshot()

    # {
    #   責務: [deactivate: マップ・出現・formのdeactivateを求める]
    #   処理: [1: マップ・出現・formのdeactivateを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def deactivate(self) -> None:
        for field in [self.rate, *self.weights.values()]:
            field.active = False

    # {
    #   責務: [toggle: マップ・出現・formを切り替える]
    #   処理: [1: マップ・出現・formを切り替える]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def toggle(self) -> None:
        self.inherit = not self.inherit
        self.deactivate()

    # {
    #   責務: [toggle_button: buttonを切り替える]
    #   処理: [1: buttonを切り替える]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: buttonを切り替えるための結果（Button）]
    # }
    def toggle_button(self) -> Button:
        label = "AI：種族/既定を継承" if self.inherit else "AI：マップで指定"
        return Button(pygame.Rect(165, 325, 310, 42), label, self.toggle)

    # {
    #   責務: [handle: マップ・出現・formを入力を処理する]
    #   処理: [1: マップ・出現・formを入力を処理する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     event: イベント（pygame.event.Event）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def handle(self, event: pygame.event.Event) -> None:
        fields = [self.rate] if self.inherit else [self.rate, *self.weights.values()]
        if not handle_fields(fields, event):
            self.toggle_button().handle(event)

    # {
    #   責務: [draw: マップ・出現・formを描画する]
    #   処理: [1: マップ・出現・formを描画する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     surface: 描画面（pygame.Surface）
    #     mouse: mouse（tuple[int, int]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def draw(self, surface: pygame.Surface, mouse: tuple[int, int]) -> None:
        self.rate.draw(surface, "マップ全体のポップ率（0〜100%）")
        draw_text(surface, "%", (367, 247), 22)
        draw_text(surface, "生成候補1枠ごとの確率です。0%では野生個体を生成しません。", (165, 291), 17, MUTED)
        self.toggle_button().draw(surface, mouse)
        if self.inherit:
            draw_text(surface, "マップではAIを指定しません。種族の設定 → 既定70/25/5を使います。", (165, 411), 18, MUTED)
            draw_text(surface, "実効比率は種族によって異なります。", (165, 452), 18, MUTED)
        else:
            for name, field in self.weights.items():
                field.draw(surface, name)
            try:
                ratios = map_ai_ratios(parse_map_spawn_controls(**self.draft)["field_ai_weights"])
            except ValueError:
                ratios = None
            if ratios is None:
                draw_text(surface, "不正な設定です。有限の非負数、AI重みは少なくとも1つ正にしてください。", (165, 480), 16, WARN)
            else:
                for index, ratio in enumerate(ratios):
                    draw_text(surface, f"{ratio:.2%}", (165 + index * 285, 480), 21, GOOD)
        draw_text(surface, "比率はマップ指定分。出現候補に個別のAI設定がある場合はそちらを優先します。", (165, 520), 16, MUTED)
