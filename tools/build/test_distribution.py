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


def run_smoke(distribution: Path, executable: Path) -> None:
    user_data = distribution / "UserData"
    if user_data.exists():
        shutil.rmtree(user_data)
    user_data.mkdir(parents=True)

    environment = os.environ.copy()
    for key in KADOKA_ENV_KEYS:
        environment.pop(key, None)
    environment["SDL_VIDEODRIVER"] = "dummy"
    environment["SDL_AUDIODRIVER"] = "dummy"
    environment["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

    completed = subprocess.run(
        [str(executable), "--smoke", "2"],
        cwd=distribution,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"distribution smoke failed ({completed.returncode})\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )

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
        run_smoke(distribution, executable)
        print(f"[ok] {name}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, subprocess.SubprocessError) as exc:
        print(f"[failed] {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
