# {
#   責務: [grid_movement: マス・移動の公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations


# {
#   責務: [GridMovement: 論理座標間の時間補間を保持し、描画用座標を求める]
#   フィールド: [
#     duration_ms: 継続時間・ミリ秒
#     start_x: start・X座標
#     target_x: 対象・X座標
#     start_y: start・Y座標
#     target_y: 対象・Y座標
#     start_time_ms: start・時刻・ミリ秒
#     moving: moving
#   ]
# }
class GridMovement:
    # {
    #   責務: [__init__: マス・移動が利用する初期状態と依存を設定する]
    #   処理: [1: マス・移動が利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     x: X座標（float）
    #     y: Y座標（float）
    #     duration_ms: 継続時間・ミリ秒（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, x: float, y: float, duration_ms: int = 120) -> None:
        self.duration_ms = max(1, int(duration_ms))
        self.start_x = self.target_x = float(x)
        self.start_y = self.target_y = float(y)
        self.start_time_ms = 0
        self.moving = False

    # {
    #   責務: [snap: マス・移動を補間せず座標を確定する]
    #   処理: [1: マス・移動を補間せず座標を確定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     x: X座標（float）
    #     y: Y座標（float）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def snap(self, x: float, y: float) -> None:
        self.start_x = self.target_x = float(x)
        self.start_y = self.target_y = float(y)
        self.moving = False

    # {
    #   責務: [move_to: toを移動する]
    #   処理: [1: toを移動する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     x: X座標（float）
    #     y: Y座標（float）
    #     now_ms: 現在時刻・ミリ秒（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def move_to(self, x: float, y: float, now_ms: int) -> None:
        current_x, current_y = self.position(now_ms)
        self.start_x, self.start_y = current_x, current_y
        self.target_x, self.target_y = float(x), float(y)
        self.start_time_ms = int(now_ms)
        self.moving = (self.start_x, self.start_y) != (self.target_x, self.target_y)

    # {
    #   責務: [position: 移動開始と目的地の間を時間に基づき滑らかに補間する]
    #   処理: [
    #     1: 移動中でなければ確定座標を返す
    #     2: 経過時間を0〜1へ制限しsmoothstepで座標を補間する
    #     3: 完了時は目的地へsnapして移動状態を解除する
    #   ]
    #   引数: [
    #     self: 処理対象インスタンス
    #     now_ms: 現在時刻・ミリ秒（int）
    #   ]
    #   戻り値: [result: 補間後のX/Y座標]
    # }
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
