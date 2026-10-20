"""Developer-only real Godot cursor stages; no attack/AI/rendering or Player imports."""
# {
#   責務: [check_gdscript_battle_session: Developer-only real Godot cursor stages; no attack/AI/rendering or Player imports.]
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


# {
#   責務: [valid_status_round_result: 状態付き八体の固定入力・最新状態・実行済み段階と一段階2000us以内を照合します]
#   処理: [1: 独立した期待入力と順序を作り、成功した全反復の資源・状態・段階を厳密に比較します]
#   引数: [
#     result: 実Godotの状態付きSession計測結果（dict）
#     request: 呼出側が指定した反復条件（dict）
#   ]
#   戻り値: [passed: 固定正常結果・原本保持・有限時間が全て一致すればTrue（bool）]
# }
def valid_status_round_result(result: dict, request: dict) -> bool:
    # 計測側の入力と出力を一緒に改変した自己一致を避け、固定八体を独立して構築します。
    teams = {"allies": [], "enemies": []}
    statuses = {"allies": {}, "enemies": {}}
    for side in teams:
        for index in range(4):
            teams[side].append({"identity": {"id": str(index), "species_id": "slime", "name": "test"},
                "stats": {"hp": 100, "mp": 20, "attack": 10, "defense": 10, "magic": 10, "speed": index % 3 + 1},
                "hp": 100, "mp": 20, "fled": False, "alive": True})
            statuses[side][str(index)] = (["bleeding", {"id": "bleeding"}, "poison",
                {"id": "mod", "metadata": {"deck": [1, {"kept": True}]}}] if side == "allies" else ["poison", "sleep", "Bleeding"])
    initial = [{"side": side, "id": str(index)} for side in teams for index in range(4)]
    order = [{"side": side, "id": str(index)} for side, index in (
        ("enemies", 2), ("allies", 2), ("enemies", 1), ("allies", 0),
        ("allies", 1), ("allies", 3), ("enemies", 0), ("enemies", 3))]
    # 全反復が実際に予約を消費した最終round/cursorまで照合し、高速な開始失敗を合格にしません。
    stages = request["warmup"] + request["iterations"] * request["samples"]
    cursor = stages % 8 or 8
    session = {"phase": "round_finished" if cursor == 8 else "round_active", "round": (stages + 7) // 8,
               "cursor": cursor, "order": order, "pending": None, "teams": teams, "scope": "base_battle_cursor"}
    duration = result.get("microseconds")
    # PythonのTrue==1による偽一致を避け、JSON上の数値・真偽値も区別して固定結果を比較します。
    expected = {"input": {**teams, "shuffle_order": initial}, "initial_statuses": statuses,
                "statuses": {"teams": statuses, "scope": "battle_status_only"}, "session": session}
    return (type(result.get("actors")) is int and result["actors"] == 8
            and all(json.dumps(result.get(field), sort_keys=True) == json.dumps(value, sort_keys=True)
                    for field, value in expected.items()) and result.get("input_preserved") is True
            and all(type(result.get(field)) is int and result[field] == request[field] for field in ("iterations", "samples", "warmup"))
            and type(duration) in (int, float) and math.isfinite(duration) and 0 <= duration <= 2000)


# {
#   責務: [main: 八体Sessionの一行動段階を実Godotで計測し、中央値2000us以内を確認します]
#   処理: [1: 専用一時JSONで計測を起動し、診断・八体の実結果・時間上限を照合します]
#   引数: []
#   戻り値: [status: 正常計測0、診断/結果不一致/超過1、Godot未指定の未検証2（int）]
# }
def main() -> int:
    # 開発者が反復条件と状態付き区分を指定できるようにし、Godot未指定は未検証として区別します。
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=20_000)
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--warmup", type=int, default=2_000)
    parser.add_argument("--with-statuses", action="store_true", help="状態付き開始と毎ラウンドの最新状態補正を計測します")
    args = parser.parse_args()
    godot = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")
    if not godot:
        print("UNVERIFIED: set KADOKA_GODOT_EXECUTABLE")
        return 2
    request = {"performance": True, "iterations": max(1, args.iterations),
               "samples": max(1, args.samples), "warmup": max(0, args.warmup), "status_round": args.with_statuses}
    # 計測要求だけを隔離し、個体・AI・保存データを入力や出力へ使用しません。
    with tempfile.TemporaryDirectory(prefix="kadoka-session-performance-") as directory:
        fixture = Path(directory) / "request.json"
        fixture.write_text(json.dumps(request), encoding="utf-8")
        process = subprocess.run([godot, "--headless", "--path", str(ROOT / "gdscript"), "--script",
                                  "res://tests/run_battle_session_probe.gd", "--", str(fixture)],
                                 capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    # 解析失敗や拒否を速い正常実行と扱わず、診断がない出力だけを固定期待値へ照合します。
    if process.returncode or "SCRIPT ERROR" in process.stderr or "ERROR:" in process.stderr:
        print(process.stderr + process.stdout)
        return 1
    for line in process.stdout.splitlines():
        if line.startswith("KADOKA_SESSION_RESULT="):
            result = json.loads(base64.b64decode(line.split("=", 1)[1]))
            passed = valid_status_round_result(result, request) if args.with_statuses else result["microseconds"] <= 2000 and result["actors"] == 8
            print(f"{'OK' if passed else 'FAIL'} Godot next+claim+zero-resource+finish (8-actor session) "
                  f"{result['microseconds']:.2f}us <= 2000us "
                  f"[{int(result['iterations'])} iterations, {int(result['samples'])} samples, "
                  f"{int(result['warmup'])} warmup; {'latest owned statuses; ' if args.with_statuses else ''}round plan amortized every 8 stages]")
            return 0 if passed else 1
    print("FAIL: missing Godot result")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
