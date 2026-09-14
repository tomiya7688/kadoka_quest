from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Callable, Sequence


USER_DATA_README = """Kadoka Quest UserData

Save data, settings, imports, and other user-owned files are created here at runtime.
This directory is intentionally shipped without development or CI test data.
"""


@dataclass(frozen=True)
class BuildTarget:
    key: str
    name: str
    entrypoint: Path


def executable_name(target: BuildTarget) -> str:
    return target.name + (".exe" if os.name == "nt" else "")


def default_targets(source_root: Path) -> dict[str, BuildTarget]:
    root = Path(source_root)
    return {
        "player": BuildTarget("player", "KadokaQuest", root / "launcher.py"),
        "developer": BuildTarget("developer", "KadokaQuestDeveloper", root / "developer_launcher.py"),
    }


def selected_targets(source_root: Path, value: str) -> list[BuildTarget]:
    targets = default_targets(source_root)
    if value == "all":
        return [targets["player"], targets["developer"]]
    return [targets[value]]


def require_pyinstaller() -> None:
    if importlib.util.find_spec("PyInstaller") is None:
        raise RuntimeError("PyInstaller is not installed. Install requirements-build.txt first.")


def reset_user_data(output: Path) -> Path:
    user_data = Path(output) / "UserData"
    shutil.rmtree(user_data, ignore_errors=True)
    for path in (
        user_data,
        user_data / "imports" / "acquire",
        user_data / "imports" / "simulation",
    ):
        path.mkdir(parents=True, exist_ok=True)
    (user_data / "README.txt").write_text(USER_DATA_README, encoding="utf-8")
    return user_data


def copy_runtime_content(output: Path, content_root: Path) -> None:
    output = Path(output)
    content_root = Path(content_root)
    for name in ("data", "assets"):
        source = content_root / name
        if not source.is_dir():
            raise RuntimeError(f"missing runtime content: {source}")
        destination = output / name
        shutil.rmtree(destination, ignore_errors=True)
        shutil.copytree(source, destination)
    reset_user_data(output)


def subprocess_pyinstaller(command: Sequence[str], *, cwd: Path) -> None:
    subprocess.run([sys.executable, "-m", "PyInstaller", *command], cwd=cwd, check=True)


def in_process_pyinstaller(command: Sequence[str], *, cwd: Path) -> None:
    """Run PyInstaller through its Python API; used by the packaged Developer app."""
    require_pyinstaller()
    from PyInstaller.__main__ import run

    previous = Path.cwd()
    try:
        os.chdir(cwd)
        run(list(command))
    finally:
        os.chdir(previous)


PyInstallerRunner = Callable[[Sequence[str]], None]


def build_target(
    target: BuildTarget,
    *,
    source_root: Path,
    content_root: Path,
    dist_root: Path,
    build_root: Path,
    runner: Callable[..., None] = subprocess_pyinstaller,
    extra_args: Sequence[str] = (),
) -> Path:
    source_root = Path(source_root)
    dist_root = Path(dist_root)
    build_root = Path(build_root)
    target_work = build_root / target.key
    spec_root = build_root / "spec"
    target_work.mkdir(parents=True, exist_ok=True)
    spec_root.mkdir(parents=True, exist_ok=True)

    command = [
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--name",
        target.name,
        "--distpath",
        str(dist_root),
        "--workpath",
        str(target_work),
        "--specpath",
        str(spec_root),
        "--paths",
        str(source_root / "src"),
        *extra_args,
        str(target.entrypoint),
    ]
    print(f"[build] {target.name}")
    runner(command, cwd=source_root)

    output = dist_root / target.name
    executable = output / executable_name(target)
    if not executable.is_file():
        raise RuntimeError(f"build completed without expected executable: {executable}")
    copy_runtime_content(output, content_root)
    return output


def build_distributions(
    *,
    source_root: Path,
    content_root: Path | None = None,
    dist_root: Path | None = None,
    build_root: Path | None = None,
    targets: str = "all",
    clean: bool = False,
    runner: Callable[..., None] = subprocess_pyinstaller,
    developer_extra_args: Sequence[str] = (),
) -> list[Path]:
    source_root = Path(source_root)
    content_root = Path(content_root or source_root)
    dist_root = Path(dist_root or source_root / "dist")
    build_root = Path(build_root or source_root / "build" / "pyinstaller")

    require_pyinstaller()
    if clean:
        shutil.rmtree(dist_root, ignore_errors=True)
        shutil.rmtree(build_root, ignore_errors=True)
    dist_root.mkdir(parents=True, exist_ok=True)

    outputs: list[Path] = []
    for target in selected_targets(source_root, targets):
        extra_args = developer_extra_args if target.key == "developer" else ()
        outputs.append(
            build_target(
                target,
                source_root=source_root,
                content_root=content_root,
                dist_root=dist_root,
                build_root=build_root,
                runner=runner,
                extra_args=extra_args,
            )
        )
    return outputs
