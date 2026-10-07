"""実Godotの8体MP付き物理行動を測る開発専用検査。Playerへimportしない。"""
# {
#   責務: [check_gdscript_physical_action: 実行時間と実MP・HP適用の開発専用検査]
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
#   責務: [main: 専用fixtureで実Godotの物理行動を測り閾値と資源を検証する]
#   処理: [
#     1: 引数とGodotを確認する
#     2: 専用一時JSONでheadless計測を実行する
#     3: 診断・時間・HP減少・MP総消費を確認する
#   ]
#   引数: []
#   戻り値: [result: 成功0・失敗1・未検証2（int）]
# }
def main() -> int:
    # 未指定を成功扱いにせず、専用コピーだけを計測用に作る。
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=20_000)
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--warmup", type=int, default=2_000)
    args = parser.parse_args()
    godot = os.environ.get("KADOKA_GODOT_EXECUTABLE") or shutil.which("godot") or shutil.which("godot4")
    if not godot:
        print("UNVERIFIED: set KADOKA_GODOT_EXECUTABLE")
        return 2
    request = {"iterations": max(1, args.iterations), "samples": max(1, args.samples), "warmup": max(0, args.warmup)}
    with tempfile.TemporaryDirectory(prefix="kadoka-physical-action-performance-") as directory:
        fixture = Path(directory) / "request.json"
        fixture.write_text(json.dumps(request), encoding="utf-8")
        process = subprocess.run([godot, "--headless", "--path", str(ROOT / "gdscript"), "--script",
                                  "res://tests/run_physical_action_performance.gd", "--", str(fixture)],
                                 capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    # 結果が出てもGodotの解析・実行エラーを成功にしない。
    if process.returncode or "SCRIPT ERROR" in process.stderr or "ERROR:" in process.stderr:
        print(process.stderr + process.stdout)
        return 1
    for line in process.stdout.splitlines():
        if line.startswith("KADOKA_PHYSICAL_ACTION_PERFORMANCE="):
            result = json.loads(base64.b64decode(line.split("=", 1)[1]))
            passed = (result["microseconds"] <= 3000 and result["actors"] == 8
                      and 0 < result["minimum_hp"] < 1_000_000_000
                      and result["spent_mp"] == result["expected_spent_mp"])
            print(f"{'OK' if passed else 'FAIL'} Godot next+physical-skill(validate/claim/MP/HP/finish) "
                  f"{result['microseconds']:.2f}us <= 3000us "
                  f"[{int(result['iterations'])} iterations, {int(result['samples'])} samples, "
                  f"{int(result['warmup'])} warmup; 8 actors; spent MP={int(result['spent_mp'])}]")
            return 0 if passed else 1
    print("FAIL: missing Godot result")
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
