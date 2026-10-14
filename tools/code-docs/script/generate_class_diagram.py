# {
#   責務: [generate_class_diagram: Pythonのトップレベルクラス・継承・メソッド名からMermaid図を生成/照合する開発用CLIです]
#   フィールド: []
# }
from __future__ import annotations

import argparse
import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


# {
#   責務: [render_class_diagram: 指定ディレクトリのPython ASTからトップレベルクラスのMermaid図本文を生成します]
#   処理: [1: クラス名・継承・直下のメソッド名を静的抽出し、クラス図本文へ順に並べます]
#   引数: [source_root: 再帰的にPythonソースを検索するディレクトリ。コードは実行しません（Path）]
#   戻り値: [result: クラス/継承/メソッド名を持つ末尾改行付きMermaid本文。図の描画や保存は行いません（str）]
# }
def render_class_diagram(source_root: Path) -> str:
    # コードをimportせずASTだけを読み、トップレベルのクラス宣言と直下のメソッドを抽出します。
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

    # 実装本文や内部状態を図へ転載せず、クラス名・継承・メソッド名だけを表示用本文へ並べます。
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
#   責務: [main: Pythonのクラス図をMermaidへ出力し、--checkでは保存済みの図の鮮度を照合します]
#   処理: [
#     1: CLIで指定されたPythonソースからクラス図の本文を生成します
#     2: --check指定時は既存ファイルと比較し、不一致や欠落なら失敗を返します
#     3: --checkがなければ指定出力先へUTF-8のMermaid本文を保存します
#   ]
#   引数: []
#   戻り値: [result: 図の保存または鮮度の一致なら0、--checkで不一致や欠落なら1（int）]
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
