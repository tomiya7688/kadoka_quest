from __future__ import annotations

import argparse
import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE = REPO_ROOT / "src" / "kadoka_quest"
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "generated" / "REPO_MAP.md"


def _format_arguments(arguments: ast.arguments, *, skip_first: bool = False) -> str:
    positional = [*arguments.posonlyargs, *arguments.args]
    defaults = [None] * (len(positional) - len(arguments.defaults)) + list(arguments.defaults)
    parts: list[str] = []
    for index, (argument, default) in enumerate(zip(positional, defaults)):
        if skip_first and index == 0:
            continue
        text = argument.arg
        if default is not None:
            text += f"={ast.unparse(default)}"
        parts.append(text)
        if arguments.posonlyargs and index + 1 == len(arguments.posonlyargs):
            parts.append("/")
    if arguments.vararg is not None:
        parts.append(f"*{arguments.vararg.arg}")
    elif arguments.kwonlyargs:
        parts.append("*")
    for argument, default in zip(arguments.kwonlyargs, arguments.kw_defaults):
        text = argument.arg
        if default is not None:
            text += f"={ast.unparse(default)}"
        parts.append(text)
    if arguments.kwarg is not None:
        parts.append(f"**{arguments.kwarg.arg}")
    return ", ".join(parts)


def _class_signature(node: ast.ClassDef) -> str:
    initializer = next(
        (
            item
            for item in node.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "__init__"
        ),
        None,
    )
    if initializer is None:
        return f"class {node.name}"
    arguments = _format_arguments(initializer.args, skip_first=True)
    return f"class {node.name}({arguments})"


def _function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    return f"{prefix} {node.name}({_format_arguments(node.args)})"


def public_symbols(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    symbols: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            symbols.append(_class_signature(node))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            symbols.append(_function_signature(node))
    return symbols


def _markdown_code(value: str) -> str:
    return f"`{value.replace('|', '&#124;')}`"


def render_repo_map(source_root: Path) -> str:
    rows: list[tuple[str, list[str]]] = []
    for path in sorted(source_root.rglob("*.py")):
        symbols = public_symbols(path)
        if not symbols:
            continue
        relative = path.relative_to(source_root).as_posix()
        rows.append((relative, symbols))

    lines = [
        "# Generated repository map",
        "",
        "Generated from `src/kadoka_quest/**/*.py`. Do not edit by hand.",
        "Only public top-level class/function signatures are included; implementation bodies and private helpers are omitted.",
        "",
        "| Module | Public top-level symbols |",
        "|---|---|",
    ]
    for relative, symbols in rows:
        rendered = "<br>".join(_markdown_code(symbol) for symbol in symbols)
        lines.append(f"| `{relative}` | {rendered} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a compact Python repository symbol map.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    source = args.source if args.source.is_absolute() else REPO_ROOT / args.source
    output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    content = render_repo_map(source)

    if args.check:
        if not output.exists() or output.read_text(encoding="utf-8") != content:
            print(f"stale generated document: {output.relative_to(REPO_ROOT)}")
            return 1
        print("generated repo map is current")
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    print(f"generated: {output.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
