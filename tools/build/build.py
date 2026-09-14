from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_quest.developer.build_core import build_distributions


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Kadoka Quest PyInstaller distributions.")
    parser.add_argument("--targets", choices=("player", "developer", "all"), default="all")
    parser.add_argument("--clean", action="store_true", help="Remove previous dist/build output before building.")
    args = parser.parse_args()

    try:
        outputs = build_distributions(
            source_root=PROJECT_ROOT,
            targets=args.targets,
            clean=args.clean,
        )
    except (OSError, RuntimeError) as exc:
        print(f"[failed] {exc}", file=sys.stderr)
        return 1

    for output in outputs:
        print(f"[ok] {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
