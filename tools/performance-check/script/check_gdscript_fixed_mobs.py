"""Developer-only actual Godot fixed-mob movement/dialogue timing; never imported by Player."""
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
    world = {"id": "benchmark", "width": 32, "height": 32, "tiles": [["floor"] * 32 for _ in range(32)],
             "fixed_mobs": [{"id": str(i), "species_id": "slime", "x": i % 8 + 5, "y": i // 8 + 5,
                             "ai": ("random", "chase")[i % 2], "move_interval_ms": 100,
                             "dialogue": ["a", "b", "c", "d", "e"]} for i in range(24)]}
    request = {"performance": True, "world": world, "blocks": {"floor": {"player_walkable": True}},
               "player": [20, 20], "iterations": max(1, args.iterations), "samples": max(1, args.samples),
               "warmup": max(0, args.warmup)}
    with tempfile.TemporaryDirectory(prefix="kadoka-fixed-performance-") as directory:
        fixture = Path(directory) / "request.json"
        fixture.write_text(json.dumps(request), encoding="utf-8")
        process = subprocess.run([godot, "--headless", "--path", str(ROOT / "gdscript"), "--script",
                                  "res://tests/run_fixed_mobs_probe.gd", "--", str(fixture)],
                                 capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    if process.returncode or "SCRIPT ERROR" in process.stderr:
        print(process.stderr + process.stdout)
        return 1
    for line in process.stdout.splitlines():
        if line.startswith("KADOKA_FIXED_MOBS="):
            result = json.loads(base64.b64decode(line.split("=", 1)[1]))
            passed = result["microseconds"] <= 2000 and result["actors"] == 24
            print(f"{'OK' if passed else 'FAIL'} Godot fixed-mobs-update+snapshot (24 actors) "
                  f"{result['microseconds']:.2f}us <= 2000us "
                  f"[{int(result['iterations'])} iterations, {int(result['samples'])} samples, "
                  f"{int(result['warmup'])} warmup]")
            dialogue_passed = result["dialogue_microseconds"] <= 100
            print(f"{'OK' if dialogue_passed else 'FAIL'} Godot fixed-mob-talk (5 cards, last of 24 actors) "
                  f"{result['dialogue_microseconds']:.2f}us <= 100us")
            return 0 if passed and dialogue_passed else 1
    print("FAIL: missing Godot result")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
