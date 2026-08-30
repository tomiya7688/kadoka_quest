from __future__ import annotations

from pathlib import Path
from typing import Any

from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.paths import IMPORT_ROOT, SAVE_ROOT


class DeveloperMonsterCreator:
    TARGETS = ("owned", "acquire", "simulation")

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

    @staticmethod
    def _validate_level(level: int) -> int:
        level = int(level)
        if not 1 <= level <= 100:
            raise ValueError("Level must be between 1 and 100")
        return level

    @staticmethod
    def _validate_optional_id(monster_id: str | None) -> str | None:
        value = str(monster_id or "").strip()
        if not value:
            return None
        allowed = "abcdefghijklmnopqrstuvwxyz0123456789_-"
        if any(character not in allowed for character in value):
            raise ValueError("Monster id may contain only lowercase letters, digits, _ and -")
        return value
