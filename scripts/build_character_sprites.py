"""Build the bundled <=64 px monster sprites from generated source sheets.

The source sheets are deliberately kept outside the distributed project.  This
script turns each five-view sheet into openly editable PNG files and preserves
the supplied Maru/Kadoka portraits as their battle artwork.
"""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path
import shutil

import pygame


ROOT = Path(__file__).resolve().parents[1]
CHARACTERS = ROOT / "assets" / "characters"
DIRECTIONS = ("front", "right", "left", "back")
SHEETS = {
    "slime": "slime.png",
    "ball_slime": "ball_slime.png",
    "metal_slime": "metal_slime.png",
    "ghost": "ghost.png",
    "dice_slime": "dice_slime.png",
    "hero": "hero.png",
    "maru": "maru.png",
}


def remove_connected_light_background(surface: pygame.Surface) -> pygame.Surface:
    """Remove the opaque pale checkerboard sometimes emitted behind Maru."""
    result = surface.convert_alpha()
    width, height = result.get_size()
    queue: deque[tuple[int, int]] = deque()
    seen: set[tuple[int, int]] = set()
    for x in range(width):
        queue.extend(((x, 0), (x, height - 1)))
    for y in range(height):
        queue.extend(((0, y), (width - 1, y)))
    while queue:
        x, y = queue.popleft()
        if (x, y) in seen:
            continue
        seen.add((x, y))
        color = result.get_at((x, y))
        if min(color.r, color.g, color.b) < 225 or max(color.r, color.g, color.b) - min(color.r, color.g, color.b) > 18:
            continue
        result.set_at((x, y), (color.r, color.g, color.b, 0))
        if x:
            queue.append((x - 1, y))
        if x + 1 < width:
            queue.append((x + 1, y))
        if y:
            queue.append((x, y - 1))
        if y + 1 < height:
            queue.append((x, y + 1))
    return result


def fit_to_canvas(source: pygame.Surface, canvas_size: int = 64, content_size: int = 60) -> pygame.Surface:
    source = source.convert_alpha()
    bounds = source.get_bounding_rect(min_alpha=8)
    if bounds.width and bounds.height:
        source = source.subsurface(bounds).copy()
    ratio = min(content_size / source.get_width(), content_size / source.get_height())
    size = (max(1, round(source.get_width() * ratio)), max(1, round(source.get_height() * ratio)))
    scaled = pygame.transform.scale(source, size)
    canvas = pygame.Surface((canvas_size, canvas_size), pygame.SRCALPHA)
    canvas.blit(scaled, scaled.get_rect(center=(canvas_size // 2, canvas_size // 2)))
    return canvas


def split_sheet(species_id: str, sheet_path: Path) -> None:
    sheet = pygame.image.load(str(sheet_path))
    if species_id == "maru" and not (sheet.get_flags() & pygame.SRCALPHA):
        sheet = remove_connected_light_background(sheet)
    destination = CHARACTERS / species_id
    destination.mkdir(parents=True, exist_ok=True)
    width, height = sheet.get_size()
    names = ("portrait", "field_front", "field_right", "field_left", "field_back")
    for index, name in enumerate(names):
        left = round(index * width / 5)
        right = round((index + 1) * width / 5)
        view = sheet.subsurface((left, 0, right - left, height)).copy()
        pygame.image.save(fit_to_canvas(view), str(destination / f"{name}.png"))
    shutil.copyfile(destination / "field_front.png", destination / "field.png")


def preserve_portrait(source_path: Path, species_id: str) -> None:
    source = pygame.image.load(str(source_path)).convert_alpha()
    # Keep the complete supplied composition; nearest-neighbour resizing retains
    # its square pixel character and does not redraw the face or silhouette.
    portrait = pygame.transform.scale(source, (64, 64))
    pygame.image.save(portrait, str(CHARACTERS / species_id / "portrait.png"))


def resize_existing_kadoka_fields() -> None:
    destination = CHARACTERS / "kadoka"
    loaded = {
        direction: pygame.image.load(str(destination / f"field_{direction}.png")).convert_alpha()
        for direction in DIRECTIONS
    }
    for direction, source in loaded.items():
        pygame.image.save(fit_to_canvas(source), str(destination / f"field_{direction}.png"))
    shutil.copyfile(destination / "field_front.png", destination / "field.png")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("sheet_root", type=Path, help="Folder containing the named five-view sheets")
    parser.add_argument("--maru-portrait", type=Path, required=True)
    parser.add_argument("--kadoka-portrait", type=Path, required=True)
    args = parser.parse_args()
    pygame.init()
    pygame.display.set_mode((1, 1))
    for species_id, filename in SHEETS.items():
        split_sheet(species_id, args.sheet_root / filename)
    preserve_portrait(args.maru_portrait, "maru")
    resize_existing_kadoka_fields()
    preserve_portrait(args.kadoka_portrait, "kadoka")
    pygame.quit()


if __name__ == "__main__":
    main()

