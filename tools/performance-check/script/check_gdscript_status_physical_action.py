"""八体・千定義の新規構築を含む付与付き物理の実更新を測定します。実セーブは使いません。"""
# {
#   責務: [check_gdscript_status_physical_action: 実Godotの固定入力・実更新・確認数・一行動中央値を照合する開発専用CLIです]
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
#   責務: [expected_source: 実Godotが返す原本とは独立に、八体・千定義・状態/耐性/装備の固定期待値を作ります]
#   処理: [1: 両陣営四体と千件一覧を固定値で組み立て、自己一致だけで性能を通さない比較原本を返します]
#   引数: []
#   戻り値: [result: 独立したteams/statuses/skillsの期待辞書（dict）]
# }
def expected_source() -> dict:
    teams, statuses = {}, {}
    for side in ("allies", "enemies"):
        teams[side], statuses[side] = [], {}
        for index in range(4):
            identifier = f"member_{index}"
            teams[side].append({"snapshot": {"identity": {"id": identifier, "species_id": "slime", "name": identifier},
                "stats": {"hp": 100, "mp": 100, "attack": 10, "defense": 10, "magic": 10, "speed": 10},
                "hp": 100, "mp": 100, "fled": False, "alive": True}, "skill_ids": ["mod_status_hit"],
                "equipment": {"allowed_species_ids": ["slime"], "fixed_bonus_damage": 3,
                              "skill_modifiers": {"mod_status_hit": {"power_multiplier": 2}}},
                "status_resistances": {"bleeding": "weak"}})
            statuses[side][identifier] = ["poison", {"id": "mod", "metadata": {"deck": [1, True]}}]
    skills = [{"id": f"other_{index}", "kind": "mod_unknown"} for index in range(999)]
    skills.append({"id": "mod_status_hit", "display_name": "計測用付与打撃", "kind": "physical", "mp_cost": 3,
        "status_effect": {"id": "bleeding", "chance": 0.4, "metadata": {"deck": [1, {"kept": True}]}}})
    return {"teams": teams, "statuses": statuses, "skills": {"schema_version": 1, "skills": skills}}


