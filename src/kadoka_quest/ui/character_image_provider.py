# {
#   責務: [character_image_provider: キャラクター・画像・providerの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from pathlib import Path
from typing import Any

import pygame


# {
#   責務: [CharacterImageProvider: Loads, crops, nearest-neighbour scales, and caches character PNGs.]
#   フィールド: [
#     repository: データ取得先
#     asset_root: asset・基準ディレクトリ
#     cache: cache（dict[tuple[str, str, int, int], pygame.Surface | None]）
#   ]
# }
class CharacterImageProvider:
    """Loads, crops, nearest-neighbour scales, and caches character PNGs."""

    # {
    #   責務: [__init__: キャラクター・画像・providerが利用する初期状態と依存を設定する]
    #   処理: [1: キャラクター・画像・providerが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     repository: データ取得先（Any）
    #     asset_root: asset・基準ディレクトリ（Path）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, repository: Any, asset_root: Path) -> None:
        self.repository = repository
        self.asset_root = Path(asset_root)
        self.cache: dict[tuple[str, str, int, int], pygame.Surface | None] = {}

    # {
    #   責務: [get: キャラクター・画像・providerを取得する]
    #   処理: [1: キャラクター・画像・providerを取得する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     species_id: 種族・識別子（str）
    #     kind: 種別（str）
    #     size: 大きさ（tuple[int, int]）
    #   ]
    #   戻り値: [result: キャラクター・画像・providerを取得するための結果（pygame.Surface | None）]
    # }
    def get(self, species_id: str, kind: str, size: tuple[int, int]) -> pygame.Surface | None:
        normalized_size = (int(size[0]), int(size[1]))
        key = (str(species_id), str(kind), *normalized_size)
        if key not in self.cache:
            self.cache[key] = self._load(str(species_id), str(kind), normalized_size)
        return self.cache[key]

    # {
    #   責務: [clear: キャラクター・画像・providerを消去する]
    #   処理: [1: キャラクター・画像・providerを消去する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def clear(self) -> None:
        self.cache.clear()

    # {
    #   責務: [appearance: Return fallback visual metadata without exposing the repository to renderers.]
    #   処理: [1: Return fallback visual metadata without exposing the repository to renderers.]
    #   引数: [
    #     self: 処理対象インスタンス
    #     species_id: 種族・識別子（str）
    #   ]
    #   戻り値: [result: Return fallback visual metadata without exposing the repository to renderers.ための結果（dict）]
    # }
    def appearance(self, species_id: str) -> dict:
        """Return fallback visual metadata without exposing the repository to renderers."""
        return self.repository.get_species(species_id).definition.get("appearance", {})

    # {
    #   責務: [_load: キャラクター・画像・providerを読み込む]
    #   処理: [1: キャラクター・画像・providerを読み込む]
    #   引数: [
    #     self: 処理対象インスタンス
    #     species_id: 種族・識別子（str）
    #     kind: 種別（str）
    #     size: 大きさ（tuple[int, int]）
    #   ]
    #   戻り値: [result: キャラクター・画像・providerを読み込むための結果（pygame.Surface | None）]
    # }
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

    # {
    #   責務: [_relative_path: キャラクター・画像・providerのrelative・パスを求める]
    #   処理: [1: キャラクター・画像・providerのrelative・パスを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     species_id: 種族・識別子（str）
    #     kind: 種別（str）
    #   ]
    #   戻り値: [result: キャラクター・画像・providerのrelative・パスを求めるための結果（str | None）]
    # }
    def _relative_path(self, species_id: str, kind: str) -> str | None:
        definition = self.repository.get_species(species_id).definition
        if kind.startswith("field"):
            direction = kind.removeprefix("field_") if kind != "field" else "front"
            value = definition.get("field_sprites", {}).get(direction) or definition.get("field_sprite_path")
        else:
            value = definition.get("portrait_path")
        return str(value) if value else None

    # {
    #   責務: [_crop_transparent_margin: キャラクター・画像・providerのcrop・transparent・marginを求める]
    #   処理: [1: キャラクター・画像・providerのcrop・transparent・marginを求める]
    #   引数: [source: 元データ（pygame.Surface）]
    #   戻り値: [result: キャラクター・画像・providerのcrop・transparent・marginを求めるための結果（pygame.Surface）]
    # }
    @staticmethod
    def _crop_transparent_margin(source: pygame.Surface) -> pygame.Surface:
        bounds = source.get_bounding_rect(min_alpha=8)
        if not bounds.width or not bounds.height:
            return source
        return source.subsurface(bounds).copy()

    # {
    #   責務: [_nearest_scale: キャラクター・画像・providerのnearest・scaleを求める]
    #   処理: [1: キャラクター・画像・providerのnearest・scaleを求める]
    #   引数: [
    #     source: 元データ（pygame.Surface）
    #     size: 大きさ（tuple[int, int]）
    #   ]
    #   戻り値: [result: キャラクター・画像・providerのnearest・scaleを求めるための結果（pygame.Surface）]
    # }
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
