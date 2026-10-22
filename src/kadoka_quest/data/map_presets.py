# {
#   責務: [map_presets: マップ・プリセット一覧の公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from kadoka_quest.data.jsonio import read_json, write_json
from kadoka_quest.paths import DATA_ROOT


# {
#   責務: [MapPresetStore: マップ・プリセット・保存先の状態と振る舞いを担当する]
#   フィールド: [root: 基準ディレクトリ]
# }
class MapPresetStore:
    # {
    #   責務: [__init__: マップ・プリセット・保存先が利用する初期状態と依存を設定する]
    #   処理: [1: マップ・プリセット・保存先が利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     data_root: データ・基準ディレクトリ（Path | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, data_root: Path | None = None) -> None:
        self.root = Path(data_root or DATA_ROOT) / "map_presets"

    # {
    #   責務: [list_ids: 識別子一覧を列挙する]
    #   処理: [1: 識別子一覧を列挙する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 識別子一覧を列挙するための結果（list[str]）]
    # }
    def list_ids(self) -> list[str]:
        return sorted(path.stem for path in self.root.glob("*.json"))

    # {
    #   責務: [get: マップ・プリセット・保存先を取得する]
    #   処理: [1: マップ・プリセット・保存先を取得する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     preset_id: プリセット・識別子（str）
    #   ]
    #   戻り値: [result: マップ・プリセット・保存先を取得するための結果（dict[str, Any]）]
    # }
    def get(self, preset_id: str) -> dict[str, Any]:
        return read_json(self.root / f"{preset_id}.json")

    # {
    #   責務: [save_from_map: from・マップを保存する]
    #   処理: [1: from・マップを保存する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     preset_id: プリセット・識別子（str）
    #     display_name: display・名前（str）
    #     map_data: マップ・データ（dict[str, Any]）
    #     overwrite: overwrite（bool）
    #   ]
    #   戻り値: [result: 要求データ（dict[str, Any]）]
    # }
    def save_from_map(
        self,
        preset_id: str,
        display_name: str,
        map_data: dict[str, Any],
        *,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        preset_id = self._validate_id(preset_id)
        display_name = self._validate_name(display_name)
        path = self.root / f"{preset_id}.json"
        if path.exists() and not overwrite:
            raise ValueError(f"Map preset already exists: {preset_id}")
        payload = deepcopy(map_data)
        payload["id"] = preset_id
        payload["display_name"] = display_name
        self._validate_document(payload)
        write_json(path, payload)
        return payload

    # {
    #   責務: [apply_to_map: to・マップを適用する]
    #   処理: [1: to・マップを適用する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     preset_id: プリセット・識別子（str）
    #     target_map: 対象・マップ（dict[str, Any]）
    #   ]
    #   戻り値: [result: 要求データ（dict[str, Any]）]
    # }
    def apply_to_map(self, preset_id: str, target_map: dict[str, Any]) -> dict[str, Any]:
        target_id = str(target_map["id"])
        target_name = str(target_map["display_name"])
        payload = deepcopy(self.get(preset_id))
        self._validate_document(payload)
        payload["id"] = target_id
        payload["display_name"] = target_name
        return payload

    # {
    #   責務: [build_map: マップを構築する]
    #   処理: [1: マップを構築する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     preset_id: プリセット・識別子（str）
    #     map_id: マップ・識別子（str）
    #     display_name: display・名前（str）
    #   ]
    #   戻り値: [result: 要求データ（dict[str, Any]）]
    # }
    def build_map(self, preset_id: str, map_id: str, display_name: str) -> dict[str, Any]:
        map_id = self._validate_id(map_id)
        display_name = self._validate_name(display_name)
        payload = deepcopy(self.get(preset_id))
        self._validate_document(payload)
        payload["id"] = map_id
        payload["display_name"] = display_name
        return payload

    # {
    #   責務: [_validate_id: 識別子を妥当性を検査する]
    #   処理: [1: 識別子を妥当性を検査する]
    #   引数: [value: 値（str）]
    #   戻り値: [result: 値（str）]
    # }
    @staticmethod
    def _validate_id(value: str) -> str:
        value = str(value).strip()
        allowed = "abcdefghijklmnopqrstuvwxyz0123456789_-"
        if not value or any(character not in allowed for character in value):
            raise ValueError("Map preset id may contain only lowercase letters, digits, _ and -")
        return value

    # {
    #   責務: [_validate_name: 名前を妥当性を検査する]
    #   処理: [1: 名前を妥当性を検査する]
    #   引数: [value: 値（str）]
    #   戻り値: [result: 値（str）]
    # }
    @staticmethod
    def _validate_name(value: str) -> str:
        value = str(value).strip()
        if not value:
            raise ValueError("Map preset display name is required")
        return value

    # {
    #   責務: [_validate_document: 文書を妥当性を検査する]
    #   処理: [1: 文書を妥当性を検査する]
    #   引数: [payload: 要求データ（dict[str, Any]）]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @staticmethod
    def _validate_document(payload: dict[str, Any]) -> None:
        width = int(payload["width"])
        height = int(payload["height"])
        tiles = payload["tiles"]
        if not (5 <= width <= 200 and 5 <= height <= 200):
            raise ValueError("Map width and height must be between 5 and 200")
        if len(tiles) != height or any(len(row) != width for row in tiles):
            raise ValueError("Map tile dimensions do not match width and height")
        payload.setdefault("schema_version", 1)
        payload.setdefault("tile_size", 32)
        payload.setdefault("spawns", [])
        payload.setdefault("fixed_mobs", [])
        payload.setdefault("events", [])
