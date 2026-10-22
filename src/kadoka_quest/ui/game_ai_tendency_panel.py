# {
#   責務: [game_ai_tendency_panel: PlayerのAI学習傾向を白黒の角形ゲージと日本語で表示する]
#   フィールド: []
# }
from __future__ import annotations

import pygame

from kadoka_quest.ui.ai_tendency_panel import LABELS, STAGES
from kadoka_quest.ui.game_ui import ACCENT, MUTED, TEXT, draw_frame, draw_text_clipped


# {
#   責務: [draw_ai_tendencies: アプリから受け取った学習傾向を変更せず、表示領域内に描く]
#   処理: [
#     1: 表示領域と列数から各項目の位置を決める
#     2: 学習済みの割合または未学習の表示を角形ゲージとともに描く
#   ]
#   引数: [
#     surface: 描画先の画面
#     rows: アプリが要約したAI学習傾向の一覧
#     rect: 全表示を許可する矩形
#     columns: ゲージを並べる列数
#   ]
#   戻り値: [result: なし（None）]
# }
def draw_ai_tendencies(surface, rows: list[dict], rect: pygame.Rect, columns: int = 2) -> None:
    # 呼び出し元の描画範囲を保ち、狭いウィンドウでも隣のパネルを覆わない。
    previous = surface.get_clip()
    surface.set_clip(previous.clip(rect))
    try:
        draw_text_clipped(surface, "AIの学習傾向", pygame.Rect(rect.x, rect.y, rect.width, 24), 16)
        if not rows:
            draw_text_clipped(surface, "左の一覧から個体を選択してください。", pygame.Rect(rect.x, rect.y + 36, rect.width, 24), 16, MUTED)
            return
        count = max(1, int(columns))
        width = rect.width // count
        for index, row in enumerate(rows):
            x = rect.x + (index % count) * width
            y = rect.y + 36 + (index // count) * 48
            ready = row.get("state") == "ready"
            stage = STAGES.get(row.get("stage"), "不明") if ready else (
                "未学習" if row.get("state") == "unlearned" else "データ不足"
            )
            # ラベルと段階を別の表示領域へ収め、日本語の長い項目名同士を重ねない。
            draw_text_clipped(surface, LABELS.get(row.get("id"), "不明"), pygame.Rect(x, y, max(0, width - 112), 22), 16)
            draw_text_clipped(surface, stage, pygame.Rect(x + max(0, width - 108), y, 100, 22), 16, MUTED)
            track = pygame.Rect(x, y + 25, max(0, width - 22), 10)
            draw_frame(surface, track, MUTED, 1)
            if ready and track.width > 2:
                fill = track.inflate(-2, -2)
                fill.width = round(fill.width * max(0, min(100, float(row.get("value", 0)))) / 100)
                pygame.draw.rect(surface, TEXT, fill)
                pygame.draw.line(surface, ACCENT, (track.centerx, track.y), (track.centerx, track.bottom - 1))
        footer_y = rect.y + 36 + ((len(rows) + count - 1) // count) * 48
        draw_text_clipped(surface, "戦闘経験から覚えた傾向です。中央は中立。", pygame.Rect(rect.x, footer_y, rect.width, 24), 16, MUTED)
    finally:
        surface.set_clip(previous)
