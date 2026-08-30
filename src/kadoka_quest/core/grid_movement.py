from __future__ import annotations


class GridMovement:
    def __init__(self, x: float, y: float, duration_ms: int = 120) -> None:
        self.duration_ms = max(1, int(duration_ms))
        self.start_x = self.target_x = float(x)
        self.start_y = self.target_y = float(y)
        self.start_time_ms = 0
        self.moving = False

    def snap(self, x: float, y: float) -> None:
        self.start_x = self.target_x = float(x)
        self.start_y = self.target_y = float(y)
        self.moving = False

    def move_to(self, x: float, y: float, now_ms: int) -> None:
        current_x, current_y = self.position(now_ms)
        self.start_x, self.start_y = current_x, current_y
        self.target_x, self.target_y = float(x), float(y)
        self.start_time_ms = int(now_ms)
        self.moving = (self.start_x, self.start_y) != (self.target_x, self.target_y)

    def position(self, now_ms: int) -> tuple[float, float]:
        if not self.moving:
            return self.target_x, self.target_y
        progress = max(0.0, min(1.0, (int(now_ms) - self.start_time_ms) / self.duration_ms))
        eased = progress * progress * (3.0 - 2.0 * progress)
        x = self.start_x + (self.target_x - self.start_x) * eased
        y = self.start_y + (self.target_y - self.start_y) * eased
        if progress >= 1.0:
            self.snap(self.target_x, self.target_y)
        return x, y
