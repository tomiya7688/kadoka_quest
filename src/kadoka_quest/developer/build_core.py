# {
#   責務: [build_core: build・coreの公開機能・宣言を定義する]
#   フィールド: []
# }
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
PLAYER_TEMPLATE_DIR = "PlayerRuntimeTemplate"


# {
#   責務: [BuildTarget: build・対象の状態と振る舞いを担当する]
#   フィールド: [
#     key: キー（str）
#     name: 名前（str）
#     entrypoint: entrypoint（Path）
#   ]
# }
@dataclass(frozen=True)
class BuildTarget:
    key: str
    name: str
    entrypoint: Path


# {
#   責務: [executable_name: build・coreのexecutable・名前を求める]
#   処理: [1: build・coreのexecutable・名前を求める]
#   引数: [target: 対象（BuildTarget）]
#   戻り値: [result: build・coreのexecutable・名前を求めるための結果（str）]
# }
def executable_name(target: BuildTarget) -> str:
    return target.name + (".exe" if os.name == "nt" else "")


# {
#   責務: [default_targets: build・coreのdefault・対象一覧を求める]
#   処理: [1: build・coreのdefault・対象一覧を求める]
#   引数: [source_root: 元データ・基準ディレクトリ（Path）]
#   戻り値: [result: build・coreのdefault・対象一覧を求めるための結果（dict[str, BuildTarget]）]
# }
def default_targets(source_root: Path) -> dict[str, BuildTarget]:
    root = Path(source_root)
    return {
        "player": BuildTarget("player", "KadokaQuest", root / "launcher.py"),
        "developer": BuildTarget("developer", "KadokaQuestDeveloper", root / "developer_launcher.py"),
    }


# {
#   責務: [selected_targets: build・coreの選択中・対象一覧を求める]
#   処理: [1: build・coreの選択中・対象一覧を求める]
#   引数: [
#     source_root: 元データ・基準ディレクトリ（Path）
#     value: 値（str）
#   ]
#   戻り値: [result: build・coreの選択中・対象一覧を求めるための結果（list[BuildTarget]）]
# }
def selected_targets(source_root: Path, value: str) -> list[BuildTarget]:
    targets = default_targets(source_root)
    if value == "all":
        return [targets["player"], targets["developer"]]
    return [targets[value]]


# {
#   責務: [require_pyinstaller: build・coreのrequire・pyinstallerを求める]
#   処理: [1: build・coreのrequire・pyinstallerを求める]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def require_pyinstaller() -> None:
    if importlib.util.find_spec("PyInstaller") is None:
        raise RuntimeError("PyInstaller is not installed. Install requirements-build.txt first.")


# {
#   責務: [reset_user_data: user・データの初期状態へ戻す]
#   処理: [1: user・データの初期状態へ戻す]
#   引数: [output: output（Path）]
#   戻り値: [result: user・データ（Path）]
# }
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


# {
#   責務: [copy_runtime_content: 実行時・contentを複製する]
#   処理: [1: 実行時・contentを複製する]
#   引数: [
#     output: output（Path）
#     content_root: content・基準ディレクトリ（Path）
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
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


# {
#   責務: [subprocess_pyinstaller: build・coreのsubprocess・pyinstallerを求める]
#   処理: [1: build・coreのsubprocess・pyinstallerを求める]
#   引数: [
#     command: コマンド（Sequence[str]）
#     cwd: cwd（Path）
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def subprocess_pyinstaller(command: Sequence[str], *, cwd: Path) -> None:
    subprocess.run([sys.executable, "-m", "PyInstaller", *command], cwd=cwd, check=True)


# {
#   責務: [build_target: 対象を構築する]
#   処理: [1: 対象を構築する]
#   引数: [
#     target: 対象（BuildTarget）
#     source_root: 元データ・基準ディレクトリ（Path）
#     content_root: content・基準ディレクトリ（Path）
#     dist_root: dist・基準ディレクトリ（Path）
#     build_root: build・基準ディレクトリ（Path）
#     runner: runner（Callable[..., None]）
#     extra_args: extra・args（Sequence[str]）
#   ]
#   戻り値: [result: output（Path）]
# }
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


# {
#   責務: [build_distributions: distributionsを構築する]
#   処理: [1: distributionsを構築する]
#   引数: [
#     source_root: 元データ・基準ディレクトリ（Path）
#     content_root: content・基準ディレクトリ（Path | None）
#     dist_root: dist・基準ディレクトリ（Path | None）
#     build_root: build・基準ディレクトリ（Path | None）
#     targets: 対象一覧（str）
#     clean: clean（bool）
#     runner: runner（Callable[..., None]）
#     developer_extra_args: developer・extra・args（Sequence[str]）
#   ]
#   戻り値: [result: outputs（list[Path]）]
# }
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


# {
#   責務: [install_player_runtime_template: Store a content-free Player runtime snapshot inside the Developer distribution.]
#   処理: [1: Store a content-free Player runtime snapshot inside the Developer distribution.]
#   引数: [
#     developer_output: developer・output（Path）
#     player_output: 主人公・output（Path）
#   ]
#   戻り値: [result: template（Path）]
# }
def install_player_runtime_template(developer_output: Path, player_output: Path) -> Path:
    """Store a content-free Player runtime snapshot inside the Developer distribution."""
    developer_output = Path(developer_output)
    player_output = Path(player_output)
    template = developer_output / PLAYER_TEMPLATE_DIR / "KadokaQuest"
    shutil.rmtree(template.parent, ignore_errors=True)
    shutil.copytree(player_output, template)
    for name in ("data", "assets", "UserData", "dist"):
        path = template / name
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
    (template / "smoke-error.txt").unlink(missing_ok=True)
    return template


# {
#   責務: [materialize_player_distribution: Create a Player distribution from a prebuilt runtime plus current canonical content.]
#   処理: [1: Create a Player distribution from a prebuilt runtime plus current canonical content.]
#   引数: [
#     template: template（Path）
#     content_root: content・基準ディレクトリ（Path）
#     dist_root: dist・基準ディレクトリ（Path）
#   ]
#   戻り値: [result: output（Path）]
# }
def materialize_player_distribution(
    template: Path,
    *,
    content_root: Path,
    dist_root: Path,
) -> Path:
    """Create a Player distribution from a prebuilt runtime plus current canonical content."""
    template = Path(template)
    content_root = Path(content_root)
    output = Path(dist_root) / "KadokaQuest"
    executable = template / ("KadokaQuest.exe" if os.name == "nt" else "KadokaQuest")
    if not executable.is_file():
        raise RuntimeError(f"invalid Player runtime template: {executable}")

    shutil.rmtree(output, ignore_errors=True)
    shutil.copytree(template, output)
    copy_runtime_content(output, content_root)
    return output
