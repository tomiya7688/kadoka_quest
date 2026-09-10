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
        "--add-data",
        f"{PROJECT_ROOT / 'data'}{os.pathsep}data",
        "--add-data",
        f"{PROJECT_ROOT / 'assets'}{os.pathsep}assets",
        str(target.entrypoint),
    ]
    print(f"[build] {target.name}")
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)

    output = DIST_ROOT / target.name
    executable = output / executable_name(target)
    if not executable.is_file():
        raise SystemExit(f"build completed without expected executable: {executable}")

    user_data = output / "UserData"
    for path in (
        user_data,
        user_data / "imports" / "acquire",
        user_data / "imports" / "simulation",
    ):
        path.mkdir(parents=True, exist_ok=True)
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
