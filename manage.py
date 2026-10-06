# {
#   責務: [manage: manageの公開機能・宣言を定義する]
#   フィールド: []
# }
from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from kadoka_quest.apps.manage import main as developer_manager_main
from kadoka_quest.apps.ranch_manager import main as ranch_manager_main


# {
#   責務: [main: manageのエントリ処理を実行する]
#   処理: [1: manageのエントリ処理を実行する]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def main() -> None:
    if os.environ.get("KADOKA_DEVELOPER_TOOLS") == "1":
        developer_manager_main()
    else:
        ranch_manager_main()


if __name__ == "__main__":
    main()
