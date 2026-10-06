# {
#   責務: [launcher: launcherの公開機能・宣言を定義する]
#   フィールド: []
# }
from pathlib import Path
import sys
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from kadoka_quest.apps.game import KadokaQuest, main as game_main
from kadoka_quest.apps.launcher import main as launcher_main
from kadoka_quest.apps.ranch_manager import main as ranch_manager_main
from kadoka_quest.apps.simulation_facility_hooks import install_simulation_facility_hooks
from kadoka_quest.apps.simulation_manager import main as simulation_manager_main

install_simulation_facility_hooks(KadokaQuest)


# {
#   責務: [main: launcherのエントリ処理を実行する]
#   処理: [1: launcherのエントリ処理を実行する]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def main() -> None:
    if "--play" in sys.argv:
        sys.argv.remove("--play")
        game_main()
        return
    if "--manager" in sys.argv:
        sys.argv.remove("--manager")
        ranch_manager_main()
        return
    if "--simulation-manager" in sys.argv:
        sys.argv.remove("--simulation-manager")
        simulation_manager_main()
        return
    launcher_main()


# {
#   責務: [run: launcherを実行する]
#   処理: [1: launcherを実行する]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
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
