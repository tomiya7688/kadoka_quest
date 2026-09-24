"""Generate a deterministic public-symbol index without importing game code."""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)


def signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    arguments = deepcopy(node.args)
    # Keep optionality, not potentially large implementation expressions.
    arguments.defaults = [ast.Constant(value=Ellipsis) for _ in arguments.defaults]
    arguments.kw_defaults = [
        None if value is None else ast.Constant(value=Ellipsis)
        for value in arguments.kw_defaults
    ]
    prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
    returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    return f"{prefix}{node.name}({ast.unparse(arguments)}){returns}"


def public_symbols(tree: ast.Module) -> list[str]:
    lines = []
    for node in tree.body:
        if isinstance(node, FUNCTIONS) and not node.name.startswith("_"):
            lines.append(signature(node))
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            bases = ", ".join(ast.unparse(base) for base in node.bases)
            lines.append(f"class {node.name}" + (f"({bases})" if bases else ""))
            for method in node.body:
                if isinstance(method, FUNCTIONS) and (
                    not method.name.startswith("_") or method.name == "__init__"
                ):
                    lines.append("  " + signature(method))
    return lines


def render_repo_map(source: Path) -> str:
    if not source.is_dir():
        raise ValueError(f"Source directory does not exist: {source}")
    lines = [
        "# REPO_MAP (generated)",
        "",
        "Do not edit. Regenerate: `python tools/code-docs/script/generate_repo_map.py`.",
        "Read the matching CODEMAP row first, then search this index for its file/class.",
        "Paths are relative to the source directory (default: src/).",
        "Public top-level classes/functions and direct public methods, including __init__, only.",
        "Defaults are abbreviated as ...; source files remain authoritative.",
        "Bodies, docstrings, private helpers, nested definitions and call graphs are omitted.",
        "",
    ]
    for path in sorted(source.rglob("*.py"), key=lambda item: item.relative_to(source).as_posix()):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        symbols = public_symbols(tree)
        if symbols:
            lines.extend([f"## {path.relative_to(source).as_posix()}", "", "```text", *symbols, "```", ""])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=REPO_ROOT / "src")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "docs/generated/REPO_MAP.md")
    parser.add_argument("--check", action="store_true", help="Check freshness without writing.")
    args = parser.parse_args(argv)
    source = args.source if args.source.is_absolute() else REPO_ROOT / args.source
    output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    try:
        content = render_repo_map(source)
        if args.check:
            if not output.exists() or output.read_text(encoding="utf-8") != content:
                print(f"stale repo map: {output}")
                return 1
            print("repo map is current")
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(content, encoding="utf-8", newline="\n")
            print(f"repo map generated ({len(content.encode('utf-8'))} bytes)")
    except (OSError, SyntaxError, ValueError) as error:
        print(f"repo map failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
