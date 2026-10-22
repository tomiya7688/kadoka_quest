# {
#   責務: [balance_analyzer: balance・analyzerの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from kadoka_quest.data.repository import GameRepository
from kadoka_quest.devtools.balance_analyzer import BalanceAnalyzer, BalanceSettings


# {
#   責務: [parse_levels: レベル一覧を解析する]
#   処理: [1: レベル一覧を解析する]
#   引数: [value: 値（str）]
#   戻り値: [result: レベル一覧を解析するための結果（tuple[int, ...]）]
# }
def parse_levels(value: str) -> tuple[int, ...]:
    try:
        return tuple(sorted({int(level.strip()) for level in value.split(",") if level.strip()}))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("levels must be comma-separated integers") from exc


# {
#   責務: [main: balance・analyzerのエントリ処理を実行する]
#   処理: [1: balance・analyzerのエントリ処理を実行する]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def main() -> None:
    parser = argparse.ArgumentParser(description="Run reproducible non-learning monster balance simulations.")
    parser.add_argument("--levels", type=parse_levels, default=(1, 25, 50, 75, 100))
    parser.add_argument("--battles", type=int, default=20, help="battles per unordered pair and level")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--max-rounds", type=int, default=80)
    parser.add_argument("--species", nargs="*", help="optional species IDs; default is every species")
    parser.add_argument("--output", type=Path, default=Path("reports/balance_report.json"))
    arguments = parser.parse_args()

    analyzer = BalanceAnalyzer(
        GameRepository(),
        BalanceSettings(arguments.levels, arguments.battles, arguments.seed, arguments.max_rounds),
    )
    report = analyzer.analyze(arguments.species)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{arguments.output}: {len(report['matchups'])} matchup groups, {len(report['recommendations'])} recommendations")


if __name__ == "__main__":
    main()
