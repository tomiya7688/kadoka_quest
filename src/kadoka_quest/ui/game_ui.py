# {
#   責務: [game_ui: Player画面だけが利用する白黒ピクセルUIの公開APIをまとめる]
#   フィールド: []
# }
from __future__ import annotations

from kadoka_quest.ui.common import handle_fields, init_pygame as initialize_window, smoke_frames
from kadoka_quest.ui.game_controls import Button, ScrollBar, TextField
from kadoka_quest.ui.game_navigation import initialize_gamepads, move_list_selection, navigation_event
from kadoka_quest.ui.game_style import (
    ACCENT, BAD, BG, GOOD, INPUT_BG, MUTED, PANEL, PANEL_ALT, SELECTED, TEXT, WARN,
    draw_cursor, draw_frame,
)
from kadoka_quest.ui.game_text import draw_text, draw_text_clipped, draw_wrapped, font, reset_text_cache, wrap_lines


# {
#   責務: [init_pygame: Player画面を開き直す前に古いフォントを破棄してウィンドウを用意する]
#   処理: [
#     1: フォントのキャッシュを破棄して既存のウィンドウ初期化へ委譲する
#     2: ゲームパッドを初期化してウィンドウの描画先を返す
#   ]
#   引数: [
#     title: ウィンドウのタイトル
#     size: ウィンドウの幅と高さ
#   ]
#   戻り値: [result: 描画先のウィンドウSurface]
# }
def init_pygame(title: str, size: tuple[int, int]):
    # pygame.quit後に再び開く管理画面でも、終了前のSDLフォントを再利用しない。
    reset_text_cache()
    surface = initialize_window(title, size)
    # 接続オブジェクトを保持し、デジタルゲームパッドのイベントを受信できるようにする。
    initialize_gamepads()
    return surface


# {
#   責務: [draw_status_bar: Playerへの操作結果や注意を角形の情報枠へ描く]
#   処理: [1: 情報枠を描いて、文字列を枠の内側で折り返す]
#   引数: [
#     surface: 描画先の画面
#     message: 表示する操作結果または注意
#     rect: 情報枠の表示矩形
#     warning: 注意として黄色の枠を表示するか
#   ]
#   戻り値: [result: なし（None）]
# }
def draw_status_bar(surface, message: str, rect, *, warning: bool = False) -> None:
    # 情報が長い場合も枠外へ描かず、黄色は注意が必要な状態に限定する。
    draw_frame(surface, rect, WARN if warning else TEXT, 2)
    draw_wrapped(surface, message, rect.inflate(-24, -12), 16)