# {
#   責務: [StatusPhysicalActionBenchmark: 付与付き物理の計測条件を所有し、固定原本と全反復の更新結果を検査します]
#   フィールド: [
#     godot: 共用基底が保持する実Godotパス（str）
#     configuration: 共用反復条件とstatus_physical_action区分（dict）
#   ]
# }
class StatusPhysicalActionBenchmark(StatusCureBenchmark):
    # {
    #   責務: [__init__: 共用起動/診断条件へ、付与付き物理の実行専用区分を設定します]
    #   処理: [1: 基底へ反復条件を渡し、行動プローブを選択します]
    #   引数: [
    #     self: 計測条件を所有するインスタンス
    #     godot: 実Godotの実行パス（str）
    #     arguments: iterations/samples/warmupを持つCLI条件（argparse.Namespace）
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def __init__(self, godot: str, arguments: argparse.Namespace):
        super().__init__(godot, arguments)
        self.configuration["status_physical_action"] = True

    # {
    #   責務: [valid_result: 全八体の残HP82/MP97・出血付与・行動完了と固定原本・確認数・性能上限を照合します]
    #   処理: [1: 実観測と独立した期待値を組み立て、高速拒否や未確認反復を成功として扱わないよう比較します]
    #   引数: [
    #     self: 標準または指定反復条件の所有者
    #     result: 実Godotの計測観測（dict）
    #   ]
    #   戻り値: [passed: 全期待値と一行動3000us以内が一致すればTrue（bool）]
    # }
    def valid_result(self, result: dict) -> bool:
        source = expected_source()
        order = [{"side": side, "id": f"member_{index}"} for side in ("allies", "enemies") for index in range(4)]
        candidate = {"id": "bleeding", "display_name": "bleeding", "removable": True,
                     "metadata": {"deck": [1, {"kept": True}]}}
        statuses = {"teams": {side: {identifier: [*effects, candidate] for identifier, effects in team.items()}
                              for side, team in source["statuses"].items()}, "scope": "battle_status_only"}
        numeric = {"phase": "round_finished", "round": 1, "cursor": 8, "pending": None, "order": order,
                   "teams": {side: [{**entry["snapshot"], "hp": 82, "mp": 97} for entry in team]
                             for side, team in source["teams"].items()}, "scope": "base_battle_cursor"}
        last = result.get("last", {})
        numbers = last.get("numbers", {})
        physical = numbers.get("physical", {})
        applied = last.get("applied_status", {})
        elapsed = result.get("microseconds")
        # 固定した最終資源/状態と全反復確認数を照合し、予測だけ・重複付与だけの高速経路を排除します。
        return (result.get("original_source") == source and result.get("original_order") == order
                and result.get("actors") == 8 and result.get("definitions") == 1000 and result.get("input_preserved") is True
                and all(result.get(field) == self.configuration[field] for field in ("iterations", "samples", "warmup"))
                and self.configuration["iterations"] % 8 == 0 and self.configuration["warmup"] % 8 == 0
                and result.get("completed") == self.configuration["iterations"] * self.configuration["samples"] + self.configuration["warmup"]
                and isinstance(elapsed, (int, float)) and not isinstance(elapsed, bool) and 0 <= elapsed <= 3000
                and result.get("numeric") == numeric and result.get("statuses") == statuses
                and last.get("ok") is True and last.get("executed") is True
                and last.get("scope") == "explicit_status_physical_skill_only"
                and last.get("ticket") == {"round": 1, "slot": 7, "actor": order[-1]}
                and last.get("target") == {"side": "allies", "id": "member_3"}
                and (last.get("spent_mp"), last.get("dealt")) == (3, 18)
                and numbers.get("ok") is True and numbers.get("status_eligible") is True
                and (physical.get("damage"), physical.get("remaining_hp"), physical.get("remaining_mp")) == (18, 82, 97)
                and applied.get("ok") is True and applied.get("applied") is True and applied.get("apply_chance") == 0.5
                and applied.get("resulting_status_effects") == statuses["teams"]["allies"]["member_3"]
                and last.get("session") == numeric and last.get("statuses") == statuses)

    # {
    #   責務: [_check_output: 共用Base64結果を復号し、固定期待値と性能上限の合否を表示します]
    #   処理: [1: 行動観測を検査し、結果がなければ失敗にします]
    #   引数: [
    #     self: 反復条件と固定期待値を持つ検査所有者
    #     output: 診断検査済みの実Godot標準出力（str）
    #   ]
    #   戻り値: [status: 合格0、不一致/欠落1（int）]
    # }
    def _check_output(self, output: str) -> int:
        for line in output.splitlines():
            if line.startswith("KADOKA_STATUS_CURE_RESULT="):
                result = json.loads(base64.b64decode(line.split("=", 1)[1]))
                passed = self.valid_result(result)
                print(f"{'OK' if passed else 'FAIL'} Godot status physical action {result.get('microseconds', -1):.2f}us <= 3000us "
                      f"[{self.configuration['iterations']} iterations, {self.configuration['samples']} samples, "
                      f"{self.configuration['warmup']} warmup; 8 actors, 1000 definitions, new setup each 8 actions]")
                return 0 if passed else 1
        print("FAIL: no Godot status-physical-action result")
        return 1


# {
#   責務: [main: CLIの反復条件と実Godot実行先を解決し、付与付き物理行動の性能検査を起動します]
#   処理: [1: 条件を解析し、Godot未指定なら未検証の終了コード2を返します]
#   引数: []
#   戻り値: [status: 合格0、不一致1、Godot未指定の未検証2（int）]
# }
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=20_000, help="八の倍数を指定してください")
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--warmup", type=int, default=2_000, help="0または八の倍数を指定してください")
    arguments = parser.parse_args()
    godot = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")
    if not godot:
        print("UNVERIFIED: set KADOKA_GODOT_EXECUTABLE")
        return 2
    return StatusPhysicalActionBenchmark(godot, arguments).run()


if __name__ == "__main__":
    raise SystemExit(main())
