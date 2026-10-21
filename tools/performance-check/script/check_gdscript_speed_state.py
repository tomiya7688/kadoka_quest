"""実Godotの速度強化ライフサイクル七操作を、固定結果と3000us上限で検査します。"""
# {
#   責務: [check_gdscript_speed_state: 速度所有者の計測要求・実Godot起動・独立した固定期待値との照合を提供します]
#   フィールド: []
# }
from __future__ import annotations

import argparse
import base64
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
PREFIX = "KADOKA_SPEED_STATE_RESULT="


# {
#   責務: [SpeedStateBenchmark: 実Godotのパスと、速度強化を測定する反復条件を所有します]
#   フィールド: [
#     godot: 実行するGodotのパス（str）
#     configuration: performance/iterations/samples/warmupの独立辞書（dict）
#   ]
# }
class SpeedStateBenchmark:
    # {
    #   責務: [__init__: 速度強化計測に必要な実行先と反復条件だけを保持します]
    #   処理: [1: CLIの条件から変更可能なコピーを作ります]
    #   引数: [
    #     self: 実行先と反復条件の所有者
    #     godot: Godot実行ファイル（str）
    #     arguments: iterations/samples/warmupを持つ条件（argparse.Namespace）
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def __init__(self, godot: str, arguments: argparse.Namespace):
        self.godot = godot
        self.configuration = {"performance": True, "iterations": arguments.iterations,
                              "samples": arguments.samples, "warmup": arguments.warmup}

    # {
    #   責務: [valid_result: 七操作の倍率・期間・復元先と、反復件数・有限時間・3000us上限を独立照合します]
    #   処理: [1: プローブの入力から計算し直さず固定期待値を作り、計測結果の全条件を確認します]
    #   引数: [
    #     self: 検査する反復条件の所有者
    #     result: 実Godotまたは拒否検証用の観測辞書（dict）
    #   ]
    #   戻り値: [passed: 実更新の結果・件数・時間が全て一致したときだけTrueです（bool）]
    # }
    def valid_result(self, result: dict) -> bool:
        # 高速な拒否・未実行・自己一致を通さず、全ての中間状態を独立した既定値へ照合します。
        expected = []
        for index, values in enumerate(((1.2, 0, 1.2), (1.5, 2, 1.2), (1.5, 3, 1.2),
                                        (1.5, 3, 1.4), (1.5, 2, 1.4), (1.5, 1, 1.4), (1.4, 0, 1.4))):
            snapshot = dict(zip(("speed_multiplier", "remaining_turns", "baseline_multiplier"), values))
            scope = "combatant_speed_apply"
            if index == 0:
                scope = "combatant_speed_started"
            elif index >= 4:
                scope = "combatant_speed_elapsed"
            reply = {"ok": True, "scope": scope, "snapshot": snapshot}
            if index >= 4:
                reply["expired"] = index == 6
            expected.append(reply)
        config = self.configuration
        duration = result.get("microseconds")
        return (result.get("trace") == expected
                and all(type(item["snapshot"]["remaining_turns"]) is int for item in result["trace"])
                and result.get("input") == {"initial": 1.2, "applications": [
                    {"multiplier": 1.5, "duration": 2}, {"multiplier": 1.3, "duration": 3}, {"multiplier": 1.4}], "ticks": 3}
                and result.get("all_traces_match") is True
                and all(type(result.get(key)) is int and result[key] == config[key]
                        for key in ("iterations", "samples", "warmup"))
                and type(result.get("operations_completed")) is int
                and result["operations_completed"] == 7 * (config["warmup"] + config["iterations"] * config["samples"])
                and type(duration) in (int, float) and math.isfinite(duration) and 0 <= duration <= 3000)

    # {
    #   責務: [run: 一時要求だけで実Godotを起動し、診断なしの計測結果を検査します]
    #   処理: [1: 一時JSONを渡して起動し、診断/結果欠落を拒否して固定期待値と速度を照合します]
    #   引数: [self: 実行先・反復条件と固定期待値を持つ所有者]
    #   戻り値: [status: 正常結果と性能上限が一致すれば0、それ以外は1です（int）]
    # }
    def run(self) -> int:
        # 個体・AI・保存JSONを読み書きせず、起動条件だけを専用一時領域へ置きます。
        with tempfile.TemporaryDirectory(prefix="kadoka-speed-performance-") as directory:
            path = Path(directory) / "request.json"
            path.write_text(json.dumps(self.configuration), encoding="utf-8")
            process = subprocess.run([self.godot, "--headless", "--path", str(ROOT / "gdscript"),
                                      "--script", "res://tests/run_speed_multiplier_probe.gd", "--", str(path)],
                                     cwd=directory, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        if process.returncode or "SCRIPT ERROR" in process.stderr or "ERROR:" in process.stderr:
            print(process.stderr + process.stdout)
            return 1
        for line in process.stdout.splitlines():
            if line.startswith(PREFIX):
                result = json.loads(base64.b64decode(line[len(PREFIX):]))
                passed = self.valid_result(result)
                print(f"{'OK' if passed else 'FAIL'} Godot speed-state lifecycle "
                      f"{result.get('microseconds', -1):.2f}us <= 3000us "
                      f"[{self.configuration['iterations']} iterations, {self.configuration['samples']} samples, "
                      f"{self.configuration['warmup']} warmup; seven real updates]")
                return 0 if passed else 1
        print("FAIL: missing Godot speed-state result")
        return 1


# {
#   責務: [main: CLIの反復条件とGodot実行先を検証し、速度強化の性能検査を起動します]
#   処理: [1: 条件を解析し、Godot未指定を未検証として返し、専用計測へ委譲します]
#   引数: []
#   戻り値: [status: 成功0、失敗1、Godot未指定2。反復条件不正はargparseで拒否します（int）]
# }
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=20_000)
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--warmup", type=int, default=2_000)
    arguments = parser.parse_args()
    if arguments.iterations < 1 or arguments.samples < 1 or arguments.warmup < 0:
        parser.error("iterations/samples must be positive; warmup must be non-negative")
    godot = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")
    if not godot:
        print("UNVERIFIED: set KADOKA_GODOT_EXECUTABLE")
        return 2
    return SpeedStateBenchmark(godot, arguments).run()


if __name__ == "__main__":
    raise SystemExit(main())
