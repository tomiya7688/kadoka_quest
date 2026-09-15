from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
TOOL_ROOT = Path(__file__).resolve().parents[1]
TARGET = REPO_ROOT / "src" / "kadoka_quest"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the pinned UPD Commander checker for Kadoka Quest.")
    parser.add_argument(
        "--advisory",
        action="store_true",
        help="Report UPD errors without failing. Warnings and attentions are already non-blocking.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    command = [sys.executable, "-m", "upd_commander_checker", str(TARGET)]
    try:
        result = subprocess.run(
            command,
            cwd=TOOL_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        print(f"CONFIG ERROR: UPD checker could not start: {exc}")
        return 2

    output = result.stdout.strip()
    error_output = result.stderr.strip()
    if output:
        print(output)
    if error_output:
        print(error_output, file=sys.stderr)

    if result.returncode in {0, 2}:
        return result.returncode
    if args.advisory:
        print("ADVISORY UPD errors were reported but are temporarily non-blocking")
        return 0
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
