from __future__ import annotations

import random
from collections.abc import Callable

from kadoka_quest.core.field_engine import FieldEngine
from kadoka_quest.core.grid_movement import GridMovement


class FixedMobController:
    """Own the runtime state and movement rules of visible fixed mobs."""

    def __init__(
        self,
        field: FieldEngine,
        rng: random.Random,
        movement_duration_ms: int = 180,
    ) -> None:
        self.field = field
        self.rng = rng
        self.movement_duration_ms = max(1, int(movement_duration_ms))
        self.npcs: list[dict] = []

    def reset(
        self,
        map_data: dict,
        blocks: dict[str, dict],
        despawned: set[str],
        player_position: tuple[int, int],
        now: int,
        species_name: Callable[[str], str],
    ) -> None:
        self.field.set_world(map_data, blocks)
        self.npcs = []
        for source in map_data.get("fixed_mobs", []):
            key = f"{map_data['id']}:{source.get('id', '')}"
            if not source.get("enabled", True) or (
                not source.get("respawn_on_map_enter", True) and key in despawned
            ):
                continue
            npc = dict(source)
            npc.setdefault("id", f"fixed_mob_{len(self.npcs) + 1}")
            npc.setdefault("name", species_name(str(npc["species_id"])))
            npc.setdefault("direction", "front")
            npc.setdefault("ai", "idle")
            npc.setdefault("move_interval_ms", 900)
            npc.setdefault("move_chance", 100)
            npc.setdefault("dialogue", ["……"])
            npc["move_count"] = 0
            npc["next_move_tick"] = int(now) + max(100, int(npc["move_interval_ms"]))
            npc["dialogue_remaining"] = []
            npc["last_dialogue"] = None
            self.npcs.append(npc)

        occupied = {(int(player_position[0]), int(player_position[1]))}
        for npc in self.npcs:
            if (int(npc["x"]), int(npc["y"])) in occupied:
                replacement = next(
                    (
                        (x, y)
                        for y, row in enumerate(map_data["tiles"])
                        for x, block_id in enumerate(row)
                        if blocks.get(block_id, {}).get("player_walkable") and (x, y) not in occupied
                    ),
                    None,
                )
                if replacement:
                    npc["x"], npc["y"] = replacement
            occupied.add((int(npc["x"]), int(npc["y"])))
        for npc in self.npcs:
            npc["_movement"] = GridMovement(
                int(npc["x"]),
                int(npc["y"]),
                self.movement_duration_ms,
            )

    def find_at(self, x: int, y: int) -> dict | None:
        return next(
            (npc for npc in self.npcs if (int(npc["x"]), int(npc["y"])) == (int(x), int(y))),
            None,
        )

    def nearby(self, front_position: tuple[int, int]) -> dict | None:
        return self.find_at(*front_position)

    def next_dialogue(self, npc: dict) -> str:
        deck = [str(line).strip() for line in npc.get("dialogue", []) if str(line).strip()] or ["……"]
        remaining = npc.setdefault("dialogue_remaining", [])
        if not remaining:
            remaining.extend(deck)
            self.rng.shuffle(remaining)
            if len(remaining) > 1 and remaining[-1] == npc.get("last_dialogue"):
                remaining[0], remaining[-1] = remaining[-1], remaining[0]
        line = remaining.pop()
        npc["last_dialogue"] = line
        return line

    def remove(self, npc: dict) -> bool:
        if npc not in self.npcs:
            return False
        self.npcs.remove(npc)
        return True

    @staticmethod
    def front_position(npc: dict) -> tuple[int, int]:
        vectors = {"left": (-1, 0), "right": (1, 0), "back": (0, -1), "front": (0, 1)}
        dx, dy = vectors.get(str(npc.get("direction", "front")), (0, 1))
        return int(npc["x"]) + dx, int(npc["y"]) + dy

    def faces_player(self, npc: dict, player_position: tuple[int, int]) -> bool:
        return self.front_position(npc) == (int(player_position[0]), int(player_position[1]))

    def move(self, npc: dict, player_position: tuple[int, int], now: int) -> bool:
        ai = str(npc.get("ai", "idle"))
        if ai == "idle" or self.faces_player(npc, player_position):
            return False
        chance = max(0, min(100, int(npc.get("move_chance", 100))))
        if self.rng.randrange(100) >= chance:
            return False
        player_x, player_y = (int(value) for value in player_position)
        occupied = {(player_x, player_y)} | {
            (int(other["x"]), int(other["y"])) for other in self.npcs if other is not npc
        }
        if ai == "chase":
            mob_x, mob_y = int(npc["x"]), int(npc["y"])
            horizontal = (1 if player_x > mob_x else -1 if player_x < mob_x else 0, 0)
            vertical = (0, 1 if player_y > mob_y else -1 if player_y < mob_y else 0)
            directions = [direction for direction in (horizontal, vertical) if direction != (0, 0)]
            fallback = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            self.rng.shuffle(fallback)
            directions.extend(direction for direction in fallback if direction not in directions)
        else:
            directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            self.rng.shuffle(directions)
        for dx, dy in directions:
            x, y = int(npc["x"]) + dx, int(npc["y"]) + dy
            if self.field.tile_allows(x, y, "player_walkable") and (x, y) not in occupied:
                npc["x"], npc["y"] = x, y
                movement = npc.get("_movement")
                if not isinstance(movement, GridMovement):
                    movement = GridMovement(x - dx, y - dy, self.movement_duration_ms)
                    npc["_movement"] = movement
                movement.move_to(x, y, int(now))
                npc["move_count"] = int(npc.get("move_count", 0)) + 1
                npc["direction"] = FieldEngine.direction_for_step(dx, dy, str(npc.get("direction", "front")))
                return True
        return False

    def move_all(self, player_position: tuple[int, int], now: int) -> bool:
        moved = False
        for npc in self.npcs:
            moved = self.move(npc, player_position, now) or moved
        return moved

    def update(self, player_position: tuple[int, int], now: int) -> bool:
        moved = False
        for npc in self.npcs:
            interval = max(100, int(npc.get("move_interval_ms", 900)))
            if int(now) < int(npc.get("next_move_tick", 0)):
                continue
            moved = self.move(npc, player_position, now) or moved
            npc["next_move_tick"] = int(now) + interval
        return moved
