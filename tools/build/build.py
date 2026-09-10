from __future__ import annotations

import argparse
from dataclasses import dataclass
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DIST_ROOT = PROJECT_ROOT / "dist"
BUILD_ROOT = PROJECT_ROOT / "build" / "pyinstaller"
USER_DATA_README = """Kadoka Quest UserData

Save data, settings, imports, and other user-owned files are created here at runtime.
This directory is intentionally shipped without development or CI test data.
"""


@dataclass(frozen=True)
class BuildTarget:
    key: str
    name: str
    entrypoint: Path


TARGETS = {
    "player": BuildTarget("player", "KadokaQuest", PROJECT_ROOT / "launcher.py"),
    "developer": BuildTarget("developer", "KadokaQuestDeveloper", PROJECT_ROOT / "developer_launcher.py"),
}


def executable_name(target: BuildTarget) -> str:
    return target.name + (".exe" if os.name == "nt" else "")


def selected_targets(value: str) -> list[BuildTarget]:
    if value == "all":
        return [TARGETS["player"], TARGETS["developer"]]
    return [TARGETS[value]]


def require_pyinstaller() -> None:
    if importlib.util.find_spec("PyInstaller") is None:
        raise SystemExit(
            "PyInstaller is not installed. Run: "
            f'"{sys.executable}" -m pip install -r "{PROJECT_ROOT / "requirements-build.txt"}"'
        )


def reset_user_data(output: Path) -> Path:
    user_data = output / "UserData"
    shutil.rmtree(user_data, ignore_errors=True)
    for path in (
        user_data,
        user_data / "imports" / "acquire",
        user_data / "imports" / "simulation",
    ):
        path.mkdir(parents=True, exist_ok=True)
    (user_data / "README.txt").write_text(USER_DATA_README, encoding="utf-8")
    return user_data


def copy_runtime_content(output: Path) -> None:
    for name in ("data", "assets"):
        destination = output / name
        shutil.rmtree(destination, ignore_errors=True)
        shutil.copytree(PROJECT_ROOT / name, destination)
    reset_user_data(output)


def build_target(target: BuildTarget) -> Path:
    target_work = BUILD_ROOT / target.key
    spec_root = BUILD_ROOT / "spec"
    target_work.mkdir(parents=True, exist_ok=True)
    spec_root.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--name",
        target.name,
        "--distpath",
        str(DIST_ROOT),
        "--workpath",
        str(target_work),
        "--specpath",
        str(spec_root),
        "--paths",
        str(PROJECT_ROOT / "src"),
        str(target.entrypoint),
    ]
    print(f"[build] {target.name}")
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)

    output = DIST_ROOT / target.name
    executable = output / executable_name(target)
    if not executable.is_file():
        raise SystemExit(f"build completed without expected executable: {executable}")

    copy_runtime_content(output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Kadoka Quest PyInstaller distributions.")
    parser.add_argument("--targets", choices=("player", "developer", "all"), default="all")
    parser.add_argument("--clean", action="store_true", help="Remove previous dist/build output before building.")
    args = parser.parse_args()

    require_pyinstaller()
    if args.clean:
        shutil.rmtree(DIST_ROOT, ignore_errors=True)
        shutil.rmtree(BUILD_ROOT, ignore_errors=True)

    DIST_ROOT.mkdir(parents=True, exist_ok=True)
    outputs = [build_target(target) for target in selected_targets(args.targets)]
    for output in outputs:
        print(f"[ok] {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
