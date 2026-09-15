from __future__ import annotations

from pathlib import Path
import os
import sys
import tempfile
import unittest


os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pygame

from kadoka_quest.ui.pixel_editor import PixelArtEditor, PixelTarget
from kadoka_quest.ui.pixel_operations import (
    KADOKA_OPAQUE_PALETTE,
    fit_imported_image,
    opaque_color_count,
    reduce_to_kadoka_palette,
)


class KadokaPaletteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    @staticmethod
    def make_multicolor_surface(size: tuple[int, int] = (128, 96)) -> pygame.Surface:
        surface = pygame.Surface(size, pygame.SRCALPHA)
        colors = (
            (12, 12, 15, 255),
            (245, 245, 240, 255),
            (210, 75, 70, 255),
            (60, 125, 225, 255),
            (145, 95, 205, 255),
            (85, 190, 110, 255),
            (245, 210, 75, 255),
            (100, 205, 245, 255),
        )
        stripe = max(1, size[0] // len(colors))
        for index, color in enumerate(colors):
            pygame.draw.rect(surface, color, pygame.Rect(index * stripe, 0, stripe, size[1]))
        pygame.draw.rect(surface, (0, 0, 0, 0), pygame.Rect(0, 0, size[0] // 8, size[1] // 8))
        return surface

    def test_high_resolution_import_fits_64_canvas_without_losing_transparency(self) -> None:
        source = self.make_multicolor_surface()

        fitted = fit_imported_image(source, 64)

        self.assertEqual(fitted.get_size(), (64, 64))
        self.assertEqual(fitted.get_at((0, 8)).a, 0)

    def test_palette_reduction_uses_only_basic_colors_and_requested_limit(self) -> None:
        source = fit_imported_image(self.make_multicolor_surface(), 64)

        reduced, changed, selected = reduce_to_kadoka_palette(source, 4)

        self.assertGreater(changed, 0)
        self.assertLessEqual(len(selected), 4)
        self.assertLessEqual(opaque_color_count(reduced), 4)
        allowed = {tuple(color[:3]) for color in KADOKA_OPAQUE_PALETTE}
        used = {
            tuple(reduced.get_at((x, y))[:3])
            for y in range(reduced.get_height())
            for x in range(reduced.get_width())
            if reduced.get_at((x, y)).a > 0
        }
        self.assertTrue(used <= allowed)
        self.assertEqual(reduced.get_at((0, 8)).a, 0)

    def test_shared_editor_import_defaults_to_five_colors_and_can_reduce_to_three(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset_root = root / "assets"
            asset_root.mkdir()
            source_path = root / "input.png"
            pygame.image.save(self.make_multicolor_surface(), str(source_path))

            editor = PixelArtEditor(
                asset_root,
                (PixelTarget("portrait", "戦闘立ち絵", "characters/test/portrait.png", 64),),
            )
            editor.images["portrait"] = pygame.Surface((64, 64), pygame.SRCALPHA)

            editor.import_image(str(source_path), tolerance=24)
            self.assertLessEqual(editor.visible_color_count(), 5)
            self.assertEqual(editor.images["portrait"].get_size(), (64, 64))

            changed, count = editor.reduce_to_kadoka_colors(3)
            self.assertGreaterEqual(changed, 0)
            self.assertLessEqual(count, 3)

            editor.save_images()
            saved = pygame.image.load(str(asset_root / "characters/test/portrait.png"))
            self.assertEqual(saved.get_size(), (64, 64))
            self.assertLessEqual(opaque_color_count(saved), 3)


if __name__ == "__main__":
    unittest.main()
