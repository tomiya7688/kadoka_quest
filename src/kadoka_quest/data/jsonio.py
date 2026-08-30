from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any


REPLACE_RETRY_DELAYS = (0.05, 0.1, 0.2, 0.4, 0.8, 1.0, 1.0, 1.0)


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        for attempt in range(len(REPLACE_RETRY_DELAYS) + 1):
            try:
                os.replace(temporary, path)
                return
            except PermissionError:
                if attempt == len(REPLACE_RETRY_DELAYS):
                    raise
                time.sleep(REPLACE_RETRY_DELAYS[attempt])
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


