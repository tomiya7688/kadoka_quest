from __future__ import annotations

import heapq

from kadoka_engine.field_engine import FieldEngine


class ChaseTraffic:
    """Bounded local path selection with soft reservations and expiring trails."""

    def __init__(self, field: FieldEngine) -> None:
        self.field = field
        self.now = 0
        self.reserved: dict[tuple[int, int], set[int]] = {}
        self.recent: dict[tuple[int, int], tuple[int, int]] = {}
        self.plans: dict[int, tuple[list[tuple[int, int]], int]] = {}

    def clear(self) -> None:
        self.reserved.clear()
        self.recent.clear()
        self.plans.clear()

    def begin(self, now: int, owners: set[int]) -> None:
        if now < self.now:
            self.clear()
        self.now = int(now)
        self.recent = {p: entry for p, entry in self.recent.items() if entry[1] > now and entry[0] in owners}
        self.plans = {owner: entry for owner, entry in self.plans.items() if entry[1] > now and owner in owners}
        self.reserved.clear()
        for owner, (path, _) in self.plans.items():
            for position in path:
                self.reserved.setdefault(position, set()).add(owner)

    def release(self, owner: int) -> None:
        self.plans.pop(owner, None)
        for position in list(self.reserved):
            self.reserved[position].discard(owner)
            if not self.reserved[position]:
                del self.reserved[position]

    def record(self, owner: int, position: tuple[int, int]) -> None:
        self.recent[position] = (owner, self.now + 1280)

    def _cost(self, position: tuple[int, int], owner: int, occupied: set[tuple[int, int]]) -> float:
        cost = 1.0 + (3.0 if position in occupied else 0.0)
        if self.reserved.get(position, set()) - {owner}:
            cost += 2.0
        trail = self.recent.get(position)
        if trail and trail[0] != owner:
            cost += 0.4
        return cost

    def plan(
        self, owner: int, start: tuple[int, int], target: tuple[int, int],
        occupied: set[tuple[int, int]], fixed: set[tuple[int, int]], interval: int,
    ) -> tuple[int, int]:
        """Return one safe step; future occupancy is soft so corridors can flow."""
        self.release(owner)
        path = self._search(owner, start, target, occupied, fixed)
        if not path:
            return start
        reserved_path = path[:3]
        self.plans[owner] = (reserved_path, self.now + interval)
        for position in reserved_path:
            self.reserved.setdefault(position, set()).add(owner)
        return path[0]

    def _search(
        self, owner: int, start: tuple[int, int], target: tuple[int, int],
        occupied: set[tuple[int, int]], fixed: set[tuple[int, int]],
    ) -> list[tuple[int, int]]:
        def remaining(position: tuple[int, int]) -> int:
            return max(0, abs(position[0] - target[0]) + abs(position[1] - target[1]) - 1)

        if remaining(start) == 0:
            return []
        # Two tiles of detour margin; at most 256 expanded nodes per actor.
        left, right = min(start[0], target[0]) - 2, max(start[0], target[0]) + 2
        top, bottom = min(start[1], target[1]) - 2, max(start[1], target[1]) + 2
        queue = [(float(remaining(start)), 0.0, start)]
        costs = {start: 0.0}
        previous: dict[tuple[int, int], tuple[int, int]] = {}
        expanded = 0
        while queue and expanded < 256:
            _, cost, position = heapq.heappop(queue)
            if cost != costs[position]:
                continue
            expanded += 1
            if remaining(position) == 0:
                path = []
                while position != start:
                    path.append(position)
                    position = previous[position]
                return list(reversed(path))
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                next_position = (position[0] + dx, position[1] + dy)
                x, y = next_position
                if not (left <= x <= right and top <= y <= bottom):
                    continue
                if next_position == target or next_position in fixed:
                    continue
                if position == start and next_position in occupied:
                    continue
                if not self.field.tile_allows(x, y, "enemy_walkable"):
                    continue
                next_cost = cost + self._cost(next_position, owner, occupied)
                if next_cost >= costs.get(next_position, float("inf")):
                    continue
                costs[next_position] = next_cost
                previous[next_position] = position
                heapq.heappush(queue, (next_cost + remaining(next_position), next_cost, next_position))
        return []
