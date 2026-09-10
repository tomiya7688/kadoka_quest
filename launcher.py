from pathlib import Path
import sys
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from kadoka_quest.apps.game import main as game_main
from kadoka_quest.apps.launcher import main as launcher_main
from kadoka_quest.apps.manage import main as manager_main


def main() -> None:
    if "--play" in sys.argv:
        sys.argv.remove("--play")
        game_main()
        return
    if "--manager" in sys.argv:
        sys.argv.remove("--manager")
        manager_main()
        return
    launcher_main()


def run() -> None:
    try:
        main()
    except Exception:
        if getattr(sys, "frozen", False) and "--smoke" in sys.argv:
            error_path = Path(sys.executable).resolve().parent / "smoke-error.txt"
            error_path.write_text(traceback.format_exc(), encoding="utf-8")
            raise SystemExit(1)
        raise


if __name__ == "__main__":
    run()
