from __future__ import annotations

from typing import Any

from kadoka_quest.core.combatant import Combatant
from kadoka_quest.core.monster import MonsterRecord, available_skill_ids, calculate_stats, equipment_allows_species
from kadoka_quest.data.repository import GameRepository


class BattleDataLoader:
    """Loads combat-ready species, skill, resistance, stat and equipment data."""

    def __init__(self, repository: GameRepository) -> None:
        self.repository = repository
        self.skill_catalog = repository.get_skills()
        self.equipment_catalog = repository.get_equipment()

    def species_definition(self, species_id: str) -> dict[str, Any]:
        return self.repository.get_species(species_id).definition

    def build_combatant(self, record: MonsterRecord) -> Combatant:
        definition = self.species_definition(record.species_id)
        skill_ids = available_skill_ids(self.repository, record)
        skills = [self.skill_catalog[item] for item in skill_ids if item in self.skill_catalog]
        equipment = self.equipment_catalog.get(record.equipment_id or "")
        if equipment and not equipment_allows_species(equipment, record.species_id):
            equipment = None
        resistances = dict(definition.get("resistances", {}))
        if equipment:
            scale = ["weak", "normal", "strong", "immune", "absorb"]
            for element, steps in equipment.get("resistance_steps", {}).items():
                current = resistances.get(element, "normal")
                index = scale.index(current) if current in scale else 1
                resistances[element] = scale[max(0, min(len(scale) - 1, index + int(steps)))]
        return Combatant(record, calculate_stats(self.repository, record), skills, resistances, equipment)
