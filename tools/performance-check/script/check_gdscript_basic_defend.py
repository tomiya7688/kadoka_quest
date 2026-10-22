# {
#   責務: [check_gdscript_basic_defend: 開発者専用の実Godot防御/攻撃/終端解除1段階を標準回数で検査する]
#   フィールド: [ROOT: Godotソースの起動root。計測入力は専用一時フォルダへ置く]
# }
"""Developer-only real Godot explicit defend/attack stage; no AI, rendering or Player imports."""
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
#   責務: [main: 実Godot計測を起動し時間・実HP減少と最終guard解除を検証する]
#   処理: [
#     1: 開発者用回数とGodotパスを取得する
#     2: 専用一時要求でheadlessプローブを呼ぶ
#     3: 中央値3ms・8体・HP減少・guard1の条件を照合する
#   ]
#   引数: []
#   戻り値: [result: 成功0/失敗1/Godot不在Unverified2（int）]
# }
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=20_000)
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--warmup", type=int, default=2_000)
    args = parser.parse_args()
    godot = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")
    if not godot:
        print("UNVERIFIED: set KADOKA_GODOT_EXECUTABLE")
        return 2
    request = {"performance": True, "iterations": max(1, args.iterations),
               "samples": max(1, args.samples), "warmup": max(0, args.warmup)}
    with tempfile.TemporaryDirectory(prefix="kadoka-basic-defend-performance-") as directory:
        fixture = Path(directory) / "request.json"
        fixture.write_text(json.dumps(request), encoding="utf-8")
        process = subprocess.run([godot, "--headless", "--path", str(ROOT / "gdscript"), "--script",
                                  "res://tests/run_basic_defend_performance.gd", "--", str(fixture)],
                                 capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    if process.returncode or "SCRIPT ERROR" in process.stderr or "ERROR:" in process.stderr:
        print(process.stderr + process.stdout)
        return 1
    for line in process.stdout.splitlines():
        if line.startswith("KADOKA_NORMAL_ACTION_RESULT="):
            result = json.loads(base64.b64decode(line.split("=", 1)[1]))
            cleared = all(value == 1 for team in result["effects"]["teams"].values() for value in team.values())
            passed = (result["microseconds"] <= 3000 and result["actors"] == 8
                      and 0 < result["minimum_hp"] < 1_000_000_000 and cleared and result["phase"] == "round_finished")
            print(f"{'OK' if passed else 'FAIL'} Godot next+defend/attack+terminal-clear "
                  f"{result['microseconds']:.2f}us <= 3000us "
                  f"[{int(result['iterations'])} iterations, {int(result['samples'])} samples, "
                  f"{int(result['warmup'])} warmup; 8 actors, 4 defend/4 attack, plan+clear amortized]")
            print(f"minimum_hp={int(result['minimum_hp'])}, guard_cleared={cleared}")
            return 0 if passed else 1
    print("FAIL: missing Godot result")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
