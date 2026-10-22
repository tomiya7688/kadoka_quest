# {
#   責務: [chase_traffic: chase・trafficの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import heapq

from kadoka_engine.field_engine import FieldEngine


# {
#   責務: [ChaseTraffic: Bounded local path selection with soft reservations and expiring trails.]
#   フィールド: [
#     field: フィールド
#     now: 現在時刻
#     reserved: reserved（dict[tuple[int, int], set[int]]）
#     recent: recent
#     plans: plans
#   ]
# }
class ChaseTraffic:
    """Bounded local path selection with soft reservations and expiring trails."""

    # {
    #   責務: [__init__: chase・trafficが利用する初期状態と依存を設定する]
    #   処理: [1: chase・trafficが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     field: フィールド（FieldEngine）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, field: FieldEngine) -> None:
        self.field = field
        self.now = 0
        self.reserved: dict[tuple[int, int], set[int]] = {}
        self.recent: dict[tuple[int, int], tuple[int, int]] = {}
        self.plans: dict[int, tuple[list[tuple[int, int]], int]] = {}

    # {
    #   責務: [clear: chase・trafficを消去する]
    #   処理: [1: chase・trafficを消去する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def clear(self) -> None:
        self.reserved.clear()
        self.recent.clear()
        self.plans.clear()

    # {
    #   責務: [begin: chase・trafficを開始する]
    #   処理: [1: chase・trafficを開始する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     now: 現在時刻（int）
    #     owners: owners（set[int]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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

    # {
    #   責務: [release: chase・trafficのreleaseを求める]
    #   処理: [1: chase・trafficのreleaseを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     owner: owner（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def release(self, owner: int) -> None:
        self.plans.pop(owner, None)
        for position in list(self.reserved):
            self.reserved[position].discard(owner)
            if not self.reserved[position]:
                del self.reserved[position]

    # {
    #   責務: [record: chase・trafficの個体レコードを求める]
    #   処理: [1: chase・trafficの個体レコードを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     owner: owner（int）
    #     position: 座標（tuple[int, int]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def record(self, owner: int, position: tuple[int, int]) -> None:
        self.recent[position] = (owner, self.now + 1280)

    # {
    #   責務: [_cost: chase・trafficの消費量を求める]
    #   処理: [1: chase・trafficの消費量を求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     position: 座標（tuple[int, int]）
    #     owner: owner（int）
    #     occupied: occupied（set[tuple[int, int]]）
    #   ]
    #   戻り値: [result: 消費量（float）]
    # }
    def _cost(self, position: tuple[int, int], owner: int, occupied: set[tuple[int, int]]) -> float:
        cost = 1.0 + (3.0 if position in occupied else 0.0)
        if self.reserved.get(position, set()) - {owner}:
            cost += 2.0
        trail = self.recent.get(position)
        if trail and trail[0] != owner:
            cost += 0.4
        return cost

    # {
    #   責務: [plan: Return one safe step; future occupancy is soft so corridors can flow.]
    #   処理: [1: Return one safe step; future occupancy is soft so corridors can flow.]
    #   引数: [
    #     self: 処理対象インスタンス
    #     owner: owner（int）
    #     start: start（tuple[int, int]）
    #     target: 対象（tuple[int, int]）
    #     occupied: occupied（set[tuple[int, int]]）
    #     fixed: fixed（set[tuple[int, int]]）
    #     interval: interval（int）
    #   ]
    #   戻り値: [result: Return one safe step; future occupancy is soft so corridors can flow.ための結果（tuple[int, int]）]
    # }
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

    # {
    #   責務: [_search: chase・trafficのsearchを求める]
    #   処理: [1: chase・trafficのsearchを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     owner: owner（int）
    #     start: start（tuple[int, int]）
    #     target: 対象（tuple[int, int]）
    #     occupied: occupied（set[tuple[int, int]]）
    #     fixed: fixed（set[tuple[int, int]]）
    #   ]
    #   戻り値: [result: chase・trafficのsearchを求めるための結果（list[tuple[int, int]]）]
    # }
    def _search(
        self, owner: int, start: tuple[int, int], target: tuple[int, int],
        occupied: set[tuple[int, int]], fixed: set[tuple[int, int]],
    ) -> list[tuple[int, int]]:
        # {
        #   責務: [remaining: chase・trafficのremainingを求める]
        #   処理: [1: chase・trafficのremainingを求める]
        #   引数: [position: 座標（tuple[int, int]）]
        #   戻り値: [result: chase・trafficのremainingを求めるための結果（int）]
        # }
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
