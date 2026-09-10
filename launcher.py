from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from kadoka_quest.apps.game import main as game_main
from kadoka_quest.apps.launcher import main as launcher_main


def main() -> None:
    if "--play" in sys.argv:
        sys.argv.remove("--play")
        game_main()
        return
    launcher_main()


if __name__ == "__main__":
    main()
