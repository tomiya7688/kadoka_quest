# {
#   責務: [common: commonの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Callable

import pygame


BG = (17, 24, 39)
PANEL = (31, 41, 55)
PANEL_ALT = (43, 55, 72)
TEXT = (238, 242, 247)
MUTED = (164, 174, 192)
ACCENT = (100, 190, 255)
GOOD = (110, 215, 145)
WARN = (255, 191, 99)
BAD = (245, 112, 112)
SELECTED = (55, 94, 122)
INPUT_BG = (24, 32, 44)


# {
#   責務: [init_pygame: pygameの初期化する]
#   処理: [1: pygameの初期化する]
#   引数: [
#     title: title（str）
#     size: 大きさ（tuple[int, int]）
#   ]
#   戻り値: [result: pygameの初期化するための結果（pygame.Surface）]
# }
def init_pygame(title: str, size: tuple[int, int]) -> pygame.Surface:
    pygame.init()
    pygame.display.set_caption(title)
    return pygame.display.set_mode(size)


# {
#   責務: [font: commonのフォントを求める]
#   処理: [1: commonのフォントを求める]
#   引数: [
#     size: 大きさ（int）
#     bold: bold（bool）
#   ]
#   戻り値: [result: commonのフォントを求めるための結果（pygame.font.Font）]
# }
def font(size: int, bold: bool = False) -> pygame.font.Font:
    names = ["Yu Gothic UI", "Meiryo", "Noto Sans CJK JP", "Arial"]
    return pygame.font.SysFont(names, size, bold=bold)


# {
#   責務: [draw_text: 文字列を描画する]
#   処理: [1: 文字列を描画する]
#   引数: [
#     surface: 描画面（pygame.Surface）
#     value: 値（object）
#     position: 座標（tuple[int, int]）
#     size: 大きさ（int）
#     color: 色（tuple[int, int, int]）
#     bold: bold（bool）
#   ]
#   戻り値: [result: 文字列を描画するための結果（pygame.Rect）]
# }
def draw_text(
    surface: pygame.Surface,
    value: object,
    position: tuple[int, int],
    size: int = 22,
    color: tuple[int, int, int] = TEXT,
    bold: bool = False,
) -> pygame.Rect:
    image = font(size, bold).render(str(value), True, color)
    return surface.blit(image, position)


# {
#   責務: [draw_wrapped: wrappedを描画する]
#   処理: [1: wrappedを描画する]
#   引数: [
#     surface: 描画面（pygame.Surface）
#     value: 値（str）
#     rect: 表示矩形（pygame.Rect）
#     size: 大きさ（int）
#     color: 色（tuple[int, int, int]）
#     line_gap: line・gap（int）
#   ]
#   戻り値: [result: current・Y座標（int）]
# }
def draw_wrapped(
    surface: pygame.Surface,
    value: str,
    rect: pygame.Rect,
    size: int = 20,
    color: tuple[int, int, int] = TEXT,
    line_gap: int = 4,
) -> int:
    current_y = rect.y
    words = list(value)
    line = ""
    current_font = font(size)
    for character in words:
        candidate = line + character
        if current_font.size(candidate)[0] > rect.width and line:
            surface.blit(current_font.render(line, True, color), (rect.x, current_y))
            current_y += size + line_gap
            line = character
        else:
            line = candidate
    if line:
        surface.blit(current_font.render(line, True, color), (rect.x, current_y))
        current_y += size + line_gap
    return current_y


# {
#   責務: [Button: buttonの状態と振る舞いを担当する]
#   フィールド: [
#     rect: 表示矩形（pygame.Rect）
#     label: 表示名（str）
#     action: action（Callable[[], None]）
#     enabled: enabled（bool）
#   ]
# }
@dataclass
class Button:
    rect: pygame.Rect
    label: str
    action: Callable[[], None]
    enabled: bool = True

    # {
    #   責務: [draw: buttonを描画する]
    #   処理: [1: buttonを描画する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     surface: 描画面（pygame.Surface）
    #     mouse: mouse（tuple[int, int]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def draw(self, surface: pygame.Surface, mouse: tuple[int, int]) -> None:
        hovered = self.enabled and self.rect.collidepoint(mouse)
        color = (64, 112, 148) if hovered else (47, 74, 99)
        if not self.enabled:
            color = (48, 52, 60)
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, ACCENT if hovered else PANEL_ALT, self.rect, 2, border_radius=8)
        image = font(20, True).render(self.label, True, TEXT if self.enabled else MUTED)
        surface.blit(image, image.get_rect(center=self.rect.center))

    # {
    #   責務: [handle: buttonを入力を処理する]
    #   処理: [1: buttonを入力を処理する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     event: イベント（pygame.event.Event）
    #   ]
    #   戻り値: [result: buttonを入力を処理するための結果（bool）]
    # }
    def handle(self, event: pygame.event.Event) -> bool:
        if self.enabled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.action()
            return True
        return False


