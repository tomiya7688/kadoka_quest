from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable

from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.jsonio import read_json, write_json
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.repository import GameRepository


class SimulationRosterService:
    """Owns simulation-only monsters and one pending battle request."""

    def __init__(self, root: Path, repository: GameRepository, import_root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.repository = repository
        self.store = MonsterStore(self.root, repository)
        self.import_root = Path(import_root)
        self.request_path = self.root / "battle_request.json"

    def list_records(self) -> list[MonsterRecord]:
        return self.store.list_records()

    def create(self, species_id: str, *, level: int = 1, name: str | None = None) -> MonsterRecord:
        return self.store.create(species_id, name=name, level=level, source="simulation")

    def delete(self, monster_id: str) -> None:
        self.store.delete(monster_id)

    def import_external(self) -> tuple[int, int]:
        existing = {record.monster_id for record in self.list_records()}
        added = 0
        skipped = 0
        if not self.import_root.exists():
            return 0, 0
        for monster_path in sorted(self.import_root.rglob("monster.json")):
            ai_path = monster_path.parent / "ai.json"
            if not ai_path.is_file():
                skipped += 1
                continue
            try:
                record = MonsterRecord(read_json(monster_path), read_json(ai_path))
                self.repository.get_species(record.species_id)
            except (OSError, ValueError, KeyError):
                skipped += 1
                continue
            if record.monster_id in existing:
                skipped += 1
                continue
            shutil.copytree(monster_path.parent, self.root / record.monster_id)
            existing.add(record.monster_id)
            added += 1
        return added, skipped

    def request_battle(self, monster_ids: Iterable[str]) -> None:
        selected: list[str] = []
        for monster_id in monster_ids:
            value = str(monster_id)
            if value in selected:
                continue
            if self.store.get(value) is None:
                raise KeyError(value)
            selected.append(value)
            if len(selected) == 4:
                break
        if not selected:
            raise ValueError("模擬戦の相手を1体以上選んでください。")
        write_json(self.request_path, {"schema_version": 1, "opponents": selected})

    def consume_battle_request(self) -> list[MonsterRecord]:
        if not self.request_path.is_file():
            return []
        try:
            data = read_json(self.request_path)
        finally:
            self.request_path.unlink(missing_ok=True)
        result: list[MonsterRecord] = []
        for monster_id in data.get("opponents", [])[:4]:
            record = self.store.get(str(monster_id))
            if record is not None:
                result.append(record)
        return result
