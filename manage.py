from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from kadoka_quest.apps.manage import main


if __name__ == "__main__":
    main()
