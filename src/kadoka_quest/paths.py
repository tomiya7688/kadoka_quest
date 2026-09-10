from __future__ import annotations

import json
import os
from pathlib import Path
import sys


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


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


def active_save_name() -> str:
    try:
        value = json.loads((SAVEDATA_ROOT / "active.json").read_text(encoding="utf-8"))
        name = str(value.get("active", "default")).strip()
        return name or "default"
    except (OSError, ValueError, TypeError):
        return "default"


SAVE_ROOT = Path(os.environ.get("KADOKA_SAVE_DIR", SAVEDATA_ROOT / active_save_name()))


def ensure_runtime_directories() -> None:
    for path in (
        SAVEDATA_ROOT,
        SAVE_ROOT / "monsters",
        SAVE_ROOT / "parties",
        SAVE_ROOT / "items",
        IMPORT_ROOT / "acquire",
        IMPORT_ROOT / "simulation",
    ):
        path.mkdir(parents=True, exist_ok=True)
