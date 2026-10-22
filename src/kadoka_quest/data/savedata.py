# {
#   責務: [savedata: セーブデータの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import shutil

from kadoka_quest.data.jsonio import read_json, write_json
from kadoka_quest.paths import SAVEDATA_ROOT


INVALID_NAME = re.compile(r'[\\/:*?"<>|]')
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


# {
#   責務: [SaveDataManager: Named, openly editable save folders under savedata/.]
#   フィールド: [root: 基準ディレクトリ]
# }
class SaveDataManager:
    """Named, openly editable save folders under savedata/."""

    # {
    #   責務: [__init__: 保存・データ・managerが利用する初期状態と依存を設定する]
    #   処理: [1: 保存・データ・managerが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     root: 基準ディレクトリ（Path | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root or SAVEDATA_ROOT)
        self.root.mkdir(parents=True, exist_ok=True)

    # {
    #   責務: [validate_name: 名前を妥当性を検査する]
    #   処理: [1: 名前を妥当性を検査する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     name: 名前（str）
    #   ]
    #   戻り値: [result: 名前を妥当性を検査するための結果（str）]
    # }
    def validate_name(self, name: str) -> str:
        if not name or not name.strip():
            raise ValueError("セーブ名を入力してください。")
        if name != name.strip():
            raise ValueError("セーブ名の先頭・末尾に空白は使えません。")
        clean = name
        if clean in {".", ".."} or INVALID_NAME.search(clean) or any(ord(character) < 32 for character in clean):
            raise ValueError("セーブ名には \\ / : * ? \" < > | や制御文字を使えません。")
        if clean.endswith("."):
            raise ValueError("セーブ名の末尾にドットは使えません。")
        device_name = clean.split(".", 1)[0].upper()
        if device_name in WINDOWS_RESERVED_NAMES:
            raise ValueError(f"{clean} はWindowsで予約されているためセーブ名に使えません。")
        return clean[:40]

    # {
    #   責務: [profile_root: 保存・データ・managerのプロファイル・基準ディレクトリを求める]
    #   処理: [1: 保存・データ・managerのプロファイル・基準ディレクトリを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     name: 名前（str）
    #   ]
    #   戻り値: [result: 保存・データ・managerのプロファイル・基準ディレクトリを求めるための結果（Path）]
    # }
    def profile_root(self, name: str) -> Path:
        return self.root / self.validate_name(name)

    # {
    #   責務: [list_names: 名前一覧を列挙する]
    #   処理: [1: 名前一覧を列挙する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 名前一覧を列挙するための結果（list[str]）]
    # }
    def list_names(self) -> list[str]:
        return sorted(path.name for path in self.root.iterdir() if path.is_dir() and (path / "state.json").is_file())

    # {
    #   責務: [active_name: 保存・データ・managerのactive・名前を求める]
    #   処理: [1: 保存・データ・managerのactive・名前を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 保存・データ・managerのactive・名前を求めるための結果（str）]
    # }
    def active_name(self) -> str:
        try:
            name = str(read_json(self.root / "active.json").get("active", "default"))
            return name if name in self.list_names() else (self.list_names()[0] if self.list_names() else "default")
        except (OSError, ValueError, KeyError):
            return self.list_names()[0] if self.list_names() else "default"

    # {
    #   責務: [set_active: activeを設定する]
    #   処理: [1: activeを設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     name: 名前（str）
    #   ]
    #   戻り値: [result: パス（Path）]
    # }
    def set_active(self, name: str) -> Path:
        path = self.profile_root(name)
        if not (path / "state.json").is_file():
            raise FileNotFoundError(name)
        write_json(self.root / "active.json", {"schema_version": 1, "active": name})
        return path

    # {
    #   責務: [_default_state: 保存・データ・managerのdefault・状態を求める]
    #   処理: [1: 保存・データ・managerのdefault・状態を求める]
    #   引数: []
    #   戻り値: [result: 保存・データ・managerのdefault・状態を求めるための結果（tuple[dict, dict]）]
    # }
    @staticmethod
    def _default_state() -> tuple[dict, dict]:
        from kadoka_quest.data.state import DEFAULT_STATE

        state = {
            key: (dict(value) if isinstance(value, dict) else list(value) if isinstance(value, list) else value)
            for key, value in DEFAULT_STATE.items()
        }
        inventory = dict(state.pop("inventory", {}))
        return state, inventory

    # {
    #   責務: [_initialize_profile: プロファイルの初期化する]
    #   処理: [1: プロファイルの初期化する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     clean: clean（str）
    #     path: パス（Path）
    #   ]
    #   戻り値: [result: パス（Path）]
    # }
    def _initialize_profile(self, clean: str, path: Path) -> Path:
        for folder in ("monsters", "items", "parties"):
            (path / folder).mkdir(parents=True, exist_ok=True)
        state, inventory = self._default_state()
        if not (path / "state.json").is_file():
            write_json(path / "state.json", state)
        if not (path / "items" / "items.json").is_file():
            write_json(path / "items" / "items.json", {"schema_version": 1, "items": inventory})
        if not (path / "meta.json").is_file():
            write_json(path / "meta.json", {"schema_version": 1, "name": clean, "created_at": datetime.now().isoformat(timespec="seconds")})
        self.set_active(clean)
        return path

    # {
    #   責務: [ensure_profile: Initialize a missing/incomplete bootstrap profile without deleting user files.]
    #   処理: [1: Initialize a missing/incomplete bootstrap profile without deleting user files.]
    #   引数: [
    #     self: 処理対象インスタンス
    #     name: 名前（str）
    #   ]
    #   戻り値: [result: Initialize a missing/incomplete bootstrap profile without deleting user files.ための結果（Path）]
    # }
    def ensure_profile(self, name: str) -> Path:
        """Initialize a missing/incomplete bootstrap profile without deleting user files."""
        clean = self.validate_name(name)
        path = self.root / clean
        path.mkdir(parents=True, exist_ok=True)
        return self._initialize_profile(clean, path)

    # {
    #   責務: [create: 保存・データ・managerを作成する]
    #   処理: [1: 保存・データ・managerを作成する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     name: 名前（str）
    #   ]
    #   戻り値: [result: 保存・データ・managerを作成するための結果（Path）]
    # }
    def create(self, name: str) -> Path:
        clean = self.validate_name(name)
        path = self.root / clean
        if path.exists():
            raise FileExistsError(clean)
        path.mkdir(parents=True)
        return self._initialize_profile(clean, path)

    # {
    #   責務: [copy_profile: プロファイルを複製する]
    #   処理: [1: プロファイルを複製する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     source_name: 元データ・名前（str）
    #     new_name: new・名前（str）
    #   ]
    #   戻り値: [result: destination（Path）]
    # }
    def copy_profile(self, source_name: str, new_name: str) -> Path:
        source = self.profile_root(source_name)
        destination = self.profile_root(new_name)
        if destination.exists():
            raise FileExistsError(new_name)
        shutil.copytree(source, destination)
        meta_path = destination / "meta.json"
        meta = read_json(meta_path) if meta_path.exists() else {"schema_version": 1}
        meta.update({"name": self.validate_name(new_name), "copied_from": source_name, "created_at": datetime.now().isoformat(timespec="seconds")})
        write_json(meta_path, meta)
        self.set_active(new_name)
        return destination

    # {
    #   責務: [import_legacy: legacyを取り込む]
    #   処理: [1: legacyを取り込む]
    #   引数: [
    #     self: 処理対象インスタンス
    #     source: 元データ（Path）
    #     name: 名前（str）
    #   ]
    #   戻り値: [result: legacyを取り込むための結果（Path | None）]
    # }
    def import_legacy(self, source: Path, name: str = "以前のセーブ") -> Path | None:
        source = Path(source)
        if not (source / "state.json").is_file():
            return None
        destination = self.profile_root(name)
        if destination.exists():
            return destination
        shutil.copytree(source, destination)
        for folder in ("monsters", "items", "parties"):
            (destination / folder).mkdir(parents=True, exist_ok=True)
        from kadoka_quest.data.state import StateStore

        states = StateStore(destination / "state.json")
        states.save(states.load())
        write_json(destination / "meta.json", {"schema_version": 1, "name": name, "imported_from": str(source), "created_at": datetime.now().isoformat(timespec="seconds")})
        return destination
