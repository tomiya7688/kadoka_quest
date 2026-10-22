# {
#   責務: [evaluation_log: evaluation・ログの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from typing import Any


# {
#   責務: [EvaluationLog: Collect plain, serializable facts from an automated evaluation run.]
#   フィールド: [entries: 項目一覧（list[dict[str, Any]]）]
# }
class EvaluationLog:
    """Collect plain, serializable facts from an automated evaluation run."""

    # {
    #   責務: [__init__: evaluation・ログが利用する初期状態と依存を設定する]
    #   処理: [1: evaluation・ログが利用する初期状態と依存を設定する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    # {
    #   責務: [add: evaluation・ログを追加する]
    #   処理: [1: evaluation・ログを追加する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     kind: 種別（str）
    #     step: step（int）
    #     details: details（Any）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def add(self, kind: str, step: int, **details: Any) -> None:
        self.entries.append({"step": int(step), "kind": str(kind), **details})

    # {
    #   責務: [report: evaluation・ログを報告を生成する]
    #   処理: [1: evaluation・ログを報告を生成する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     status: 状態異常（str）
    #     visited_maps: visited・マップ一覧（set[str]）
    #     attempted_events: attempted・イベント一覧（set[str]）
    #   ]
    #   戻り値: [result: evaluation・ログを報告を生成するための結果（dict[str, Any]）]
    # }
    def report(self, *, status: str, visited_maps: set[str], attempted_events: set[str]) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "kind": "game_evaluation",
            "status": status,
            "visited_maps": sorted(visited_maps),
            "attempted_events": sorted(attempted_events),
            "entries": self.entries,
        }
