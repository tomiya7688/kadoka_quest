"""状態異常一つの治療予測、または--cure-healで治療付きHP回復を測定します。実セーブ・実治療は使用しません。"""
# {
#   責務: [check_gdscript_status_cure: 解除不可を飛ばす治療予測の時間・実結果・入力保持を検査する開発専用CLIです]
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
#   責務: [StatusCureBenchmark: 反復条件と実Godotの起動・治療結果/性能検査を所有します]
#   フィールド: [
#     godot: 計測するGodot実行ファイルのパス（str）
#     configuration: 反復・サンプル・事前実行回数の独立した辞書（dict）
#   ]
# }
class StatusCureBenchmark:
    # {
    #   責務: [__init__: 指定されたGodotとCLIの反復条件を保持します]
    #   処理: [1: 可変CLIオブジェクトではなく、計測に必要な値だけを取り出します]
    #   引数: [
    #     self: 治療予測の計測条件を持つ所有者
    #     godot: 実Godotのパス（str）
    #     arguments: iterations/samples/warmupと任意cure_heal区分を持つCLI条件（argparse.Namespace）
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def __init__(self, godot: str, arguments: argparse.Namespace):
        self.godot = godot
        self.configuration = {"performance": True, "iterations": max(1, arguments.iterations),
                              "samples": max(1, arguments.samples), "warmup": max(0, arguments.warmup),
                              "cure_heal": getattr(arguments, "cure_heal", False)}

    # {
    #   責務: [run: 専用JSONで治療予測の実Godotプローブを起動し、診断と計測結果を確認します]
    #   処理: [1: 専用JSONの一時領域でプローブを呼び、診断がなければ結果検査へ委譲します]
    #   引数: [self: 計測先と反復条件を持つ所有者]
    #   戻り値: [status: 正常結果と性能条件を満たせば0、診断や条件不一致なら1（int）]
    # }
    def run(self) -> int:
        # 利用者の個体・AI・保存データを読み書きせず、計測要求だけを一時ファイルにする。
        with tempfile.TemporaryDirectory(prefix="kadoka-cure-performance-") as directory:
            path = Path(directory) / "request.json"
            path.write_text(json.dumps(self.configuration), encoding="utf-8")
            process = subprocess.run(
                [self.godot, "--headless", "--path", str(ROOT / "gdscript"), "--script",
                 "res://tests/run_status_cure_probe.gd", "--", str(path)],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
            )
        # 高速な解析失敗や拒否結果を、正常な治療予測の性能と扱わない。
        if process.returncode or "SCRIPT ERROR" in process.stderr or "ERROR:" in process.stderr:
            print(process.stderr + process.stdout)
            return 1
        return self._check_output(process.stdout)

    # {
    #   責務: [_check_output: 時間上限・一件治療・入力保持と、回復付きならHP上限/MP消費を照合します]
    #   処理: [1: Base64の結果を読み、治療候補2・毒の解除と入力保持・時間上限を確認し、回復区分はHP/MPも照合します]
    #   引数: [
    #     self: 治療予測の性能条件を持つ所有者
    #     output: 実Godotの標準出力（str）
    #   ]
    #   戻り値: [status: 全条件一致なら0、結果欠落や不一致なら1（int）]
    # }
    def _check_output(self, output: str) -> int:
        for line in output.splitlines():
            if not line.startswith("KADOKA_STATUS_CURE_RESULT="):
                continue
            result = json.loads(base64.b64decode(line.split("=", 1)[1]))
            quote = result["quote"]
            original = result["original_effects"]
            # 4件中の候補2を除く一件治療を確認し、候補なしや拒否だけで通過させない。
            passed = (0 <= result["microseconds"] <= 3000 and result["input_preserved"] and quote["ok"]
                      and len(original) == 4 and original[2]["id"] == "poison"
                      and (quote["candidate_index"], quote["cured"], quote["cured_name"], quote["roll_required"]) == (2, True, "毒", True)
                      and quote["remaining_status_effects"] == [original[0], original[1], original[3]])
            if self.configuration["cure_heal"]:
                # 最大HPで制限された実回復量とMP消費まで一致した統合経路だけを合格にする。
                passed = passed and self._valid_heal_result(result)
            label = "cure-heal skill" if self.configuration["cure_heal"] else "status-cure"
            print(f"{'OK' if passed else 'FAIL'} Godot {label} quote {result['microseconds']:.2f}us <= 3000us "
                  f"[{result['iterations']} iterations, {result['samples']} samples, {result['warmup']} warmup; no writes]")
            return 0 if passed else 1
        print("FAIL: missing Godot status-cure result")
        return 1

    # {
    #   責務: [_valid_heal_result: 治療付き回復が回復上限30・実回復10・残MP6を返し、入力を保持したか確認します]
    #   処理: [1: 固定定義・固定資源要求と統合予測のHP/MP数値を照合します]
    #   引数: [
    #     self: 計測区分と反復条件を持つ所有者
    #     result: 実Godotから復号した計測結果（dict）
    #   ]
    #   戻り値: [passed: 定義・資源入力と期待した回復/MP消費が一致すればTrue（bool）]
    # }
    def _valid_heal_result(self, result: dict) -> bool:
        quote = result["quote"]
        definition = result.get("original_definition")
        request = result.get("original_request")
        return (definition == {"id": "spirit_recover", "display_name": "精霊回復", "kind": "heal",
                               "mp_cost": 4, "heal_ratio": 0.03, "status_cure_chance": 0.03}
                and request == {"current_mp": 10, "target_hp": 990, "target_max_hp": 1000,
                                "roll": 0.02, "status_effects": result["original_effects"]}
                and quote.get("scope") == "cure_heal_skill_quote"
                and (quote.get("heal_amount"), quote.get("healed"), quote.get("remaining_hp"),
                     quote.get("mp_cost"), quote.get("remaining_mp")) == (30, 10, 1000, 4, 6))


# {
#   責務: [main: CLI条件とGodot実行先を確認し、治療予測の性能計測へ委譲します]
#   処理: [1: 反復条件を解析し、実Godot指定済みなら計測、未指定なら未検証を返します]
#   引数: []
#   戻り値: [status: 成功0・失敗1・Godot未指定の未検証2（int）]
# }
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=20_000)
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--warmup", type=int, default=2_000)
    parser.add_argument("--cure-heal", action="store_true", help="一件治療と最大HP制限付きHP回復の統合予測を測定します")
    arguments = parser.parse_args()
    godot = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")
    # Godotがない環境では、計測したように成功を返しません。
    if not godot:
        print("UNVERIFIED: set KADOKA_GODOT_EXECUTABLE")
        return 2
    return StatusCureBenchmark(godot, arguments).run()


if __name__ == "__main__":
    raise SystemExit(main())
