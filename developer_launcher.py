from pathlib import Path
import sys
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from kadoka_quest.apps import block_editor as block_editor_app
from kadoka_quest.apps import data_creator as data_creator_app
from kadoka_quest.apps import game as game_app
from kadoka_quest.apps import manage as manage_app
from kadoka_quest.apps import map_editor as map_editor_app
from kadoka_quest.apps import monster_editor as monster_editor_app
from kadoka_quest.apps.developer_launcher import main as launcher_main
from kadoka_quest.developer.build_core import (
    PLAYER_TEMPLATE_DIR,
    build_distributions,
    materialize_player_distribution,
)
from kadoka_quest.developer.distribution_smoke import smoke_distributions
from kadoka_quest.developer.project_validator import ProjectValidator
from kadoka_quest.paths import PROJECT_ROOT, is_frozen


DEV_TOOLS = {
    "manage": manage_app.main,
    "block_editor": block_editor_app.main,
    "map_editor": map_editor_app.main,
    "monster_editor": monster_editor_app.main,
    "data_creator": data_creator_app.main,
}
AUTOMATION_LOGS = {
    "--validate-project": "project-validation.log",
    "--build-player": "player-build.log",
    "--smoke-player-build": "player-smoke.log",
}


def _dist_root() -> Path:
    return PROJECT_ROOT / "dist"


def build_player() -> None:
    if is_frozen():
        output = materialize_player_distribution(
            PROJECT_ROOT / PLAYER_TEMPLATE_DIR / "KadokaQuest",
            content_root=PROJECT_ROOT,
            dist_root=_dist_root(),
        )
        print(f"[ok] {output}")
        return

    outputs = build_distributions(
        source_root=Path(__file__).resolve().parent,
        content_root=PROJECT_ROOT,
        dist_root=_dist_root(),
        build_root=PROJECT_ROOT / "build" / "pyinstaller",
        targets="player",
        clean=True,
    )
    for output in outputs:
        print(f"[ok] {output}")


def smoke_player_build() -> None:
    smoke_distributions(_dist_root(), targets="player")


def validate_project() -> None:
    report = ProjectValidator(PROJECT_ROOT / "data", PROJECT_ROOT / "assets").validate()
    print(report.summary(detail_limit=20))
    if not report.ok:
        raise SystemExit(1)


def main() -> None:
    if "--dev-tool" in sys.argv:
        index = sys.argv.index("--dev-tool")
        try:
            tool_name = sys.argv[index + 1]
        except IndexError as exc:
            raise SystemExit("--dev-tool requires a tool name") from exc
        del sys.argv[index:index + 2]
        try:
            tool_main = DEV_TOOLS[tool_name]
        except KeyError as exc:
            raise SystemExit(f"unknown developer tool: {tool_name}") from exc
        tool_main()
        return
    if "--player-preview" in sys.argv:
        sys.argv.remove("--player-preview")
        game_app.main()
        return
    if "--validate-project" in sys.argv:
        sys.argv.remove("--validate-project")
        validate_project()
        return
    if "--build-player" in sys.argv:
        sys.argv.remove("--build-player")
        build_player()
        return
    if "--smoke-player-build" in sys.argv:
        sys.argv.remove("--smoke-player-build")
        smoke_player_build()
        return
    launcher_main()


def run() -> None:
    automation_flag = next((flag for flag in AUTOMATION_LOGS if flag in sys.argv), None)
    redirected = None
    if automation_flag and is_frozen():
        log_root = PROJECT_ROOT / "UserData" / "developer"
        log_root.mkdir(parents=True, exist_ok=True)
        redirected = (log_root / AUTOMATION_LOGS[automation_flag]).open("w", encoding="utf-8")
        sys.stdout = redirected
        sys.stderr = redirected

    try:
        main()
    except Exception:
        if automation_flag:
            traceback.print_exc()
            raise SystemExit(1)
        if getattr(sys, "frozen", False) and "--smoke" in sys.argv:
            error_path = Path(sys.executable).resolve().parent / "smoke-error.txt"
            error_path.write_text(traceback.format_exc(), encoding="utf-8")
            raise SystemExit(1)
        raise
    finally:
        if redirected is not None:
            redirected.flush()
            redirected.close()


if __name__ == "__main__":
    run()
