# {
#   責務: [pixel_editor: ピクセル・editorの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable

import pygame

from kadoka_quest.ui.pixel_operations import (
    KADOKA_PALETTE,
    fit_imported_image,
    flood_fill_copy,
    opaque_color_count,
    reduce_similar_colors,
    reduce_to_kadoka_palette,
)


# {
#   責務: [PixelTarget: ピクセル・対象の状態と振る舞いを担当する]
#   フィールド: [
#     key: キー（str）
#     label: 表示名（str）
#     path: パス（str）
#     size: 大きさ（int）
#   ]
# }
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

PALETTE = KADOKA_PALETTE
ZOOM_LEVELS = (0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0)
CANVAS_SIZES = (1, 2, 4, 8, 16, 32, 64, 128)
TOOL_MODES = ("pen", "fill", "pan")
UNDO_LIMIT = 50
PALETTE_LIMIT = 16


# {
#   責務: [PixelArtEditor: Shared pixel editor; callers supply only the image targets and metadata.]
#   フィールド: [
#     asset_root: asset・基準ディレクトリ
#     targets: 対象一覧
#     selected: 選択中
#     palette: パレット
#     brush: brush
#     images: 画像一覧（dict[str, pygame.Surface]）
#     paths: パス一覧
#     dirty: dirty（set[str]）
#     zoom_index: 拡大率・位置番号
#     tool_mode: tool・mode
#     pan_offset: pan・表示位置
#     _pan_last: pan・last
#     undo_stacks: undo・stacks
#     _stroke_active: stroke・active
#     _stroke_slot: stroke・編成枠
#     _stroke_changed: stroke・changed
#     kadoka_palette_limit: kadoka・パレット・limit
#     _stroke_last_pixel: stroke・last・ピクセル
#   ]
# }
class PixelArtEditor:
    """Shared pixel editor; callers supply only the image targets and metadata."""

    # {
    #   責務: [__init__: ピクセル・art・editorが利用する初期状態と依存を設定する]
    #   処理: [1: ピクセル・art・editorが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     asset_root: asset・基準ディレクトリ（Path）
    #     targets: 対象一覧（Iterable[PixelTarget]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, asset_root: Path, targets: Iterable[PixelTarget] = ()) -> None:
        self.asset_root = asset_root
        self.targets: dict[str, PixelTarget] = {}
        self.selected = ""
        self.palette = list(PALETTE)
        self.brush = self.palette[1]
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
        self.kadoka_palette_limit: int | None = None
        self._stroke_last_pixel: tuple[int, int] | None = None
        self.set_targets(targets)

    # {
    #   責務: [zoom: ピクセル・art・editorの拡大率を求める]
    #   処理: [1: ピクセル・art・editorの拡大率を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: ピクセル・art・editorの拡大率を求めるための結果（float）]
    # }
    @property
    def zoom(self) -> float:
        return ZOOM_LEVELS[self.zoom_index]

    # {
    #   責務: [zoom_percent: ピクセル・art・editorの拡大率・percentを求める]
    #   処理: [1: ピクセル・art・editorの拡大率・percentを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: ピクセル・art・editorの拡大率・percentを求めるための結果（int）]
    # }
    @property
    def zoom_percent(self) -> int:
        return round(self.zoom * 100)

    # {
    #   責務: [logical_size: ピクセル・art・editorのlogical・大きさを求める]
    #   処理: [1: ピクセル・art・editorのlogical・大きさを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: ピクセル・art・editorのlogical・大きさを求めるための結果（int）]
    # }
    @property
    def logical_size(self) -> int:
        return self.images[self.selected].get_width() if self.selected else 64

    # {
    #   責務: [set_targets: 対象一覧を設定する]
    #   処理: [1: 対象一覧を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     targets: 対象一覧（Iterable[PixelTarget]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def set_targets(self, targets: Iterable[PixelTarget]) -> None:
        values = list(targets)
        self.targets = {target.key: target for target in values}
        self.paths = {target.key: target.path for target in values}
        self.selected = values[0].key if values else ""
        self.images.clear()
        self.dirty.clear()
        self.undo_stacks = {target.key: [] for target in values}
        self.kadoka_palette_limit = None
        self.end_stroke()
        self.end_pan()
        self.reset_zoom()

    # {
    #   責務: [load_targets: 対象一覧を読み込む]
    #   処理: [1: 対象一覧を読み込む]
    #   引数: [
    #     self: 処理対象インスタンス
    #     targets: 対象一覧（Iterable[PixelTarget]）
    #     body_color: body・色（tuple[int, int, int]）
    #     selected: 選択中（str | None）
    #     kadoka_palette_limit: kadoka・パレット・limit（int | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def load_targets(
        self,
        targets: Iterable[PixelTarget],
        body_color: tuple[int, int, int] = (128, 128, 128),
        selected: str | None = None,
        kadoka_palette_limit: int | None = None,
    ) -> None:
        self.set_targets(targets)
        self.kadoka_palette_limit = kadoka_palette_limit
        for target in self.targets.values():
            path = self.asset_root / target.path
            try:
                source = pygame.image.load(str(path)).convert_alpha()
                self.images[target.key] = self._fit(source, target.size)
            except (OSError, pygame.error, ValueError):
                self.images[target.key] = self._placeholder(target.size, target.key, body_color)
        if selected in self.images:
            self.selected = str(selected)

    # {
    #   責務: [load_species: 種族を読み込む]
    #   処理: [1: 種族を読み込む]
    #   引数: [
    #     self: 処理対象インスタンス
    #     definition: 定義（dict）
    #     species_id: 種族・識別子（str）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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
        self.load_targets(targets, body_color, selected="front", kadoka_palette_limit=5)

    # {
    #   責務: [load_block: ブロックを読み込む]
    #   処理: [1: ブロックを読み込む]
    #   引数: [
    #     self: 処理対象インスタンス
    #     relative_path: relative・パス（str）
    #     body_color: body・色（tuple[int, int, int]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def load_block(self, relative_path: str, body_color: tuple[int, int, int] = (128, 128, 128)) -> None:
        size = 64
        try:
            width, height = pygame.image.load(str(self.asset_root / relative_path)).get_size()
            if width == height and width in CANVAS_SIZES:
                size = width
        except (OSError, pygame.error, ValueError):
            pass
        self.load_targets(
            (PixelTarget("appearance", "ブロック見た目", relative_path, size),),
            body_color,
            kadoka_palette_limit=5,
        )

    # {
    #   責務: [resize_canvas: Resize a block with nearest-neighbour sampling as one undo step.]
    #   処理: [1: Resize a block with nearest-neighbour sampling as one undo step.]
    #   引数: [
    #     self: 処理対象インスタンス
    #     size: 大きさ（int）
    #   ]
    #   戻り値: [result: Resize a block with nearest-neighbour sampling as one undo step.ための結果（bool）]
    # }
    def resize_canvas(self, size: int) -> bool:
        """Resize a block with nearest-neighbour sampling as one undo step."""
        if size not in CANVAS_SIZES:
            raise ValueError(f"キャンバスサイズは {CANVAS_SIZES} から選択してください。")
        if not self.selected:
            return False
        if self.selected != "appearance" and size != 64:
            raise ValueError("モンスター画像は64×64固定です。")
        size = int(size)
        image = self.images[self.selected]
        if image.get_size() == (size, size):
            return False
        self.end_pan()
        self._replace_selected_image(pygame.transform.scale(image, (size, size)))
        self.targets[self.selected] = replace(self.targets[self.selected], size=size)
        self.reset_zoom()
        return True

    # {
    #   責務: [_fit: ピクセル・art・editorを表示範囲へ合わせる]
    #   処理: [1: ピクセル・art・editorを表示範囲へ合わせる]
    #   引数: [
    #     source: 元データ（pygame.Surface）
    #     size: 大きさ（int）
    #   ]
    #   戻り値: [result: キャンバス（pygame.Surface）]
    # }
    @staticmethod
    def _fit(source: pygame.Surface, size: int) -> pygame.Surface:
        canvas = pygame.Surface((size, size), pygame.SRCALPHA)
        ratio = min(size / source.get_width(), size / source.get_height())
        scaled_size = (max(1, round(source.get_width() * ratio)), max(1, round(source.get_height() * ratio)))
        scaled = pygame.transform.scale(source, scaled_size)
        canvas.blit(scaled, scaled.get_rect(center=(size // 2, size // 2)))
        return canvas

    # {
    #   責務: [_placeholder: ピクセル・art・editorのplaceholderを求める]
    #   処理: [1: ピクセル・art・editorのplaceholderを求める]
    #   引数: [
    #     size: 大きさ（int）
    #     slot: 編成枠（str）
    #     body_color: body・色（tuple[int, int, int]）
    #   ]
    #   戻り値: [result: 画像（pygame.Surface）]
    # }
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

    # {
    #   責務: [select: ピクセル・art・editorを選択する]
    #   処理: [1: ピクセル・art・editorを選択する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     slot: 編成枠（str）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def select(self, slot: str) -> None:
        if slot in self.images:
            self.end_stroke()
            self.end_pan()
            self.selected = slot
            self.reset_zoom()

    # {
    #   責務: [set_tool_mode: tool・modeを設定する]
    #   処理: [1: tool・modeを設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     mode: mode（str）
    #   ]
    #   戻り値: [result: tool・modeを設定するための結果（bool）]
    # }
    def set_tool_mode(self, mode: str) -> bool:
        if mode not in TOOL_MODES:
            return False
        self.end_stroke()
        self.end_pan()
        self.tool_mode = mode
        return True

    # {
    #   責務: [color_to_hex: ピクセル・art・editorの色・to・hexを求める]
    #   処理: [1: ピクセル・art・editorの色・to・hexを求める]
    #   引数: [color: 色（tuple[int, int, int, int]）]
    #   戻り値: [result: ピクセル・art・editorの色・to・hexを求めるための結果（str）]
    # }
    @staticmethod
    def color_to_hex(color: tuple[int, int, int, int]) -> str:
        return f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}"

    # {
    #   責務: [parse_palette_color: パレット・色を解析する]
    #   処理: [1: パレット・色を解析する]
    #   引数: [value: 値（str）]
    #   戻り値: [result: パレット・色を解析するための結果（tuple[int, int, int, int]）]
    # }
    @staticmethod
    def parse_palette_color(value: str) -> tuple[int, int, int, int]:
        clean = str(value).strip().lstrip("#")
        if len(clean) != 6:
            raise ValueError("色は #RRGGBB 形式で入力してください。")
        try:
            red, green, blue = (int(clean[index:index + 2], 16) for index in (0, 2, 4))
        except ValueError as error:
            raise ValueError("色は #RRGGBB 形式で入力してください。") from error
        return red, green, blue, 255

    # {
    #   責務: [parse_tolerance: toleranceを解析する]
    #   処理: [1: toleranceを解析する]
    #   引数: [value: 値（str）]
    #   戻り値: [result: tolerance（int）]
    # }
    @staticmethod
    def parse_tolerance(value: str) -> int:
        try:
            tolerance = int(str(value).strip())
        except ValueError as error:
            raise ValueError("近似色のしきい値は0〜255の整数にしてください。") from error
        if not 0 <= tolerance <= 255:
            raise ValueError("近似色のしきい値は0〜255の整数にしてください。")
        return tolerance

    # {
    #   責務: [add_palette_color: パレット・色を追加する]
    #   処理: [1: パレット・色を追加する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（str）
    #   ]
    #   戻り値: [result: 色（tuple[int, int, int, int]）]
    # }
    def add_palette_color(self, value: str) -> tuple[int, int, int, int]:
        color = self.parse_palette_color(value)
        if color in self.palette:
            self.brush = color
            return color
        if len(self.palette) >= PALETTE_LIMIT:
            raise ValueError(f"パレットは最大{PALETTE_LIMIT}色です。不要な色を削除してください。")
        self.palette.append(color)
        self.brush = color
        return color

    # {
    #   責務: [remove_palette_color: パレット・色を取り除く]
    #   処理: [1: パレット・色を取り除く]
    #   引数: [
    #     self: 処理対象インスタンス
    #     color: 色（tuple[int, int, int, int] | None）
    #   ]
    #   戻り値: [result: パレット・色を取り除くための結果（bool）]
    # }
    def remove_palette_color(self, color: tuple[int, int, int, int] | None = None) -> bool:
        target = color or self.brush
        if target not in self.palette or target[3] == 0:
            return False
        if sum(item[3] > 0 for item in self.palette) <= 1:
            return False
        index = self.palette.index(target)
        self.palette.remove(target)
        if self.brush == target:
            replacement_index = min(index, len(self.palette) - 1)
            self.brush = self.palette[replacement_index]
        return True

    # {
    #   責務: [palette_rects: ピクセル・art・editorのパレット・rectsを求める]
    #   処理: [1: ピクセル・art・editorのパレット・rectsを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     origin: origin（tuple[int, int]）
    #     columns: columns（int）
    #     swatch_size: swatch・大きさ（tuple[int, int]）
    #     gap: gap（tuple[int, int]）
    #   ]
    #   戻り値: [result: ピクセル・art・editorのパレット・rectsを求めるための結果（list[tuple[tuple[int, int, int, int], pygame.Rect]]）]
    # }
    def palette_rects(
        self,
        origin: tuple[int, int],
        columns: int,
        swatch_size: tuple[int, int],
        gap: tuple[int, int] = (8, 8),
    ) -> list[tuple[tuple[int, int, int, int], pygame.Rect]]:
        columns = max(1, int(columns))
        width, height = swatch_size
        gap_x, gap_y = gap
        return [
            (
                color,
                pygame.Rect(
                    origin[0] + (index % columns) * (width + gap_x),
                    origin[1] + (index // columns) * (height + gap_y),
                    width,
                    height,
                ),
            )
            for index, color in enumerate(self.palette)
        ]

    # {
    #   責務: [zoom_in: ピクセル・art・editorの拡大率・inを求める]
    #   処理: [1: ピクセル・art・editorの拡大率・inを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: ピクセル・art・editorの拡大率・inを求めるための結果（bool）]
    # }
    def zoom_in(self) -> bool:
        old = self.zoom_index
        self.zoom_index = min(len(ZOOM_LEVELS) - 1, self.zoom_index + 1)
        return self.zoom_index != old

    # {
    #   責務: [zoom_out: ピクセル・art・editorの拡大率・outを求める]
    #   処理: [1: ピクセル・art・editorの拡大率・outを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: ピクセル・art・editorの拡大率・outを求めるための結果（bool）]
    # }
    def zoom_out(self) -> bool:
        old = self.zoom_index
        self.zoom_index = max(0, self.zoom_index - 1)
        return self.zoom_index != old

    # {
    #   責務: [reset_zoom: 拡大率の初期状態へ戻す]
    #   処理: [1: 拡大率の初期状態へ戻す]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def reset_zoom(self) -> None:
        self.zoom_index = ZOOM_LEVELS.index(1.0)
        self.pan_offset.update(0, 0)

    # {
    #   責務: [_clamp_pan: ピクセル・art・editorのclamp・panを求める]
    #   処理: [1: ピクセル・art・editorのclamp・panを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     canvas: キャンバス（pygame.Rect）
    #     side: 陣営（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def _clamp_pan(self, canvas: pygame.Rect, side: int) -> None:
        maximum_x = max(0, (side - canvas.width) / 2)
        maximum_y = max(0, (side - canvas.height) / 2)
        self.pan_offset.x = max(-maximum_x, min(maximum_x, self.pan_offset.x))
        self.pan_offset.y = max(-maximum_y, min(maximum_y, self.pan_offset.y))

    # {
    #   責務: [image_rect: ピクセル・art・editorの画像・表示矩形を求める]
    #   処理: [1: ピクセル・art・editorの画像・表示矩形を求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     canvas: キャンバス（pygame.Rect）
    #   ]
    #   戻り値: [result: ピクセル・art・editorの画像・表示矩形を求めるための結果（pygame.Rect）]
    # }
    def image_rect(self, canvas: pygame.Rect) -> pygame.Rect:
        side = max(1, round(min(canvas.width, canvas.height) * self.zoom))
        self._clamp_pan(canvas, side)
        return pygame.Rect(
            canvas.centerx - side // 2 + round(self.pan_offset.x),
            canvas.centery - side // 2 + round(self.pan_offset.y),
            side,
            side,
        )

    # {
    #   責務: [begin_pan: panを開始する]
    #   処理: [1: panを開始する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     position: 座標（tuple[int, int]）
    #     canvas: キャンバス（pygame.Rect）
    #   ]
    #   戻り値: [result: panを開始するための結果（bool）]
    # }
    def begin_pan(self, position: tuple[int, int], canvas: pygame.Rect) -> bool:
        if self.tool_mode != "pan" or not canvas.collidepoint(position):
            return False
        self.end_stroke()
        self._pan_last = position
        return True

    # {
    #   責務: [pan_to: ピクセル・art・editorのpan・toを求める]
    #   処理: [1: ピクセル・art・editorのpan・toを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     position: 座標（tuple[int, int]）
    #     canvas: キャンバス（pygame.Rect）
    #   ]
    #   戻り値: [result: ピクセル・art・editorのpan・toを求めるための結果（bool）]
    # }
    def pan_to(self, position: tuple[int, int], canvas: pygame.Rect) -> bool:
        if self.tool_mode != "pan" or self._pan_last is None:
            return False
        dx = position[0] - self._pan_last[0]
        dy = position[1] - self._pan_last[1]
        self._pan_last = position
        self.pan_offset.update(self.pan_offset.x + dx, self.pan_offset.y + dy)
        self.image_rect(canvas)
        return bool(dx or dy)

    # {
    #   責務: [end_pan: ピクセル・art・editorのend・panを求める]
    #   処理: [1: ピクセル・art・editorのend・panを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def end_pan(self) -> None:
        self._pan_last = None

    # {
    #   責務: [begin_stroke: strokeを開始する]
    #   処理: [1: strokeを開始する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: strokeを開始するための結果（bool）]
    # }
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
        self._stroke_last_pixel = None
        return True

    # {
    #   責務: [end_stroke: ピクセル・art・editorのend・strokeを求める]
    #   処理: [1: ピクセル・art・editorのend・strokeを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def end_stroke(self) -> None:
        if self._stroke_active and not self._stroke_changed:
            stack = self.undo_stacks.get(self._stroke_slot, [])
            if stack:
                stack.pop()
        self._stroke_active = False
        self._stroke_slot = ""
        self._stroke_changed = False
        self._stroke_last_pixel = None

    # {
    #   責務: [
    #     undo: 選択中の画像に対する直前の編集を一段階戻す
    #   ]
    #   処理: [
    #     1: 進行中のstrokeを確定し、選択/履歴がなければ何もしない
    #     2: 画像と論理サイズを復元し、選択対象を未保存状態へ印付けする
    #   ]
    #   引数: [
    #     self: 処理対象インスタンス
    #   ]
    #   戻り値: [
    #     result: 復元できたらTrue。保存ファイルは変更しない
    #   ]
    # }
    def undo(self) -> bool:
        self.end_stroke()
        if not self.selected:
            return False
        stack = self.undo_stacks.setdefault(self.selected, [])
        if not stack:
            return False
        self.images[self.selected] = stack.pop()
        self.targets[self.selected] = replace(self.targets[self.selected], size=self.logical_size)
        self.dirty.add(self.selected)
        return True

    # {
    #   責務: [_replace_selected_image: ピクセル・art・editorのreplace・選択中・画像を求める]
    #   処理: [1: ピクセル・art・editorのreplace・選択中・画像を求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     image: 画像（pygame.Surface）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def _replace_selected_image(self, image: pygame.Surface) -> None:
        self.end_stroke()
        stack = self.undo_stacks.setdefault(self.selected, [])
        stack.append(self.images[self.selected].copy())
        if len(stack) > UNDO_LIMIT:
            del stack[0]
        self.images[self.selected] = image
        self.dirty.add(self.selected)

    # {
    #   責務: [import_image: 画像を取り込む]
    #   処理: [1: 画像を取り込む]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（str）
    #     tolerance: tolerance（int）
    #   ]
    #   戻り値: [result: changed（int）]
    # }
    def import_image(self, value: str, tolerance: int = 24) -> int:
        if not self.selected:
            raise ValueError("編集する画像が選択されていません。")
        path = Path(str(value).strip()).expanduser()
        if not path.is_absolute():
            path = self.asset_root.parent / path
        if not path.is_file():
            raise ValueError("読み込む画像ファイルが見つかりません。")
        try:
            source = pygame.image.load(str(path))
        except (OSError, pygame.error) as error:
            raise ValueError("画像ファイルを読み込めませんでした。") from error
        fitted = fit_imported_image(source, self.logical_size)
        reduced, changed = reduce_similar_colors(fitted, tolerance)
        if self.kadoka_palette_limit is not None:
            reduced, palette_changed, _ = reduce_to_kadoka_palette(reduced, self.kadoka_palette_limit)
            changed += palette_changed
        self._replace_selected_image(reduced)
        return changed

    # {
    #   責務: [merge_similar_colors: similar・色一覧を結合する]
    #   処理: [1: similar・色一覧を結合する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     tolerance: tolerance（int）
    #   ]
    #   戻り値: [result: similar・色一覧を結合するための結果（int）]
    # }
    def merge_similar_colors(self, tolerance: int = 24) -> int:
        if not self.selected:
            return 0
        reduced, changed = reduce_similar_colors(self.images[self.selected], tolerance)
        if changed:
            self._replace_selected_image(reduced)
        return changed

    # {
    #   責務: [reduce_to_kadoka_colors: ピクセル・art・editorのreduce・to・kadoka・色一覧を求める]
    #   処理: [1: ピクセル・art・editorのreduce・to・kadoka・色一覧を求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     max_colors: max・色一覧（int）
    #   ]
    #   戻り値: [result: ピクセル・art・editorのreduce・to・kadoka・色一覧を求めるための結果（tuple[int, int]）]
    # }
    def reduce_to_kadoka_colors(self, max_colors: int) -> tuple[int, int]:
        if not self.selected:
            return 0, 0
        reduced, changed, _ = reduce_to_kadoka_palette(self.images[self.selected], max_colors)
        if changed:
            self._replace_selected_image(reduced)
        return changed, opaque_color_count(reduced)

    # {
    #   責務: [visible_color_count: ピクセル・art・editorのvisible・色・countを求める]
    #   処理: [1: ピクセル・art・editorのvisible・色・countを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: ピクセル・art・editorのvisible・色・countを求めるための結果（int）]
    # }
    def visible_color_count(self) -> int:
        if not self.selected:
            return 0
        return opaque_color_count(self.images[self.selected])

    # {
    #   責務: [draw_checker: checkerを描画する]
    #   処理: [1: checkerを描画する]
    #   引数: [
    #     surface: 描画面（pygame.Surface）
    #     rect: 表示矩形（pygame.Rect）
    #     cell: cell（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @staticmethod
    def draw_checker(surface: pygame.Surface, rect: pygame.Rect, cell: int = 8) -> None:
        for y in range(rect.y, rect.bottom, cell):
            for x in range(rect.x, rect.right, cell):
                color = (205, 205, 205) if ((x - rect.x) // cell + (y - rect.y) // cell) % 2 == 0 else (150, 150, 150)
                pygame.draw.rect(surface, color, pygame.Rect(x, y, min(cell, rect.right - x), min(cell, rect.bottom - y)))

    # {
    #   責務: [draw_canvas: キャンバスを描画する]
    #   処理: [1: キャンバスを描画する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     surface: 描画面（pygame.Surface）
    #     canvas: キャンバス（pygame.Rect）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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

    # {
    #   責務: [_pixel_at: ピクセル・art・editorのピクセル・atを求める]
    #   処理: [1: ピクセル・art・editorのピクセル・atを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     position: 座標（tuple[int, int]）
    #     canvas: キャンバス（pygame.Rect）
    #   ]
    #   戻り値: [result: ピクセル・art・editorのピクセル・atを求めるための結果（tuple[int, int] | None）]
    # }
    def _pixel_at(self, position: tuple[int, int], canvas: pygame.Rect) -> tuple[int, int] | None:
        if not canvas.collidepoint(position) or not self.selected:
            return None
        image_rect = self.image_rect(canvas)
        if not image_rect.collidepoint(position):
            return None
        size = self.logical_size
        x = int((position[0] - image_rect.x) * size / image_rect.width)
        y = int((position[1] - image_rect.y) * size / image_rect.height)
        if not (0 <= x < size and 0 <= y < size):
            return None
        return x, y

    # {
    #   責務: [_line_pixels: ピクセル・art・editorのline・ピクセル一覧を求める]
    #   処理: [1: ピクセル・art・editorのline・ピクセル一覧を求める]
    #   引数: [
    #     start: start（tuple[int, int]）
    #     end: end（tuple[int, int]）
    #   ]
    #   戻り値: [result: ピクセル一覧（list[tuple[int, int]]）]
    # }
    @staticmethod
    def _line_pixels(start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int]]:
        x, y = start
        target_x, target_y = end
        delta_x = abs(target_x - x)
        delta_y = -abs(target_y - y)
        step_x = 1 if x < target_x else -1
        step_y = 1 if y < target_y else -1
        error = delta_x + delta_y
        pixels: list[tuple[int, int]] = []
        while True:
            pixels.append((x, y))
            if x == target_x and y == target_y:
                return pixels
            doubled = error * 2
            if doubled >= delta_y:
                error += delta_y
                x += step_x
            if doubled <= delta_x:
                error += delta_x
                y += step_y

    # {
    #   責務: [
    #     paint: ペンモードでキャンバス座標をドットへ変換し連続strokeを描く
    #   ]
    #   処理: [
    #     1: 選択・モード・キャンバス範囲を確認する
    #     2: 前回のドットからの線を塗り、変更がある場合だけdirty/undo用strokeへ記録する
    #   ]
    #   引数: [
    #     self: 処理対象インスタンス
    #     position: 座標（tuple[int, int]）
    #     canvas: キャンバス（pygame.Rect）
    #     erase: erase（bool）
    #   ]
    #   戻り値: [
    #     result: 画像ピクセルを変更した場合True。パンモードでは塗らない
    #   ]
    # }
    def paint(self, position: tuple[int, int], canvas: pygame.Rect, erase: bool = False) -> bool:
        if self.tool_mode != "pen" or not self.selected:
            return False
        pixel = self._pixel_at(position, canvas)
        if pixel is None:
            self._stroke_last_pixel = None
            return False
        automatic_stroke = not self._stroke_active
        if automatic_stroke:
            self.begin_stroke()
        color = (0, 0, 0, 0) if erase else self.brush
        start = self._stroke_last_pixel if self._stroke_slot == self.selected else None
        changed = False
        for target in self._line_pixels(start or pixel, pixel):
            if self.images[self.selected].get_at(target) != color:
                self.images[self.selected].set_at(target, color)
                changed = True
        self._stroke_last_pixel = pixel
        if changed:
            self.dirty.add(self.selected)
            self._stroke_changed = True
        if automatic_stroke:
            self.end_stroke()
        return changed

    # {
    #   責務: [fill: ピクセル・art・editorのfillを求める]
    #   処理: [1: ピクセル・art・editorのfillを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     position: 座標（tuple[int, int]）
    #     canvas: キャンバス（pygame.Rect）
    #     erase: erase（bool）
    #   ]
    #   戻り値: [result: ピクセル・art・editorのfillを求めるための結果（int）]
    # }
    def fill(self, position: tuple[int, int], canvas: pygame.Rect, erase: bool = False) -> int:
        if self.tool_mode != "fill" or not canvas.collidepoint(position) or not self.selected:
            return 0
        image_rect = self.image_rect(canvas)
        if not image_rect.collidepoint(position):
            return 0
        size = self.logical_size
        x = int((position[0] - image_rect.x) * size / image_rect.width)
        y = int((position[1] - image_rect.y) * size / image_rect.height)
        replacement = (0, 0, 0, 0) if erase else self.brush
        result, changed = flood_fill_copy(self.images[self.selected], (x, y), replacement)
        if changed:
            self._replace_selected_image(result)
        return changed

    # {
    #   責務: [save_images: 画像一覧を保存する]
    #   処理: [1: 画像一覧を保存する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def save_images(self) -> None:
        for key in tuple(self.dirty):
            path = self.asset_root / self.paths[key]
            path.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(self.images[key], str(path))
        self.dirty.clear()

    # {
    #   責務: [save_all: allを保存する]
    #   処理: [1: allを保存する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     definition: 定義（dict）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def save_all(self, definition: dict) -> None:
        self.save_images()
        definition["portrait_path"] = self.paths["portrait"]
        definition["field_sprite_path"] = self.paths["front"]
        definition["field_sprites"] = {direction: self.paths[direction] for direction in ("front", "right", "left", "back")}
