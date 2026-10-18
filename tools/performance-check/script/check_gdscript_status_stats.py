"""出血中の実効防御力と素早さの純粋予測を実Godotで測定します。実セーブは使いません。"""
# {
#   責務: [check_gdscript_status_stats: 共用Godot起動へ委譲し、状態能力値の固定期待結果・原本保持・計測条件を検査します]
#   フィールド: []
# }
from __future__ import annotations

import argparse
import base64
import json
import os
import shutil

from check_gdscript_status_cure import StatusCureBenchmark


# {
#   責務: [StatusStatBenchmark: 状態能力値の反復条件を所有し、実Godotの観測を独立した固定期待値へ照合します]
#   フィールド: [
#     godot: 共用基底が保持する実Godotのパス（str）
#     configuration: 共用反復条件とstatus_stats区分の辞書（dict）
#   ]
# }
class StatusStatBenchmark(StatusCureBenchmark):
    # {
    #   責務: [__init__: 共用Godot起動条件へ状態能力値の専用計測区分を追加します]
    #   処理: [1: 基底へ反復条件を渡し、状態能力値プローブを選択します]
    #   引数: [
    #     self: 計測設定を所有するインスタンス
    #     godot: 実Godotのパス（str）
    #     arguments: iterations/samples/warmupを持つCLI条件（argparse.Namespace）
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def __init__(self, godot: str, arguments: argparse.Namespace):
        super().__init__(godot, arguments)
        self.configuration["status_stats"] = True

    # {
    #   責務: [valid_result: 状態補正の固定入力・防御45/速度55・原本保持・計測条件と上限を照合します]
    #   処理: [1: 予測の拒否や入力と出力だけの自己一致を許さず、独立した期待値と比較します]
    #   引数: [
    #     self: 反復条件を持つ計測インスタンス
    #     result: 実Godotが返した観測辞書（dict）
    #   ]
    #   戻り値: [passed: 全期待値と一予測3000us以内が一致すればTrue（bool）]
    # }
    def valid_result(self, result: dict) -> bool:
        expected = {"defense": 51, "speed": 41, "speed_multiplier": 1.5,
                    "status_effects": ["poison", {"id": "bleeding", "removable": False}, "bleeding",
                                       {"id": "mod", "metadata": {"deck": [1, {"kept": True}]}}]}
        return (result.get("request") == expected and result.get("input_preserved") is True
                and result.get("quote") == {"ok": True, "scope": "status_stat_quote", "defense": 45, "speed": 55}
                and all(result.get(key) == self.configuration[key] for key in ("iterations", "samples", "warmup"))
                and 0 <= result.get("microseconds", -1) <= 3000)

    # {
    #   責務: [_check_output: 共用Base64形式を復号し、正常な能力値補正の性能検査結果を表示します]
    #   処理: [1: 結果が存在すれば固定期待値を検査し、結果欠落は失敗にします]
    #   引数: [
    #     self: 固定期待値と反復条件を持つ計測インスタンス
    #     output: 実Godotの診断検査済み標準出力（str）
    #   ]
    #   戻り値: [status: 全条件一致なら0、欠落または不一致なら1（int）]
    # }
    def _check_output(self, output: str) -> int:
        for line in output.splitlines():
            if line.startswith("KADOKA_STATUS_CURE_RESULT="):
                result = json.loads(base64.b64decode(line.split("=", 1)[1]))
                passed = self.valid_result(result)
                print(f"{'OK' if passed else 'FAIL'} Godot status stats {result.get('microseconds', -1):.2f}us <= 3000us "
                      f"[{self.configuration['iterations']} iterations, {self.configuration['samples']} samples, "
                      f"{self.configuration['warmup']} warmup; fixed inputs and successful quote]")
                return 0 if passed else 1
        print("FAIL: no Godot status-stat result")
        return 1


# {
#   責務: [main: CLI反復条件と実Godotパスを解決し、状態能力値の性能検査を起動します]
#   処理: [1: 条件を解析し、実Godotがなければ未検証の終了コード2を返します]
#   引数: []
#   戻り値: [status: 成功0、検査失敗1、Godot未指定2（int）]
# }
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=20_000)
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--warmup", type=int, default=2_000)
    arguments = parser.parse_args()
    godot = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")
    if not godot:
        print("UNVERIFIED: set KADOKA_GODOT_EXECUTABLE")
        return 2
    return StatusStatBenchmark(godot, arguments).run()


if __name__ == "__main__":
    raise SystemExit(main())
