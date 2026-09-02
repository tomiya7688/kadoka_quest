from __future__ import annotations

from kadoka_quest.core.field_engine import FieldEngine
from kadoka_quest.core.grid_movement import GridMovement


class PlayerFieldController:
    """Own player grid position, facing, held movement, and visual interpolation."""

    DIRECTIONS = {
        "left": (-1, 0),
        "right": (1, 0),
        "back": (0, -1),
        "front": (0, 1),
    }

    def __init__(
        self,
        x: int,
        y: int,
        movement_duration_ms: int = 120,
        repeat_delay_ms: int = 180,
        repeat_interval_ms: int = 90,
    ) -> None:
        self.x = int(x)
        self.y = int(y)
        self.direction = "front"
        self.visual = GridMovement(self.x, self.y, movement_duration_ms)
        self.repeat_delay_ms = max(1, int(repeat_delay_ms))
        self.repeat_interval_ms = max(1, int(repeat_interval_ms))
        self.held_direction: str | None = None
        self.next_move_tick = 0

    def snap(self, x: int, y: int) -> None:
        self.x = int(x)
        self.y = int(y)
        self.visual.snap(self.x, self.y)

    def attempt_move(
        self,
        field: FieldEngine,
        dx: int,
        dy: int,
        visible_characters: list[dict],
        hidden_characters: list[dict],
        now: int,
    ) -> dict:
        result = field.resolve_player_move(
            self.x,
            self.y,
            int(dx),
            int(dy),
            self.direction,
            visible_characters,
            hidden_characters,
        )
        self.direction = str(result["direction"])
        if result["kind"] == "moved":
            self.x, self.y = int(result["x"]), int(result["y"])
            self.visual.move_to(self.x, self.y, int(now))
        return result

    def begin_hold(self, direction: str, now: int) -> tuple[int, int] | None:
        vector = self.DIRECTIONS.get(str(direction))
        if vector is None:
            return None
        self.held_direction = str(direction)
        self.next_move_tick = int(now) + self.repeat_delay_ms
        return vector

    def stop_hold(self, direction: str) -> bool:
        if str(direction) != self.held_direction:
            return False
        self.clear_hold()
        return True

    def clear_hold(self) -> None:
        self.held_direction = None

    def repeated_vector(self, now: int) -> tuple[int, int] | None:
        vector = self.DIRECTIONS.get(str(self.held_direction))
        if vector is None:
            self.clear_hold()
            return None
        if int(now) < self.next_move_tick:
            return None
        self.next_move_tick = int(now) + self.repeat_interval_ms
        return vector