# {
#   責務: [ScrollBar: scroll・barの状態と振る舞いを担当する]
#   フィールド: [
#     rect: 表示矩形
#     orientation: orientation
#     total: total
#     page: page
#     value: 値
#     dragging: dragging
#     drag_offset: drag・表示位置
#   ]
# }
class ScrollBar:
    # {
    #   責務: [__init__: scroll・barが利用する初期状態と依存を設定する]
    #   処理: [1: scroll・barが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     rect: 表示矩形（pygame.Rect）
    #     orientation: orientation（str）
    #     total: total（int）
    #     page: page（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, rect: pygame.Rect, orientation: str = "vertical", total: int = 0, page: int = 1) -> None:
        self.rect = rect
        self.orientation = orientation
        self.total = max(0, total)
        self.page = max(1, page)
        self.value = 0
        self.dragging = False
        self.drag_offset = 0

    # {
    #   責務: [maximum: scroll・barのmaximumを求める]
    #   処理: [1: scroll・barのmaximumを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: scroll・barのmaximumを求めるための結果（int）]
    # }
    @property
    def maximum(self) -> int:
        return max(0, self.total - self.page)

    # {
    #   責務: [configure: scroll・barを設定する]
    #   処理: [1: scroll・barを設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     total: total（int）
    #     page: page（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def configure(self, total: int, page: int) -> None:
        self.total = max(0, int(total))
        self.page = max(1, int(page))
        self.value = max(0, min(self.maximum, int(self.value)))

    # {
    #   責務: [_axis: scroll・barのaxisを求める]
    #   処理: [1: scroll・barのaxisを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     position: 座標（tuple[int, int]）
    #   ]
    #   戻り値: [result: scroll・barのaxisを求めるための結果（int）]
    # }
    def _axis(self, position: tuple[int, int]) -> int:
        return position[1] if self.orientation == "vertical" else position[0]

    # {
    #   責務: [_track_start: scroll・barのtrack・startを求める]
    #   処理: [1: scroll・barのtrack・startを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: scroll・barのtrack・startを求めるための結果（int）]
    # }
    def _track_start(self) -> int:
        return self.rect.y if self.orientation == "vertical" else self.rect.x

    # {
    #   責務: [_track_length: scroll・barのtrack・lengthを求める]
    #   処理: [1: scroll・barのtrack・lengthを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: scroll・barのtrack・lengthを求めるための結果（int）]
    # }
    def _track_length(self) -> int:
        return self.rect.height if self.orientation == "vertical" else self.rect.width

    # {
    #   責務: [thumb_rect: scroll・barのthumb・表示矩形を求める]
    #   処理: [1: scroll・barのthumb・表示矩形を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: scroll・barのthumb・表示矩形を求めるための結果（pygame.Rect）]
    # }
    def thumb_rect(self) -> pygame.Rect:
        track_length = self._track_length()
        if self.total <= 0 or self.maximum <= 0:
            thumb_length = track_length
            offset = 0
        else:
            thumb_length = max(24, round(track_length * min(1.0, self.page / self.total)))
            travel = max(0, track_length - thumb_length)
            offset = round(travel * self.value / self.maximum)
        if self.orientation == "vertical":
            return pygame.Rect(self.rect.x, self.rect.y + offset, self.rect.width, thumb_length)
        return pygame.Rect(self.rect.x + offset, self.rect.y, thumb_length, self.rect.height)

    # {
    #   責務: [_set_from_axis: from・axisを設定する]
    #   処理: [1: from・axisを設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     axis: axis（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def _set_from_axis(self, axis: int) -> None:
        thumb = self.thumb_rect()
        thumb_length = thumb.height if self.orientation == "vertical" else thumb.width
        travel = self._track_length() - thumb_length
        if travel <= 0 or self.maximum <= 0:
            self.value = 0
            return
        offset = axis - self._track_start() - self.drag_offset
        self.value = round(max(0, min(travel, offset)) / travel * self.maximum)

    # {
    #   責務: [handle: scroll・barを入力を処理する]
    #   処理: [1: scroll・barを入力を処理する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     event: イベント（pygame.event.Event）
    #   ]
    #   戻り値: [result: scroll・barを入力を処理するための結果（bool）]
    # }
    def handle(self, event: pygame.event.Event) -> bool:
        if self.maximum <= 0:
            self.dragging = False
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            thumb = self.thumb_rect()
            axis = self._axis(event.pos)
            if thumb.collidepoint(event.pos):
                self.dragging = True
                self.drag_offset = axis - (thumb.y if self.orientation == "vertical" else thumb.x)
            else:
                thumb_length = thumb.height if self.orientation == "vertical" else thumb.width
                self.drag_offset = thumb_length // 2
                self._set_from_axis(axis)
                self.dragging = True
            return True
        if event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_axis(self._axis(event.pos))
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging:
            self.dragging = False
            return True
        return False

    # {
    #   責務: [draw: scroll・barを描画する]
    #   処理: [1: scroll・barを描画する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     surface: 描画面（pygame.Surface）
    #     mouse: mouse（tuple[int, int]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def draw(self, surface: pygame.Surface, mouse: tuple[int, int]) -> None:
        pygame.draw.rect(surface, INPUT_BG, self.rect, border_radius=6)
        thumb = self.thumb_rect()
        hovered = self.maximum > 0 and (thumb.collidepoint(mouse) or self.dragging)
        color = ACCENT if hovered else MUTED
        pygame.draw.rect(surface, color, thumb, border_radius=6)


