# {
#   責務: [check: 外部UPD設計検査ツールを起動し、Kadoka QuestのPython実装の責務と依存を検査します]
#   フィールド: []
# }
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
TOOL_ROOT = Path(__file__).resolve().parents[1]
TARGET = REPO_ROOT / "src" / "kadoka_quest"


# {
#   責務: [build_parser: Python実装のUPD検査について、エラーを非停止にする調査専用モードを受け付けます]
#   処理: [1: --advisoryだけを任意引数として定義し、既定のblocking検査と区別します]
#   引数: []
#   戻り値: [result: advisory調査モードの引数を解釈するパーサー（argparse.ArgumentParser）]
# }
def build_parser() -> argparse.ArgumentParser:
    # 調査専用モードを明示引数にし、既定では検査失敗を終了コードへ残す。
    parser = argparse.ArgumentParser(description="Run the installed UPD Commander checker for Kadoka Quest.")
    parser.add_argument(
        "--advisory",
        action="store_true",
        help="Report UPD errors without failing. Warnings and attentions are already non-blocking.",
    )
    return parser


# {
#   責務: [main: インストール済みUPD検査器でsrc/kadoka_questを検査し、診断と終了コードを返します]
#   処理: [1: 同じPythonから検査器を呼び、設定不備は常に失敗、検査エラーは調査モード以外で失敗にします]
#   引数: []
#   戻り値: [result: 検査成功0・検査失敗1・設定不備2。advisory指定時だけ検査失敗を報告後0にします（int）]
# }
def main() -> int:
    # 検証中のPythonから外部ツールを起動し、Playerの起動経路へ依存を足さない。
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

    # 外部検査の標準出力と診断出力を、終了コードの判定前にそのまま表示する。
    output = result.stdout.strip()
    error_output = result.stderr.strip()
    if output:
        print(output)
    if error_output:
        print(error_output, file=sys.stderr)

    # 設定不備はadvisory指定でも成功へ変換せず、検査失敗だけを調査時に許容する。
    if result.returncode in {0, 2}:
        return result.returncode
    if args.advisory:
        print("ADVISORY UPD errors were reported but are temporarily non-blocking")
        return 0
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
