# {
#   責務: [parties: partiesの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import re
from pathlib import Path

from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.jsonio import read_json, write_json
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.paths import SAVE_ROOT


# {
#   責務: [PartyStore: Unlimited preset files. A playable party still has four positions.]
#   フィールド: [root: 基準ディレクトリ]
# }
class PartyStore:
    """Unlimited preset files. A playable party still has four positions."""

    # {
    #   責務: [__init__: パーティ・保存先が利用する初期状態と依存を設定する]
    #   処理: [1: パーティ・保存先が利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     root: 基準ディレクトリ（Path | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root or (SAVE_ROOT / "parties"))
        self.root.mkdir(parents=True, exist_ok=True)

    # {
    #   責務: [_slug: パーティ・保存先のslugを求める]
    #   処理: [1: パーティ・保存先のslugを求める]
    #   引数: [name: 名前（str）]
    #   戻り値: [result: パーティ・保存先のslugを求めるための結果（str）]
    # }
    @staticmethod
    def _slug(name: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", name).strip("_").lower()
        return slug or "party"

    # {
    #   責務: [save: パーティ・保存先を保存する]
    #   処理: [1: パーティ・保存先を保存する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     name: 名前（str）
    #     member_ids: 個体・識別子一覧（list[str | None]）
    #     overwrite: overwrite（bool）
    #   ]
    #   戻り値: [result: パス（Path）]
    # }
    def save(self, name: str, member_ids: list[str | None], overwrite: bool = False) -> Path:
        base = self._slug(name)
        path = self.root / f"{base}.json"
        if path.exists() and not overwrite:
            index = 2
            while (self.root / f"{base}_{index}.json").exists():
                index += 1
            path = self.root / f"{base}_{index}.json"
        write_json(
            path,
            {
                "schema_version": 1,
                "name": name,
                "members": list(member_ids[:4]) + [None] * max(0, 4 - len(member_ids)),
            },
        )
        return path

    # {
    #   責務: [list_presets: プリセット一覧を列挙する]
    #   処理: [1: プリセット一覧を列挙する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: プリセット一覧を列挙するための結果（list[Path]）]
    # }
    def list_presets(self) -> list[Path]:
        return sorted(self.root.glob("*.json"))

    # {
    #   責務: [update: パーティ・保存先を更新する]
    #   処理: [1: パーティ・保存先を更新する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     path: パス（Path）
    #     name: 名前（str）
    #     member_ids: 個体・識別子一覧（list[str | None]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def update(self, path: Path, name: str, member_ids: list[str | None]) -> None:
        if Path(path).parent.resolve() != self.root.resolve():
            raise ValueError("Preset must be inside the party directory")
        write_json(
            Path(path),
            {
                "schema_version": 1,
                "name": name,
                "members": list(member_ids[:4]) + [None] * max(0, 4 - len(member_ids)),
            },
        )

    # {
    #   責務: [load: パーティ・保存先を読み込む]
    #   処理: [1: パーティ・保存先を読み込む]
    #   引数: [
    #     self: 処理対象インスタンス
    #     path: パス（Path）
    #     monsters: モンスター一覧（MonsterStore）
    #   ]
    #   戻り値: [result: パーティ・保存先を読み込むための結果（list[MonsterRecord | None]）]
    # }
    def load(self, path: Path, monsters: MonsterStore) -> list[MonsterRecord | None]:
        data = read_json(path)
        result: list[MonsterRecord | None] = []
        for monster_id in list(data.get("members", []))[:4]:
            result.append(monsters.get(str(monster_id)) if monster_id else None)
        return result + [None] * (4 - len(result))

