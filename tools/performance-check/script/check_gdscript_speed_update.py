"""取得済み予約による八体の速度実付与を、固定結果と3000us上限で検査します。"""
# {
#   責務: [check_gdscript_speed_update: 専用一時要求で速度実付与を測り、固定八体・全実更新数・再送拒否を照合します]
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
#   責務: [valid_result: 実Godotの最終八体・正常予約・所有倍率/期間と全反復件数を固定期待値へ照合します]
#   処理: [1: 計測入力から逆算しない固定八体を作り、正常更新・原本保持・有限時間を厳密比較します]
#   引数: [
#     result: 実Godotまたは拒否検証用の観測辞書（dict）
#     request: 呼出側が指定したiterations/samples/warmup（dict）
#   ]
#   戻り値: [passed: 全固定結果と反復数、中央値3000us以内が一致するときだけTrueです（bool）]
# }
def valid_result(result: dict, request: dict) -> bool:
    # 計測側の入力と結果を同時に偽装した自己一致を通さず、八体を独立して構築します。
    statuses = {"allies": {}, "enemies": {}}
    multipliers = {"allies": {}, "enemies": {}}
    states = {"allies": {}, "enemies": {}}
    guards = {"allies": {}, "enemies": {}}
    snapshots = {"allies": [], "enemies": []}
    order = []
    for side in snapshots:
        for index in range(4):
            identifier = f"member_{index}"
            snapshots[side].append({"identity": {"id": identifier, "species_id": "slime", "name": identifier},
                "stats": {"hp": 100, "mp": 100, "attack": 10, "defense": 10, "magic": 10, "speed": 10},
                "hp": 100, "mp": 100, "alive": True, "fled": False})
            statuses[side][identifier] = []
            multipliers[side][identifier] = 1.2
            states[side][identifier] = {"speed_multiplier": 1.5, "remaining_turns": 3, "baseline_multiplier": 1.2}
            guards[side][identifier] = 1.0
            order.append({"side": side, "id": identifier})
    numeric = {"phase": "round_finished", "round": 1, "cursor": 8, "order": order, "pending": None,
               "teams": snapshots, "scope": "base_battle_cursor"}
    last_state = {"speed_multiplier": 1.5, "remaining_turns": 3, "baseline_multiplier": 1.2}
    expected = {"actors": 8, "original_source": {"snapshots": snapshots, "statuses": statuses,
        "multipliers": multipliers, "request": {"multiplier": 1.5, "duration": 3}}, "original_order": order,
        "numeric": numeric, "statuses": {"teams": statuses, "scope": "battle_status_only"},
        "speeds": {"teams": states, "scope": "battle_speed_only"}, "guards": {"teams": guards, "scope": "basic_guard_only"},
        "last": {"applied": {"ok": True, "scope": "combatant_speed_apply", "snapshot": last_state},
                 "repeated": {"ok": False, "reason": "speed_multiplier_already_applied"},
                 "single": {"ok": True, "snapshot": last_state}, "finished": {"ok": True, "session": numeric}}}
    duration = result.get("microseconds")
    # True==1の偽一致を避け、JSONの真偽値/数値も区別して全結果を照合します。
    return (all(json.dumps(result.get(key), sort_keys=True) == json.dumps(value, sort_keys=True)
                for key, value in expected.items()) and result.get("input_preserved") is True
            and all(type(result.get(key)) is int and result[key] == request[key] for key in ("iterations", "samples", "warmup"))
            and type(result.get("completed")) is int
            and result["completed"] == request["warmup"] + request["iterations"] * request["samples"]
            and type(duration) in (int, float) and math.isfinite(duration) and 0 <= duration <= 3000)


# {
#   責務: [main: 標準反復条件を解析し、専用JSONだけを使う実Godot計測と独立結果検査を実行します]
#   処理: [1: 完全八行動条件とGodot実行先を確認し、診断なしの結果を固定期待値と時間上限へ照合します]
#   引数: []
#   戻り値: [status: 正常結果と性能成功0、失敗1、Godot未指定2。不正CLI条件はargparseで拒否します（int）]
# }
def main() -> int:
    # 保存データを条件へ使わず、専用反復数とGodot実行先だけを受け付けます。
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=20_000)
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--warmup", type=int, default=2_000)
    args = parser.parse_args()
    if args.iterations < 8 or args.iterations % 8 or args.samples < 1 or args.warmup < 0 or args.warmup % 8:
        parser.error("iterations/warmup must be complete eight-actor batches; samples must be positive")
    godot = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")
    if not godot:
        print("UNVERIFIED: set KADOKA_GODOT_EXECUTABLE")
        return 2
    request = {"performance": True, "claimed_speed": True,
               "iterations": args.iterations, "samples": args.samples, "warmup": args.warmup}
    with tempfile.TemporaryDirectory(prefix="kadoka-claimed-speed-performance-") as directory:
        path = Path(directory) / "request.json"
        path.write_text(json.dumps(request), encoding="utf-8")
        process = subprocess.run([godot, "--headless", "--path", str(ROOT / "gdscript"), "--script",
            "res://tests/run_speed_multiplier_probe.gd", "--", str(path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    # 拒否や解析失敗の速さを性能成功にせず、診断と結果の欠落も失敗へ分けます。
    if process.returncode or "SCRIPT ERROR" in process.stderr or "ERROR:" in process.stderr:
        print(process.stderr + process.stdout)
        return 1
    for line in process.stdout.splitlines():
        if line.startswith(PREFIX):
            result = json.loads(base64.b64decode(line[len(PREFIX):]))
            passed = valid_result(result, request)
            print(f"{'OK' if passed else 'FAIL'} Godot claimed speed update "
                  f"{result.get('microseconds', -1):.2f}us <= 3000us "
                  f"[{args.iterations} iterations, {args.samples} samples, {args.warmup} warmup; real update per actor]")
            return 0 if passed else 1
    print("FAIL: missing Godot claimed speed result")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
