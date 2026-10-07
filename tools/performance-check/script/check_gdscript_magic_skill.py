"""単体魔法の純粋予測を実Godotで測定します。Playerと実セーブは使用しません。"""
# {
#   責務: [check_gdscript_magic_skill: 魔法予測の時間・HP/MP予測・入力不変を確認する開発専用CLIです]
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
#   責務: [MagicSkillBenchmark: 専用の計測条件と実Godotの起動・結果検証を所有します]
#   フィールド: [
#     godot: 計測するGodot実行ファイルのパス（str）
#     configuration: 反復回数・サンプル数・事前実行回数の独立した計測条件（dict）
#   ]
# }
class MagicSkillBenchmark:
    # {
    #   責務: [__init__: 計測先とCLIから受け取った計測条件を保持します]
    #   処理: [1: CLI引数を専用の計測辞書へ投影します]
    #   引数: [
    #     self: 計測条件の所有者
    #     godot: 使用するGodot実行ファイルのパス（str）
    #     arguments: iterations/samples/warmupを持つCLI引数（argparse.Namespace）
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def __init__(self, godot: str, arguments: argparse.Namespace):
        # 可変CLIオブジェクトを保持せず、計測に必要な値だけを取り出す。
        self.godot = godot
        self.configuration = {"performance": True, "iterations": max(1, arguments.iterations),
                              "samples": max(1, arguments.samples), "warmup": max(0, arguments.warmup)}

    # {
    #   責務: [run: 専用JSONで実Godotを起動し、診断と計測結果を確認します]
    #   処理: [
    #     1: 一時JSONで計測プローブを起動します
    #     2: Godot診断を確認します
    #     3: 計測結果の検証へ委譲します
    #   ]
    #   引数: [self: 実行先と計測条件の所有者]
    #   戻り値: [status: 成功0・失敗1（int）]
    # }
    def run(self) -> int:
        # 計測用JSON以外は作成せず、利用者のモンスターやAIを読み書きしない。
        with tempfile.TemporaryDirectory(prefix="kadoka-magic-performance-") as directory:
            path = Path(directory) / "request.json"
            path.write_text(json.dumps(self.configuration), encoding="utf-8")
            process = subprocess.run(
                [self.godot, "--headless", "--path", str(ROOT / "gdscript"), "--script",
                 "res://tests/run_magic_skill_probe.gd", "--", str(path)],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
            )
        # 高速に失敗した実行を、正常な予測の性能と扱わない。
        if process.returncode or "SCRIPT ERROR" in process.stderr or "ERROR:" in process.stderr:
            print(process.stderr + process.stdout)
            return 1
        return self._check_output(process.stdout)

    # {
    #   責務: [_check_output: 時間上限・期待したHP/MP予測・元資源の不変を照合します]
    #   処理: [1: プローブ結果を読み取り、性能と資源の期待値を確認します]
    #   引数: [
    #     self: 計測条件の所有者
    #     output: Godotプローブの標準出力（str）
    #   ]
    #   戻り値: [status: すべて一致なら0、不一致または結果欠落なら1（int）]
    # }
    def _check_output(self, output: str) -> int:
        # 時間だけでなく、魔力100・威力0.55の正常予測が成立したことも確認する。
        for line in output.splitlines():
            if not line.startswith("KADOKA_MAGIC_SKILL_RESULT="):
                continue
            result = json.loads(base64.b64decode(line.split("=", 1)[1]))
            quote = result["quote"]
            passed = (result["microseconds"] <= 3000 and quote["ok"] and result["input_preserved"]
                      and (result["current_mp"], result["target_hp"]) == (10, 1000)
                      and (quote["remaining_mp"], quote["remaining_hp"], quote["dealt"]) == (5, 945, 55))
            print(f"{'OK' if passed else 'FAIL'} Godot magic-skill quote {result['microseconds']:.2f}us <= 3000us "
                  f"[{result['iterations']} iterations, {result['samples']} samples, {result['warmup']} warmup; no writes]")
            return 0 if passed else 1
        print("FAIL: missing Godot magic-skill result")
        return 1


# {
#   責務: [main: Godotの実行先とCLI条件を選び、魔法予測の計測へ委譲します]
#   処理: [
#     1: CLI条件を読み取ります
#     2: Godotの有無を確認して計測を呼び出します
#   ]
#   引数: []
#   戻り値: [status: 成功0・失敗1・Godot未指定による未検証2（int）]
# }
def main() -> int:
    # Godot未指定は成功とせず、必要な環境変数を表示する。
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=20_000)
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--warmup", type=int, default=2_000)
    arguments = parser.parse_args()
    godot = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")
    if not godot:
        print("UNVERIFIED: set KADOKA_GODOT_EXECUTABLE")
        return 2
    return MagicSkillBenchmark(godot, arguments).run()


if __name__ == "__main__":
    raise SystemExit(main())
