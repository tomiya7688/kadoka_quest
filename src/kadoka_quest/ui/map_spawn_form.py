from __future__ import annotations

import pygame

from kadoka_engine.field_ai import FIELD_AI_TYPES
from kadoka_engine.spawn_controls import map_ai_ratios, parse_map_spawn_controls
from kadoka_quest.ui.common import (
    GOOD, MUTED, WARN, Button, TextField, draw_text, handle_fields,
)


class MapSpawnForm:
    """Map-level draft widgets, kept independent from the candidate-row draft."""

    def __init__(self) -> None:
        self.rate = TextField(pygame.Rect(165, 240, 190, 42), "100")
        self.weights = {
            name: TextField(pygame.Rect(165 + index * 285, 415, 235, 42), value)
            for index, (name, value) in enumerate(zip(FIELD_AI_TYPES, ("70", "25", "5")))
        }
        self.inherit = True
        self.baseline = self.snapshot()

    def snapshot(self) -> tuple:
        return (self.rate.value, self.inherit, *(field.value for field in self.weights.values()))

    @property
    def changed(self) -> bool:
        return self.snapshot() != self.baseline

    @property
    def draft(self) -> dict:
        return {"rate": self.rate.value,
                "weights": None if self.inherit else {name: field.value for name, field in self.weights.items()}}

    def load(self, document: dict) -> None:
        self.rate.value = str(document.get("pop_rate", 100))
        weights = document.get("field_ai_weights")
        self.inherit = weights is None
        for name, field in self.weights.items():
            field.value = str(weights.get(name, 0)) if isinstance(weights, dict) else {"random": "70", "chase": "25", "idle": "5"}[name]
        self.deactivate()
        self.baseline = self.snapshot()

    def deactivate(self) -> None:
        for field in [self.rate, *self.weights.values()]:
            field.active = False

    def toggle(self) -> None:
        self.inherit = not self.inherit
        self.deactivate()

    def toggle_button(self) -> Button:
        label = "AI：種族/既定を継承" if self.inherit else "AI：マップで指定"
        return Button(pygame.Rect(165, 325, 310, 42), label, self.toggle)

    def handle(self, event: pygame.event.Event) -> None:
        fields = [self.rate] if self.inherit else [self.rate, *self.weights.values()]
        if not handle_fields(fields, event):
            self.toggle_button().handle(event)

    def draw(self, surface: pygame.Surface, mouse: tuple[int, int]) -> None:
        self.rate.draw(surface, "マップ全体のポップ率（0〜100%）")
        draw_text(surface, "%", (367, 247), 22)
        draw_text(surface, "注意：ポップ率のゲーム内反映は後続実装です。", (165, 291), 17, WARN)
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
