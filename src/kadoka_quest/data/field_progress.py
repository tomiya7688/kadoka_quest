from __future__ import annotations

from kadoka_quest.data.state import StateStore


class FieldProgressStore:
    """Persist field position, revival, inventory, flags, and despawn progress."""

    def __init__(self, states: StateStore) -> None:
        self.states = states

    def save_position(self, state: dict, map_id: str, x: int, y: int) -> None:
        state["map_id"] = str(map_id)
        state["player"] = {"x": int(x), "y": int(y)}
        self.states.save(state)

    def register_church(self, state: dict, revive: dict) -> None:
        state["revive_point"] = dict(revive)
        self.states.save(state)

    def add_item(self, state: dict, item_id: str, amount: int = 1) -> int:
        inventory = state.setdefault("inventory", {})
        inventory[str(item_id)] = int(inventory.get(str(item_id), 0)) + int(amount)
        self.states.save(state)
        return int(inventory[str(item_id)])

    def set_flag(self, state: dict, flag_id: str, value: bool) -> None:
        state.setdefault("flags", {})[str(flag_id)] = bool(value)
        self.states.save(state)

    def mark_despawned(self, state: dict, key: str) -> bool:
        despawned = state.setdefault("despawned_fixed_mobs", [])
        if str(key) in despawned:
            return False
        despawned.append(str(key))
        self.states.save(state)
        return True

    @staticmethod
    def revive_point(state: dict) -> dict:
        return dict(
            state.get(
                "revive_point",
                {"map_id": "starting_town", "x": 18, "y": 11, "name": "はじまりの街の教会"},
            )
        )
