from __future__ import annotations

import os
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path(os.environ.get("KADOKA_DATA_DIR", PROJECT_ROOT / "data"))
ASSET_ROOT = Path(os.environ.get("KADOKA_ASSET_DIR", PROJECT_ROOT / "assets"))
SAVEDATA_ROOT = Path(os.environ.get("KADOKA_SAVEDATA_ROOT", PROJECT_ROOT / "savedata"))


def active_save_name() -> str:
    try:
        value = json.loads((SAVEDATA_ROOT / "active.json").read_text(encoding="utf-8"))
        name = str(value.get("active", "default")).strip()
        return name or "default"
    except (OSError, ValueError, TypeError):
        return "default"


SAVE_ROOT = Path(os.environ.get("KADOKA_SAVE_DIR", SAVEDATA_ROOT / active_save_name()))
IMPORT_ROOT = Path(os.environ.get("KADOKA_IMPORT_DIR", PROJECT_ROOT / "imports"))


def ensure_runtime_directories() -> None:
    for path in (
        SAVE_ROOT / "monsters",
        SAVE_ROOT / "parties",
        SAVE_ROOT / "items",
        IMPORT_ROOT / "acquire",
        IMPORT_ROOT / "simulation",
    ):
        path.mkdir(parents=True, exist_ok=True)

