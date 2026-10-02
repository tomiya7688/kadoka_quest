"""Render the player-facing learning summary supplied by the application."""
from __future__ import annotations

from typing import Any

import pygame

from kadoka_quest.ui.common import ACCENT, MUTED, PANEL_ALT, TEXT, draw_text


LABELS = {
    "aggression": "攻撃性", "healing": "回復優先", "mp_economy": "MP節約",
    "critical_defense": "瀕死時防御", "stronger_aggression": "格上への強気",
}
STAGES = {
    "very_low": "とても低い", "low": "低い", "neutral": "中立",
    "high": "高い", "very_high": "とても高い",
}


def draw_ai_tendencies(
    surface: pygame.Surface, rows: list[dict[str, Any]], rect: pygame.Rect, columns: int = 2,
) -> None:
    """Draw finite gauges and explicit unknown states without exposing tables."""
    previous_clip = surface.get_clip()
    surface.set_clip(previous_clip.clip(rect))
    try:
        draw_text(surface, "AIの学習傾向", (rect.x, rect.y), 20, ACCENT, True)
        if not rows:
            draw_text(surface, "左の一覧から個体を選択してください。", (rect.x, rect.y + 42), 15, MUTED)
            return
        width = rect.width // columns
        for index, row in enumerate(rows):
            x = rect.x + (index % columns) * width
            y = rect.y + 38 + (index // columns) * 48
            ready = row["state"] == "ready"
            stage = STAGES.get(row["stage"], "不明") if ready else (
                "未学習" if row["state"] == "unlearned" else "データ不足"
            )
            draw_text(surface, LABELS[row["id"]], (x, y), 14, TEXT, True)
            draw_text(surface, stage, (x + width - 92, y), 13, ACCENT if ready else MUTED)
            track = pygame.Rect(x, y + 23, width - 22, 10)
            pygame.draw.rect(surface, PANEL_ALT, track, border_radius=4)
            if ready:
                fill = track.copy()
                fill.width = round(track.width * row["value"] / 100)
                if fill.width:
                    pygame.draw.rect(surface, ACCENT, fill, border_radius=4)
                pygame.draw.line(surface, TEXT, (track.centerx, track.y), (track.centerx, track.bottom - 1))
        footer_y = rect.y + 38 + ((len(rows) + columns - 1) // columns) * 48
        draw_text(surface, "戦闘経験から覚えた傾向です。ゲージ中央は中立。", (rect.x, footer_y), 13, MUTED)
        draw_text(surface, "記録が少ない項目はまだ不明です。F5で最新の学習を再読み込み。", (rect.x, footer_y + 20), 13, MUTED)
    finally:
        surface.set_clip(previous_clip)
