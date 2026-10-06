# {
#   責務: [generate_class_diagram: generate・クラス・diagramの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import argparse
import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


# {
#   責務: [render_class_diagram: クラス・diagramを表示用データを生成する]
#   処理: [1: クラス・diagramを表示用データを生成する]
#   引数: [source_root: 元データ・基準ディレクトリ（Path）]
#   戻り値: [result: クラス・diagramを表示用データを生成するための結果（str）]
# }
def render_class_diagram(source_root: Path) -> str:
    classes: list[tuple[str, list[str], list[str]]] = []
    for path in sorted(source_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            bases = [ast.unparse(base) for base in node.bases]
            methods = [
                item.name
                for item in node.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            classes.append((node.name, bases, methods))

    lines = ["classDiagram"]
    for name, bases, methods in classes:
        for base in bases:
            lines.append(f"    {base} <|-- {name}")
        lines.append(f"    class {name} {{")
        for method in methods:
            lines.append(f"        +{method}()")
        lines.append("    }")
    return "\n".join(lines) + "\n"


# {
#   責務: [main: generate・クラス・diagramのエントリ処理を実行する]
#   処理: [1: generate・クラス・diagramのエントリ処理を実行する]
#   引数: []
#   戻り値: [result: generate・クラス・diagramのエントリ処理を実行するための結果（int）]
# }
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a compact Mermaid class diagram from Python sources."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=REPO_ROOT / "src" / "kadoka_quest",
        help="Source tree to inspect.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "docs" / "generated" / "class_diagram.mmd",
        help="Generated Mermaid output.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when the generated document is missing or stale.",
    )
    args = parser.parse_args()

    source = args.source if args.source.is_absolute() else REPO_ROOT / args.source
    output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    content = render_class_diagram(source)

    if args.check:
        if not output.exists() or output.read_text(encoding="utf-8") != content:
            print(f"stale generated document: {output.relative_to(REPO_ROOT)}")
            return 1
        print("generated class diagram is current")
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    print(f"generated: {output.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
