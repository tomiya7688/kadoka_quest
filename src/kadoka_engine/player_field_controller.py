# {
#   責務: [player_field_controller: 主人公・フィールド・controllerの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from kadoka_engine.field_engine import FieldEngine
from kadoka_engine.grid_movement import GridMovement


# {
#   責務: [PlayerFieldController: Own player grid position, facing, held movement, and visual interpolation.]
#   フィールド: [
#     DIRECTIONS: directions
#     x: X座標
#     y: Y座標
#     direction: direction
#     visual: visual
#     repeat_delay_ms: repeat・delay・ミリ秒
#     repeat_interval_ms: repeat・interval・ミリ秒
#     held_direction: 長押し・direction
#     next_move_tick: next・move・tick
#   ]
# }
class PlayerFieldController:
    """Own player grid position, facing, held movement, and visual interpolation."""

    DIRECTIONS = {
        "left": (-1, 0),
        "right": (1, 0),
        "back": (0, -1),
        "front": (0, 1),
    }

    # {
    #   責務: [__init__: 主人公・フィールド・controllerが利用する初期状態と依存を設定する]
    #   処理: [1: 主人公・フィールド・controllerが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     x: X座標（int）
    #     y: Y座標（int）
    #     movement_duration_ms: 移動・継続時間・ミリ秒（int）
    #     repeat_delay_ms: repeat・delay・ミリ秒（int）
    #     repeat_interval_ms: repeat・interval・ミリ秒（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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

    # {
    #   責務: [snap: 主人公・フィールド・controllerを補間せず座標を確定する]
    #   処理: [1: 主人公・フィールド・controllerを補間せず座標を確定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     x: X座標（int）
    #     y: Y座標（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def snap(self, x: int, y: int) -> None:
        self.x = int(x)
        self.y = int(y)
        self.visual.snap(self.x, self.y)

    # {
    #   責務: [attempt_move: 主人公・フィールド・controllerのattempt・moveを求める]
    #   処理: [1: 主人公・フィールド・controllerのattempt・moveを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     field: フィールド（FieldEngine）
    #     dx: 横方向の移動量（int）
    #     dy: 縦方向の移動量（int）
    #     visible_characters: visible・characters（list[dict]）
    #     hidden_characters: 非表示・characters（list[dict]）
    #     now: 現在時刻（int）
    #   ]
    #   戻り値: [result: 処理結果（dict）]
    # }
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

    # {
    #   責務: [begin_hold: holdを開始する]
    #   処理: [1: holdを開始する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     direction: direction（str）
    #     now: 現在時刻（int）
    #   ]
    #   戻り値: [result: holdを開始するための結果（tuple[int, int] | None）]
    # }
    def begin_hold(self, direction: str, now: int) -> tuple[int, int] | None:
        vector = self.DIRECTIONS.get(str(direction))
        if vector is None:
            return None
        self.held_direction = str(direction)
        self.next_move_tick = int(now) + self.repeat_delay_ms
        return vector

    # {
    #   責務: [stop_hold: holdを停止する]
    #   処理: [1: holdを停止する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     direction: direction（str）
    #   ]
    #   戻り値: [result: holdを停止するための結果（bool）]
    # }
    def stop_hold(self, direction: str) -> bool:
        if str(direction) != self.held_direction:
            return False
        self.clear_hold()
        return True

    # {
    #   責務: [clear_hold: holdを消去する]
    #   処理: [1: holdを消去する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def clear_hold(self) -> None:
        self.held_direction = None

    # {
    #   責務: [repeated_vector: 主人公・フィールド・controllerのrepeated・vectorを求める]
    #   処理: [1: 主人公・フィールド・controllerのrepeated・vectorを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     now: 現在時刻（int）
    #   ]
    #   戻り値: [result: 主人公・フィールド・controllerのrepeated・vectorを求めるための結果（tuple[int, int] | None）]
    # }
    def repeated_vector(self, now: int) -> tuple[int, int] | None:
        vector = self.DIRECTIONS.get(str(self.held_direction))
        if vector is None:
            self.clear_hold()
            return None
        if int(now) < self.next_move_tick:
            return None
        self.next_move_tick = int(now) + self.repeat_interval_ms
        return vector
