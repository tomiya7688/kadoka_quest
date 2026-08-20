from __future__ import annotations

from pathlib import Path
from typing import Any

from kadoka_quest.data.jsonio import read_json, write_json
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.paths import SAVE_ROOT


DEFAULT_STATE: dict[str, Any] = {
    "schema_version": 1,
    "map_id": "starting_town",
    "player": {"x": 18, "y": 14},
    "revive_point": {"map_id": "starting_town", "x": 18, "y": 11, "name": "はじまりの街の教会"},
    "current_party": [],
    "inventory": {"orange": 3},
    "flags": {"story_complete": False, "ghost_entrance_open": False},
}


class StateStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or (SAVE_ROOT / "state.json"))

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {
                **DEFAULT_STATE,
                "player": dict(DEFAULT_STATE["player"]),
                "revive_point": dict(DEFAULT_STATE["revive_point"]),
                "current_party": [],
                "inventory": dict(DEFAULT_STATE["inventory"]),
                "flags": dict(DEFAULT_STATE["flags"]),
            }
        state = read_json(self.path)
        item_path = self.path.parent / "items" / "items.json"
        if item_path.exists():
            state["inventory"] = dict(read_json(item_path).get("items", {}))
        for key, default in DEFAULT_STATE.items():
            state.setdefault(key, default.copy() if isinstance(default, dict) else list(default) if isinstance(default, list) else default)
        return state

    def save(self, state: dict[str, Any]) -> None:
        payload = dict(state)
        inventory = dict(payload.pop("inventory", {}))
        write_json(self.path, payload)
        write_json(self.path.parent / "items" / "items.json", {"schema_version": 1, "items": inventory})

    def ensure_starters(self, state: dict[str, Any], monsters: MonsterStore) -> None:
        hero = monsters.ensure_species("hero", "主人公")
        ball = monsters.ensure_species("ball_slime", "ボールスライム")
        valid = [record.monster_id for record in monsters.list_records()]
        current = [item for item in state.get("current_party", []) if item in valid]
        for record in (hero, ball):
            if record.monster_id not in current and len(current) < 4:
                current.append(record.monster_id)
        state["current_party"] = current[:4]
        self.save(state)

    @staticmethod
    def party_records(state: dict[str, Any], monsters: MonsterStore) -> list:
        return [record for monster_id in state.get("current_party", []) if (record := monsters.get(str(monster_id)))]

