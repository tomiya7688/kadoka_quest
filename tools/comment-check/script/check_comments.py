"""Read-only declaration-comment coverage checks for this project's languages.

This is a project contract guard, not the upstream JSON-like Comment Outs
parser or a natural-language correctness validator. Never import game modules.
"""
# {
#   責務: [check_comments: Read-only declaration-comment coverage checks for this project's languages.]
#   フィールド: []
# }
from __future__ import annotations

import argparse
import ast
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
SEMANTIC_KEYS = {
    "責務": "responsibility", "responsibility": "responsibility",
    "処理": "action", "action": "action",
    "引数": "param", "param": "param", "parameters": "param",
    "戻り値": "return", "return": "return",
    "フィールド": "fields", "fields": "fields",
    "副作用": "side_effect", "sideeffect": "side_effect",
    "エラー": "error", "error": "error", "補足": "note", "note": "note",
}
SUPPORTED = {".py", ".gd", ".bat", ".yml"}
SECTION = re.compile(r"^\s*([^:\[\]]+):\s*\[(.*)$")
ENTRY = re.compile(r"^\s*([^:]+):\s*(.+?)\s*$")
GD_FUNCTION = re.compile(r"^(\s*)(?:static )?func\s+(\w+)\((.*)\)\s*(?:->\s*[\w\[\], ]+)?\s*:\s*(?:#.*)?$")


# {
#   責務: [
#     tracked_sources: 追跡中の実行ソースだけをGit索引から列挙する
#   ]
#   処理: [
#     1: git ls-files -zを読み、日本語や空白を含むパスを保持する
#     2: Python/GDScript/batchと実行CIだけを選び、順序を固定する
#   ]
#   引数: [
#     root: 基準ディレクトリ（Path）
#   ]
#   戻り値: [
#     result: 対象Path一覧。未追跡の私有ファイルを走査しない
#   ]
# }
def tracked_sources(root: Path) -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True,
    )
    names = completed.stdout.decode("utf-8").split("\0")
    return sorted(root / name for name in names if name and Path(name).suffix in SUPPORTED
                  and (Path(name).suffix != ".yml" or name.startswith(".github/workflows/")))