# {
#   責務: [TextField: 文字列・フィールドの状態と振る舞いを担当する]
#   フィールド: [
#     rect: 表示矩形
#     value: 値
#     numeric: numeric
#     active: active
#   ]
# }
class TextField:
    # {
    #   責務: [__init__: 文字列・フィールドが利用する初期状態と依存を設定する]
    #   処理: [1: 文字列・フィールドが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     rect: 表示矩形（pygame.Rect）
    #     value: 値（str）
    #     numeric: numeric（bool）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, rect: pygame.Rect, value: str = "", numeric: bool = False) -> None:
        self.rect = rect
        self.value = str(value)
        self.numeric = numeric
        self.active = False

    # {
    #   責務: [draw: 文字列・フィールドを描画する]
    #   処理: [1: 文字列・フィールドを描画する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     surface: 描画面（pygame.Surface）
    #     label: 表示名（str）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def draw(self, surface: pygame.Surface, label: str = "") -> None:
        if label:
            draw_text(surface, label, (self.rect.x, self.rect.y - 24), 17, MUTED)
        pygame.draw.rect(surface, INPUT_BG, self.rect, border_radius=5)
        pygame.draw.rect(surface, ACCENT if self.active else PANEL_ALT, self.rect, 2, border_radius=5)
        clipped = self.value
        active_font = font(20)
        while clipped and active_font.size(clipped)[0] > self.rect.width - 12:
            clipped = clipped[1:]
        text_image = active_font.render(clipped, True, TEXT)
        surface.blit(text_image, (self.rect.x + 8, self.rect.y + 7))
        if self.active and pygame.time.get_ticks() % 1000 < 550:
            caret_x = min(self.rect.right - 7, self.rect.x + 9 + text_image.get_width())
            pygame.draw.line(surface, ACCENT, (caret_x, self.rect.y + 8), (caret_x, self.rect.bottom - 8), 2)

    # {
    #   責務: [handle: 文字列・フィールドを入力を処理する]
    #   処理: [1: 文字列・フィールドを入力を処理する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     event: イベント（pygame.event.Event）
    #   ]
    #   戻り値: [result: 文字列・フィールドを入力を処理するための結果（bool）]
    # }
    def handle(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
            return self.active
        if self.active and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.value = self.value[:-1]
            elif event.key in {pygame.K_RETURN, pygame.K_TAB}:
                self.active = False
            elif event.unicode and event.unicode.isprintable():
                if not self.numeric or event.unicode.isdigit() or (event.unicode == "-" and not self.value):
                    self.value += event.unicode
            return True
        return False


# {
#   責務: [handle_fields: Send an event to every field so a mouse click leaves only one field active.]
#   処理: [1: Send an event to every field so a mouse click leaves only one field active.]
#   引数: [
#     fields: 入力項目（list[TextField]）
#     event: イベント（pygame.event.Event）
#   ]
#   戻り値: [result: handled（bool）]
# }
def handle_fields(fields: list[TextField], event: pygame.event.Event) -> bool:
    """Send an event to every field so a mouse click leaves only one field active."""
    handled = False
    for field in fields:
        handled = field.handle(event) or handled
    return handled


# {
#   責務: [draw_status_bar: 状態異常・barを描画する]
#   処理: [1: 状態異常・barを描画する]
#   引数: [
#     surface: 描画面（pygame.Surface）
#     message: message（str）
#     rect: 表示矩形（pygame.Rect）
#     warning: warning（bool）
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def draw_status_bar(surface: pygame.Surface, message: str, rect: pygame.Rect, *, warning: bool = False) -> None:
    pygame.draw.rect(surface, PANEL_ALT, rect, border_radius=8)
    color = WARN if warning else ACCENT
    pygame.draw.rect(surface, color, pygame.Rect(rect.x, rect.y, 5, rect.height), border_radius=3)
    draw_wrapped(surface, message, rect.inflate(-24, -12), 16)


# {
#   責務: [smoke_frames: commonのsmoke・framesを求める]
#   処理: [1: commonのsmoke・framesを求める]
#   引数: []
#   戻り値: [result: commonのsmoke・framesを求めるための結果（int | None）]
# }
def smoke_frames() -> int | None:
    for index, arg in enumerate(os.sys.argv):
        if arg == "--smoke":
            if index + 1 < len(os.sys.argv) and os.sys.argv[index + 1].isdigit():
                return int(os.sys.argv[index + 1])
            return 3
    return None


