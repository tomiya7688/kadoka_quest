# {
#   責務: [build: buildの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_quest.developer.build_core import build_distributions, install_player_runtime_template


# {
#   責務: [main: buildのエントリ処理を実行する]
#   処理: [1: buildのエントリ処理を実行する]
#   引数: []
#   戻り値: [result: buildのエントリ処理を実行するための結果（int）]
# }
def main() -> int:
    parser = argparse.ArgumentParser(description="Build Kadoka Quest PyInstaller distributions.")
    parser.add_argument("--targets", choices=("player", "developer", "all"), default="all")
    parser.add_argument("--clean", action="store_true", help="Remove previous dist/build output before building.")
    args = parser.parse_args()

    # A Developer distribution always receives a Player runtime snapshot from
    # the same source revision. Developer-only builds therefore compile Player
    # as staging input and remove the standalone Player result afterwards.
    effective_targets = "all" if args.targets == "developer" else args.targets
    try:
        outputs = build_distributions(
            source_root=PROJECT_ROOT,
            targets=effective_targets,
            clean=args.clean,
        )
        by_name = {path.name: path for path in outputs}
        if "KadokaQuestDeveloper" in by_name:
            install_player_runtime_template(
                by_name["KadokaQuestDeveloper"],
                by_name["KadokaQuest"],
            )
        if args.targets == "developer":
            shutil.rmtree(by_name["KadokaQuest"], ignore_errors=True)
            outputs = [by_name["KadokaQuestDeveloper"]]
    except (OSError, RuntimeError) as exc:
        print(f"[failed] {exc}", file=sys.stderr)
        return 1

    for output in outputs:
        print(f"[ok] {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
