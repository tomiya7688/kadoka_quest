from __future__ import annotations

from pathlib import Path

import pygame


VISUAL_SLOTS = (
    ("portrait", "戦闘立ち絵", 64),
    ("front", "正面", 48),
    ("right", "右向き", 48),
    ("left", "左向き", 48),
    ("back", "後ろ", 48),
)

PALETTE = (
    (0, 0, 0, 0),
    (0, 0, 0, 255),
    (255, 255, 255, 255),
    (214, 214, 214, 255),
    (156, 156, 156, 255),
    (85, 85, 85, 255),
    (255, 110, 110, 255),
    (255, 205, 90, 255),
    (100, 210, 255, 255),
    (120, 220, 140, 255),
)


class PixelArtEditor:
    """Small, dependency-free pixel editor for species portrait/directional art."""

    def __init__(self, asset_root: Path) -> None:
        self.asset_root = asset_root
        self.selected = "front"
        self.brush = PALETTE[1]
        self.images: dict[str, pygame.Surface] = {}
        self.paths: dict[str, str] = {}
        self.dirty: set[str] = set()

    @property
    def logical_size(self) -> int:
        return next(size for slot, _, size in VISUAL_SLOTS if slot == self.selected)

    def load_species(self, definition: dict, species_id: str) -> None:
        old_field = str(definition.get("field_sprite_path", ""))
        field_paths = dict(definition.get("field_sprites", {}))
        defaults = {
            "portrait": str(definition.get("portrait_path", f"characters/{species_id}/portrait.png")),
            **{
                direction: str(field_paths.get(direction) or old_field or f"characters/{species_id}/field_{direction}.png")
                for direction in ("front", "right", "left", "back")
            },
        }
        self.paths = defaults
        self.images = {}
        self.dirty.clear()
        color_value = str(definition.get("appearance", {}).get("value", "#808080")).lstrip("#")
        try:
            body_color = tuple(int(color_value[index:index + 2], 16) for index in (0, 2, 4))
        except ValueError:
            body_color = (128, 128, 128)
        for slot, _, size in VISUAL_SLOTS:
            path = self.asset_root / defaults[slot]
            try:
                source = pygame.image.load(str(path)).convert_alpha()
                if slot != "portrait":
                    bounds = source.get_bounding_rect(min_alpha=8)
                    if bounds.width and bounds.height:
                        source = source.subsurface(bounds).copy()
                self.images[slot] = self._fit(source, size)
            except (OSError, pygame.error, ValueError):
                self.images[slot] = self._placeholder(size, slot, body_color)
        self.selected = "front"

    @staticmethod
    def _fit(source: pygame.Surface, size: int) -> pygame.Surface:
        canvas = pygame.Surface((size, size), pygame.SRCALPHA)
        limit = size if source.get_width() == source.get_height() else size - 2
        ratio = min(limit / source.get_width(), limit / source.get_height())
        scaled_size = (max(1, round(source.get_width() * ratio)), max(1, round(source.get_height() * ratio)))
        scaled = pygame.transform.scale(source, scaled_size)
        canvas.blit(scaled, scaled.get_rect(center=(size // 2, size // 2)))
        return canvas

    @staticmethod
    def _placeholder(size: int, slot: str, body_color: tuple[int, int, int]) -> pygame.Surface:
        image = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.ellipse(image, body_color, pygame.Rect(size // 6, size // 7, size * 2 // 3, size * 3 // 4))
        if slot != "back":
            if slot == "right":
                eyes = ((size * 2 // 3, size * 2 // 5),)
            elif slot == "left":
                eyes = ((size // 3, size * 2 // 5),)
            else:
                eyes = ((size * 2 // 5, size * 2 // 5), (size * 3 // 5, size * 2 // 5))
            for center in eyes:
                pygame.draw.circle(image, (0, 0, 0), center, max(1, size // 16))
        return image

    def select(self, slot: str) -> None:
        if slot in self.images:
            self.selected = slot

    def paint(self, position: tuple[int, int], canvas: pygame.Rect, erase: bool = False) -> bool:
        if not canvas.collidepoint(position):
            return False
        size = self.logical_size
        x = min(size - 1, max(0, (position[0] - canvas.x) * size // canvas.width))
        y = min(size - 1, max(0, (position[1] - canvas.y) * size // canvas.height))
        self.images[self.selected].set_at((x, y), (0, 0, 0, 0) if erase else self.brush)
        self.dirty.add(self.selected)
        return True

    def save_all(self, definition: dict) -> None:
        for slot, _, _ in VISUAL_SLOTS:
            if slot not in self.dirty:
                continue
            relative = self.paths[slot]
            path = self.asset_root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(self.images[slot], str(path))
        definition["portrait_path"] = self.paths["portrait"]
        definition["field_sprite_path"] = self.paths["front"]
        definition["field_sprites"] = {direction: self.paths[direction] for direction in ("front", "right", "left", "back")}
        self.dirty.clear()

