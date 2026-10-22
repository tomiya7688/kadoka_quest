# {
#   責務: [test_distribution: test・distributionの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIST_ROOT = PROJECT_ROOT / "dist"
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_quest.developer.distribution_smoke import smoke_distributions


# {
#   責務: [main: test・distributionのエントリ処理を実行する]
#   処理: [1: test・distributionのエントリ処理を実行する]
#   引数: []
#   戻り値: [result: test・distributionのエントリ処理を実行するための結果（int）]
# }
def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test built Kadoka Quest distributions as external processes.")
    parser.add_argument("--targets", choices=("player", "developer", "all"), default="all")
    parser.add_argument("--dist-root", type=Path, default=DEFAULT_DIST_ROOT)
    args = parser.parse_args()

    try:
        smoke_distributions(args.dist_root, targets=args.targets)
    except (AssertionError, OSError, subprocess.SubprocessError) as exc:
        print(f"[failed] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
