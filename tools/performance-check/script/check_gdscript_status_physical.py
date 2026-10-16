"""付与付き物理の予測を測ります。--contextは八体/千定義の準備済み索引から成功選択を測ります。実セーブは使いません。"""
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
#   責務: [StatusPhysicalBenchmark: 共用起動条件を継承し、付与付き物理の予測または準備済み索引の選択を固定期待値で検査します]
#   フィールド: [
#     godot: 共用基底が保持する実Godotパス（str）
#     configuration: 共用基底が保持する反復条件と予測/選択の専用区分（dict）
#   ]
# }
class StatusPhysicalBenchmark(StatusCureBenchmark):
    # {
    #   責務: [__init__: 共用のGodot起動/反復条件を設定し、CLIの予測/選択区分を設定します]
    #   処理: [1: 基底の設定へ委譲し、CLIに従いstatus_physicalまたはstatus_physical_contextの一方だけを設定します]
    #   引数: [
    #     self: 専用計測の設定所有者
    #     godot: 実Godotのパス（str）
    #     arguments: iterations/samples/warmupと任意contextのCLI条件（argparse.Namespace）
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def __init__(self, godot: str, arguments: argparse.Namespace):
        # 起動/I/O/診断検査を複製せず、共用の開発専用基底へ任せます。
        super().__init__(godot, arguments)
        self.configuration["status_physical_context"] = getattr(arguments, "context", False)
        self.configuration["status_physical"] = not self.configuration["status_physical_context"]

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
                kind = "context selection" if self.configuration["status_physical_context"] else "quote"
                print(f"{'OK' if passed else 'FAIL'} Godot status-physical {kind} "
                      f"{result.get('microseconds', -1):.2f}us <= 3000us "
                      f"[{self.configuration['iterations']} iterations, {self.configuration['samples']} samples, "
                      f"{self.configuration['warmup']} warmup; fixed inputs and successful result]")
                return 0 if passed else 1
        print("FAIL: no Godot status-physical result")
        return 1

    # {
    #   責務: [valid_result: 予測は非致死79ダメージ/MP97/出血、選択は八体/千定義の固定期待値へ照合します]
    #   処理: [1: CLIの区分に応じた固定期待値へ照合し、高速拒否や原本改変を排除します]
    #   引数: [
    #     self: 反復条件を持つ所有者
    #     result: 実Godotの性能/原本/予測観測（dict）
    #   ]
    #   戻り値: [passed: 固定入力・期待結果・反復条件・一予測/選択3000us以内が一致すればTrue（bool）]
    # }
    def valid_result(self, result: dict) -> bool:
        # 選択性能をダメージ予測の成功と混同せず、専用の固定期待値へ分けます。
        if self.configuration["status_physical_context"]:
            return self._valid_context_result(result)
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
    #   責務: [_valid_context_result: 八体/千定義と付与付き定義/装備補正・初期状態/耐性・固定数値/原本を照合します]
    #   処理: [1: 成功選択と独立した固定期待値、反復条件と3000us上限を同時に確認します]
    #   引数: [
    #     self: --contextの反復条件を所有する性能検査
    #     result: 実Godotが返した選択と準備/入力保持の観測（dict）
    #   ]
    #   戻り値: [passed: 全固定条件と時間が一致すればTrue、不一致/欠落ならFalse（bool）]
    # }
    def _valid_context_result(self, result: dict) -> bool:
        # 正常な物理/状態定義と威力2/固定加算3が選択された証拠を、原本と別に組み立てます。
        skill = {"id": "mod_status_hit", "display_name": "計測用付与打撃", "kind": "physical", "mp_cost": 3,
                 "power": 1, "critical_multiplier": 1,
                 "status_effect": {"id": "bleeding", "chance": 0.4, "metadata": {"deck": [1, {"kept": True}]}}}
        equipment = {"allowed_species_ids": ["slime"], "fixed_bonus_damage": 3,
                     "skill_modifiers": {"mod_status_hit": {"power_multiplier": 2}}}
        member = {"skill_ids": ["mod_status_hit"], "equipment": equipment, "status_resistances": {"bleeding": "weak"}}
        stats = {"hp": 100, "mp": 100, "attack": 10, "defense": 10, "magic": 10, "speed": 10}
        snapshot = {"identity": {"id": "member_0", "species_id": "slime", "name": "member_0"}, "stats": stats,
                    "hp": 100, "mp": 100, "fled": False, "alive": True}
        return (0 <= result.get("microseconds", -1) <= 3000
                and all(result.get(key) == self.configuration[key] for key in ("iterations", "samples", "warmup"))
                and (result.get("actors"), result.get("definitions")) == (8, 1000)
                and result.get("input_preserved") is True and result.get("prepared_preserved") is True
                and result.get("selected") == {"ok": True, "skill": skill,
                                               "equipment": {"power_multiplier": 2, "fixed_bonus_damage": 3}}
                and result.get("member") == member and result.get("snapshot") == snapshot
                and result.get("initial_statuses") == ["poison", {"id": "mod", "metadata": {"deck": [1, True]}}])


# {
#   責務: [main: 反復条件とGodotを確認し、共用起動の付与付き物理計測を実行します]
#   処理: [1: CLIを解析し、Godotが使えなければ未検証2、使えれば計測の終了コードを返します]
#   引数: []
#   戻り値: [status: 成功0、不一致1、Godot未指定2（int）]
# }
def main() -> int:
    # Player起動には組み込まず、開発者が明示した実Godotだけを使います。
    parser = argparse.ArgumentParser(description="Measure pure status-bearing physical predictions.")
    parser.add_argument("--context", action="store_true", help="Measure status-physical selection with 8 actors and 1000 definitions.")
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
