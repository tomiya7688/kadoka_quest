from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import shutil

from kadoka_quest.data.jsonio import read_json, write_json
from kadoka_quest.paths import SAVEDATA_ROOT


INVALID_NAME = re.compile(r'[\\/:*?"<>|]')


class SaveDataManager:
    """Named, openly editable save folders under savedata/."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root or SAVEDATA_ROOT)
        self.root.mkdir(parents=True, exist_ok=True)

    def validate_name(self, name: str) -> str:
        clean = name.strip()
        if not clean or clean in {".", ".."} or INVALID_NAME.search(clean):
            raise ValueError("セーブ名には \\ / : * ? \" < > | を使えません。")
        return clean[:40]

    def profile_root(self, name: str) -> Path:
        return self.root / self.validate_name(name)

    def list_names(self) -> list[str]:
        return sorted(path.name for path in self.root.iterdir() if path.is_dir() and (path / "state.json").is_file())

    def active_name(self) -> str:
        try:
            name = str(read_json(self.root / "active.json").get("active", "default"))
            return name if name in self.list_names() else (self.list_names()[0] if self.list_names() else "default")
        except (OSError, ValueError, KeyError):
            return self.list_names()[0] if self.list_names() else "default"

    def set_active(self, name: str) -> Path:
        path = self.profile_root(name)
        if not (path / "state.json").is_file():
            raise FileNotFoundError(name)
        write_json(self.root / "active.json", {"schema_version": 1, "active": name})
        return path

    def create(self, name: str) -> Path:
        from kadoka_quest.data.state import DEFAULT_STATE

        clean = self.validate_name(name)
        path = self.root / clean
        if path.exists():
            raise FileExistsError(clean)
        for folder in ("monsters", "items", "parties"):
            (path / folder).mkdir(parents=True, exist_ok=True)
        state = {key: (dict(value) if isinstance(value, dict) else list(value) if isinstance(value, list) else value) for key, value in DEFAULT_STATE.items()}
        inventory = dict(state.pop("inventory", {}))
        write_json(path / "state.json", state)
        write_json(path / "items" / "items.json", {"schema_version": 1, "items": inventory})
        write_json(path / "meta.json", {"schema_version": 1, "name": clean, "created_at": datetime.now().isoformat(timespec="seconds")})
        self.set_active(clean)
        return path

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

