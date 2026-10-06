# {
#   責務: [jsonio: jsonioの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any


REPLACE_RETRY_DELAYS = (0.05, 0.1, 0.2, 0.4, 0.8, 1.0, 1.0, 1.0)


# {
#   責務: [read_json: JSONを読み取る]
#   処理: [1: JSONを読み取る]
#   引数: [path: パス（Path）]
#   戻り値: [result: 値（dict[str, Any]）]
# }
def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


# {
#   責務: [write_json: JSONを書き込み、一時ファイルからの置換で保存先を更新する]
#   処理: [
#     1: 保存先の親を用意しUTF-8のJSONを一時ファイルへ書く
#     2: Windowsの一時的な置換失敗を再試行し、解消しない失敗は呼出元へ返す
#   ]
#   引数: [
#     path: パス（Path）
#     value: 値（dict[str, Any]）
#   ]
#   戻り値: [result: なし。解消しない保存失敗は例外]
# }
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


