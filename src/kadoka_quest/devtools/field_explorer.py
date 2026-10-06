# {
#   責務: [field_explorer: フィールド・explorerの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from collections import deque
from typing import Any


# {
#   責務: [FieldExplorer: Choose reachable unexplored field events using plain map data only.]
#   フィールド: [DIRECTIONS: directions]
# }
class FieldExplorer:
    """Choose reachable unexplored field events using plain map data only."""

    DIRECTIONS = (("left", -1, 0), ("right", 1, 0), ("back", 0, -1), ("front", 0, 1))

    # {
    #   責務: [next_plan: planを次の値を求める]
    #   処理: [1: planを次の値を求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     map_data: マップ・データ（dict[str, Any]）
    #     blocks: ブロック定義（dict[str, dict[str, Any]]）
    #     player: 主人公（tuple[int, int]）
    #     visited_maps: visited・マップ一覧（set[str]）
    #     attempted_events: attempted・イベント一覧（set[str]）
    #   ]
    #   戻り値: [result: planを次の値を求めるための結果（dict[str, Any] | None）]
    # }
    def next_plan(
        self,
        map_data: dict[str, Any],
        blocks: dict[str, dict[str, Any]],
        player: tuple[int, int],
        visited_maps: set[str],
        attempted_events: set[str],
    ) -> dict[str, Any] | None:
        candidates: list[tuple[int, str, dict[str, Any]]] = []
        map_id = str(map_data["id"])
        for index, event in enumerate(map_data.get("events", [])):
            event_key = f"{map_id}:{event.get('id', index)}"
            if event_key in attempted_events:
                continue
            target_map = str(event.get("target", {}).get("map_id", ""))
            priority = 0 if event.get("type") == "transition" and target_map and target_map not in visited_maps else 1
            candidates.append((priority, event_key, event))
        for _priority, event_key, event in sorted(candidates, key=lambda item: (item[0], item[1])):
            path = self._path_to_event(map_data, blocks, player, event)
            if path is not None:
                return {"event_key": event_key, "event": dict(event), "directions": path}
        return None

    # {
    #   責務: [_path_to_event: フィールド・explorerのパス・to・イベントを求める]
    #   処理: [1: フィールド・explorerのパス・to・イベントを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     map_data: マップ・データ（dict[str, Any]）
    #     blocks: ブロック定義（dict[str, dict[str, Any]]）
    #     player: 主人公（tuple[int, int]）
    #     event: イベント（dict[str, Any]）
    #   ]
    #   戻り値: [result: フィールド・explorerのパス・to・イベントを求めるための結果（list[str] | None）]
    # }
    def _path_to_event(
        self,
        map_data: dict[str, Any],
        blocks: dict[str, dict[str, Any]],
        player: tuple[int, int],
        event: dict[str, Any],
    ) -> list[str] | None:
        event_position = (int(event["x"]), int(event["y"]))
        if event.get("activation", "interact") == "step":
            goals = {event_position}
        else:
            goals = {
                (event_position[0] + dx, event_position[1] + dy)
                for _direction, dx, dy in self.DIRECTIONS
                if self._walkable(map_data, blocks, event_position[0] + dx, event_position[1] + dy)
            }
            if self._walkable(map_data, blocks, *event_position):
                goals.add(event_position)
        return self._find_path(map_data, blocks, player, goals)

    # {
    #   責務: [_find_path: パスを探す]
    #   処理: [1: パスを探す]
    #   引数: [
    #     self: 処理対象インスタンス
    #     map_data: マップ・データ（dict[str, Any]）
    #     blocks: ブロック定義（dict[str, dict[str, Any]]）
    #     start: start（tuple[int, int]）
    #     goals: goals（set[tuple[int, int]]）
    #   ]
    #   戻り値: [result: パスを探すための結果（list[str] | None）]
    # }
    def _find_path(
        self,
        map_data: dict[str, Any],
        blocks: dict[str, dict[str, Any]],
        start: tuple[int, int],
        goals: set[tuple[int, int]],
    ) -> list[str] | None:
        if start in goals:
            return []
        queue = deque([start])
        routes: dict[tuple[int, int], list[str]] = {start: []}
        while queue:
            x, y = queue.popleft()
            for direction, dx, dy in self.DIRECTIONS:
                point = (x + dx, y + dy)
                if point in routes or not self._walkable(map_data, blocks, *point):
                    continue
                route = routes[(x, y)] + [direction]
                if point in goals:
                    return route
                routes[point] = route
                queue.append(point)
        return None

    # {
    #   責務: [_walkable: フィールド・explorerのwalkableを求める]
    #   処理: [1: フィールド・explorerのwalkableを求める]
    #   引数: [
    #     map_data: マップ・データ（dict[str, Any]）
    #     blocks: ブロック定義（dict[str, dict[str, Any]]）
    #     x: X座標（int）
    #     y: Y座標（int）
    #   ]
    #   戻り値: [result: フィールド・explorerのwalkableを求めるための結果（bool）]
    # }
    @staticmethod
    def _walkable(map_data: dict[str, Any], blocks: dict[str, dict[str, Any]], x: int, y: int) -> bool:
        if not 0 <= x < int(map_data["width"]) or not 0 <= y < int(map_data["height"]):
            return False
        if any(int(event.get("x", -1)) == x and int(event.get("y", -1)) == y and bool(event.get("blocking")) for event in map_data.get("events", [])):
            return False
        block_id = str(map_data["tiles"][y][x])
        return bool(blocks.get(block_id, {}).get("player_walkable", False))
