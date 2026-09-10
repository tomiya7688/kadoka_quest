from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from kadoka_quest.apps.manage import main as developer_manager_main
from kadoka_quest.apps.ranch_manager import main as ranch_manager_main


def main() -> None:
    if os.environ.get("KADOKA_DEVELOPER_TOOLS") == "1":
        developer_manager_main()
    else:
        ranch_manager_main()


if __name__ == "__main__":
    main()
