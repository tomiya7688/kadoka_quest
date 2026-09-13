from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
import random

from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.jsonio import read_json, write_json
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.repository import GameRepository


class SimulationFacilityService:
    """Own the isolated roster used by the in-world simulation facility."""

    def __init__(
        self,
        repository: GameRepository,
        simulation_root: Path,
        battle_factory: Callable[..., BattleEngine] = BattleEngine,
    ) -> None:
        self.repository = repository
        self.root = Path(simulation_root)
        self.store = MonsterStore(self.root, repository)
        self.party_path = self.root / "simulation_party.json"
        self.battle_factory = battle_factory

    def list_individuals(self) -> list[MonsterRecord]:
        return self.store.list_records()

    def create_individual(self, species_id: str, level: int = 1, name: str | None = None) -> MonsterRecord:
        return self.store.create(species_id, name=name, level=level, source="simulation_facility")

    def delete_individual(self, monster_id: str) -> bool:
        if self.store.get(monster_id) is None:
            return False
        self.store.delete(monster_id)
        self._save_opponent_ids([item for item in self.opponent_ids() if item != monster_id])
        return True

    def opponent_ids(self) -> list[str]:
        try:
            value = read_json(self.party_path)
            identifiers = value.get("monster_ids", [])
        except (OSError, ValueError, TypeError):
            return []
        if not isinstance(identifiers, list):
            return []
        return [str(identifier) for identifier in identifiers]

    def set_opponents(self, monster_ids: Sequence[str]) -> list[MonsterRecord]:
        records = {record.monster_id: record for record in self.list_individuals()}
        unique_ids = list(dict.fromkeys(str(identifier) for identifier in monster_ids))
        selected = [records[identifier] for identifier in unique_ids if identifier in records]
        if not selected:
            raise ValueError("模擬戦相手を1体以上選択してください。")
        self._save_opponent_ids([record.monster_id for record in selected])
        return selected

    def clear_opponents(self) -> None:
        self._save_opponent_ids([])

    def opponents(self) -> list[MonsterRecord]:
        records = {record.monster_id: record for record in self.list_individuals()}
        return [records[identifier] for identifier in self.opponent_ids() if identifier in records]

    def create_battle(
        self, allies: Sequence[MonsterRecord], rng: random.Random
    ) -> tuple[BattleEngine | None, str]:
        opponents = self.opponents()
        if not opponents:
            return None, "模擬戦施設で相手パーティを編成してください。"
        try:
            battle = self.battle_factory(
                self.repository, list(allies), opponents, rng, learning_enabled=False
            )
        except (OSError, ValueError, KeyError) as exc:
            return None, f"模擬戦個体を読めません: {exc}"
        return battle, "模擬戦を開始。双方のAIは更新されず、報酬も発生しません。"

    def _save_opponent_ids(self, monster_ids: list[str]) -> None:
        write_json(self.party_path, {"schema_version": 1, "monster_ids": monster_ids})
