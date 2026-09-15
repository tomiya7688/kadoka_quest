from __future__ import annotations

from collections import Counter, deque
from collections.abc import Iterable

import pygame


ColorTuple = tuple[int, int, int, int]

TRANSPARENT: ColorTuple = (0, 0, 0, 0)
KADOKA_OPAQUE_PALETTE: tuple[ColorTuple, ...] = (
    (0, 0, 0, 255),
    (255, 255, 255, 255),
    (214, 214, 214, 255),
    (230, 80, 80, 255),
    (70, 120, 220, 255),
    (155, 100, 210, 255),
    (90, 185, 105, 255),
    (240, 205, 80, 255),
    (100, 210, 255, 255),
    (235, 130, 185, 255),
    (145, 95, 60, 255),
)
KADOKA_PALETTE: tuple[ColorTuple, ...] = (TRANSPARENT, *KADOKA_OPAQUE_PALETTE)


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


def nearest_palette_color(color: ColorTuple, palette: Iterable[ColorTuple]) -> ColorTuple:
    candidates = tuple(palette)
    if not candidates:
        raise ValueError("palette must contain at least one color")
    return min(candidates, key=lambda candidate: color_distance_squared(color, candidate))


def opaque_color_count(source: pygame.Surface) -> int:
    return len(
        {
            rgba(source.get_at((x, y)))[:3]
            for y in range(source.get_height())
            for x in range(source.get_width())
            if source.get_at((x, y)).a > 0
        }
    )


def _palette_usage(source: pygame.Surface) -> Counter[ColorTuple]:
    usage: Counter[ColorTuple] = Counter()
    for y in range(source.get_height()):
        for x in range(source.get_width()):
            color = rgba(source.get_at((x, y)))
            if color[3] == 0:
                continue
            usage[nearest_palette_color(color, KADOKA_OPAQUE_PALETTE)] += 1
    return usage


def select_kadoka_palette(source: pygame.Surface, max_colors: int) -> tuple[ColorTuple, ...]:
    """Select a compact basic-palette subset while retaining contrasting details."""
    limit = max(1, min(len(KADOKA_OPAQUE_PALETTE), int(max_colors)))
    usage = _palette_usage(source)
    if not usage:
        return ()
    candidates = [color for color in KADOKA_OPAQUE_PALETTE if color in usage]
    if len(candidates) <= limit:
        return tuple(candidates)

    palette_order = {color: index for index, color in enumerate(KADOKA_OPAQUE_PALETTE)}
    first = max(candidates, key=lambda color: (usage[color], -palette_order[color]))
    selected = [first]
    while len(selected) < limit:
        remaining = [color for color in candidates if color not in selected]
        if not remaining:
            break
        chosen = max(
            remaining,
            key=lambda color: (
                usage[color]
                * (1 + min(color_distance_squared(color, existing) for existing in selected)),
                usage[color],
                -palette_order[color],
            ),
        )
        selected.append(chosen)
    return tuple(selected)


def reduce_to_kadoka_palette(
    source: pygame.Surface,
    max_colors: int = 5,
) -> tuple[pygame.Surface, int, tuple[ColorTuple, ...]]:
    """Map opaque pixels to at most ``max_colors`` Kadoka Quest basic colors.

    Fully transparent pixels stay transparent. Any visible source pixel becomes
    fully opaque so antialiasing does not create extra color/alpha information.
    """
    selected = select_kadoka_palette(source, max_colors)
    result = source.copy()
    changed = 0
    for y in range(source.get_height()):
        for x in range(source.get_width()):
            original = rgba(source.get_at((x, y)))
            if original[3] == 0:
                replacement = TRANSPARENT
            elif selected:
                replacement = nearest_palette_color(original, selected)
            else:
                replacement = TRANSPARENT
            if replacement != original:
                result.set_at((x, y), replacement)
                changed += 1
    return result, changed, selected


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
