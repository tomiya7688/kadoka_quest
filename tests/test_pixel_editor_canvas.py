from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import pygame

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_quest.ui.pixel_editor import CANVAS_SIZES, PixelArtEditor


class PixelEditorCanvasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.display.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1, 1))

    def test_block_canvas_supports_each_configured_square_size(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            assets = Path(temporary) / "assets"
            editor = PixelArtEditor(assets)
            editor.load_block("appearance/blocks/size_test.png", (20, 40, 60))

            self.assertEqual(editor.logical_size, 64)
            for size in CANVAS_SIZES:
                editor.resize_canvas(size)
                self.assertEqual(editor.logical_size, size)
                self.assertEqual(editor.images["appearance"].get_size(), (size, size))

    def test_block_canvas_save_and_reload_preserves_its_actual_size(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            assets = Path(temporary) / "assets"
            editor = PixelArtEditor(assets)
            editor.load_block("appearance/blocks/one_pixel.png", (80, 120, 160))
            editor.resize_canvas(1)
            editor.save_images()

            restored = PixelArtEditor(assets)
            restored.load_block("appearance/blocks/one_pixel.png")
            self.assertEqual(restored.logical_size, 1)
            self.assertEqual(restored.images["appearance"].get_size(), (1, 1))

    def test_block_canvas_rejects_sizes_outside_the_documented_choices(self) -> None:
        editor = PixelArtEditor(Path("assets"))
        editor.load_block("appearance/blocks/invalid_size.png")

        with self.assertRaises(ValueError):
            editor.resize_canvas(3)
