# {
#   責務: [check_project_rules: check・project・rulesの公開機能・宣言を定義する]
#   フィールド: []
# }
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
    "docs/CODING_RULES.md",
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
#   責務: [imported_root: check・project・rulesのimported・基準ディレクトリを求める]
#   処理: [1: check・project・rulesのimported・基準ディレクトリを求める]
#   引数: [node: node（ast.Import | ast.ImportFrom）]
#   戻り値: [result: check・project・rulesのimported・基準ディレクトリを求めるための結果（str）]
# }
def imported_root(node: ast.Import | ast.ImportFrom) -> str:
    if isinstance(node, ast.Import):
        return node.names[0].name.split(".", 1)[0]
    return str(node.module or "").split(".", 1)[0]


# {
#   責務: [display_path: check・project・rulesのdisplay・パスを求める]
#   処理: [1: check・project・rulesのdisplay・パスを求める]
#   引数: [
#     path: パス（Path）
#     root: 基準ディレクトリ（Path | None）
#   ]
#   戻り値: [result: check・project・rulesのdisplay・パスを求めるための結果（str）]
# }
def display_path(path: Path, root: Path | None = None) -> str:
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
#   責務: [check: 必須パスとcoreの依存境界の診断をまとめます]
#   処理: [1: 必須パスとcoreの依存境界の診断をまとめます]
#   引数: []
#   戻り値: [result: 必須パス欠落とcore境界違反の診断一覧（list[str]）]
# }
def check() -> list[str]:
    # パス検査と依存検査は別関数に保ち、公開入口では結果だけを統合する。
    return [*required_path_errors(), *core_boundary_errors()]


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
