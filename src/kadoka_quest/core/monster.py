from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kadoka_quest.data.repository import GameRepository, STAT_KEYS


@dataclass
class MonsterRecord:
    monster: dict[str, Any]
    ai: dict[str, Any]

    @property
    def monster_id(self) -> str:
        return str(self.monster["id"])

    @property
    def species_id(self) -> str:
        return str(self.monster["species_id"])

    @property
    def name(self) -> str:
        return str(self.monster["name"])

    @property
    def level(self) -> int:
        return int(self.monster.get("level", 1))

    @property
    def plus_choices(self) -> list[str]:
        return [str(item) for item in self.monster.get("plus_choices", [])]

    @property
    def equipment_id(self) -> str | None:
        value = self.monster.get("equipment_id")
        return str(value) if value else None


def calculate_stats(repository: GameRepository, record: MonsterRecord) -> dict[str, int]:
    stats = repository.stats_at(record.species_id, record.level)
    bundle = repository.get_species(record.species_id)
    selected = set(record.plus_choices)

    for stage in bundle.plus.get("stages", []):
        for option in stage.get("options", []):
            if option.get("id") not in selected:
                continue
            kind = option.get("kind")
            stat = option.get("stat")
            if stat not in STAT_KEYS:
                continue
            if kind == "stat_add":
                stats[stat] += int(option.get("value", 0))
            elif kind == "stat_multiplier":
                stats[stat] = round(stats[stat] * float(option.get("value", 1.0)))

    if record.equipment_id:
        equipment = repository.get_equipment().get(record.equipment_id)
        if equipment:
            allowed = set(bundle.definition.get("equipment_categories", []))
            if equipment.get("category") in allowed:
                for stat, multiplier in equipment.get("stat_multipliers", {}).items():
                    if stat in stats:
                        stats[stat] = round(stats[stat] * float(multiplier))

    return {key: max(1, int(stats[key])) for key in STAT_KEYS}


def available_skill_ids(repository: GameRepository, record: MonsterRecord) -> list[str]:
    return repository.skill_ids_at(record.species_id, record.level, record.plus_choices)


