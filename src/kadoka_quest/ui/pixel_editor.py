from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pygame


@dataclass(frozen=True)
class PixelTarget:
    key: str
    label: str
    path: str
    size: int = 64


MONSTER_VISUAL_SLOTS = (
    ("portrait", "戦闘立ち絵", 64),
    ("front", "正面", 64),
    ("right", "右向き", 64),
    ("left", "左向き", 64),
    ("back", "後ろ", 64),
)
VISUAL_SLOTS = MONSTER_VISUAL_SLOTS

PALETTE = (
    (0, 0, 0, 0), (0, 0, 0, 255), (255, 255, 255, 255),
    (214, 214, 214, 255), (156, 156, 156, 255), (85, 85, 85, 255),
    (255, 110, 110, 255), (255, 205, 90, 255), (100, 210, 255, 255),
    (120, 220, 140, 255),
)
ZOOM_LEVELS = (0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0)
TOOL_MODES = ("pen", "pan")
UNDO_LIMIT = 50


class PixelArtEditor:
    """Shared pixel editor; callers supply only the image targets and metadata."""

    def __init__(self, asset_root: Path, targets: Iterable[PixelTarget] = ()) -> None:
        self.asset_root = asset_root
        self.targets: dict[str, PixelTarget] = {}
        self.selected = ""
        self.brush = PALETTE[1]
        self.images: dict[str, pygame.Surface] = {}
        self.paths: dict[str, str] = {}
        self.dirty: set[str] = set()
        self.zoom_index = ZOOM_LEVELS.index(1.0)
        self.tool_mode = "pen"
        self.pan_offset = pygame.Vector2()
        self._pan_last: tuple[int, int] | None = None
        self.undo_stacks: dict[str, list[pygame.Surface]] = {}
        self._stroke_active = False
        self._stroke_slot = ""
        self._stroke_changed = False
        self.set_targets(targets)

    @property
    def zoom(self) -> float:
        return ZOOM_LEVELS[self.zoom_index]

    @property
    def zoom_percent(self) -> int:
        return round(self.zoom * 100)

    @property
    def logical_size(self) -> int:
        return self.images[self.selected].get_width() if self.selected else 64

    def set_targets(self, targets: Iterable[PixelTarget]) -> None:
        values = list(targets)
        self.targets = {target.key: target for target in values}
        self.paths = {target.key: target.path for target in values}
        self.selected = values[0].key if values else ""
        self.images.clear()
        self.dirty.clear()
        self.undo_stacks = {target.key: [] for target in values}
        self.end_stroke()
        self.end_pan()
        self.reset_zoom()

    def load_targets(
        self,
        targets: Iterable[PixelTarget],
        body_color: tuple[int, int, int] = (128, 128, 128),
        selected: str | None = None,
    ) -> None:
        self.set_targets(targets)
        for target in self.targets.values():
            path = self.asset_root / target.path
            try:
                source = pygame.image.load(str(path)).convert_alpha()
                self.images[target.key] = self._fit(source, target.size)
            except (OSError, pygame.error, ValueError):
                self.images[target.key] = self._placeholder(target.size, target.key, body_color)
        if selected in self.images:
            self.selected = str(selected)

    def load_species(self, definition: dict, species_id: str) -> None:
        old_field = str(definition.get("field_sprite_path", ""))
        field_paths = dict(definition.get("field_sprites", {}))
        paths = {
            "portrait": str(definition.get("portrait_path", f"characters/{species_id}/portrait.png")),
            **{
                direction: str(field_paths.get(direction) or old_field or f"characters/{species_id}/field_{direction}.png")
                for direction in ("front", "right", "left", "back")
            },
        }
        color_value = str(definition.get("appearance", {}).get("value", "#808080")).lstrip("#")
        try:
            body_color = tuple(int(color_value[index:index + 2], 16) for index in (0, 2, 4))
        except ValueError:
            body_color = (128, 128, 128)
        targets = (PixelTarget(slot, label, paths[slot], 64) for slot, label, _ in MONSTER_VISUAL_SLOTS)
        self.load_targets(targets, body_color, selected="front")

    def load_block(self, relative_path: str, body_color: tuple[int, int, int] = (128, 128, 128)) -> None:
        self.load_targets((PixelTarget("appearance", "ブロック見た目", relative_path, 64),), body_color)

    @staticmethod
    def _fit(source: pygame.Surface, size: int) -> pygame.Surface:
        canvas = pygame.Surface((size, size), pygame.SRCALPHA)
        ratio = min(size / source.get_width(), size / source.get_height())
        scaled_size = (max(1, round(source.get_width() * ratio)), max(1, round(source.get_height() * ratio)))
        scaled = pygame.transform.scale(source, scaled_size)
        canvas.blit(scaled, scaled.get_rect(center=(size // 2, size // 2)))
        return canvas

    @staticmethod
    def _placeholder(size: int, slot: str, body_color: tuple[int, int, int]) -> pygame.Surface:
        image = pygame.Surface((size, size), pygame.SRCALPHA)
        if slot == "appearance":
            image.fill(body_color)
            return image
        pygame.draw.ellipse(image, body_color, pygame.Rect(size // 6, size // 7, size * 2 // 3, size * 3 // 4))
        if slot != "back":
            eyes = (((size * 2 // 3, size * 2 // 5),) if slot == "right" else
                    ((size // 3, size * 2 // 5),) if slot == "left" else
                    ((size * 2 // 5, size * 2 // 5), (size * 3 // 5, size * 2 // 5)))
            for center in eyes:
                pygame.draw.circle(image, (0, 0, 0), center, max(1, size // 16))
        return image

    def select(self, slot: str) -> None:
        if slot in self.images:
            self.end_stroke()
            self.end_pan()
            self.selected = slot
            self.reset_zoom()

    def set_tool_mode(self, mode: str) -> bool:
        if mode not in TOOL_MODES:
            return False
        self.end_stroke()
        self.end_pan()
        self.tool_mode = mode
        return True

    def zoom_in(self) -> bool:
        old = self.zoom_index
        self.zoom_index = min(len(ZOOM_LEVELS) - 1, self.zoom_index + 1)
        return self.zoom_index != old

    def zoom_out(self) -> bool:
        old = self.zoom_index
        self.zoom_index = max(0, self.zoom_index - 1)
        return self.zoom_index != old

    def reset_zoom(self) -> None:
        self.zoom_index = ZOOM_LEVELS.index(1.0)
        self.pan_offset.update(0, 0)

    def _clamp_pan(self, canvas: pygame.Rect, side: int) -> None:
        maximum_x = max(0, (side - canvas.width) / 2)
        maximum_y = max(0, (side - canvas.height) / 2)
        self.pan_offset.x = max(-maximum_x, min(maximum_x, self.pan_offset.x))
        self.pan_offset.y = max(-maximum_y, min(maximum_y, self.pan_offset.y))

    def image_rect(self, canvas: pygame.Rect) -> pygame.Rect:
        side = max(1, round(min(canvas.width, canvas.height) * self.zoom))
        self._clamp_pan(canvas, side)
        return pygame.Rect(
            canvas.centerx - side // 2 + round(self.pan_offset.x),
            canvas.centery - side // 2 + round(self.pan_offset.y),
            side,
            side,
        )

    def begin_pan(self, position: tuple[int, int], canvas: pygame.Rect) -> bool:
        if self.tool_mode != "pan" or not canvas.collidepoint(position):
            return False
        self.end_stroke()
        self._pan_last = position
        return True

    def pan_to(self, position: tuple[int, int], canvas: pygame.Rect) -> bool:
        if self.tool_mode != "pan" or self._pan_last is None:
            return False
        dx = position[0] - self._pan_last[0]
        dy = position[1] - self._pan_last[1]
        self._pan_last = position
        self.pan_offset.update(self.pan_offset.x + dx, self.pan_offset.y + dy)
        self.image_rect(canvas)
        return bool(dx or dy)

    def end_pan(self) -> None:
        self._pan_last = None

    def begin_stroke(self) -> bool:
        if self.tool_mode != "pen" or not self.selected or self._stroke_active:
            return False
        stack = self.undo_stacks.setdefault(self.selected, [])
        stack.append(self.images[self.selected].copy())
        if len(stack) > UNDO_LIMIT:
            del stack[0]
        self._stroke_active = True
        self._stroke_slot = self.selected
        self._stroke_changed = False
        return True

    def end_stroke(self) -> None:
        if self._stroke_active and not self._stroke_changed:
            stack = self.undo_stacks.get(self._stroke_slot, [])
            if stack:
                stack.pop()
        self._stroke_active = False
        self._stroke_slot = ""
        self._stroke_changed = False

    def undo(self) -> bool:
        self.end_stroke()
        if not self.selected:
            return False
        stack = self.undo_stacks.setdefault(self.selected, [])
        if not stack:
            return False
        self.images[self.selected] = stack.pop()
        self.dirty.add(self.selected)
        return True

    @staticmethod
    def draw_checker(surface: pygame.Surface, rect: pygame.Rect, cell: int = 8) -> None:
        for y in range(rect.y, rect.bottom, cell):
            for x in range(rect.x, rect.right, cell):
                color = (205, 205, 205) if ((x - rect.x) // cell + (y - rect.y) // cell) % 2 == 0 else (150, 150, 150)
                pygame.draw.rect(surface, color, pygame.Rect(x, y, min(cell, rect.right - x), min(cell, rect.bottom - y)))

    def draw_canvas(self, surface: pygame.Surface, canvas: pygame.Rect) -> None:
        pygame.draw.rect(surface, (38, 45, 55), canvas.inflate(20, 20), border_radius=8)
        self.draw_checker(surface, canvas, 12)
        if not self.selected:
            return
        image = self.images[self.selected]
        size = image.get_width()
        image_rect = self.image_rect(canvas)
        cell = image_rect.width / size
        old_clip = surface.get_clip()
        surface.set_clip(canvas)
        for y in range(size):
            for x in range(size):
                color = image.get_at((x, y))
                if color.a:
                    left = round(image_rect.x + x * cell)
                    top = round(image_rect.y + y * cell)
                    right = round(image_rect.x + (x + 1) * cell)
                    bottom = round(image_rect.y + (y + 1) * cell)
                    pygame.draw.rect(surface, color, pygame.Rect(left, top, max(1, right - left), max(1, bottom - top)))
        if cell >= 4:
            grid_color = (72, 78, 88)
            for index in range(size + 1):
                x = round(image_rect.x + index * cell)
                y = round(image_rect.y + index * cell)
                pygame.draw.line(surface, grid_color, (x, image_rect.y), (x, image_rect.bottom), 1)
                pygame.draw.line(surface, grid_color, (image_rect.x, y), (image_rect.right, y), 1)
        surface.set_clip(old_clip)

    def paint(self, position: tuple[int, int], canvas: pygame.Rect, erase: bool = False) -> bool:
        if self.tool_mode != "pen" or not canvas.collidepoint(position) or not self.selected:
            return False
        image_rect = self.image_rect(canvas)
        if not image_rect.collidepoint(position):
            return False
        size = self.logical_size
        x = int((position[0] - image_rect.x) * size / image_rect.width)
        y = int((position[1] - image_rect.y) * size / image_rect.height)
        if not (0 <= x < size and 0 <= y < size):
            return False
        automatic_stroke = not self._stroke_active
        if automatic_stroke:
            self.begin_stroke()
        color = (0, 0, 0, 0) if erase else self.brush
        if self.images[self.selected].get_at((x, y)) == color:
            if automatic_stroke:
                self.end_stroke()
            return False
        self.images[self.selected].set_at((x, y), color)
        self.dirty.add(self.selected)
        self._stroke_changed = True
        if automatic_stroke:
            self.end_stroke()
        return True

    def save_images(self) -> None:
        for key in tuple(self.dirty):
            path = self.asset_root / self.paths[key]
            path.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(self.images[key], str(path))
        self.dirty.clear()

    def save_all(self, definition: dict) -> None:
        self.save_images()
        definition["portrait_path"] = self.paths["portrait"]
        definition["field_sprite_path"] = self.paths["front"]
        definition["field_sprites"] = {direction: self.paths[direction] for direction in ("front", "right", "left", "back")}
