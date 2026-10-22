# {
#   責務: [paths: パス一覧の公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import json
import os
from pathlib import Path
import sys


# {
#   責務: [is_frozen: frozenを該当するか判定する]
#   処理: [1: frozenを該当するか判定する]
#   引数: []
#   戻り値: [result: frozenを該当するか判定するための結果（bool）]
# }
def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


# {
#   責務: [runtime_root: パス一覧の実行時・基準ディレクトリを求める]
#   処理: [1: パス一覧の実行時・基準ディレクトリを求める]
#   引数: []
#   戻り値: [result: パス一覧の実行時・基準ディレクトリを求めるための結果（Path）]
# }
def runtime_root() -> Path:
    override = os.environ.get("KADOKA_PROJECT_ROOT")
    if override:
        return Path(override).resolve()
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


PROJECT_ROOT = runtime_root()
DATA_ROOT = Path(os.environ.get("KADOKA_DATA_DIR", PROJECT_ROOT / "data"))
ASSET_ROOT = Path(os.environ.get("KADOKA_ASSET_DIR", PROJECT_ROOT / "assets"))
DEFAULT_SAVEDATA_ROOT = PROJECT_ROOT / ("UserData" if is_frozen() else "savedata")
SAVEDATA_ROOT = Path(os.environ.get("KADOKA_SAVEDATA_ROOT", DEFAULT_SAVEDATA_ROOT))
DEFAULT_IMPORT_ROOT = SAVEDATA_ROOT / "imports" if is_frozen() else PROJECT_ROOT / "imports"
IMPORT_ROOT = Path(os.environ.get("KADOKA_IMPORT_DIR", DEFAULT_IMPORT_ROOT))


# {
#   責務: [active_save_name: パス一覧のactive・保存・名前を求める]
#   処理: [1: パス一覧のactive・保存・名前を求める]
#   引数: []
#   戻り値: [result: パス一覧のactive・保存・名前を求めるための結果（str）]
# }
def active_save_name() -> str:
    try:
        value = json.loads((SAVEDATA_ROOT / "active.json").read_text(encoding="utf-8"))
        name = str(value.get("active", "default")).strip()
        return name or "default"
    except (OSError, ValueError, TypeError):
        return "default"


SAVE_ROOT = Path(os.environ.get("KADOKA_SAVE_DIR", SAVEDATA_ROOT / active_save_name()))


# {
#   責務: [ensure_runtime_directories: 実行時・directoriesを必要な状態を用意する]
#   処理: [1: 実行時・directoriesを必要な状態を用意する]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def ensure_runtime_directories() -> None:
    for path in (
        SAVEDATA_ROOT,
        SAVE_ROOT / "monsters",
        SAVE_ROOT / "parties",
        SAVE_ROOT / "items",
        SAVE_ROOT / "simulation",
        IMPORT_ROOT / "acquire",
        IMPORT_ROOT / "simulation",
    ):
        path.mkdir(parents=True, exist_ok=True)
