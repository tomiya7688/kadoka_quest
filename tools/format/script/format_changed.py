"""作業ブランチで追加したPythonファイルとGDScriptファイルだけを、固定版のRuffとgdformatで整形または整形確認します。"""

# {
#   責務: [format_changed: 比較元ブランチとの差分で新しく追加されたPythonファイルとGDScriptファイルを選び、拡張子ごとの固定版formatterで整形、または--checkで書き換えずに整形漏れを検出します]
#   フィールド: [
#     ROOT: Gitコマンドを実行するリポジトリ直下のパス（Path）
#     FORMATTERS: 拡張子ごとのformatter。Pythonの.pyはRuff、GDScriptの.gdはgdtoolkitのgdformatです（tuple[Formatter, ...]）
#   ]
# }
from __future__ import annotations

import argparse
from dataclasses import dataclass
import importlib.util
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]


# {
#   責務: [Formatter: 一つの言語の整形対象の拡張子と、そのformatterを実行中のPythonから起動する方法を保持します]
#   フィールド: [
#     name: 案内に表示するformatterの名前（str）
#     suffix: 整形対象のファイルの拡張子（str）
#     module: formatterが導入済みか確かめるPythonモジュール名（str）
#     arguments: 実行中のPythonの後ろに付ける、整形する場合のformatterの起動引数（tuple[str, ...]）
#   ]
# }
@dataclass(frozen=True)
class Formatter:
    name: str
    suffix: str
    module: str
    arguments: tuple[str, ...]

    # {
    #   責務: [command: 対象ファイルを整形する、または--checkで書き換えずに確認するコマンドを作ります]
    #   処理: [1: 実行中のPython・起動引数・確認用の引数・対象ファイルを並べます]
    #   引数: [
    #     self: 起動引数argumentsを保持するFormatter
    #     check: 書き換えずに整形漏れを差分付きで報告するか（bool）
    #     files: リポジトリ直下からの相対パスの整形対象（list[str]）
    #   ]
    #   戻り値: [result: subprocessへ渡す引数の一覧（list[str]）]
    # }
    def command(self, check: bool, files: list[str]) -> list[str]:
        return [sys.executable, *self.arguments, *(["--check", "--diff"] if check else []), *files]


# 行の上限は、Ruffの設定（pyproject.tomlの[tool.ruff]）とCIのflake8の報告と同じ127文字にそろえます。
FORMATTERS = (
    Formatter("Ruff", ".py", "ruff", ("-m", "ruff", "format")),
    Formatter("gdformat", ".gd", "gdtoolkit", ("-m", "gdtoolkit.formatter", "--line-length=127")),
)


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
#   責務: [added_files: 比較元との共通祖先から現在の作業ツリーまでに、新しく追加された指定拡張子のファイルを列挙します]
#   処理: [
#     1: 共通祖先からHEADまでのコミット、indexへの追加、未追跡のファイルから、指定拡張子の追加ファイルを集めます
#     2: 既存ファイルの変更は含めず、存在するファイルだけを重複なく並べて返します
#   ]
#   引数: [
#     base: 比較元のGit参照名（str）
#     suffix: 対象にするファイルの拡張子。例えばPythonは".py"です（str）
#   ]
#   戻り値: [result: リポジトリ直下からの相対パスの一覧（list[str]）]
# }
def added_files(base: str, suffix: str) -> list[str]:
    merge_base = git_lines("merge-base", base, "HEAD")[0]
    candidates = [
        *git_lines("diff", "--name-only", "--diff-filter=A", merge_base, "HEAD"),
        *git_lines("diff", "--name-only", "--diff-filter=A", "--cached"),
        *git_lines("ls-files", "--others", "--exclude-standard"),
    ]
    # 既存ファイルの全体整形は他の作業者の行まで書き換えるため、追加したファイルだけを対象にします。
    # 既存ファイルの移動（Gitの判定はR）も、移動前の行を書き換えないよう対象にしません。
    return sorted({path for path in candidates if path.endswith(suffix) and (ROOT / path).is_file()})


# {
#   責務: [restore_lf_line_endings: 整形前に改行がLFだけだったファイルで、formatterがCRLFへ変えた改行をLFへ戻します]
#   処理: [1: 指定ファイルを読み、CRLFがあればLFへ置き換えて書き戻します。CRLFがなければ書き込みません]
#   引数: [files: 整形前にCRLFを含まなかった、リポジトリ直下からの相対パス（list[str]）]
#   戻り値: [result: なし（None）]
# }
def restore_lf_line_endings(files: list[str]) -> None:
    # gdformatはWindowsで改行をCRLFにして書き込み、リポジトリには改行を正規化する.gitattributesがないため、
    # 戻さないと整形した行以外もすべて変更としてコミットされます。
    for path in files:
        content = (ROOT / path).read_bytes()
        if b"\r\n" in content:
            (ROOT / path).write_bytes(content.replace(b"\r\n", b"\n"))


# {
#   責務: [main: 追加したPythonファイルをRuffで、GDScriptファイルをgdformatで整形、または--checkで整形漏れを報告します]
#   処理: [
#     1: 比較元を決め、formatterごとに追加ファイルを集めます。対象がなければ対象なしとして成功します
#     2: 対象のある言語のformatterが導入されているかを、実行前にすべて確かめます
#     3: formatterごとに実行し、整形した場合は、整形前にLFだけだったファイルの改行をLFへ戻します
#     4: 一つでも失敗すれば、最初に失敗したformatterの終了コードを返します
#   ]
#   引数: [argv: コマンドライン引数。省略時はsys.argvを使います（list[str] | None）]
#   戻り値: [result: formatterの終了コード。比較元が見つからない場合とformatterが導入されていない場合は2です（int）]
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
        targets = [(formatter, added_files(base, formatter.suffix)) for formatter in FORMATTERS]
    except RuntimeError as error:
        # 比較元がないまま対象なしで成功すると、整形漏れを見逃すため失敗にします。
        print(f"[ERROR] 比較元{base}との差分を調べられません: {error}")
        return 2
    targets = [(formatter, files) for formatter, files in targets if files]
    if not targets:
        print(f"[OK] {base}からの追加Python・GDScriptファイルはありません。")
        return 0
    # formatterがないことによる失敗を整形漏れの失敗（終了コード1）と区別し、一部の言語だけ整形した状態で止めないよう先に確かめます。
    missing = [formatter.name for formatter, _ in targets if importlib.util.find_spec(formatter.module) is None]
    if missing:
        print(
            f"[ERROR] {sys.executable}に{'・'.join(missing)}がありません。リポジトリ直下で次を実行してください: "
            f"{sys.executable} -m pip install -r tools/format/requirements.txt"
        )
        return 2
    result = 0
    for formatter, files in targets:
        print(
            f"{'check' if args.check else 'format'}: {base}から追加した{len(files)}件の{formatter.suffix}ファイル（{formatter.name}）"
        )
        lf_files = [path for path in files if b"\r\n" not in (ROOT / path).read_bytes()]
        # 引数はリストでshellを通さず、対象はGitが列挙したリポジトリ内のファイル名だけです。
        code = subprocess.run(  # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit
            formatter.command(args.check, files), cwd=ROOT, check=False
        ).returncode
        if not args.check:
            restore_lf_line_endings(lf_files)
        # 後の言語の整形漏れも同じ実行で報告するため、失敗しても残りのformatterを実行します。
        result = result or code
    return result


if __name__ == "__main__":
    raise SystemExit(main())
