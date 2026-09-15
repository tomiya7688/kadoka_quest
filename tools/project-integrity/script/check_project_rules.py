from __future__ import annotations

import ast
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
CORE_ROOT = REPO_ROOT / "src" / "kadoka_quest" / "core"
FORBIDDEN_CORE_IMPORTS = {
    "pygame",
    "pathlib",
    "os",
    "io",
    "json",
    "shutil",
    "subprocess",
}
REQUIRED_PATHS = (
    "AGENTS.md",
    "README.md",
    "docs/FORMATS.md",
    "docs/context/WORKFLOW.md",
    "launcher.py",
    "developer_launcher.py",
    "src/kadoka_quest/application/app_command.py",
    "src/kadoka_quest/application/runtime_orchestrator.py",
    "src/kadoka_quest/apps/game.py",
    "src/kadoka_quest/core/battle.py",
    "src/kadoka_quest/data/repository.py",
    "tools/code-docs/script/generate_class_diagram.py",
)


def imported_root(node: ast.Import | ast.ImportFrom) -> str:
    if isinstance(node, ast.Import):
        return node.names[0].name.split(".", 1)[0]
    return str(node.module or "").split(".", 1)[0]


def core_boundary_errors(root: Path = CORE_ROOT) -> list[str]:
    errors: list[str] = []
    for path in sorted(root.glob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            errors.append(f"{path.relative_to(REPO_ROOT)}: parse failed: {exc}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imported = imported_root(node)
                if imported in FORBIDDEN_CORE_IMPORTS:
                    errors.append(
                        f"{path.relative_to(REPO_ROOT)}:{node.lineno}: "
                        f"core must not import {imported}"
                    )
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open":
                errors.append(
                    f"{path.relative_to(REPO_ROOT)}:{node.lineno}: core must not perform file I/O with open()"
                )
    return errors


def required_path_errors(repo_root: Path = REPO_ROOT) -> list[str]:
    return [f"missing required project path: {relative}" for relative in REQUIRED_PATHS if not (repo_root / relative).exists()]


def check() -> list[str]:
    return [*required_path_errors(), *core_boundary_errors()]


def main() -> int:
    errors = check()
    if errors:
        print(f"[FAIL] project rules: {len(errors)}")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[OK] project rules")
    return 0


if __name__ == "__main__":
    sys.exit(main())
