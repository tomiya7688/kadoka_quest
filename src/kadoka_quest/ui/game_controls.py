# {
#   責務: [game_controls: Player用ボタン、入力欄、スクロールバーの表示と入力状態を所有する]
#   フィールド: []
# }
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pygame

from kadoka_quest.ui.common import ScrollBar as BaseScrollBar, TextField as BaseTextField
from kadoka_quest.ui.game_style import ACCENT, BG, MUTED, SELECTED, TEXT, draw_cursor, draw_frame
from kadoka_quest.ui.game_text import draw_text, font


# {
#   責務: [Button: Playerの選択状態と操作コールバックを保持し、マウスと決定キーを受け付ける]
#   フィールド: [
#     rect: ボタンが所有する表示矩形のコピー
#     label: ボタンの表示文字列
#     action: 有効な決定操作で一度呼ぶコールバック
#     enabled: 操作を受け付けるか
#     focused: キーボードの決定操作を受け付けるか
#     selected: 現在のタブなどの持続的な選択を示すか
#   ]
# }
@dataclass
class Button:
    rect: pygame.Rect
    label: str
    action: Callable[[], None]
    enabled: bool = True
    focused: bool = False
    selected: bool = False

    # {
    #   責務: [__post_init__: ボタンの配置変更を呼び出し元の矩形から分離する]
    #   処理: [1: 表示矩形の独立コピーを保持する]
    #   引数: [self: 初期化するButton]
    #   戻り値: [result: なし（None）]
    # }
    def __post_init__(self) -> None:
        # フォーカス配置や画面再配置が呼び出し元の矩形を変更しないようにする。
        self.rect = pygame.Rect(self.rect)

    # {
    #   責務: [draw: 角形ボタンへ選択カーソルと領域内に収まるラベルを描く]
    #   処理: [
    #     1: 有効状態とフォーカスから枠の色を選ぶ
    #     2: ラベルをボタン内へ制限して描き、選択時だけカーソルを添える
    #   ]
    #   引数: [
    #     self: 描画するButton
    #     surface: 描画先の画面
    #     mouse: マウスの画面座標
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def draw(self, surface: pygame.Surface, mouse: tuple[int, int]) -> None:
        # 無効項目はカーソルと黄色を付けず、操作できない状態を表示する。
        highlighted = self.enabled and (self.focused or self.selected or self.rect.collidepoint(mouse))
        color = ACCENT if highlighted else TEXT if self.enabled else MUTED
        draw_frame(surface, self.rect, color, 3 if highlighted else 2, SELECTED if self.selected else BG)
        interior = self.rect.inflate(-16, -8)
        if highlighted:
            draw_cursor(surface, (self.rect.x + 7, self.rect.centery - 5), color)
            interior.x += 12
            interior.width -= 12
        # 長い日本語ラベルでも隣のボタンへ描画しない。
        previous = surface.get_clip()
        surface.set_clip(previous.clip(interior))
        try:
            text_width, text_height = font(16).size(self.label)
            x = max(interior.x, interior.centerx - text_width // 2)
            draw_text(surface, self.label, (x, self.rect.centery - text_height // 2), 16, color)
        finally:
            surface.set_clip(previous)

    # {
    #   責務: [handle: 有効なクリックまたはフォーカス中の決定キーで操作を一度呼ぶ]
    #   処理: [1: 入力条件が成立した場合だけコールバックを実行する]
    #   引数: [
    #     self: 入力を受けるButton
    #     event: pygameの入力イベント
    #   ]
    #   戻り値: [result: ボタンが操作を実行した場合はTrue]
    # }
    def handle(self, event: pygame.event.Event) -> bool:
        # キーリピートによる連続保存や連続変更を避け、決定キーの最初の押下だけを使う。
        clicked = event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)
        confirmed = (
            self.focused and event.type == pygame.KEYDOWN
            and event.key in {pygame.K_RETURN, pygame.K_SPACE}
            and not getattr(event, "repeat", False)
        )
        if self.enabled and (clicked or confirmed):
            self.action()
            return True
        return False


# {
#   責務: [TextField: 既存の文字入力操作を保ち、Player専用の角形入力欄と末尾表示を提供する]
#   フィールド: [
#     rect: 入力欄が所有する表示矩形のコピー
#     value: 編集中の文字列
#     numeric: 数字と先頭の負号だけを受け付けるか
#     active: キー入力を受け付けるか
#   ]
# }
class TextField(BaseTextField):
    # {
    #   責務: [__init__: 呼び出し元から独立した入力欄の矩形と編集状態を用意する]
    #   処理: [1: 矩形を複製して既存の入力状態を初期化する]
    #   引数: [
    #     self: 初期化するTextField
    #     rect: 入力欄の表示矩形
    #     value: 初期表示する文字列
    #     numeric: 数字と先頭の負号だけを受け付けるか
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def __init__(self, rect: pygame.Rect, value: str = "", numeric: bool = False) -> None:
        # 表示専用の差し替えで既存の編集ルールを維持する。
        super().__init__(pygame.Rect(rect), value, numeric)

    # {
    #   責務: [draw: 入力欄の値の末尾と入力中のカーソルを枠内へ描く]
    #   処理: [
    #     1: ラベルとフォーカス状態に応じた角形の枠を描く
    #     2: 値の右端を入力領域へ合わせて描き、描画範囲を復元する
    #   ]
    #   引数: [
    #     self: 描画するTextField
    #     surface: 描画先の画面
    #     label: 入力欄の上に表示するラベル
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def draw(self, surface: pygame.Surface, label: str = "") -> None:
        # ラベルは入力欄の上へ配置し、値の文字画像だけを枠内に制限する。
        if label:
            draw_text(surface, label, (self.rect.x, self.rect.y - 24), 16, MUTED)
        draw_frame(surface, self.rect, ACCENT if self.active else TEXT, 2)
        interior = self.rect.inflate(-16, -10)
        image = font(16)._image(self.value, TEXT, None)
        previous = surface.get_clip()
        surface.set_clip(previous.clip(interior))
        try:
            # 元文字列を書き換えず、横幅を超える入力は右端を見せる。
            x = min(interior.x, interior.right - image.get_width() - 4)
            surface.blit(image, (x, self.rect.centery - image.get_height() // 2))
            if self.active and pygame.time.get_ticks() % 1000 < 550:
                caret_x = min(interior.right - 2, x + image.get_width() + 2)
                pygame.draw.rect(surface, ACCENT, (caret_x, interior.y + 1, 2, max(0, interior.height - 2)))
        finally:
            surface.set_clip(previous)


# {
#   責務: [ScrollBar: 既存のドラッグ操作を保ち、空一覧と小さな表示領域に対応した角形バーを描く]
#   フィールド: [
#     rect: バーが所有する表示矩形のコピー
#     orientation: verticalまたはhorizontalの軸
#     total: 一覧全体の項目数
#     page: 同時に表示する項目数
#     value: 表示を開始する項目の位置
#     dragging: つまみをドラッグ中か
#     drag_offset: つまみの先頭から押下位置までの距離
#   ]
# }
class ScrollBar(BaseScrollBar):
    # {
    #   責務: [__init__: 表示矩形を複製してスクロール軸と範囲を初期化する]
    #   処理: [1: 軸を確認して既存のドラッグ状態を初期化する]
    #   引数: [
    #     self: 初期化するScrollBar
    #     rect: バーの表示矩形
    #     orientation: verticalまたはhorizontal
    #     total: 一覧全体の項目数
    #     page: 同時に表示する項目数
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def __init__(self, rect: pygame.Rect, orientation: str = "vertical", total: int = 0, page: int = 1) -> None:
        # 不明な軸を横向きへ黙って変換せず、呼び出し元の指定誤りを明示する。
        if orientation not in {"vertical", "horizontal"}:
            raise ValueError("スクロール軸はverticalまたはhorizontalを指定してください。")
        super().__init__(pygame.Rect(rect), orientation, total, page)

    # {
    #   責務: [configure: 一覧件数を更新し、表示位置とドラッグ状態を有効範囲へ戻す]
    #   処理: [1: 範囲を更新し、スクロール不要の場合はドラッグを解除する]
    #   引数: [
    #     self: 更新するScrollBar
    #     total: 更新後の一覧項目数
    #     page: 同時に表示する項目数
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def configure(self, total: int, page: int) -> None:
        # 個体削除や再読み込みで一覧が縮んでも、存在しない位置を表示しない。
        super().configure(total, page)
        if self.maximum == 0:
            self.dragging = False

    # {
    #   責務: [thumb_rect: 一覧の表示割合を示すつまみを必ずバーの内側に収める]
    #   処理: [1: バーの長さを上限としてつまみの長さと位置を計算する]
    #   引数: [self: 計測するScrollBar]
    #   戻り値: [result: バーの内側に収まるつまみ矩形]
    # }
    def thumb_rect(self) -> pygame.Rect:
        # 24px未満のバーでも、最小つまみ長がバー全体を超えないようにする。
        length = max(0, self._track_length())
        thumb_length = length
        offset = 0
        if self.maximum:
            thumb_length = min(length, max(12, round(length * self.page / self.total)))
            value = max(0, min(self.maximum, self.value))
            offset = round((length - thumb_length) * value / self.maximum)
        if self.orientation == "vertical":
            return pygame.Rect(self.rect.x, self.rect.y + offset, self.rect.width, thumb_length)
        return pygame.Rect(self.rect.x + offset, self.rect.y, thumb_length, self.rect.height)

    # {
    #   責務: [draw: スクロール範囲とつまみを単色の角形で描く]
    #   処理: [1: 枠とつまみを描き、操作中だけつまみを黄色にする]
    #   引数: [
    #     self: 描画するScrollBar
    #     surface: 描画先の画面
    #     mouse: マウスの画面座標
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def draw(self, surface: pygame.Surface, mouse: tuple[int, int]) -> None:
        # 空一覧では灰色の全長つまみを示し、操作中の色を表示しない。
        draw_frame(surface, self.rect, MUTED, 1)
        thumb = self.thumb_rect()
        highlighted = self.maximum > 0 and (self.dragging or thumb.collidepoint(mouse))
        pygame.draw.rect(surface, ACCENT if highlighted else MUTED, thumb)
