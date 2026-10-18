"""固定八体の状態補正済み行動順を実Godotで測定します。実セーブは使いません。"""
# {
#   責務: [check_gdscript_status_turn_order: 状態順序の正常計画・固定入力・原本保持・標準性能上限を照合する開発専用CLIです]
#   フィールド: []
# }
from __future__ import annotations

import argparse
import base64
import json
import math
import os
import shutil

from check_gdscript_status_cure import StatusCureBenchmark


# {
#   責務: [StatusTurnOrderBenchmark: 専用の反復条件を保持し、状態補正済み順序の実観測を独立した固定期待値へ照合します]
#   フィールド: [
#     godot: 共用基底が保持する実Godotのパス（str）
#     configuration: 共用反復条件とstatus_turn_order区分の辞書（dict）
#   ]
# }
class StatusTurnOrderBenchmark(StatusCureBenchmark):
    # {
    #   責務: [__init__: 共用の実Godot起動条件へ状態行動順の専用計測区分を追加します]
    #   処理: [1: 基底に反復条件を渡し、状態順序プローブを選択します]
    #   引数: [
    #     self: 状態順序の計測条件を持つ所有者
    #     godot: 実Godotのパス（str）
    #     arguments: iterations/samples/warmupのCLI条件（argparse.Namespace）
    #   ]
    #   戻り値: [result: なし（None）]
    # }
    def __init__(self, godot: str, arguments: argparse.Namespace):
        # 共用の起動/診断検査を維持したまま、状態行動順だけの固定計測へ切り替えます。
        super().__init__(godot, arguments)
        self.configuration["status_turn_order"] = True

    # {
    #   責務: [valid_result: 固定八体の入力・速度・安定順序・反復条件・保持と一計画3000us以内を照合します]
    #   処理: [1: 入力と出力だけの自己一致を避け、独立した既定値と正常計画を確認します]
    #   引数: [
    #     self: 反復条件と専用区分を持つ計測インスタンス
    #     result: 実Godotの反復計測の観測辞書（dict）
    #   ]
    #   戻り値: [passed: 固定期待値・反復条件・原本保持・有限所要時間が全て一致すればTrue（bool）]
    # }
    def valid_result(self, result: dict) -> bool:
        # 計測側で返した入力/結果同士の一致ではなく、四状態と補正結果を独立に組み立てて比較します。
        expected = {"allies": [], "enemies": [], "statuses": {"allies": {}, "enemies": {}},
                    "speed_multipliers": {"allies": {}, "enemies": {}}, "shuffle_order": []}
        initial = []
        for side in ("allies", "enemies"):
            for index, speed in enumerate((41, 40, 0, 3)):
                identifier = f"member_{index}"
                expected[side].append({"identity": {"id": identifier, "species_id": "slime", "name": identifier},
                                       "stats": {"hp": 30, "mp": 10, "attack": 20, "defense": 51, "speed": speed, "magic": 10},
                                       "hp": 30, "mp": 7, "fled": False, "alive": True})
                expected["statuses"][side][identifier] = (
                    ["poison", {"id": "bleeding", "removable": False}, "bleeding", {"id": "mod", "metadata": {"deck": [1, {"kept": True}]}}]
                    if side == "allies" else ["poison", "sleep", "Bleeding", {"id": "mod", "metadata": {"deck": [1, {"kept": True}]}}])
                expected["speed_multipliers"][side][identifier] = 0.0 if index == 2 else 1.5
                initial.append({"side": side, "id": identifier})
        expected["shuffle_order"] = initial[::-1]
        order = [{"side": side, "id": f"member_{index}"} for side, index in (
            ("enemies", 0), ("enemies", 1), ("allies", 0), ("allies", 1),
            ("enemies", 3), ("allies", 3), ("enemies", 2), ("allies", 2))]
        speeds = {"allies": dict(zip((f"member_{i}" for i in range(4)), (55, 54, 1, 4))),
                  "enemies": dict(zip((f"member_{i}" for i in range(4)), (61, 60, 1, 4)))}
        duration = result.get("microseconds")
        plan = result.get("plan", {})
        return (result.get("request") == expected and result.get("input_preserved") is True
                and plan == {"ok": True, "scope": "status_turn_order", "initial": initial, "order": order, "speeds": speeds}
                and plan["ok"] is True and all(type(value) is int for team in plan["speeds"].values() for value in team.values())
                and all(type(result.get(field)) is int and result[field] == self.configuration[field]
                        for field in ("iterations", "samples", "warmup"))
                and type(duration) in (int, float) and math.isfinite(duration) and 0 <= duration <= 3000)

    # {
    #   責務: [_check_output: 共用のBase64出力を復号し、状態順序の性能と正常結果の合否を表示します]
    #   処理: [1: 計測結果を固定期待値へ照合し、結果欠落は失敗にします]
    #   引数: [
    #     self: 固定入力と反復条件を持つ所有者
    #     output: 共用起動が診断なしを確認した標準出力（str）
    #   ]
    #   戻り値: [status: 全条件一致なら0、欠落または不一致なら1（int）]
    # }
    def _check_output(self, output: str) -> int:
        # 高速な拒否や結果欠落を合格にせず、正常な計画と時間を同時に満たす観測だけを通します。
        for line in output.splitlines():
            if line.startswith("KADOKA_STATUS_CURE_RESULT="):
                result = json.loads(base64.b64decode(line.split("=", 1)[1]))
                passed = self.valid_result(result)
                print(f"{'OK' if passed else 'FAIL'} Godot status turn order {result.get('microseconds', -1):.2f}us <= 3000us "
                      f"[{self.configuration['iterations']} iterations, {self.configuration['samples']} samples, "
                      f"{self.configuration['warmup']} warmup; 8 actors, fixed inputs and successful stable plan]")
                return 0 if passed else 1
        print("FAIL: no Godot status turn-order result")
        return 1


# {
#   責務: [main: CLI反復条件と実Godotパスを解決し、状態補正済み行動順の性能検査を起動します]
#   処理: [1: 条件を解析し、実Godotがなければ未検証の終了コード2を返します]
#   引数: []
#   戻り値: [status: 成功0、検査失敗1、Godot未指定2（int）]
# }
def main() -> int:
    # 標準反復条件をCLIで再現可能にし、Godotがない検証環境を成功として扱わないようにします。
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=20_000)
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--warmup", type=int, default=2_000)
    arguments = parser.parse_args()
    godot = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")
    if not godot:
        print("UNVERIFIED: set KADOKA_GODOT_EXECUTABLE")
        return 2
    return StatusTurnOrderBenchmark(godot, arguments).run()


if __name__ == "__main__":
    raise SystemExit(main())
