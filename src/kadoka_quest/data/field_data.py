# {
#   責務: [field_data: フィールド・データの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from kadoka_quest.data.jsonio import read_json
from kadoka_quest.data.repository import GameRepository


# {
#   責務: [FieldDataLoader: Load field maps and blocks and normalize a requested entry position.]
#   フィールド: [repository: データ取得先]
# }
class FieldDataLoader:
    """Load field maps and blocks and normalize a requested entry position."""

    # {
    #   責務: [__init__: フィールド・データ・loaderが利用する初期状態と依存を設定する]
    #   処理: [1: フィールド・データ・loaderが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     repository: データ取得先（GameRepository）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, repository: GameRepository) -> None:
        self.repository = repository

    # {
    #   責務: [blocks: フィールド・データ・loaderのブロック定義を求める]
    #   処理: [1: フィールド・データ・loaderのブロック定義を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: フィールド・データ・loaderのブロック定義を求めるための結果（dict[str, dict]）]
    # }
    def blocks(self) -> dict[str, dict]:
        return {item["id"]: item for item in self.repository.list_blocks()}

    # {
    #   責務: [species_ai_weights: フィールド・データ・loaderの種族・AI・重み一覧を求める]
    #   処理: [1: フィールド・データ・loaderの種族・AI・重み一覧を求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     map_data: マップ・データ（dict）
    #   ]
    #   戻り値: [result: フィールド・データ・loaderの種族・AI・重み一覧を求めるための結果（dict）]
    # }
    def species_ai_weights(self, map_data: dict) -> dict:
        species_ids = sorted({entry["species_id"] for entry in map_data.get("spawns", [])})
        return {
            species_id: self.repository.get_species(species_id).definition.get("field_ai_weights")
            for species_id in species_ids
        }

    # {
    #   責務: [_additional_events: フィールド・データ・loaderのadditional・イベント一覧を求める]
    #   処理: [1: フィールド・データ・loaderのadditional・イベント一覧を求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     map_id: マップ・識別子（str）
    #   ]
    #   戻り値: [result: イベント一覧（list[dict]）]
    # }
    def _additional_events(self, map_id: str) -> list[dict]:
        root = self.repository.root / "maps" / str(map_id) / "events"
        events: list[dict] = []
        if not root.is_dir():
            return events
        for path in sorted(root.glob("*.json")):
            try:
                payload = read_json(path)
            except (OSError, ValueError):
                continue
            if not isinstance(payload, dict):
                continue
            embedded = payload.get("events")
            values = embedded if isinstance(embedded, list) else [payload]
            events.extend(dict(event) for event in values if isinstance(event, dict) and event.get("id"))
        return events

    # {
    #   責務: [load_map: マップを読み込む]
    #   処理: [1: マップを読み込む]
    #   引数: [
    #     self: 処理対象インスタンス
    #     map_id: マップ・識別子（str）
    #     x: X座標（int | None）
    #     y: Y座標（int | None）
    #   ]
    #   戻り値: [result: マップを読み込むための結果（dict）]
    # }
    def load_map(self, map_id: str, x: int | None = None, y: int | None = None) -> dict:
        map_id = str(map_id)
        map_data = self.repository.get_map(map_id)
        additional_events = self._additional_events(map_id)
        if additional_events:
            map_data = dict(map_data)
            map_data["events"] = [*map_data.get("events", []), *additional_events]
        requested_x = map_data["start"]["x"] if x is None else int(x)
        requested_y = map_data["start"]["y"] if y is None else int(y)
        return {
            "map": map_data,
            "x": max(0, min(int(map_data["width"]) - 1, requested_x)),
            "y": max(0, min(int(map_data["height"]) - 1, requested_y)),
        }
