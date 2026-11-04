# {
#   責務: [check_project_rules: 必須ファイルの存在と、coreが画面/ファイルI/Oへ依存していないことを静的検査します]
#   フィールド: []
# }
from __future__ import annotations

import ast
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
CORE_ROOT = REPO_ROOT / "src" / "kadoka_quest" / "core"
SOURCE_ROOT = REPO_ROOT / "src"
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
    "docs/CODING_RULES.md",
    "docs/開発者向け/README.md",
    "docs/開発者向け/コーディング規約.md",
    "docs/開発者向け/CODING_RULES.md",
    "docs/開発者向け/COMMENT_RULES.md",
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
    "tools/upd-commander/requirements.txt",
    "tools/upd-commander/config/path.json",
    "tools/upd-commander/script/check.py",
    "tools/performance-check/script/check_runtime_performance.py",
)


# {
#   責務: [imported_root: ASTのimport文から禁止依存との照合に使う先頭モジュール名を取り出します]
#   処理: [1: ASTのimport文から禁止依存との照合に使う先頭モジュール名を取り出します]
#   引数: [node: 構文解析済みのimport/from文（ast.Import | ast.ImportFrom）]
#   戻り値: [result: pygame/osなどの先頭モジュール名。from文の指定がなければ空文字（str）]
# }
def imported_root(node: ast.Import | ast.ImportFrom) -> str:
    # 検査対象の依存をimportせず、文の種類に応じてモジュール名だけを読みます。
    if isinstance(node, ast.Import):
        return node.names[0].name.split(".", 1)[0]
    return str(node.module or "").split(".", 1)[0]


# {
#   責務: [display_path: 診断対象のパスをリポジトリ相対、指定基準相対、絶対パスの順に表示形式へ変換します]
#   処理: [1: 診断対象のパスをリポジトリ相対、指定基準相対、絶対パスの順に表示形式へ変換します]
#   引数: [
#     path: 診断に表示するファイルのパス（Path）
#     root: リポジトリ外の対象へ使う任意の相対表示基準（Path | None）
#   ]
#   戻り値: [result: 基準内なら相対パス、どちらの基準外でも対象を示すパス文字列（str）]
# }
def display_path(path: Path, root: Path | None = None) -> str:
    # 基準外でも例外にせず、利用者が診断対象を特定できる表示へ戻します。
    for base in (REPO_ROOT, root):
        if base is None:
            continue
        try:
            return str(path.relative_to(base))
        except ValueError:
            continue
    return str(path)


