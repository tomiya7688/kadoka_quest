#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path


def imports(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeError):
        return []

    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            result.add("." * node.level + (node.module or ""))
    return sorted(result)


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit a compact Python file/import index as JSON.")
    parser.add_argument("root", nargs="?", type=Path, default=Path("src/kadoka_quest"))
    parser.add_argument("--limit", type=int, default=300)
    args = parser.parse_args()

    root = args.root.resolve()
    rows: list[dict[str, object]] = []
    truncated = False
    for path in sorted(root.rglob("*.py")):
        if any(part in {"__pycache__", ".venv", "venv"} for part in path.parts):
            continue
        if len(rows) >= args.limit:
            truncated = True
            break
        rows.append({"file": path.relative_to(root).as_posix(), "imports": imports(path)})

    print(
        json.dumps(
            {"root": root.name, "files": rows, "truncated": truncated},
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
