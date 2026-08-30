from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from kadoka_quest.core.ai import default_ai
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.jsonio import read_json, write_json
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.paths import SAVE_ROOT, ensure_runtime_directories


class MonsterStore:
    """One directory per individual. There is intentionally no ownership limit."""

    def __init__(self, root: Path | None = None, repository: GameRepository | None = None) -> None:
        if root is None:
            ensure_runtime_directories()
        self.root = Path(root or (SAVE_ROOT / "monsters"))
        self.root.mkdir(parents=True, exist_ok=True)
        self.repository = repository or GameRepository()

    def _folder(self, monster_id: str) -> Path:
        return self.root / monster_id

    def list_records(self) -> list[MonsterRecord]:
        records: list[MonsterRecord] = []
        for path in sorted(self.root.glob("*/monster.json")):
            try:
                record = MonsterRecord(read_json(path), read_json(path.parent / "ai.json"))
                self.repository.get_species(record.species_id)
            except (OSError, ValueError, KeyError):
                continue
            records.append(record)
        return records

    def get(self, monster_id: str) -> MonsterRecord | None:
        folder = self._folder(monster_id)
        try:
            return MonsterRecord(read_json(folder / "monster.json"), read_json(folder / "ai.json"))
        except (OSError, ValueError, KeyError):
            return None

    def create(
        self,
        species_id: str,
        name: str | None = None,
        level: int = 1,
        source: str = "game",
        monster_id: str | None = None,
    ) -> MonsterRecord:
        bundle = self.repository.get_species(species_id)
        monster_id = monster_id or f"monster_{uuid4().hex[:12]}"
        if self._folder(monster_id).exists():
            raise FileExistsError(monster_id)
        profile = str(bundle.definition.get("ai_profile", "normal"))
        monster = {
            "schema_version": 1,
            "id": monster_id,
            "species_id": species_id,
            "name": name or str(bundle.definition["display_name"]),
            "level": max(1, min(100, int(level))),
            "experience": 0,
            "plus_choices": [],
            "equipment_id": None,
            "source": source,
        }
        ai = default_ai(profile)
        write_json(self._folder(monster_id) / "monster.json", monster)
        write_json(self._folder(monster_id) / "ai.json", ai)
        return MonsterRecord(monster, ai)

    def save(self, record: MonsterRecord) -> None:
        write_json(self._folder(record.monster_id) / "monster.json", record.monster)
        write_json(self._folder(record.monster_id) / "ai.json", record.ai)

    def save_ai(self, monster_id: str, ai: dict) -> None:
        write_json(self._folder(monster_id) / "ai.json", ai)

    def reset_ai(self, monster_id: str) -> MonsterRecord:
        record = self.get(monster_id)
        if not record:
            raise KeyError(monster_id)
        profile = str(self.repository.get_species(record.species_id).definition.get("ai_profile", "normal"))
        record.ai = default_ai(profile, str(record.ai.get("tactic", "balanced")))
        self.save_ai(monster_id, record.ai)
        return record

    def set_tactic(self, monster_id: str, tactic: str) -> None:
        record = self.get(monster_id)
        if not record:
            raise KeyError(monster_id)
        record.ai["tactic"] = tactic
        self.save_ai(monster_id, record.ai)

    @staticmethod
    def discover_external(root: Path) -> list[MonsterRecord]:
        records: list[MonsterRecord] = []
        if not root.exists():
            return records
        for path in sorted(root.rglob("monster.json")):
            ai_path = path.parent / "ai.json"
            if not ai_path.exists():
                continue
            try:
                records.append(MonsterRecord(read_json(path), read_json(ai_path)))
            except (OSError, ValueError, KeyError):
                continue
        return records

    def acquire_from_scan(self, source_root: Path) -> tuple[int, int]:
        existing = {record.monster_id for record in self.list_records()}
        added = 0
        skipped = 0
        source_root = Path(source_root)
        if not source_root.exists():
            return 0, 0
        for monster_path in sorted(source_root.rglob("monster.json")):
            ai_path = monster_path.parent / "ai.json"
            if not ai_path.exists():
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
            shutil.copytree(monster_path.parent, self._folder(record.monster_id))
            existing.add(record.monster_id)
            added += 1
        return added, skipped

    def ensure_species(self, species_id: str, name: str | None = None) -> MonsterRecord:
        for record in self.list_records():
            if record.species_id == species_id:
                return record
        return self.create(species_id, name=name, source="starter")

    def delete(self, monster_id: str) -> None:
        folder = self._folder(monster_id)
        if folder.exists():
            shutil.rmtree(folder)

    def save_all_ai(self, records: Iterable[MonsterRecord]) -> None:
        owned = {record.monster_id for record in self.list_records()}
        for record in records:
            if record.monster_id in owned:
                self.save_ai(record.monster_id, record.ai)