# {
#   責務: [core_boundary_errors: coreのPythonソースを静的解析し、禁止依存とopenによるI/Oを検出します]
#   処理: [1: coreのPythonソースを静的解析し、禁止依存とopenによるI/Oを検出します]
#   引数: [
#     root: core境界検査の対象ディレクトリ（Path）
#   ]
#   戻り値: [result: 解析失敗・禁止依存・禁止I/Oの診断一覧（list[str]）]
# }
def core_boundary_errors(root: Path = CORE_ROOT) -> list[str]:
    # coreのコードを実行せず、構文木から禁止依存とファイルI/Oを検出する。
    errors: list[str] = []
    for path in sorted(root.glob("*.py")):
        shown_path = display_path(path, root)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            errors.append(f"{shown_path}: parse failed: {exc}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imported = imported_root(node)
                if imported in FORBIDDEN_CORE_IMPORTS:
                    errors.append(
                        f"{shown_path}:{node.lineno}: core must not import {imported}"
                    )
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open":
                errors.append(
                    f"{shown_path}:{node.lineno}: core must not perform file I/O with open()"
                )
    return errors



# {
#   責務: [class_base_name: Pythonクラス定義の基底型式から、リポジトリ内クラス照合に使う末尾の型名を取り出します]
#   処理: [
#     1: 単純名ならその識別子を返します
#     2: 属性参照なら末尾属性名を返します
#     3: それ以外の式は静的に安全に解決できないため空文字を返します
#   ]
#   引数: [node: クラス定義の基底型を表すASTノード（ast.expr）]
#   戻り値: [result: 照合可能な基底クラス名、または空文字（str）]
# }
def class_base_name(node: ast.expr) -> str:
    # 呼び出し等を推測して誤検出せず、宣言から明示的に読める型名だけを扱う。
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


# {
#   責務: [class_is_abstract: PythonクラスがABC系の基底またはabstractmethod宣言を持つ明示的な抽象クラスか判定します]
#   処理: [
#     1: ABC基底またはABCMetaメタクラスを確認します
#     2: クラス直下のメソッドにabstractmethodデコレータがあれば抽象クラスと判定します
#   ]
#   引数: [node: 検査対象のクラス定義（ast.ClassDef）]
#   戻り値: [result: 明示的な抽象クラスならTrue、それ以外はFalse（bool）]
# }
def class_is_abstract(node: ast.ClassDef) -> bool:
    # 明示的なABC宣言だけを例外にし、名前やdocstringから抽象性を推測しない。
    if any(class_base_name(base) == "ABC" for base in node.bases):
        return True
    for keyword in node.keywords:
        if keyword.arg == "metaclass" and class_base_name(keyword.value) == "ABCMeta":
            return True
    for member in node.body:
        if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in member.decorator_list:
            if class_base_name(decorator) == "abstractmethod":
                return True
    return False


# {
#   責務: [concrete_inheritance_chain_errors: リポジトリ所有Pythonコードから具象クラス起点の三段以上の継承を静的検出します]
#   処理: [
#     1: 対象配下のPythonファイルを解析し、重複しないクラス名・基底名・抽象性を収集します
#     2: C→B→Aの順でリポジトリ所有クラスを解決します
#     3: 起点Aが具象クラスなら規約違反としてCの宣言位置を診断します
#   ]
#   引数: [root: 検査対象のリポジトリ所有Pythonソースの基準ディレクトリ（Path）]
#   戻り値: [result: 具象クラス起点の連続継承に対する診断一覧（list[str]）]
# }
def concrete_inheritance_chain_errors(root: Path = SOURCE_ROOT) -> list[str]:
    # 同名クラスを誤って別モジュール間で結び付けないため、名前が一意な宣言だけを自動判定に使う。
    definitions: dict[str, list[tuple[Path, ast.ClassDef]]] = {}
    for path in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                definitions.setdefault(node.name, []).append((path, node))

    unique = {name: values[0] for name, values in definitions.items() if len(values) == 1}
    errors: list[str] = []
    for child_name, (child_path, child) in unique.items():
        for child_base in child.bases:
            middle_name = class_base_name(child_base)
            middle_entry = unique.get(middle_name)
            if middle_entry is None:
                continue
            _, middle = middle_entry
            for middle_base in middle.bases:
                root_name = class_base_name(middle_base)
                root_entry = unique.get(root_name)
                if root_entry is None:
                    continue
                _, root_class = root_entry
                if class_is_abstract(root_class):
                    continue
                shown_path = display_path(child_path, root)
                errors.append(
                    f"{shown_path}:{child.lineno}: concrete inheritance chain is prohibited: "
                    f"{root_name} -> {middle_name} -> {child_name}"
                )
    return errors


# {
#   責務: [required_path_errors: プロジェクトの必須パスが存在するか確認します]
#   処理: [1: プロジェクトの必須パスが存在するか確認します]
#   引数: [
#     repo_root: 必須パスを解決するリポジトリのルート（Path）
#   ]
#   戻り値: [result: 欠落した必須パスの診断一覧（list[str]）]
# }
def required_path_errors(repo_root: Path = REPO_ROOT) -> list[str]:
    # 欠落ファイルを自動生成せず、必須パスの不足を診断として返す。
    return [f"missing required project path: {relative}" for relative in REQUIRED_PATHS if not (repo_root / relative).exists()]


# {
#   責務: [check: 必須パス・core依存境界・具象クラス起点の連続継承の診断をまとめます]
#   処理: [1: 必須パス・core依存境界・継承規約の診断をまとめます]
#   引数: []
#   戻り値: [result: 必須パス欠落・core境界違反・継承規約違反の診断一覧（list[str]）]
# }
def check() -> list[str]:
    # パス検査と依存検査は別関数に保ち、公開入口では結果だけを統合する。
    return [*required_path_errors(), *core_boundary_errors(), *concrete_inheritance_chain_errors()]


# {
#   責務: [main: プロジェクト規約の静的検査を実行し、診断と合否を表示します]
#   処理: [1: プロジェクト規約の静的検査を実行し、診断と合否を表示します]
#   引数: []
#   戻り値: [result: 違反なしなら0、違反があれば1（int）]
# }
def main() -> int:
    # 静的な診断を表示し、規約違反をCIから判別できる終了コードにする。
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
