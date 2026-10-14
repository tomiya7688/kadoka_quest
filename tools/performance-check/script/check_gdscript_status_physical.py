"""付与付き物理の非致死ダメージと一件付与成功を測ります。実セーブは使いません。"""
# {
#   責務: [check_gdscript_status_physical: 共用Godot起動へ委譲し、固定物理/状態予測と原本・性能条件を検査します]
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
#   責務: [StatusPhysicalBenchmark: 共用の起動条件を継承し、付与付き物理の固定期待結果を検査します]
#   フィールド: [
#     godot: 共用基底が保持する実Godotパス（str）
#     configuration: 共用基底が保持する反復条件と専用区分（dict）
#   ]
# }
class StatusPhysicalBenchmark(StatusCureBenchmark):
    # {
    #   責務: [__init__: 共用のGodot起動/反復条件を設定し、付与付き物理の区分だけを選びます]
    #   処理: [1: 基底の設定へ委譲し、専用プローブを示すstatus_physicalを設定します]
    #   引数: [
    #     self: 専用計測の設定所有者
    #     godot: 実Godotのパス（str）
    #     arguments: iterations/samples/warmupのCLI条件（argparse.Namespace）
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def __init__(self, godot: str, arguments: argparse.Namespace):
        # 起動/I/O/診断検査を複製せず、共用の開発専用基底へ任せます。
        super().__init__(godot, arguments)
        self.configuration["status_physical"] = True

    # {
    #   責務: [_check_output: 共用形式の結果を復号し、固定期待値と時間条件を検査します]
    #   処理: [1: 専用結果を復号し、欠落/拒否を失敗として結果を表示します]
    #   引数: [
    #     self: 反復条件を保持する計測所有者
    #     output: 診断なしの実Godot標準出力（str）
    #   ]
    #   戻り値: [status: 全条件一致なら0、不一致/欠落なら1（int）]
    # }
    def _check_output(self, output: str) -> int:
        for line in output.splitlines():
            if line.startswith("KADOKA_STATUS_CURE_RESULT="):
                result = json.loads(base64.b64decode(line.split("=", 1)[1]))
                passed = self.valid_result(result)
                print(f"{'OK' if passed else 'FAIL'} Godot status-physical quote "
                      f"{result.get('microseconds', -1):.2f}us <= 3000us "
                      f"[{self.configuration['iterations']} iterations, {self.configuration['samples']} samples, "
                      f"{self.configuration['warmup']} warmup; nonlethal damage and status success]")
                return 0 if passed else 1
        print("FAIL: no Godot status-physical result")
        return 1

    # {
    #   責務: [valid_result: 固定原本と非致死79ダメージ/残MP97/出血一件成功・時間を照合します]
    #   処理: [1: 原本と結果を別々の固定期待値へ照合し、高速拒否/致死/重複/入力改変を排除します]
    #   引数: [
    #     self: 反復条件を持つ所有者
    #     result: 実Godotの性能/原本/予測観測（dict）
    #   ]
    #   戻り値: [passed: 固定入力・期待結果・反復条件・一予測3000us以内が一致すればTrue（bool）]
    # }
    def valid_result(self, result: dict) -> bool:
        effect = {"id": "bleeding", "display_name": "出血", "chance": 0.4,
                  "metadata": {"deck": ["a", {"kept": True}]}}
        definition = {"id": "mod_status_hit", "display_name": "計測用付与打撃", "kind": "physical",
                      "mp_cost": 3, "status_effect": effect}
        effects = [{"id": "lock", "removable": False}, "poison", {"id": "mod", "metadata": {"deck": [1]}}]
        request = {"attack": 100, "defense": 50, "target_hp": 1000, "current_mp": 100, "critical_roll": 0.5,
                   "variance": 1.0, "status_resistance_level": "weak", "status_roll": 0.49, "status_effects": effects}
        candidate = {key: value for key, value in effect.items() if key != "chance"}
        candidate["removable"] = True
        quote = result.get("quote", {})
        physical = quote.get("physical", {})
        status = quote.get("status", {})
        # 正常な一件成功と独立原本を同時に照合し、結果だけの自己一致を許しません。
        return (result.get("definition") == definition and result.get("request") == request
                and result.get("input_preserved") is True and 0 <= result.get("microseconds", -1) <= 3000
                and all(result.get(field) == self.configuration[field] for field in ("iterations", "samples", "warmup"))
                and quote.get("ok") is True and quote.get("scope") == "status_physical_skill_quote"
                and quote.get("status_eligible") is True and physical.get("ok") is True
                and physical.get("scope") == "physical_skill_quote" and physical.get("skill_id") == "mod_status_hit"
                and (physical.get("damage"), physical.get("dealt"), physical.get("remaining_hp"),
                     physical.get("remaining_mp"), physical.get("mp_cost")) == (79, 79, 921, 97, 3)
                and physical.get("critical") is False and physical.get("critical_chance") == 1 / 16
                and status == {"ok": True, "scope": "status_apply_quote", "status_id": "bleeding", "apply_chance": 0.5,
                               "roll_required": True, "applied": True, "applied_name": "出血", "outcome": "applied",
                               "resulting_status_effects": [*effects, candidate]})


# {
#   責務: [main: 反復条件とGodotを確認し、共用起動の付与付き物理計測を実行します]
#   処理: [1: CLIを解析し、Godotが使えなければ未検証2、使えれば計測の終了コードを返します]
#   引数: []
#   戻り値: [status: 成功0、不一致1、Godot未指定2（int）]
# }
def main() -> int:
    # Player起動には組み込まず、開発者が明示した実Godotだけを使います。
    parser = argparse.ArgumentParser(description="Measure pure status-bearing physical predictions.")
    parser.add_argument("--iterations", type=int, default=20000)
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--warmup", type=int, default=2000)
    arguments = parser.parse_args()
    godot = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")
    if not godot:
        print("UNVERIFIED: set KADOKA_GODOT_EXECUTABLE to the Godot executable")
        return 2
    return StatusPhysicalBenchmark(godot, arguments).run()


if __name__ == "__main__":
    raise SystemExit(main())
