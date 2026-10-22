# {
#   責務: [developer_monster_creator: developer・モンスター・creatorの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from pathlib import Path
from typing import Any

from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.paths import IMPORT_ROOT, SAVE_ROOT


# {
#   責務: [DeveloperMonsterCreator: developer・モンスター・creatorの状態と振る舞いを担当する]
#   フィールド: [
#     TARGETS: 対象一覧
#     repository: データ取得先
#     output_roots: output・roots
#   ]
# }
class DeveloperMonsterCreator:
    TARGETS = ("owned", "acquire", "simulation")

    # {
    #   責務: [__init__: developer・モンスター・creatorが利用する初期状態と依存を設定する]
    #   処理: [1: developer・モンスター・creatorが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     repository: データ取得先（GameRepository | None）
    #     output_roots: output・roots（dict[str, Path] | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(
        self,
        repository: GameRepository | None = None,
        output_roots: dict[str, Path] | None = None,
    ) -> None:
        self.repository = repository or GameRepository()
        self.output_roots = output_roots or {
            "owned": SAVE_ROOT / "monsters",
            "acquire": IMPORT_ROOT / "acquire",
            "simulation": IMPORT_ROOT / "simulation",
        }

    # {
    #   責務: [preview: developer・モンスター・creatorをプレビューする]
    #   処理: [1: developer・モンスター・creatorをプレビューする]
    #   引数: [
    #     self: 処理対象インスタンス
    #     species_id: 種族・識別子（str）
    #     level: レベル（int）
    #   ]
    #   戻り値: [result: developer・モンスター・creatorをプレビューするための結果（dict[str, Any]）]
    # }
    def preview(self, species_id: str, level: int) -> dict[str, Any]:
        level = self._validate_level(level)
        bundle = self.repository.get_species(species_id)
        return {
            "species_id": species_id,
            "display_name": str(bundle.definition.get("display_name", species_id)),
            "level": level,
            "stats": self.repository.stats_at(species_id, level),
            "skill_ids": self.repository.skill_ids_at(species_id, level),
        }

    # {
    #   責務: [create: developer・モンスター・creatorを作成する]
    #   処理: [1: developer・モンスター・creatorを作成する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     species_id: 種族・識別子（str）
    #     level: レベル（int）
    #     name: 名前（str）
    #     target: 対象（str）
    #     monster_id: モンスター・識別子（str | None）
    #   ]
    #   戻り値: [result: developer・モンスター・creatorを作成するための結果（tuple[MonsterRecord, Path]）]
    # }
    def create(
        self,
        species_id: str,
        level: int,
        name: str,
        target: str,
        monster_id: str | None = None,
    ) -> tuple[MonsterRecord, Path]:
        level = self._validate_level(level)
        target = str(target)
        if target not in self.TARGETS or target not in self.output_roots:
            raise ValueError(f"Unknown developer output target: {target}")
        clean_name = str(name).strip()
        if not clean_name:
            clean_name = str(self.repository.get_species(species_id).definition["display_name"])
        clean_id = self._validate_optional_id(monster_id)
        store = MonsterStore(self.output_roots[target], self.repository)
        record = store.create(
            species_id,
            name=clean_name,
            level=level,
            source=f"developer_{target}",
            monster_id=clean_id,
        )
        return record, store.root / record.monster_id

    # {
    #   責務: [_validate_level: レベルを妥当性を検査する]
    #   処理: [1: レベルを妥当性を検査する]
    #   引数: [level: レベル（int）]
    #   戻り値: [result: レベル（int）]
    # }
    @staticmethod
    def _validate_level(level: int) -> int:
        level = int(level)
        if not 1 <= level <= 100:
            raise ValueError("Level must be between 1 and 100")
        return level

    # {
    #   責務: [_validate_optional_id: optional・識別子を妥当性を検査する]
    #   処理: [1: optional・識別子を妥当性を検査する]
    #   引数: [monster_id: モンスター・識別子（str | None）]
    #   戻り値: [result: optional・識別子を妥当性を検査するための結果（str | None）]
    # }
    @staticmethod
    def _validate_optional_id(monster_id: str | None) -> str | None:
        value = str(monster_id or "").strip()
        if not value:
            return None
        allowed = "abcdefghijklmnopqrstuvwxyz0123456789_-"
        if any(character not in allowed for character in value):
            raise ValueError("Monster id may contain only lowercase letters, digits, _ and -")
        return value
