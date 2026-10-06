# {
#   責務: [field_engine: フィールド・ルール処理の公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations


# {
#   責務: [FieldEngine: Resolve field-grid rules without depending on pygame or file I/O.]
#   フィールド: [
#     DIRECTIONS: directions
#     map_data: マップ・データ
#     blocks: ブロック定義
#   ]
# }
class FieldEngine:
    """Resolve field-grid rules without depending on pygame or file I/O."""

    DIRECTIONS = {
        "left": (-1, 0),
        "right": (1, 0),
        "back": (0, -1),
        "front": (0, 1),
    }

    # {
    #   責務: [__init__: フィールド・ルール処理が利用する初期状態と依存を設定する]
    #   処理: [1: フィールド・ルール処理が利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     map_data: マップ・データ（dict）
    #     blocks: ブロック定義（dict[str, dict]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, map_data: dict, blocks: dict[str, dict]) -> None:
        self.set_world(map_data, blocks)

    # {
    #   責務: [set_world: マップ状態を設定する]
    #   処理: [1: マップ状態を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     map_data: マップ・データ（dict）
    #     blocks: ブロック定義（dict[str, dict]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def set_world(self, map_data: dict, blocks: dict[str, dict]) -> None:
        self.map_data = map_data
        self.blocks = blocks

    # {
    #   責務: [direction_for_step: フィールド・ルール処理のdirection・for・stepを求める]
    #   処理: [1: フィールド・ルール処理のdirection・for・stepを求める]
    #   引数: [
    #     dx: 横方向の移動量（int）
    #     dy: 縦方向の移動量（int）
    #     current: current（str）
    #   ]
    #   戻り値: [result: フィールド・ルール処理のdirection・for・stepを求めるための結果（str）]
    # }
    @staticmethod
    def direction_for_step(dx: int, dy: int, current: str = "front") -> str:
        if dx < 0:
            return "left"
        if dx > 0:
            return "right"
        if dy < 0:
            return "back"
        if dy > 0:
            return "front"
        return current

    # {
    #   責務: [_character_at: フィールド・ルール処理のキャラクター・atを求める]
    #   処理: [1: フィールド・ルール処理のキャラクター・atを求める]
    #   引数: [
    #     characters: characters（list[dict]）
    #     x: X座標（int）
    #     y: Y座標（int）
    #   ]
    #   戻り値: [result: フィールド・ルール処理のキャラクター・atを求めるための結果（dict | None）]
    # }
    @staticmethod
    def _character_at(characters: list[dict], x: int, y: int) -> dict | None:
        return next(
            (item for item in characters if (int(item["x"]), int(item["y"])) == (int(x), int(y))),
            None,
        )

    # {
    #   責務: [resolve_player_move: Return a plain-data move result and never mutate the supplied world.]
    #   処理: [1: Return a plain-data move result and never mutate the supplied world.]
    #   引数: [
    #     self: 処理対象インスタンス
    #     x: X座標（int）
    #     y: Y座標（int）
    #     dx: 横方向の移動量（int）
    #     dy: 縦方向の移動量（int）
    #     direction: direction（str）
    #     visible_characters: visible・characters（list[dict]）
    #     hidden_characters: 非表示・characters（list[dict]）
    #   ]
    #   戻り値: [result: Return a plain-data move result and never mutate the supplied world.ための結果（dict）]
    # }
    def resolve_player_move(
        self,
        x: int,
        y: int,
        dx: int,
        dy: int,
        direction: str,
        visible_characters: list[dict],
        hidden_characters: list[dict],
    ) -> dict:
        """Return a plain-data move result and never mutate the supplied world."""
        next_direction = self.direction_for_step(dx, dy, direction)
        new_x, new_y = int(x) + int(dx), int(y) + int(dy)
        result = {
            "kind": "blocked",
            "reason": "out_of_bounds",
            "x": int(x),
            "y": int(y),
            "direction": next_direction,
        }
        if not (0 <= new_x < int(self.map_data["width"]) and 0 <= new_y < int(self.map_data["height"])):
            return result

        hidden = self._character_at(hidden_characters, new_x, new_y)
        if hidden is not None:
            return {**result, "reason": "hidden_character", "character": hidden}

        visible = self._character_at(visible_characters, new_x, new_y)
        if visible is not None:
            return {**result, "reason": "visible_character", "character": visible}

        blocking_event = next(
            (
                event
                for event in self.map_data.get("events", [])
                if int(event["x"]) == new_x and int(event["y"]) == new_y and bool(event.get("blocking"))
            ),
            None,
        )
        if blocking_event is not None:
            return {**result, "reason": "blocking_event", "event": blocking_event}

        block_id = self.map_data["tiles"][new_y][new_x]
        block = self.blocks.get(block_id, {})
        if not bool(block.get("player_walkable", False)):
            return {**result, "reason": "blocked_tile", "block_id": block_id, "block": block}

        return {
            "kind": "moved",
            "reason": "walkable",
            "x": new_x,
            "y": new_y,
            "direction": next_direction,
            "block_id": block_id,
        }

    # {
    #   責務: [front_position: フィールド・ルール処理のfront・座標を求める]
    #   処理: [1: フィールド・ルール処理のfront・座標を求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     x: X座標（int）
    #     y: Y座標（int）
    #     direction: direction（str）
    #   ]
    #   戻り値: [result: フィールド・ルール処理のfront・座標を求めるための結果（tuple[int, int]）]
    # }
    def front_position(self, x: int, y: int, direction: str) -> tuple[int, int]:
        dx, dy = self.DIRECTIONS.get(direction, (0, 1))
        return int(x) + dx, int(y) + dy

    # {
    #   責務: [step_transition_at: フィールド・ルール処理のstep・移動ポイント・atを求める]
    #   処理: [1: フィールド・ルール処理のstep・移動ポイント・atを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     x: X座標（int）
    #     y: Y座標（int）
    #   ]
    #   戻り値: [result: フィールド・ルール処理のstep・移動ポイント・atを求めるための結果（dict | None）]
    # }
    def step_transition_at(self, x: int, y: int) -> dict | None:
        return next(
            (
                event
                for event in self.map_data.get("events", [])
                if int(event["x"]) == int(x)
                and int(event["y"]) == int(y)
                and event.get("type") == "transition"
                and event.get("activation", "step") == "step"
            ),
            None,
        )

    # {
    #   責務: [nearby_event: イベントを近くの対象を探す]
    #   処理: [1: イベントを近くの対象を探す]
    #   引数: [
    #     self: 処理対象インスタンス
    #     x: X座標（int）
    #     y: Y座標（int）
    #   ]
    #   戻り値: [result: イベントを近くの対象を探すための結果（dict | None）]
    # }
    def nearby_event(self, x: int, y: int) -> dict | None:
        candidates = []
        for index, event in enumerate(self.map_data.get("events", [])):
            distance = abs(int(event["x"]) - int(x)) + abs(int(event["y"]) - int(y))
            if distance <= 1:
                candidates.append((distance, index, event))
        return min(candidates, default=(0, 0, None))[2]

    # {
    #   責務: [tile_allows: フィールド・ルール処理のマス・allowsを求める]
    #   処理: [1: フィールド・ルール処理のマス・allowsを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     x: X座標（int）
    #     y: Y座標（int）
    #     rule: rule（str）
    #   ]
    #   戻り値: [result: フィールド・ルール処理のマス・allowsを求めるための結果（bool）]
    # }
    def tile_allows(self, x: int, y: int, rule: str) -> bool:
        if not (0 <= int(x) < int(self.map_data["width"]) and 0 <= int(y) < int(self.map_data["height"])):
            return False
        block_id = self.map_data["tiles"][int(y)][int(x)]
        return bool(self.blocks.get(block_id, {}).get(rule, False))

    # {
    #   責務: [has_clear_axis_path: Check an unobstructed horizontal or vertical path using a block rule.]
    #   処理: [1: Check an unobstructed horizontal or vertical path using a block rule.]
    #   引数: [
    #     self: 処理対象インスタンス
    #     start: start（tuple[int, int]）
    #     target: 対象（tuple[int, int]）
    #     rule: rule（str）
    #   ]
    #   戻り値: [result: Check an unobstructed horizontal or vertical path using a block rule.ための結果（bool）]
    # }
    def has_clear_axis_path(self, start: tuple[int, int], target: tuple[int, int], rule: str) -> bool:
        """Check an unobstructed horizontal or vertical path using a block rule."""
        start_x, start_y = (int(value) for value in start)
        target_x, target_y = (int(value) for value in target)
        if start_x != target_x and start_y != target_y:
            return False
        dx = 0 if start_x == target_x else (1 if target_x > start_x else -1)
        dy = 0 if start_y == target_y else (1 if target_y > start_y else -1)
        x, y = start_x + dx, start_y + dy
        while (x, y) != (target_x, target_y):
            if not self.tile_allows(x, y, rule):
                return False
            x, y = x + dx, y + dy
        return True
