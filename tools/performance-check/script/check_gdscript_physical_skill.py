"""Developer-only real Godot physical-skill quote benchmark. No Player imports or real saves."""
# {
#   責務: [check_gdscript_physical_skill: 純粋な物理スキル予測の性能退行を実Godotで検出する]
#   フィールド: []
# }
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]


# {
#   責務: [PhysicalSkillBenchmark: 計測条件と実Godotの起動・結果確認を所有する]
#   フィールド: [
#     godot: 使用する実Godot実行ファイル（str）
#     configuration: iterations/samples/warmupの専用fixture（dict）
#   ]
# }
class PhysicalSkillBenchmark:
    # {
    #   責務: [__init__: 計測先と独立した計測条件を保持する]
    #   処理: [1: 引数を正規化し計測要求として保持する]
    #   引数: [
    #     self: 計測条件の所有者
    #     godot: 実行ファイル（str）
    #     arguments: CLIから得た計測条件（argparse.Namespace）
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def __init__(self, godot: str, arguments: argparse.Namespace):
        # CLIの可変Namespaceを保持せず、計測に必要な値だけを専用JSONへ投影する。
        self.godot = godot
        self.configuration = {"performance": True, "iterations": max(1, arguments.iterations),
                              "samples": max(1, arguments.samples), "warmup": max(0, arguments.warmup)}

    # {
    #   責務: [run: 専用fixtureでプローブを起動し、測定値と資源予測を確認する]
    #   処理: [
    #     1: 一時fixtureで実Godotを起動する
    #     2: 終了結果と診断を確認する
    #     3: プローブ結果の検証へ委譲する
    #   ]
    #   引数: [self: 計測条件と実行先の所有者]
    #   戻り値: [status: 成功0、失敗1（int）]
    # }
    def run(self) -> int:
        # ファイル生成は専用の一時領域だけ。Playerや利用者セーブを起動しない。
        with tempfile.TemporaryDirectory(prefix="kadoka-physical-performance-") as directory:
            path = Path(directory) / "request.json"
            path.write_text(json.dumps(self.configuration), encoding="utf-8")
            process = subprocess.run(
                [self.godot, "--headless", "--path", str(ROOT / "gdscript"), "--script",
                 "res://tests/run_physical_skill_probe.gd", "--", str(path)],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
            )
        # エンジン診断がある場合は、測定結果の有無にかかわらず失敗とする。
        if process.returncode or "SCRIPT ERROR" in process.stderr or "ERROR:" in process.stderr:
            print(process.stderr + process.stdout)
            return 1
        return self._check_output(process.stdout)

    # {
    #   責務: [_check_output: 時間だけでなく期待した予測と入力不変も確認する]
    #   処理: [1: プローブの結果を読み、上限と入力・出力を照合する]
    #   引数: [
    #     self: 計測条件の所有者
    #     output: プローブ標準出力（str）
    #   ]
    #   戻り値: [status: 成功0、失敗1（int）]
    # }
    def _check_output(self, output: str) -> int:
        # 予測が失敗した高速経路を、正常経路の性能として報告しない。
        for line in output.splitlines():
            if not line.startswith("KADOKA_PHYSICAL_SKILL_RESULT="):
                continue
            result = json.loads(base64.b64decode(line.split("=", 1)[1]))
            quote = result["quote"]
            passed = (result["microseconds"] <= 3000 and quote["ok"]
                      and (result["current_mp"], result["target_hp"]) == (10, 1000)
                      and (quote["remaining_mp"], quote["remaining_hp"]) == (7, 951))
            print(f"{'OK' if passed else 'FAIL'} Godot physical-skill quote {result['microseconds']:.2f}us <= 3000us "
                  f"[{result['iterations']} iterations, {result['samples']} samples, {result['warmup']} warmup; no writes]")
            return 0 if passed else 1
        print("FAIL: missing Godot physical-skill result")
        return 1


# {
#   責務: [main: CLI条件を受け取り実Godot計測へ委譲する]
#   処理: [1: 条件と実行ファイルを選び計測を呼び出す]
#   引数: []
#   戻り値: [status: 成功0、失敗1、実Godot未指定2（int）]
# }
def main() -> int:
    # 前提がない環境を性能成功と扱わず、設定方法を表示する。
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=20_000)
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--warmup", type=int, default=2_000)
    arguments = parser.parse_args()
    godot = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")
    if not godot:
        print("UNVERIFIED: set KADOKA_GODOT_EXECUTABLE")
        return 2
    return PhysicalSkillBenchmark(godot, arguments).run()


if __name__ == "__main__":
    raise SystemExit(main())
