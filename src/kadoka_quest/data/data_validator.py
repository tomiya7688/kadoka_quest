# {
#   責務: [data_validator: データ・検証処理の公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from pathlib import Path

from kadoka_engine.data_validator import DataValidator as EngineDataValidator
from kadoka_quest.paths import DATA_ROOT


# {
#   責務: [DataValidator: Backward-compatible Kadoka Quest adapter for the reusable validator.]
#   フィールド: []
# }
class DataValidator(EngineDataValidator):
    """Backward-compatible Kadoka Quest adapter for the reusable validator."""

    # {
    #   責務: [__init__: データ・検証処理が利用する初期状態と依存を設定する]
    #   処理: [1: データ・検証処理が利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     data_root: データ・基準ディレクトリ（Path | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, data_root: Path | None = None) -> None:
        super().__init__(Path(data_root or DATA_ROOT))
