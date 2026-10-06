# {
#   責務: [distribution_smoke: distribution・smokeの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

from kadoka_quest.developer.build_core import reset_user_data


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


# {
#   責務: [selected_targets: distribution・smokeの選択中・対象一覧を求める]
#   処理: [1: distribution・smokeの選択中・対象一覧を求める]
#   引数: [value: 値（str）]
#   戻り値: [result: distribution・smokeの選択中・対象一覧を求めるための結果（list[str]）]
# }
def selected_targets(value: str) -> list[str]:
    if value == "all":
        return ["player", "developer"]
    return [value]


# {
#   責務: [executable_path: distribution・smokeのexecutable・パスを求める]
#   処理: [1: distribution・smokeのexecutable・パスを求める]
#   引数: [
#     distribution: distribution（Path）
#     name: 名前（str）
#   ]
#   戻り値: [result: distribution・smokeのexecutable・パスを求めるための結果（Path）]
# }
def executable_path(distribution: Path, name: str) -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    return Path(distribution) / f"{name}{suffix}"


# {
#   責務: [verify_static_layout: distribution・smokeのverify・static・layoutを求める]
#   処理: [1: distribution・smokeのverify・static・layoutを求める]
#   引数: [
#     distribution: distribution（Path）
#     name: 名前（str）
#   ]
#   戻り値: [result: executable（Path）]
# }
def verify_static_layout(distribution: Path, name: str) -> Path:
    distribution = Path(distribution)
    executable = executable_path(distribution, name)
    required = (executable, distribution / "data", distribution / "assets", distribution / "UserData")
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise AssertionError("missing distribution content:\n" + "\n".join(missing))
    return executable


# {
#   責務: [smoke_environment: distribution・smokeのsmoke・environmentを求める]
#   処理: [1: distribution・smokeのsmoke・environmentを求める]
#   引数: []
#   戻り値: [result: environment（dict[str, str]）]
# }
def smoke_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for key in KADOKA_ENV_KEYS:
        environment.pop(key, None)
    environment["SDL_VIDEODRIVER"] = "dummy"
    environment["SDL_AUDIODRIVER"] = "dummy"
    environment["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    return environment


# {
#   責務: [diagnostic_text: distribution・smokeのdiagnostic・文字列を求める]
#   処理: [1: distribution・smokeのdiagnostic・文字列を求める]
#   引数: [distribution: distribution（Path）]
#   戻り値: [result: distribution・smokeのdiagnostic・文字列を求めるための結果（str）]
# }
def diagnostic_text(distribution: Path) -> str:
    error_path = Path(distribution) / "smoke-error.txt"
    if not error_path.is_file():
        return ""
    try:
        return "\nsmoke-error.txt:\n" + error_path.read_text(encoding="utf-8")
    except OSError:
        return "\nsmoke-error.txt exists but could not be read."


# {
#   責務: [run_process: processを実行する]
#   処理: [1: processを実行する]
#   引数: [
#     distribution: distribution（Path）
#     executable: executable（Path）
#     arguments: arguments（list[str]）
#     environment: environment（dict[str, str]）
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def run_process(distribution: Path, executable: Path, arguments: list[str], environment: dict[str, str]) -> None:
    distribution = Path(distribution)
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


# {
#   責務: [run_smoke: smokeを実行する]
#   処理: [1: smokeを実行する]
#   引数: [
#     key: キー（str）
#     distribution: distribution（Path）
#     executable: executable（Path）
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def run_smoke(key: str, distribution: Path, executable: Path) -> None:
    distribution = Path(distribution)
    user_data = distribution / "UserData"
    if user_data.exists():
        shutil.rmtree(user_data)
    user_data.mkdir(parents=True)
    environment = smoke_environment()

    run_process(distribution, executable, ["--smoke", "2"], environment)
    if key == "player":
        run_process(distribution, executable, ["--manager", "--smoke", "2"], environment)
        run_process(distribution, executable, ["--simulation-manager", "--smoke", "2"], environment)
        run_process(distribution, executable, ["--play", "--smoke", "2"], environment)
    else:
        for tool in DEVELOPER_TOOLS:
            run_process(distribution, executable, ["--dev-tool", tool, "--smoke", "2"], environment)

    required_writable = (
        user_data / "active.json",
        user_data / "default" / "state.json",
        user_data / "default" / "items" / "items.json",
        user_data / "default" / "simulation",
        user_data / "imports" / "acquire",
        user_data / "imports" / "simulation",
    )
    missing = [str(path) for path in required_writable if not path.exists()]
    if missing:
        raise AssertionError("distribution did not initialize UserData correctly:\n" + "\n".join(missing))
    if (distribution / "savedata").exists():
        raise AssertionError("frozen distribution wrote to savedata/ instead of UserData/")

    (distribution / "smoke-error.txt").unlink(missing_ok=True)
    reset_user_data(distribution)


# {
#   責務: [smoke_distributions: distribution・smokeのsmoke・distributionsを求める]
#   処理: [1: distribution・smokeのsmoke・distributionsを求める]
#   引数: [
#     dist_root: dist・基準ディレクトリ（Path）
#     targets: 対象一覧（str）
#   ]
#   戻り値: [result: checked（list[Path]）]
# }
def smoke_distributions(dist_root: Path, *, targets: str = "all") -> list[Path]:
    checked: list[Path] = []
    for key in selected_targets(targets):
        name = TARGET_NAMES[key]
        distribution = Path(dist_root) / name
        executable = verify_static_layout(distribution, name)
        print(f"[smoke] {executable}")
        run_smoke(key, distribution, executable)
        checked.append(distribution)
        print(f"[ok] {name}")
    return checked
