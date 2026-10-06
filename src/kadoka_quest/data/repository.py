# {
#   責務: [repository: データ取得先の公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kadoka_quest.data.jsonio import read_json, write_json
from kadoka_quest.paths import DATA_ROOT


STAT_KEYS = ("attack", "defense", "speed", "magic", "hp", "mp")


# {
#   責務: [SpeciesBundle: 種族・bundleの状態と振る舞いを担当する]
#   フィールド: [
#     definition: 定義（dict[str, Any]）
#     stats: 能力値（dict[str, Any]）
#     skills: スキル一覧（dict[str, Any]）
#     plus: ＋選択（dict[str, Any]）
#   ]
# }
@dataclass(frozen=True)
class SpeciesBundle:
    definition: dict[str, Any]
    stats: dict[str, Any]
    skills: dict[str, Any]
    plus: dict[str, Any]

    # {
    #   責務: [species_id: 種族・bundleの種族・識別子を求める]
    #   処理: [1: 種族・bundleの種族・識別子を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 種族・bundleの種族・識別子を求めるための結果（str）]
    # }
    @property
    def species_id(self) -> str:
        return str(self.definition["id"])


# {
#   責務: [GameRepository: ゲーム・データ取得先の状態と振る舞いを担当する]
#   フィールド: [root: 基準ディレクトリ]
# }
class GameRepository:
    # {
    #   責務: [__init__: ゲーム・データ取得先が利用する初期状態と依存を設定する]
    #   処理: [1: ゲーム・データ取得先が利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     data_root: データ・基準ディレクトリ（Path | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, data_root: Path | None = None) -> None:
        self.root = Path(data_root or DATA_ROOT)

    # {
    #   責務: [list_blocks: ブロック定義を列挙する]
    #   処理: [1: ブロック定義を列挙する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: ブロック定義を列挙するための結果（list[dict[str, Any]]）]
    # }
    def list_blocks(self) -> list[dict[str, Any]]:
        blocks = [read_json(path) for path in sorted((self.root / "blocks").glob("*.json"))]
        return sorted(blocks, key=lambda item: str(item.get("id", "")))

    # {
    #   責務: [get_block: ブロックを取得する]
    #   処理: [1: ブロックを取得する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     block_id: ブロック・識別子（str）
    #   ]
    #   戻り値: [result: ブロックを取得するための結果（dict[str, Any]）]
    # }
    def get_block(self, block_id: str) -> dict[str, Any]:
        return read_json(self.root / "blocks" / f"{block_id}.json")

    # {
    #   責務: [save_block: ブロックを保存する]
    #   処理: [1: ブロックを保存する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     block: ブロック（dict[str, Any]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def save_block(self, block: dict[str, Any]) -> None:
        block_id = str(block["id"]).strip()
        if not block_id or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for char in block_id):
            raise ValueError("Block id may contain only lowercase letters, digits, _ and -")
        write_json(self.root / "blocks" / f"{block_id}.json", block)

    # {
    #   責務: [list_maps: マップ一覧を列挙する]
    #   処理: [1: マップ一覧を列挙する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: マップ一覧を列挙するための結果（list[str]）]
    # }
    def list_maps(self) -> list[str]:
        return sorted(path.parent.name for path in (self.root / "maps").glob("*/map.json"))

    # {
    #   責務: [get_map: マップを取得する]
    #   処理: [1: マップを取得する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     map_id: マップ・識別子（str）
    #   ]
    #   戻り値: [result: マップを取得するための結果（dict[str, Any]）]
    # }
    def get_map(self, map_id: str) -> dict[str, Any]:
        return read_json(self.root / "maps" / map_id / "map.json")

    # {
    #   責務: [save_map: マップを保存する]
    #   処理: [1: マップを保存する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     map_data: マップ・データ（dict[str, Any]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def save_map(self, map_data: dict[str, Any]) -> None:
        map_id = str(map_data["id"])
        write_json(self.root / "maps" / map_id / "map.json", map_data)

    # {
    #   責務: [create_map: マップを作成する]
    #   処理: [1: マップを作成する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     map_id: マップ・識別子（str）
    #     display_name: display・名前（str）
    #     width: 幅（int）
    #     height: 高さ（int）
    #     fill_block_id: fill・ブロック・識別子（str）
    #   ]
    #   戻り値: [result: 要求データ（dict[str, Any]）]
    # }
    def create_map(self, map_id: str, display_name: str, width: int, height: int, fill_block_id: str) -> dict[str, Any]:
        map_id = str(map_id).strip()
        display_name = str(display_name).strip()
        width, height = int(width), int(height)
        if not map_id or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for char in map_id):
            raise ValueError("Map id may contain only lowercase letters, digits, _ and -")
        if (self.root / "maps" / map_id / "map.json").exists():
            raise ValueError(f"Map already exists: {map_id}")
        if not display_name:
            raise ValueError("Map display name is required")
        if not (5 <= width <= 200 and 5 <= height <= 200):
            raise ValueError("Map width and height must be between 5 and 200")
        self.get_block(fill_block_id)
        payload: dict[str, Any] = {
            "schema_version": 1,
            "id": map_id,
            "display_name": display_name,
            "width": width,
            "height": height,
            "tile_size": 32,
            "start": {"x": width // 2, "y": height // 2},
            "tiles": [[fill_block_id for _ in range(width)] for _ in range(height)],
            "spawns": [],
            "fixed_mobs": [],
            "events": [],
        }
        self.save_map(payload)
        return payload

    # {
    #   責務: [create_map_from_document: マップ・from・文書を作成する]
    #   処理: [1: マップ・from・文書を作成する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     map_data: マップ・データ（dict[str, Any]）
    #   ]
    #   戻り値: [result: 要求データ（dict[str, Any]）]
    # }
    def create_map_from_document(self, map_data: dict[str, Any]) -> dict[str, Any]:
        map_id = str(map_data["id"]).strip()
        display_name = str(map_data["display_name"]).strip()
        if not map_id or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for char in map_id):
            raise ValueError("Map id may contain only lowercase letters, digits, _ and -")
        if (self.root / "maps" / map_id / "map.json").exists():
            raise ValueError(f"Map already exists: {map_id}")
        if not display_name:
            raise ValueError("Map display name is required")
        width, height = int(map_data["width"]), int(map_data["height"])
        tiles = map_data["tiles"]
        if not (5 <= width <= 200 and 5 <= height <= 200):
            raise ValueError("Map width and height must be between 5 and 200")
        if len(tiles) != height or any(len(row) != width for row in tiles):
            raise ValueError("Map tile dimensions do not match width and height")
        known_blocks = {str(block["id"]) for block in self.list_blocks()}
        unknown_blocks = {str(block_id) for row in tiles for block_id in row} - known_blocks
        if unknown_blocks:
            raise ValueError(f"Map references unknown blocks: {', '.join(sorted(unknown_blocks))}")
        payload = dict(map_data)
        self.save_map(payload)
        return payload

    # {
    #   責務: [list_species_ids: 種族・識別子一覧を列挙する]
    #   処理: [1: 種族・識別子一覧を列挙する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 種族・識別子一覧を列挙するための結果（list[str]）]
    # }
    def list_species_ids(self) -> list[str]:
        return sorted(path.parent.name for path in (self.root / "species").glob("*/species.json"))

    # {
    #   責務: [get_species: 種族を取得する]
    #   処理: [1: 種族を取得する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     species_id: 種族・識別子（str）
    #   ]
    #   戻り値: [result: 種族を取得するための結果（SpeciesBundle）]
    # }
    def get_species(self, species_id: str) -> SpeciesBundle:
        folder = self.root / "species" / species_id
        return SpeciesBundle(
            read_json(folder / "species.json"),
            read_json(folder / "stats.json"),
            read_json(folder / "skills.json"),
            read_json(folder / "plus.json"),
        )

    # {
    #   責務: [save_species_definition: 種族・定義を保存する]
    #   処理: [1: 種族・定義を保存する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     definition: 定義（dict[str, Any]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def save_species_definition(self, definition: dict[str, Any]) -> None:
        species_id = str(definition["id"])
        write_json(self.root / "species" / species_id / "species.json", definition)

    # {
    #   責務: [save_species_stats: 種族・能力値を保存する]
    #   処理: [1: 種族・能力値を保存する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     species_id: 種族・識別子（str）
    #     stats: 能力値（dict[str, Any]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def save_species_stats(self, species_id: str, stats: dict[str, Any]) -> None:
        write_json(self.root / "species" / species_id / "stats.json", stats)

    # {
    #   責務: [save_species_skills: 種族・スキル一覧を保存する]
    #   処理: [1: 種族・スキル一覧を保存する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     species_id: 種族・識別子（str）
    #     skills: スキル一覧（dict[str, Any]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def save_species_skills(self, species_id: str, skills: dict[str, Any]) -> None:
        write_json(self.root / "species" / species_id / "skills.json", skills)

    # {
    #   責務: [save_species_plus: 種族・＋選択を保存する]
    #   処理: [1: 種族・＋選択を保存する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     species_id: 種族・識別子（str）
    #     plus: ＋選択（dict[str, Any]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def save_species_plus(self, species_id: str, plus: dict[str, Any]) -> None:
        write_json(self.root / "species" / species_id / "plus.json", plus)

    # {
    #   責務: [stats_at: ゲーム・データ取得先の能力値・atを求める]
    #   処理: [1: ゲーム・データ取得先の能力値・atを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     species_id: 種族・識別子（str）
    #     level: レベル（int）
    #   ]
    #   戻り値: [result: ゲーム・データ取得先の能力値・atを求めるための結果（dict[str, int]）]
    # }
    def stats_at(self, species_id: str, level: int) -> dict[str, int]:
        level = max(1, min(100, int(level)))
        values = self.get_species(species_id).stats["levels"][str(level)]
        return {key: int(values[key]) for key in STAT_KEYS}

    # {
    #   責務: [skill_ids_at: ゲーム・データ取得先のスキル・識別子一覧・atを求める]
    #   処理: [1: ゲーム・データ取得先のスキル・識別子一覧・atを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     species_id: 種族・識別子（str）
    #     level: レベル（int）
    #     plus_choices: ＋選択・choices（list[str] | None）
    #   ]
    #   戻り値: [result: ゲーム・データ取得先のスキル・識別子一覧・atを求めるための結果（list[str]）]
    # }
    def skill_ids_at(self, species_id: str, level: int, plus_choices: list[str] | None = None) -> list[str]:
        bundle = self.get_species(species_id)
        learned = [
            str(entry["skill_id"])
            for entry in bundle.skills.get("learnset", [])
            if int(entry.get("level", 1)) <= int(level)
        ]
        chosen = set(plus_choices or [])
        for stage in bundle.plus.get("stages", []):
            for option in stage.get("options", []):
                if option.get("id") in chosen and option.get("kind") == "skill":
                    learned.append(str(option["skill_id"]))
        return list(dict.fromkeys(learned))

    # {
    #   責務: [get_skills: スキル一覧を取得する]
    #   処理: [1: スキル一覧を取得する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: スキル一覧を取得するための結果（dict[str, dict[str, Any]]）]
    # }
    def get_skills(self) -> dict[str, dict[str, Any]]:
        payload = read_json(self.root / "skills" / "skills.json")
        return {str(item["id"]): item for item in payload["skills"]}

    # {
    #   責務: [get_equipment: 装備を取得する]
    #   処理: [1: 装備を取得する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 装備を取得するための結果（dict[str, dict[str, Any]]）]
    # }
    def get_equipment(self) -> dict[str, dict[str, Any]]:
        payload = read_json(self.root / "equipment" / "equipment.json")
        return {str(item["id"]): item for item in payload["equipment"]}

