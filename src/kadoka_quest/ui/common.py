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


def init_pygame(title: str, size: tuple[int, int]) -> pygame.Surface:
    pygame.init()
    pygame.display.set_caption(title)
    return pygame.display.set_mode(size)


def font(size: int, bold: bool = False) -> pygame.font.Font:
    names = ["Yu Gothic UI", "Meiryo", "Noto Sans CJK JP", "Arial"]
    return pygame.font.SysFont(names, size, bold=bold)


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


@dataclass
class Button:
    rect: pygame.Rect
    label: str
    action: Callable[[], None]
    enabled: bool = True

    def draw(self, surface: pygame.Surface, mouse: tuple[int, int]) -> None:
        hovered = self.enabled and self.rect.collidepoint(mouse)
        color = (64, 112, 148) if hovered else (47, 74, 99)
        if not self.enabled:
            color = (48, 52, 60)
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, ACCENT if hovered else PANEL_ALT, self.rect, 2, border_radius=8)
        image = font(20, True).render(self.label, True, TEXT if self.enabled else MUTED)
        surface.blit(image, image.get_rect(center=self.rect.center))

    def handle(self, event: pygame.event.Event) -> bool:
        if self.enabled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.action()
            return True
        return False


class TextField:
    def __init__(self, rect: pygame.Rect, value: str = "", numeric: bool = False) -> None:
        self.rect = rect
        self.value = str(value)
        self.numeric = numeric
        self.active = False

    def draw(self, surface: pygame.Surface, label: str = "") -> None:
        if label:
            draw_text(surface, label, (self.rect.x, self.rect.y - 24), 17, MUTED)
        pygame.draw.rect(surface, (24, 32, 44), self.rect, border_radius=5)
        pygame.draw.rect(surface, ACCENT if self.active else PANEL_ALT, self.rect, 2, border_radius=5)
        clipped = self.value
        active_font = font(20)
        while clipped and active_font.size(clipped)[0] > self.rect.width - 12:
            clipped = clipped[1:]
        surface.blit(active_font.render(clipped, True, TEXT), (self.rect.x + 6, self.rect.y + 7))

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


def smoke_frames() -> int | None:
    for index, arg in enumerate(os.sys.argv):
        if arg == "--smoke":
            if index + 1 < len(os.sys.argv) and os.sys.argv[index + 1].isdigit():
                return int(os.sys.argv[index + 1])
            return 3
    return None


