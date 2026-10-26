# {
#   責務: [sync_remote_context: Kadoka QuestのリモートGit履歴を取得し、作業前に確認する未取り込みコミットと差分の要約を表示します]
#   フィールド: [REPO_ROOT: Gitコマンドを実行するKadoka Questのリポジトリ直下のパス]
# }
from __future__ import annotations

import argparse
import os
from shutil import which
import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


# {
#   責務: [git_executable: リモート差分の取得に使うGit実行ファイルを環境変数またはPATHから選びます]
#   処理: [1: KADOKA_GIT_EXECUTABLEを優先し、未指定ならPATHのgitを探し、見つからなければ設定を促す例外を送出します]
#   引数: []
#   戻り値: [result: Git起動に使う実行ファイルのパスまたはコマンド名（str）]
# }
def git_executable() -> str:
    # Git実行ファイルの選択処理は、環境変数KADOKA_GIT_EXECUTABLEが指定されていればPATHにあるGitより優先します。
    configured = os.environ.get("KADOKA_GIT_EXECUTABLE", "")
    if configured:
        return configured
    discovered = which("git")
    if discovered:
        return discovered
    raise RuntimeError("Git was not found. Set KADOKA_GIT_EXECUTABLE to git.exe.")


# {
#   責務: [run_git: Kadoka Questのリポジトリ直下で指定したGitコマンドを実行し、標準出力をUTF-8として取得します]
#   処理: [1: Gitの標準出力と標準エラーを取得し、checkがtrueの場合は終了コードの失敗を例外へ変換します]
#   引数: [
#     check: Gitの終了コードが0以外ならRuntimeErrorを送出するかの指定（bool）
#     args: Gitへ渡すサブコマンドとオプションの可変長引数（str）
#   ]
#   戻り値: [result: 前後の空白を除いたGitの標準出力。checkがfalseの場合は失敗時も標準出力を返します（str）]
# }
def run_git(*args: str, check: bool = True) -> str:
    # Gitコマンドの実行処理は、日本語を含む差分をWindowsのコンソール文字コードに依存せず読み取ります。
    result = subprocess.run(
        [git_executable(), *args],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


# {
#   責務: [compact_diff: 指定したGit参照間の差分を、作業判断用の行数上限付き要約へ整えます]
#   処理: [1: 前後各1行の文脈を含むGit差分を取得し、上限を超える本文行を省いて省略行数を末尾へ追加します]
#   引数: [
#     base: 要約するGit差分の比較元のコミットまたは参照名（str）
#     head: 要約するGit差分の比較先のコミットまたは参照名（str）
#     max_lines: 要約へ残すGit差分本文の最大行数。省略行数の案内行は上限に含めません（int）
#   ]
#   戻り値: [result: 全差分または行数上限で切り詰めた差分と省略行数の案内（str）]
# }
def compact_diff(base: str, head: str, max_lines: int) -> str:
    # Git差分の要約処理は、外部diffプログラムや色付き表示を使わず、一定の差分形式を取得します。
    diff = run_git(
        "diff",
        "--unified=1",
        "--no-ext-diff",
        "--no-color",
        f"{base}..{head}",
    )
    lines = diff.splitlines()
    if len(lines) <= max_lines:
        return diff
    omitted = len(lines) - max_lines
    return "\n".join(lines[:max_lines] + [f"... ({omitted} diff lines omitted)"])


# {
#   責務: [active_remote_branches: 他の開発者や実装AIが進行中の作業を重複させないよう、比較先へ未統合の最近のリモートブランチを列挙します]
#   処理: [
#     1: 比較先に未統合のリモート追跡ブランチを、コミット日時の新しい順に取得します
#     2: 比較先自身・HEAD別名・指定日数より古いブランチを除き、件数上限まで残します
#     3: 残したブランチごとに、比較先にない独自コミット数を数えて表示行へ整えます
#   ]
#   引数: [
#     remote: リモート追跡ブランチを列挙するリモート名（str）
#     remote_ref: 統合済みかを判定する比較先のリモート追跡参照名。例はorigin/mainです（str）
#     active_days: 最終コミットがこの日数以内のブランチだけを進行中として表示する日数（int）
#     max_branches: 表示する進行中リモートブランチの最大件数（int）
#     now: 日数判定の基準にするUNIX時刻の秒数。テストでは固定値を渡します（float）
#   ]
#   戻り値: [result: 「ブランチ名 | 最終コミット日 | 独自コミット数 | 件名」形式の表示行一覧（list[str]）]
# }
def active_remote_branches(
    remote: str, remote_ref: str, active_days: int, max_branches: int, now: float
) -> list[str]:
    # 進行中ブランチの一覧は、比較先へ統合済みのブランチを除き、新しい作業から確認できる順に取得します。
    listing = run_git(
        "for-each-ref",
        "--sort=-committerdate",
        f"--no-merged={remote_ref}",
        "--format=%(refname:short)%09%(committerdate:unix)%09%(committerdate:short)%09%(subject)",
        f"refs/remotes/{remote}",
    )
    oldest = now - active_days * 86400
    rows: list[str] = []
    for line in listing.splitlines():
        name, timestamp, date, subject = (line.split("\t", 3) + ["", "", ""])[:4]
        # HEAD別名と比較先自身は他者の作業ではないため除外し、古い放置ブランチは件数上限を使わせません。
        if name in (remote_ref, f"{remote}/HEAD", remote) or not timestamp.isdigit():
            continue
        if int(timestamp) < oldest:
            break
        ahead = run_git("rev-list", "--count", f"{remote_ref}..{name}")
        rows.append(f"{name} | {date} | ahead {ahead} | {subject}")
        if len(rows) >= max_branches:
            break
    return rows


# {
#   責務: [main: リモートの全ブランチを取得して進行中ブランチとローカルとの差分を表示し、明示指定時だけ安全条件を満たすfast-forward更新を行います]
#   処理: [
#     1: CLIの比較先と表示上限を読み取り、リモートの全ブランチをfetchします
#     2: 比較先へ未統合の最近のリモートブランチを表示します
#     3: ローカルとリモートの差分コミット数・変更ファイル・差分要約を表示します
#     4: --update指定時だけ、未コミット変更とローカル独自コミットがない場合にfast-forwardします
#   ]
#   引数: []
#   戻り値: [result: 比較または更新の成功時は0、安全条件で更新を拒否した場合は2。Git失敗はRuntimeErrorとして呼び出し元へ伝えます（int）]
# }
def main() -> int:
    # リモート差分要約CLIは、日本語のパスを表示できるように標準出力をUTF-8にそろえます。
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="Fetch remote changes and print a compact implementation context."
    )
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--max-diff-lines", type=int, default=220)
    parser.add_argument(
        "--active-days",
        type=int,
        default=14,
        help="List unmerged remote branches whose last commit is within this many days.",
    )
    parser.add_argument("--max-branches", type=int, default=10)
    parser.add_argument(
        "--update",
        action="store_true",
        help="After summarizing, fast-forward the current branch to the remote branch. Refuses dirty worktrees.",
    )
    args = parser.parse_args()

    # リモート差分要約CLIは、比較前にリモート追跡参照を更新し、古い取得結果を最新の差分として扱わないようにします。
    remote_ref = f"{args.remote}/{args.branch}"
    run_git("fetch", "--prune", args.remote)

    local = run_git("rev-parse", "HEAD")
    remote = run_git("rev-parse", remote_ref)
    base = run_git("merge-base", local, remote)

    # リモート差分要約CLIは、比較するコミットと共通祖先を表示し、差分の基準を利用者が確認できるようにします。
    print("# Remote context")
    print(f"local:  {local[:12]}")
    print(f"remote: {remote[:12]} ({remote_ref})")
    print(f"base:   {base[:12]}")

    # リモート差分要約CLIは、共同開発者や他の実装AIが未統合で進めている作業を、着手前の重複確認用に表示します。
    print("\n## Active remote branches")
    branches = active_remote_branches(
        args.remote, remote_ref, max(1, args.active_days), max(1, args.max_branches), time.time()
    )
    print("\n".join(branches) or "(none)")

    if local == remote:
        print("\nstatus: up to date")
        return 0

    # リモート差分要約CLIは、未取り込み履歴と共通祖先からのリモート差分を、作業判断用に要約します。
    behind = run_git("rev-list", "--count", f"{local}..{remote}")
    ahead = run_git("rev-list", "--count", f"{remote}..{local}")
    print(f"\nstatus: ahead {ahead}, behind {behind}")

    print("\n## Remote commits")
    commits = run_git(
        "log",
        "--format=%h %s",
        "--no-merges",
        f"{local}..{remote}",
        check=False,
    )
    print(commits or "(none)")

    print("\n## Changed files")
    names = run_git("diff", "--name-status", f"{base}..{remote}")
    print(names or "(none)")

    print("\n## Diff stat")
    stat = run_git("diff", "--stat", "--compact-summary", f"{base}..{remote}")
    print(stat or "(none)")

    print("\n## Compact diff")
    compact = compact_diff(base, remote, max(20, args.max_diff_lines))
    print(compact or "(none)")

    # リモート差分要約CLIは、比較だけの実行では作業ブランチを変更せず、明示更新でも利用者の変更や独自履歴を保護します。
    if args.update:
        dirty = run_git("status", "--porcelain")
        if dirty:
            print("\nupdate: skipped (dirty worktree)", file=sys.stderr)
            return 2
        if ahead != "0":
            print("\nupdate: skipped (local commits diverge from remote)", file=sys.stderr)
            return 2
        run_git("merge", "--ff-only", remote_ref)
        print(f"\nupdate: fast-forwarded to {remote_ref}")

    return 0


if __name__ == "__main__":
    # リモート差分要約CLIは、Git取得や比較の失敗を標準エラーへ表示し、終了コード1として通知します。
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
