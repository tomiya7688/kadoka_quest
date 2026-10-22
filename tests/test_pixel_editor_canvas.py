# {
#   責務: [test_pixel_editor_canvas: test・ピクセル・editor・キャンバスの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import pygame

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_quest.ui.pixel_editor import CANVAS_SIZES, PixelArtEditor


# {
#   責務: [PixelEditorCanvasTests: ピクセル・editor・キャンバス・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class PixelEditorCanvasTests(unittest.TestCase):
    # {
    #   責務: [setUpClass: 検証に必要な専用fixtureと依存を準備する]
    #   処理: [1: 検証に必要な専用fixtureと依存を準備する]
    #   引数: [cls: 対象クラス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @classmethod
    def setUpClass(cls) -> None:
        pygame.display.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1, 1))

    # {
    #   責務: [test_block_canvas_supports_each_configured_square_size: 検証: block canvas supports each configured square size]
    #   処理: [1: 検証: block canvas supports each configured square size]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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

    # {
    #   責務: [test_block_canvas_save_and_reload_preserves_its_actual_size: 検証: block canvas save and reload preserves its actual size]
    #   処理: [1: 検証: block canvas save and reload preserves its actual size]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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

    # {
    #   責務: [test_block_canvas_rejects_sizes_outside_the_documented_choices: 検証: block canvas rejects sizes outside the documented choices]
    #   処理: [1: 検証: block canvas rejects sizes outside the documented choices]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_block_canvas_rejects_sizes_outside_the_documented_choices(self) -> None:
        editor = PixelArtEditor(Path("assets"))
        editor.load_block("appearance/blocks/invalid_size.png")

        with self.assertRaises(ValueError):
            editor.resize_canvas(3)

    # {
    #   責務: [test_resize_undo_restores_pixels_size_and_target: 検証: resize undo restores pixels size and target]
    #   処理: [1: 検証: resize undo restores pixels size and target]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_resize_undo_restores_pixels_size_and_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            editor = PixelArtEditor(Path(temporary))
            editor.load_block("tile.png")
            editor.images["appearance"].set_at((0, 0), (17, 42, 90, 0))
            before = pygame.image.tobytes(editor.images["appearance"], "RGBA")
            self.assertTrue(editor.resize_canvas(128))
            self.assertEqual(editor.images["appearance"].get_at((1, 1)), (17, 42, 90, 0))
            self.assertFalse(editor.resize_canvas(128))
            self.assertTrue(editor.undo())
            self.assertEqual(editor.targets["appearance"].size, 64)
            self.assertEqual(pygame.image.tobytes(editor.images["appearance"], "RGBA"), before)
            self.assertFalse(editor.undo())

    # {
    #   責務: [test_monster_canvas_remains_fixed_at_64: 検証: monster canvas remains fixed at 64]
    #   処理: [1: 検証: monster canvas remains fixed at 64]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_monster_canvas_remains_fixed_at_64(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            editor = PixelArtEditor(Path(temporary))
            editor.load_species({}, "example")
            with self.assertRaises(ValueError):
                editor.resize_canvas(128)
            self.assertEqual(editor.logical_size, 64)
