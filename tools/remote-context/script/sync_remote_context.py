# {
#   責務: [sync_remote_context: sync・remote・判断用コンテキストの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import argparse
import os
from shutil import which
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


# {
#   責務: [git_executable: sync・remote・判断用コンテキストのgit・executableを求める]
#   処理: [1: sync・remote・判断用コンテキストのgit・executableを求める]
#   引数: []
#   戻り値: [result: sync・remote・判断用コンテキストのgit・executableを求めるための結果（str）]
# }
def git_executable() -> str:
    configured = os.environ.get("KADOKA_GIT_EXECUTABLE", "")
    if configured:
        return configured
    discovered = which("git")
    if discovered:
        return discovered
    raise RuntimeError("Git was not found. Set KADOKA_GIT_EXECUTABLE to git.exe.")


# {
#   責務: [run_git: gitを実行する]
#   処理: [1: gitを実行する]
#   引数: [
#     check: check（bool）
#     args: args（str）
#   ]
#   戻り値: [result: gitを実行するための結果（str）]
# }
def run_git(*args: str, check: bool = True) -> str:
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
#   責務: [compact_diff: sync・remote・判断用コンテキストのcompact・diffを求める]
#   処理: [1: sync・remote・判断用コンテキストのcompact・diffを求める]
#   引数: [
#     base: base（str）
#     head: head（str）
#     max_lines: max・lines（int）
#   ]
#   戻り値: [result: sync・remote・判断用コンテキストのcompact・diffを求めるための結果（str）]
# }
def compact_diff(base: str, head: str, max_lines: int) -> str:
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
#   責務: [main: sync・remote・判断用コンテキストのエントリ処理を実行する]
#   処理: [1: sync・remote・判断用コンテキストのエントリ処理を実行する]
#   引数: []
#   戻り値: [result: sync・remote・判断用コンテキストのエントリ処理を実行するための結果（int）]
# }
def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="Fetch remote changes and print a compact implementation context."
    )
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--max-diff-lines", type=int, default=220)
    parser.add_argument(
        "--update",
        action="store_true",
        help="After summarizing, fast-forward the current branch to the remote branch. Refuses dirty worktrees.",
    )
    args = parser.parse_args()

    remote_ref = f"{args.remote}/{args.branch}"
    run_git("fetch", "--prune", args.remote, args.branch)

    local = run_git("rev-parse", "HEAD")
    remote = run_git("rev-parse", remote_ref)
    base = run_git("merge-base", local, remote)

    print("# Remote context")
    print(f"local:  {local[:12]}")
    print(f"remote: {remote[:12]} ({remote_ref})")
    print(f"base:   {base[:12]}")

    if local == remote:
        print("status: up to date")
        return 0

    behind = run_git("rev-list", "--count", f"{local}..{remote}")
    ahead = run_git("rev-list", "--count", f"{remote}..{local}")
    print(f"status: ahead {ahead}, behind {behind}")

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
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
