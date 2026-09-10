from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from kadoka_quest.apps import block_editor as block_editor_app
from kadoka_quest.apps import data_creator as data_creator_app
from kadoka_quest.apps import manage as manage_app
from kadoka_quest.apps import map_editor as map_editor_app
from kadoka_quest.apps import monster_editor as monster_editor_app
from kadoka_quest.apps.developer_launcher import main as launcher_main


DEV_TOOLS = {
    "manage": manage_app.main,
    "block_editor": block_editor_app.main,
    "map_editor": map_editor_app.main,
    "monster_editor": monster_editor_app.main,
    "data_creator": data_creator_app.main,
}


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
    launcher_main()


if __name__ == "__main__":
    main()
