from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def run_git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


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


def main() -> int:
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
