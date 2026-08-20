from __future__ import annotations

import re
from pathlib import Path

from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.jsonio import read_json, write_json
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.paths import SAVE_ROOT


class PartyStore:
    """Unlimited preset files. A playable party still has four positions."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root or (SAVE_ROOT / "parties"))
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _slug(name: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", name).strip("_").lower()
        return slug or "party"

    def save(self, name: str, member_ids: list[str | None], overwrite: bool = False) -> Path:
        base = self._slug(name)
        path = self.root / f"{base}.json"
        if path.exists() and not overwrite:
            index = 2
            while (self.root / f"{base}_{index}.json").exists():
                index += 1
            path = self.root / f"{base}_{index}.json"
        write_json(
            path,
            {
                "schema_version": 1,
                "name": name,
                "members": list(member_ids[:4]) + [None] * max(0, 4 - len(member_ids)),
            },
        )
        return path

    def list_presets(self) -> list[Path]:
        return sorted(self.root.glob("*.json"))

    def update(self, path: Path, name: str, member_ids: list[str | None]) -> None:
        if Path(path).parent.resolve() != self.root.resolve():
            raise ValueError("Preset must be inside the party directory")
        write_json(
            Path(path),
            {
                "schema_version": 1,
                "name": name,
                "members": list(member_ids[:4]) + [None] * max(0, 4 - len(member_ids)),
            },
        )

    def load(self, path: Path, monsters: MonsterStore) -> list[MonsterRecord | None]:
        data = read_json(path)
        result: list[MonsterRecord | None] = []
        for monster_id in list(data.get("members", []))[:4]:
            result.append(monsters.get(str(monster_id)) if monster_id else None)
        return result + [None] * (4 - len(result))

