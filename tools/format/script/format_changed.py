"""作業ブランチで追加したPythonファイルだけを、固定版のRuffで整形または整形確認します。"""

# {
#   責務: [format_changed: 比較元ブランチとの差分で新しく追加されたPythonファイルを選び、固定版Ruffのformatで整形、または--checkで書き換えずに整形漏れを検出します]
#   フィールド: [ROOT: Gitコマンドを実行するリポジトリ直下のパス（Path）]
# }
from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]


# {
#   責務: [git_lines: リポジトリ直下でGitコマンドを実行し、出力を空行なしの行一覧で返します]
#   処理: [1: パスを引用符付きの8進表記にしない設定でGitを実行し、失敗した場合は標準エラーを含む例外を送出します]
#   引数: [args: Gitへ渡すサブコマンドとオプション（str）]
#   戻り値: [result: 出力の各行（list[str]）]
# }
def git_lines(*args: str) -> list[str]:
    # 既定のcore.quotepath=trueでは日本語のファイル名が引用符付きの8進表記で出力され、対象から黙って外れるため無効にします。
    completed = subprocess.run(
        ["git", "-c", "core.quotepath=false", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or f"git {' '.join(args)} failed")
    return [line for line in completed.stdout.splitlines() if line.strip()]


# {
#   責務: [default_base: 整形対象を決める比較元を、CIのPull Requestでは対象ブランチ、それ以外ではorigin/mainにします]
#   処理: [1: GITHUB_BASE_REFがあればorigin/<その名前>を、なければorigin/mainを返します]
#   引数: []
#   戻り値: [result: 比較元のGit参照名（str）]
# }
def default_base() -> str:
    base_ref = os.environ.get("GITHUB_BASE_REF", "")
    return f"origin/{base_ref}" if base_ref else "origin/main"


# {
#   責務: [added_python_files: 比較元との共通祖先から現在の作業ツリーまでに、新しく追加されたPythonファイルを列挙します]
#   処理: [
#     1: 共通祖先からHEADまでのコミット、indexへの追加、未追跡のファイルから、追加された.pyを集めます
#     2: 既存ファイルの変更は含めず、存在するファイルだけを重複なく並べて返します
#   ]
#   引数: [base: 比較元のGit参照名（str）]
#   戻り値: [result: リポジトリ直下からの相対パスの一覧（list[str]）]
# }
def added_python_files(base: str) -> list[str]:
    merge_base = git_lines("merge-base", base, "HEAD")[0]
    candidates = [
        *git_lines("diff", "--name-only", "--diff-filter=A", merge_base, "HEAD"),
        *git_lines("diff", "--name-only", "--diff-filter=A", "--cached"),
        *git_lines("ls-files", "--others", "--exclude-standard"),
    ]
    # 既存ファイルの全体整形は他の作業者の行まで書き換えるため、追加したファイルだけを対象にします。
    # 既存ファイルの移動（Gitの判定はR）も、移動前の行を書き換えないよう対象にしません。
    return sorted({path for path in candidates if path.endswith(".py") and (ROOT / path).is_file()})


# {
#   責務: [main: 追加したPythonファイルをRuffで整形、または--checkで整形漏れを報告します]
#   処理: [
#     1: 比較元を決め、追加されたPythonファイルを集めます
#     2: 対象がなければ対象なしとして成功し、あれば実行中のPythonのRuffへ渡してその終了コードを返します
#   ]
#   引数: [argv: コマンドライン引数。省略時はsys.argvを使います（list[str] | None）]
#   戻り値: [result: Ruffの終了コード。比較元が見つからない場合とRuffが導入されていない場合は2です（int）]
# }
def main(argv: list[str] | None = None) -> int:
    # Windowsのコンソールでも日本語の案内を文字化けさせないよう、標準出力をUTF-8にそろえます。
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="ファイルを書き換えずに整形漏れだけを報告します")
    parser.add_argument("--base", default=None, help="比較元のGit参照。既定はorigin/<GITHUB_BASE_REF>またはorigin/main")
    args = parser.parse_args(argv)
    base = args.base or default_base()
    try:
        files = added_python_files(base)
    except RuntimeError as error:
        # 比較元がないまま対象なしで成功すると、整形漏れを見逃すため失敗にします。
        print(f"[ERROR] 比較元{base}との差分を調べられません: {error}")
        return 2
    if not files:
        print(f"[OK] {base}からの追加Pythonファイルはありません。")
        return 0
    # Ruffがないことによる失敗を、整形漏れの失敗（終了コード1）と区別します。
    if importlib.util.find_spec("ruff") is None:
        print(
            f"[ERROR] {sys.executable}にRuffがありません。リポジトリ直下で次を実行してください: "
            f"{sys.executable} -m pip install -r tools/format/requirements.txt"
        )
        return 2
    print(f"{'check' if args.check else 'format'}: {base}から追加した{len(files)}件のPythonファイル")
    command = [sys.executable, "-m", "ruff", "format", *(["--check", "--diff"] if args.check else []), *files]
    return subprocess.run(command, cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
