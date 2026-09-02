from __future__ import annotations

import random

from kadoka_quest.core.field_engine import FieldEngine


class HiddenEnemyController:
    """Own invisible field-enemy population, vision, and timed movement."""

    def __init__(
        self,
        field: FieldEngine,
        rng: random.Random,
        chase_interval_ms: int = 320,
        wander_interval_ms: int = 950,
        vision_range: int = 8,
    ) -> None:
        self.field = field
        self.rng = rng
        self.chase_interval_ms = max(1, int(chase_interval_ms))
        self.wander_interval_ms = max(1, int(wander_interval_ms))
        self.vision_range = max(0, int(vision_range))
        self.monsters: list[dict] = []
        self.map_data: dict = {}
        self.blocks: dict[str, dict] = {}

    def set_world(self, map_data: dict, blocks: dict[str, dict]) -> None:
        self.map_data = map_data
        self.blocks = blocks
        self.field.set_world(map_data, blocks)

    def spawn_options(self, flags: dict) -> list[dict]:
        return [
            entry
            for entry in self.map_data.get("spawns", [])
            if entry.get("species_id") != "ball_slime"
            and (not entry.get("requires_flag") or flags.get(entry["requires_flag"], False))
        ]

    def reset(self, player_position: tuple[int, int], flags: dict, now: int) -> None:
        self.monsters = []
        options = self.spawn_options(flags)
        if not options:
            return
        player = (int(player_position[0]), int(player_position[1]))
        spawn_tiles = [
            (x, y)
            for y, row in enumerate(self.map_data["tiles"])
            for x, block_id in enumerate(row)
            if self.blocks.get(block_id, {}).get("enemy_spawnable")
            and self.blocks.get(block_id, {}).get("enemy_walkable")
            and (x, y) != player
        ]
        self.rng.shuffle(spawn_tiles)
        population = min(
            len(spawn_tiles),
            max(12, min(24, int(self.map_data["width"] * self.map_data["height"]) // 60)),
        )
        weights = [int(item.get("weight", 1)) for item in options]
        for x, y in spawn_tiles[:population]:
            spawn = self.rng.choices(options, weights=weights)[0]
            self.monsters.append(
                {
                    "x": x,
                    "y": y,
                    "spawn": dict(spawn),
                    "next_move_tick": int(now) + self.wander_interval_ms,
                }
            )

    def find_at(self, position: tuple[int, int]) -> dict | None:
        return next(
            (
                monster
                for monster in self.monsters
                if (int(monster["x"]), int(monster["y"]))
                == (int(position[0]), int(position[1]))
            ),
            None,
        )

    def remove(self, monster: dict) -> bool:
        if monster not in self.monsters:
            return False
        self.monsters.remove(monster)
        return True

    def sees_player(self, monster: dict, player_position: tuple[int, int]) -> bool:
        monster_x, monster_y = int(monster["x"]), int(monster["y"])
        player_x, player_y = (int(value) for value in player_position)
        if monster_x != player_x and monster_y != player_y:
            return False
        distance = abs(monster_x - player_x) + abs(monster_y - player_y)
        if distance > self.vision_range:
            return False
        return self.field.has_clear_axis_path(
            (monster_x, monster_y),
            (player_x, player_y),
            "enemy_walkable",
        )

    def move(
        self,
        monster: dict,
        player_position: tuple[int, int],
        visible_positions: set[tuple[int, int]],
    ) -> bool:
        sees_player = self.sees_player(monster, player_position)
        monster_x, monster_y = int(monster["x"]), int(monster["y"])
        player_x, player_y = (int(value) for value in player_position)
        if sees_player:
            dx = 0 if monster_x == player_x else (1 if player_x > monster_x else -1)
            dy = 0 if monster_y == player_y else (1 if player_y > monster_y else -1)
            directions = [(dx, dy), (0, 0)]
        else:
            directions = [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]
            self.rng.shuffle(directions)
        occupied = {(player_x, player_y)} | visible_positions | {
            (int(other["x"]), int(other["y"])) for other in self.monsters if other is not monster
        }
        for dx, dy in directions:
            x, y = monster_x + dx, monster_y + dy
            if self.field.tile_allows(x, y, "enemy_walkable") and (x, y) not in occupied:
                monster["x"], monster["y"] = x, y
                monster["sees_player"] = sees_player
                return bool(dx or dy)
        monster["sees_player"] = sees_player
        return False

    def move_all(
        self,
        player_position: tuple[int, int],
        visible_positions: set[tuple[int, int]],
    ) -> bool:
        moved = False
        for monster in list(self.monsters):
            moved = self.move(monster, player_position, visible_positions) or moved
        return moved

    def update(
        self,
        player_position: tuple[int, int],
        visible_positions: set[tuple[int, int]],
        now: int,
    ) -> bool:
        moved = False
        for monster in list(self.monsters):
            if int(now) < int(monster.get("next_move_tick", 0)):
                continue
            moved = self.move(monster, player_position, visible_positions) or moved
            interval = self.chase_interval_ms if monster.get("sees_player") else self.wander_interval_ms
            monster["next_move_tick"] = int(now) + interval
        return moved
