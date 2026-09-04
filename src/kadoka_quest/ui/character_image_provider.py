from __future__ import annotations

from pathlib import Path
from typing import Any

import pygame


class CharacterImageProvider:
    """Loads, crops, nearest-neighbour scales, and caches character PNGs."""

    def __init__(self, repository: Any, asset_root: Path) -> None:
        self.repository = repository
        self.asset_root = Path(asset_root)
        self.cache: dict[tuple[str, str, int, int], pygame.Surface | None] = {}

    def get(self, species_id: str, kind: str, size: tuple[int, int]) -> pygame.Surface | None:
        normalized_size = (int(size[0]), int(size[1]))
        key = (str(species_id), str(kind), *normalized_size)
        if key not in self.cache:
            self.cache[key] = self._load(str(species_id), str(kind), normalized_size)
        return self.cache[key]

    def clear(self) -> None:
        self.cache.clear()

    def _load(self, species_id: str, kind: str, size: tuple[int, int]) -> pygame.Surface | None:
        relative = self._relative_path(species_id, kind)
        if not relative:
            return None
        try:
            source = pygame.image.load(str(self.asset_root / relative)).convert_alpha()
            if kind.startswith("field"):
                source = self._crop_transparent_margin(source)
            return self._nearest_scale(source, size)
        except (OSError, pygame.error, ValueError, ZeroDivisionError):
            return None

    def _relative_path(self, species_id: str, kind: str) -> str | None:
        definition = self.repository.get_species(species_id).definition
        if kind.startswith("field"):
            direction = kind.removeprefix("field_") if kind != "field" else "front"
            value = definition.get("field_sprites", {}).get(direction) or definition.get("field_sprite_path")
        else:
            value = definition.get("portrait_path")
        return str(value) if value else None

    @staticmethod
    def _crop_transparent_margin(source: pygame.Surface) -> pygame.Surface:
        bounds = source.get_bounding_rect(min_alpha=8)
        if not bounds.width or not bounds.height:
            return source
        return source.subsurface(bounds).copy()

    @staticmethod
    def _nearest_scale(source: pygame.Surface, size: tuple[int, int]) -> pygame.Surface:
        if size[0] <= 0 or size[1] <= 0:
            raise ValueError("画像の表示サイズは1以上である必要があります。")
        ratio = min(size[0] / source.get_width(), size[1] / source.get_height())
        scaled_size = (
            max(1, round(source.get_width() * ratio)),
            max(1, round(source.get_height() * ratio)),
        )
        return pygame.transform.scale(source, scaled_size)
