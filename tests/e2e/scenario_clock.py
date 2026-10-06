"""One explicit, monotonic timeline for test ticks and preset timestamps."""
# {
#   責務: [scenario_clock: One explicit, monotonic timeline for test ticks and preset timestamps.]
#   フィールド: []
# }

from __future__ import annotations

from datetime import datetime, timedelta


# {
#   責務: [nonnegative_integer: scenario・clockのnonnegative・integerを求める]
#   処理: [1: scenario・clockのnonnegative・integerを求める]
#   引数: [
#     value: 値（object）
#     name: 名前（str）
#   ]
#   戻り値: [result: 値（int）]
# }
def nonnegative_integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


# {
#   責務: [ScenarioClock: scenario・clockの状態と振る舞いを担当する]
#   フィールド: [now: 現在時刻]
# }
class ScenarioClock:
    # {
    #   責務: [__init__: scenario・clockが利用する初期状態と依存を設定する]
    #   処理: [1: scenario・clockが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     start_ms: start・ミリ秒（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, start_ms: int) -> None:
        self.now = nonnegative_integer(start_ms, "start_ms")

    # {
    #   責務: [ticks: scenario・clockのticksを求める]
    #   処理: [1: scenario・clockのticksを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.now（int）]
    # }
    def ticks(self) -> int:
        return self.now

    # {
    #   責務: [advance: scenario・clockのadvanceを求める]
    #   処理: [1: scenario・clockのadvanceを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     milliseconds: milliseconds（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def advance(self, milliseconds: int) -> None:
        self.now += nonnegative_integer(milliseconds, "ms")

    # {
    #   責務: [datetime_now: scenario・clockのdatetime・現在時刻を求める]
    #   処理: [1: scenario・clockのdatetime・現在時刻を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: scenario・clockのdatetime・現在時刻を求めるための結果（datetime）]
    # }
    def datetime_now(self) -> datetime:
        return datetime(2000, 1, 1) + timedelta(milliseconds=self.now)
