# {
#   責務: [game_evaluator: 評価専用セーブを選び、非対話探索のJSONレポートを出力します]
#   フィールド: []
# }
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


# {
#   責務: [main: CLIで選んだ評価用セーブをゲーム読込前に設定し、探索結果を指定先へ保存します]
#   処理: [1: 引数から評価用セーブと出力先を決め、ゲームを読み込み探索レポートを保存します]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def main() -> None:
    parser = argparse.ArgumentParser(description="Run a headless, non-interactive Kadoka Quest exploration evaluation.")
    parser.add_argument("--steps", type=int, default=2_000)
    parser.add_argument("--output", type=Path, default=Path("reports/game_evaluation.json"))
    parser.add_argument("--save-dir", type=Path, help="isolated save root; defaults beside the report")
    arguments = parser.parse_args()
    output = arguments.output
    save_dir = arguments.save_dir or output.parent / "evaluator_save"
    # 通常プレイ用の環境変数を継承していても、評価では明示指定またはレポート隣の専用領域を使います。
    os.environ["KADOKA_SAVE_DIR"] = str(save_dir.resolve())

    from kadoka_quest.devtools.game_evaluator import GameEvaluationRunner

    report = GameEvaluationRunner.from_default_game().run(arguments.steps)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{output}: {report['status']}; maps={len(report['visited_maps'])}; entries={len(report['entries'])}")


if __name__ == "__main__":
    main()
