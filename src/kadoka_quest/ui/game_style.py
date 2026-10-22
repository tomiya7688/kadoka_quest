# {
#   責務: [game_style: Player専用の白黒配色、角形フレーム、独自の菱形カーソルを定義する]
#   フィールド: []
# }
from __future__ import annotations

import pygame


BG = (0, 0, 0)
PANEL = BG
PANEL_ALT = (24, 24, 24)
TEXT = (245, 245, 245)
MUTED = (183, 183, 183)
ACCENT = (255, 230, 109)
GOOD = TEXT
WARN = ACCENT
BAD = TEXT
SELECTED = (38, 38, 38)
INPUT_BG = BG


# {
#   責務: [draw_frame: Playerのパネルを単色背景と角のある太枠で描く]
#   処理: [1: 必要な背景を塗り、指定幅の長方形の枠を描く]
#   引数: [
#     surface: 描画先の画面
#     rect: パネルの外側の矩形
#     color: 枠の色
#     width: 枠の太さを画素数で指定する
#     fill: 背景色。Noneの場合は背景を塗らない
#   ]
#   戻り値: [result: なし（None）]
# }
def draw_frame(surface, rect, color=TEXT, width: int = 3, fill=BG) -> None:
    # 角丸や補間を使用せず、小さい画面でも枠の境界を明確にする。
    if fill is not None:
        pygame.draw.rect(surface, fill, rect)
    pygame.draw.rect(surface, color, rect, max(1, int(width)))


# {
#   責務: [draw_cursor: 選択項目の左に、中央が空いた独自のピクセル菱形を描く]
#   処理: [1: 5行の画素模様を指定倍率で描く]
#   引数: [
#     surface: 描画先の画面
#     position: カーソル模様の左上座標
#     color: カーソルの色
#     scale: 1画素を拡大する正の整数倍率
#   ]
#   戻り値: [result: なし（None）]
# }
def draw_cursor(surface, position, color=ACCENT, scale: int = 2) -> None:
    # 中央の空白と右側の先端を持つ模様で、作品固有の図柄を複製せず選択を示す。
    unit = max(1, int(scale))
    for row, pattern in enumerate(("00100", "01110", "11011", "01110", "00100")):
        for column, pixel in enumerate(pattern):
            if pixel == "1":
                pygame.draw.rect(surface, color, (position[0] + column * unit, position[1] + row * unit, unit, unit))
