# {
#   責務: [data_validator: データ・検証処理の公開機能・宣言を定義する]
#   フィールド: []
# }
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from kadoka_quest.apps.data_validator import main


if __name__ == "__main__":
    main()
