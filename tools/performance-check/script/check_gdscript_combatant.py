"""Developer-only real Godot resource states and base turn ordering/eligibility; no Player imports."""
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
    with tempfile.TemporaryDirectory(prefix="kadoka-combatant-performance-") as directory:
        fixture = Path(directory) / "request.json"
        fixture.write_text(json.dumps(request), encoding="utf-8")
        process = subprocess.run([godot, "--headless", "--path", str(ROOT / "gdscript"), "--script",
                                  "res://tests/run_combatant_probe.gd", "--", str(fixture)],
                                 capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    if process.returncode or "SCRIPT ERROR" in process.stderr or "ERROR:" in process.stderr:
        print(process.stderr + process.stdout)
        return 1
    for line in process.stdout.splitlines():
        if line.startswith("KADOKA_COMBATANT_RESULT="):
            result = json.loads(base64.b64decode(line.split("=", 1)[1]))
            passed = result["microseconds"] <= 1000 and result["actors"] == 8
            print(f"{'OK' if passed else 'FAIL'} Godot combatant init+damage+MP+flee+snapshot+living (8 actors) "
                  f"{result['microseconds']:.2f}us <= 1000us "
                  f"[{int(result['iterations'])} iterations, {int(result['samples'])} samples, "
                  f"{int(result['warmup'])} warmup]")
            round_passed = result["round_microseconds"] <= 2000 and result["actors"] == 8
            print(f"{'OK' if round_passed else 'FAIL'} Godot turn plan+one-latest-eligibility (8 actors) "
                  f"{result['round_microseconds']:.2f}us <= 2000us")
            return 0 if passed and round_passed else 1
    print("FAIL: missing Godot result")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