# {
#   責務: [
#     declaration_parameters: Python宣言の全引数名を取得する
#   ]
#   処理: [
#     1: 位置専用・通常・keyword専用・可変長引数を名前一覧へまとめる
#   ]
#   引数: [
#     node: node（ast.FunctionDef | ast.AsyncFunctionDef）
#   ]
#   戻り値: [
#     result: self/clsも含む実際の引数名一覧
#   ]
# }
def declaration_parameters(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    parameters = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    parameters += [item for item in (node.args.vararg, node.args.kwarg) if item]
    return [item.arg for item in parameters]


# {
#   責務: [split_parameters: Split a GDScript signature without splitting collection/string defaults.]
#   処理: [1: Split a GDScript signature without splitting collection/string defaults.]
#   引数: [text: 文字列（str）]
#   戻り値: [result: Split a GDScript signature without splitting collection/string defaults.ための結果（list[str]）]
# }
def split_parameters(text: str) -> list[str]:
    """Split a GDScript signature without splitting collection/string defaults."""
    entries = []
    start = 0
    depth = 0
    quote = None
    escaped = False
    for index, char in enumerate(text):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in ("\"", "'"):
            quote = char
        elif char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            entries.append(text[start:index].strip())
            start = index + 1
    if text[start:].strip():
        entries.append(text[start:].strip())
    return [re.match(r"\w+", entry).group(0) for entry in entries]


# {
#   責務: [
#     python_declarations: ASTから非公開・ネスト・decorator付きのPython宣言も列挙する
#   ]
#   処理: [
#     1: ソースを解析しclass/function/async functionを走査する
#     2: decoratorを含む宣言開始行と名前/種別/引数名を取得する
#   ]
#   引数: [
#     text: 文字列（str）
#   ]
#   戻り値: [
#     result: 0始まり開始行・名前・種別・引数名の一覧
#   ]
# }
def python_declarations(text: str) -> list[tuple[int, str, str, list[str]]]:
    tree = ast.parse(text)
    result = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            line = min([node.lineno, *[item.lineno for item in node.decorator_list]]) - 1
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            params = [] if kind == "class" else declaration_parameters(node)
            result.append((line, node.name, kind, params))
    return result


# {
#   責務: [
#     gdscript_declarations: 名前付きGDScript宣言を複数行シグネチャも含めて列挙する
#   ]
#   処理: [
#     1: 名前付き関数のシグネチャを結合し、解析できない宣言を拒否する
#     2: 引数名と開始行を抽出し、ネストしたclassも追加する
#   ]
#   引数: [
#     text: 文字列（str）
#   ]
#   戻り値: [
#     result: 宣言一覧。未対応/破損したシグネチャはValueError
#   ]
# }
def gdscript_declarations(text: str) -> list[tuple[int, str, str, list[str]]]:
    result = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if re.match(r"^\s*(?:static )?func\s+\w+\(", line):
            signature = line
            end = index
            match = GD_FUNCTION.match(signature)
            while not match and end + 1 < len(lines) and end - index < 128:
                end += 1
                signature += " " + lines[end].strip()
                match = GD_FUNCTION.match(signature)
            if not match:
                raise ValueError(f"unsupported GDScript declaration at line {index + 1}")
            result.append((index, match[2], "function", split_parameters(match[3])))
        else:
            match = re.match(r"^\s*class\s+(\w+)", line)
            if match:
                result.append((index, match[1], "class", []))
    return result


# {
#   責務: [comment_before: Find only the contiguous block belonging to a declaration, not a sibling.]
#   処理: [1: Find only the contiguous block belonging to a declaration, not a sibling.]
#   引数: [
#     lines: lines（list[str]）
#     line: line（int）
#     prefix: prefix（str）
#   ]
#   戻り値: [result: Find only the contiguous block belonging to a declaration, not a sibling.ための結果（list[str]）]
# }
def comment_before(lines: list[str], line: int, prefix: str = "#") -> list[str]:
    """Find only the contiguous block belonging to a declaration, not a sibling."""
    index = line - 1
    while index >= 0 and not lines[index].strip():
        index -= 1
    # Ordinary notes may sit between a structured block and its declaration.
    while index >= 0 and lines[index].lstrip().startswith(prefix + " "):
        if lines[index].lstrip() == prefix + " }":
            break
        index -= 1
    found = []
    while index >= 0 and lines[index].lstrip().startswith(prefix + " "):
        payload = lines[index].lstrip()[len(prefix):].strip()
        found.append(payload)
        if payload == "{":
            break
        index -= 1
    found.reverse()
    if not found or found[0] != "{" or found[-1] != "}":
        return []
    return found


# {
#   責務: [
#     parse_block: 平坦な構造化コメントをSemantic Key単位へ解析する
#   ]
#   処理: [
#     1: 日本語/英語の既知キーを共通の意味へ解決し、未知キーは保持する
#     2: リストの名前/説明を集め、重複・空欄・閉じ忘れを記録する
#   ]
#   引数: [
#     block: ブロック（list[str]）
#   ]
#   戻り値: [
#     result: 項目別の説明一覧と構造エラー一覧
#   ]
# }
def parse_block(block: list[str]) -> tuple[dict[str, list[tuple[str, str]]], list[str]]:
    sections = {}
    errors = []
    current = None
    for line in block[1:-1]:
        match = SECTION.match(line)
        if match:
            if current is not None:
                errors.append("unclosed section: " + current)
            raw_key = match[1].strip()
            key = SEMANTIC_KEYS.get(raw_key.casefold(), raw_key)
            if key in sections:
                errors.append("duplicate semantic key: " + key)
            sections[key] = []
            content = match[2].strip()
            current = key
            if content.endswith("]"):
                content = content[:-1].strip()
                current = None
            if content:
                entry = ENTRY.match(content)
                if entry:
                    sections[key].append((entry[1].strip(), entry[2].strip()))
                else:
                    errors.append("blank/malformed entry: " + raw_key)
        elif line == "]":
            if current is None:
                errors.append("unexpected closing bracket")
            current = None
        elif current:
            entry = ENTRY.match(line)
            if entry:
                sections[current].append((entry[1].strip(), entry[2].strip()))
            else:
                errors.append("blank/malformed entry: " + current)
        else:
            errors.append("malformed section: " + line)
    if current:
        errors.append("unclosed section: " + current)
    return sections, errors


# {
#   責務: [
#     block_errors: 宣言名・必須項目・実引数と構造化コメントの対応を検査する
#   ]
#   処理: [
#     1: 必須Semantic Keyと責務内の宣言名を照合する
#     2: 関数では実引数名、処理番号、戻り値の説明を検証する
#   ]
#   引数: [
#     block: ブロック（list[str]）
#     name: 名前（str）
#     kind: 種別（str）
#     params: params（list[str]）
#   ]
#   戻り値: [
#     result: 不一致の説明一覧。文章の自然言語正確性は判定しない
#   ]
# }
def block_errors(block: list[str], name: str, kind: str, params: list[str]) -> list[str]:
    if not block:
        return ["missing JSON-like declaration comment"]
    sections, errors = parse_block(block)
    required = {"responsibility", "fields"} if kind == "class" else {"responsibility", "action", "param", "return"}
    for key in sorted(required - sections.keys()):
        errors.append("missing semantic key: " + key)
    responsibilities = sections.get("responsibility", [])
    if not any(identifier == name for identifier, _ in responsibilities):
        errors.append("missing JSON-like declaration comment for " + name + " (responsibility name mismatch)")
    if kind == "function":
        declared = [identifier for identifier, _ in sections.get("param", [])]
        if sorted(declared) != sorted(params):
            errors.append(f"parameter mismatch: expected {params}, documented {declared}")
        actions = [identifier for identifier, _ in sections.get("action", [])]
        if actions != [str(index + 1) for index in range(len(actions))] or not actions:
            errors.append("actions must be nonempty and numbered from 1")
        if not sections.get("return"):
            errors.append("return must describe the result, including void/None")
    return errors


# {
#   責務: [
#     check_source: 1ソースの全宣言とモジュール/スクリプトの注釈を静的に検査する
#   ]
#   処理: [
#     1: UTF-8ソースを読み、言語別に宣言と入力名を列挙する
#     2: 各宣言に隣接するブロックとヘッダーの項目を検証する
#   ]
#   引数: [
#     path: パス（Path）
#   ]
#   戻り値: [
#     result: 宣言数と位置付きエラー一覧。対象を実行/importしない
#   ]
# }
def check_source(path: Path) -> tuple[int, list[str]]:
    """Check every named declaration, including private and nested definitions."""
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    if path.suffix == ".py":
        declarations = python_declarations(text)
    elif path.suffix == ".gd":
        declarations = gdscript_declarations(text)
    elif path.suffix == ".bat":
        declarations = []
        labels = [(index, line[1:].strip()) for index, line in enumerate(lines) if re.match(r"^:[^:]", line)]
        for slot, (index, name) in enumerate(labels):
            end = labels[slot + 1][0] if slot + 1 < len(labels) else len(lines)
            # Goto-only error labels have no positional parameters, unlike call :find_issue.
            body = "\n".join(line for line in lines[index + 1:end] if not line.lstrip().startswith("rem "))
            params = sorted(set(re.findall(r"%~?([1-9])", body)))
            declarations.append((index, name, "function", params))
    else:
        declarations = []  # CI workflow: script/module contract, not class/function syntax.
    errors = []
    prefix = "rem" if path.suffix == ".bat" else "#"
    for index, name, kind, params in declarations:
        for error in block_errors(comment_before(lines, index, prefix), name, kind, params):
            errors.append(f"{path}:{index + 1}: {error}")
    # Module/script entry coverage also covers wrappers and empty __init__.py files.
    blocks = [index for index, line in enumerate(lines) if line.lstrip() == prefix + " {"]
    if not blocks:
        errors.append(f"{path}: missing module/script comment")
    else:
        header_end = next((index + 1 for index in range(blocks[0] + 1, len(lines))
                           if lines[index].lstrip() == prefix + " }"), 0)
        first_code = next((index for index, line in enumerate(lines)
                           if line.strip() and not line.lstrip().startswith((prefix, "@echo off"))), len(lines))
        if path.suffix in (".gd", ".bat", ".yml") and blocks[0] > first_code:
            errors.append(f"{path}: module/script header must precede executable content")
        header = comment_before(lines, header_end, prefix)
        kind = "function" if path.suffix == ".bat" else "class"
        params = ["argv"] if path.suffix == ".bat" else []
        for error in block_errors(header, path.stem, kind, params):
            errors.append(f"{path}:1: module/script: {error}")
    return len(declarations), errors


# {
#   責務: [
#     check: 指定されたソース群の検査結果を集約する
#   ]
#   処理: [
#     1: 各ファイルを静的検査する
#     2: 読込/構文/未対応宣言の失敗もエラーとして残す
#   ]
#   引数: [
#     paths: パス一覧（list[Path]）
#   ]
#   戻り値: [
#     result: 総宣言数とエラー一覧
#   ]
# }
def check(paths: list[Path]) -> tuple[int, list[str]]:
    declarations = 0
    errors = []
    for path in paths:
        try:
            count, findings = check_source(path)
            declarations += count
            errors.extend(findings)
        except (OSError, UnicodeError, SyntaxError, ValueError, AttributeError) as exc:
            errors.append(f"{path}: cannot inspect source: {exc}")
    return declarations, errors


# {
#   責務: [
#     main: CLI指定または追跡ソースを検査して結果と終了コードを返す
#   ]
#   処理: [
#     1: 引数を読み、個別パスまたはGit索引の対象を取得する
#     2: 検査結果と総数を表示し、不一致/列挙失敗を成功扱いしない
#   ]
#   引数: []
#   戻り値: [
#     result: 成功0、検査または対象列挙の失敗1
#   ]
# }
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()
    try:
        paths = args.paths or tracked_sources(args.root)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"[FAIL] cannot enumerate tracked source: {exc}")
        return 1
    count, errors = check(paths)
    for error in errors:
        print(error)
    print(f"[{'FAIL' if errors else 'OK'}] comments: {len(paths)} files, {count} declarations, {len(errors)} errors")
    return int(bool(errors))


if __name__ == "__main__":
    sys.exit(main())
