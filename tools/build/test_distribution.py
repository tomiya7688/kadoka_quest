from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIST_ROOT = PROJECT_ROOT / "dist"
TARGET_NAMES = {
    "player": "KadokaQuest",
    "developer": "KadokaQuestDeveloper",
}
DEVELOPER_TOOLS = ("manage", "block_editor", "map_editor", "monster_editor", "data_creator")
KADOKA_ENV_KEYS = (
    "KADOKA_PROJECT_ROOT",
    "KADOKA_DATA_DIR",
    "KADOKA_ASSET_DIR",
    "KADOKA_SAVEDATA_ROOT",
    "KADOKA_SAVE_DIR",
    "KADOKA_IMPORT_DIR",
)


def selected_targets(value: str) -> list[str]:
    if value == "all":
        return ["player", "developer"]
    return [value]


def executable_path(distribution: Path, name: str) -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    return distribution / f"{name}{suffix}"


def verify_static_layout(distribution: Path, name: str) -> Path:
    executable = executable_path(distribution, name)
    required = (executable, distribution / "data", distribution / "assets", distribution / "UserData")
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise AssertionError("missing distribution content:\n" + "\n".join(missing))
    return executable


def smoke_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for key in KADOKA_ENV_KEYS:
        environment.pop(key, None)
    environment["SDL_VIDEODRIVER"] = "dummy"
    environment["SDL_AUDIODRIVER"] = "dummy"
    environment["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    return environment


def diagnostic_text(distribution: Path) -> str:
    error_path = distribution / "smoke-error.txt"
    if not error_path.is_file():
        return ""
    try:
        return "\nsmoke-error.txt:\n" + error_path.read_text(encoding="utf-8")
    except OSError:
        return "\nsmoke-error.txt exists but could not be read."


def run_process(distribution: Path, executable: Path, arguments: list[str], environment: dict[str, str]) -> None:
    error_path = distribution / "smoke-error.txt"
    error_path.unlink(missing_ok=True)
    try:
        completed = subprocess.run(
            [str(executable), *arguments],
            cwd=distribution,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise AssertionError(
            f"distribution smoke timed out: {executable.name} {' '.join(arguments)}"
            + diagnostic_text(distribution)
        ) from exc
    if completed.returncode != 0:
        raise AssertionError(
            f"distribution smoke failed: {executable.name} {' '.join(arguments)} "
            f"({completed.returncode})\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
            + diagnostic_text(distribution)
        )


def run_smoke(key: str, distribution: Path, executable: Path) -> None:
    user_data = distribution / "UserData"
    if user_data.exists():
        shutil.rmtree(user_data)
    user_data.mkdir(parents=True)
    environment = smoke_environment()

    run_process(distribution, executable, ["--smoke", "2"], environment)
    if key == "player":
        run_process(distribution, executable, ["--manager", "--smoke", "2"], environment)
        run_process(distribution, executable, ["--play", "--smoke", "2"], environment)
    else:
        for tool in DEVELOPER_TOOLS:
            run_process(distribution, executable, ["--dev-tool", tool, "--smoke", "2"], environment)

    required_writable = (
        user_data / "active.json",
        user_data / "default" / "state.json",
        user_data / "default" / "items" / "items.json",
        user_data / "imports" / "acquire",
        user_data / "imports" / "simulation",
    )
    missing = [str(path) for path in required_writable if not path.exists()]
    if missing:
        raise AssertionError("distribution did not initialize UserData correctly:\n" + "\n".join(missing))

    if (distribution / "savedata").exists():
        raise AssertionError("frozen distribution wrote to savedata/ instead of UserData/")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test built Kadoka Quest distributions as external processes.")
    parser.add_argument("--targets", choices=("player", "developer", "all"), default="all")
    parser.add_argument("--dist-root", type=Path, default=DEFAULT_DIST_ROOT)
    args = parser.parse_args()

    for key in selected_targets(args.targets):
        name = TARGET_NAMES[key]
        distribution = args.dist_root / name
        executable = verify_static_layout(distribution, name)
        print(f"[smoke] {executable}")
        run_smoke(key, distribution, executable)
        print(f"[ok] {name}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, subprocess.SubprocessError) as exc:
        print(f"[failed] {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
