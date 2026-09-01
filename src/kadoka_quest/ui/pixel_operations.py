from __future__ import annotations

from collections import deque

import pygame


ColorTuple = tuple[int, int, int, int]


def rgba(color: pygame.Color | ColorTuple) -> ColorTuple:
    return int(color[0]), int(color[1]), int(color[2]), int(color[3])


def flood_fill_copy(
    source: pygame.Surface,
    start: tuple[int, int],
    replacement: ColorTuple,
) -> tuple[pygame.Surface, int]:
    """Replace one four-way-connected exact-color region and return a copy."""
    width, height = source.get_size()
    x, y = start
    if not (0 <= x < width and 0 <= y < height):
        return source.copy(), 0
    target = rgba(source.get_at(start))
    replacement = rgba(replacement)
    if target == replacement:
        return source.copy(), 0

    result = source.copy()
    pending = deque([start])
    visited = {start}
    changed = 0
    while pending:
        current_x, current_y = pending.popleft()
        if rgba(result.get_at((current_x, current_y))) != target:
            continue
        result.set_at((current_x, current_y), replacement)
        changed += 1
        for neighbour in (
            (current_x - 1, current_y),
            (current_x + 1, current_y),
            (current_x, current_y - 1),
            (current_x, current_y + 1),
        ):
            if (
                0 <= neighbour[0] < width
                and 0 <= neighbour[1] < height
                and neighbour not in visited
            ):
                visited.add(neighbour)
                pending.append(neighbour)
    return result, changed


def color_distance_squared(first: ColorTuple, second: ColorTuple) -> int:
    return sum((first[index] - second[index]) ** 2 for index in range(3))


def reduce_similar_colors(
    source: pygame.Surface,
    tolerance: int,
) -> tuple[pygame.Surface, int]:
    """Merge scan-order colors within an RGB distance while preserving alpha."""
    tolerance = max(0, min(255, int(tolerance)))
    maximum_distance = tolerance * tolerance
    result = source.copy()
    representatives: list[ColorTuple] = []
    mapping: dict[ColorTuple, ColorTuple] = {}
    changed = 0

    for y in range(source.get_height()):
        for x in range(source.get_width()):
            color = rgba(source.get_at((x, y)))
            if color[3] == 0:
                continue
            if color not in mapping:
                closest = min(
                    (
                        candidate
                        for candidate in representatives
                        if candidate[3] == color[3]
                        and color_distance_squared(candidate, color) <= maximum_distance
                    ),
                    key=lambda candidate: color_distance_squared(candidate, color),
                    default=color,
                )
                mapping[color] = closest
                if closest == color:
                    representatives.append(color)
            replacement = mapping[color]
            if replacement != color:
                result.set_at((x, y), replacement)
                changed += 1
    return result, changed


def fit_imported_image(source: pygame.Surface, size: int = 64) -> pygame.Surface:
    """Downscale with nearest neighbour into a transparent square canvas."""
    if source.get_width() <= 0 or source.get_height() <= 0:
        raise ValueError("画像サイズが不正です。")
    ratio = min(1.0, size / source.get_width(), size / source.get_height())
    scaled_size = (
        max(1, round(source.get_width() * ratio)),
        max(1, round(source.get_height() * ratio)),
    )
    scaled = pygame.transform.scale(source, scaled_size)
    canvas = pygame.Surface((size, size), pygame.SRCALPHA)
    canvas.blit(scaled, scaled.get_rect(center=(size // 2, size // 2)))
    return canvas
