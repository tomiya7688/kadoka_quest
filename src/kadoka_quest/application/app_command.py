# {
#   責務: [app_command: app・コマンドの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


PLAIN_SCALARS = (str, int, float, bool, type(None))


# {
#   責務: [is_plain_data: plain data・データを該当するか判定する]
#   処理: [1: plain data・データを該当するか判定する]
#   引数: [value: 値（Any）]
#   戻り値: [result: plain data・データを該当するか判定するための結果（bool）]
# }
def is_plain_data(value: Any) -> bool:
    if isinstance(value, PLAIN_SCALARS):
        return True
    if isinstance(value, list):
        return all(is_plain_data(item) for item in value)
    if isinstance(value, Mapping):
        return all(isinstance(key, str) and is_plain_data(item) for key, item in value.items())
    return False


# {
#   責務: [AppCommand: Plain command exchanged between runtime applications.]
#   フィールド: [
#     target: 対象（str）
#     action: action（str）
#     payload: 要求データ（Mapping[str, Any]）
#   ]
# }
@dataclass(frozen=True)
class AppCommand:
    """Plain command exchanged between runtime applications."""

    target: str
    action: str
    payload: Mapping[str, Any] = field(default_factory=dict)

    # {
    #   責務: [__post_init__: app・コマンドが利用する初期状態と依存を設定する]
    #   処理: [1: app・コマンドが利用する初期状態と依存を設定する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __post_init__(self) -> None:
        if not is_plain_data(self.payload):
            raise TypeError("command payload must contain only plain JSON-like data")
