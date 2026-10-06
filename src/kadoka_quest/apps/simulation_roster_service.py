# {
#   責務: [simulation_roster_service: simulation・所有個体台帳・serviceの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable

from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.jsonio import read_json, write_json
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.repository import GameRepository


# {
#   責務: [SimulationRosterService: Owns simulation-only monsters and one pending battle request.]
#   フィールド: [
#     root: 基準ディレクトリ
#     repository: データ取得先
#     store: 保存先
#     import_root: import・基準ディレクトリ
#     request_path: 要求・パス
#   ]
# }
class SimulationRosterService:
    """Owns simulation-only monsters and one pending battle request."""

    # {
    #   責務: [__init__: simulation・所有個体台帳・serviceが利用する初期状態と依存を設定する]
    #   処理: [1: simulation・所有個体台帳・serviceが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     root: 基準ディレクトリ（Path）
    #     repository: データ取得先（GameRepository）
    #     import_root: import・基準ディレクトリ（Path）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, root: Path, repository: GameRepository, import_root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.repository = repository
        self.store = MonsterStore(self.root, repository)
        self.import_root = Path(import_root)
        self.request_path = self.root / "battle_request.json"

    # {
    #   責務: [list_records: 個体レコード一覧を列挙する]
    #   処理: [1: 個体レコード一覧を列挙する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 個体レコード一覧を列挙するための結果（list[MonsterRecord]）]
    # }
    def list_records(self) -> list[MonsterRecord]:
        return self.store.list_records()

    # {
    #   責務: [create: simulation・所有個体台帳・serviceを作成する]
    #   処理: [1: simulation・所有個体台帳・serviceを作成する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     species_id: 種族・識別子（str）
    #     level: レベル（int）
    #     name: 名前（str | None）
    #     monster_id: モンスター・識別子（str | None）
    #   ]
    #   戻り値: [result: simulation・所有個体台帳・serviceを作成するための結果（MonsterRecord）]
    # }
    def create(
        self,
        species_id: str,
        *,
        level: int = 1,
        name: str | None = None,
        monster_id: str | None = None,
    ) -> MonsterRecord:
        return self.store.create(
            species_id,
            name=name,
            level=level,
            source="simulation",
            monster_id=monster_id,
        )

    # {
    #   責務: [delete: simulation・所有個体台帳・serviceを削除する]
    #   処理: [1: simulation・所有個体台帳・serviceを削除する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     monster_id: モンスター・識別子（str）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def delete(self, monster_id: str) -> None:
        self.store.delete(monster_id)

    # {
    #   責務: [import_external: externalを取り込む]
    #   処理: [1: externalを取り込む]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: externalを取り込むための結果（tuple[int, int]）]
    # }
    def import_external(self) -> tuple[int, int]:
        existing = {record.monster_id for record in self.list_records()}
        added = 0
        skipped = 0
        if not self.import_root.exists():
            return 0, 0
        for monster_path in sorted(self.import_root.rglob("monster.json")):
            ai_path = monster_path.parent / "ai.json"
            if not ai_path.is_file():
                skipped += 1
                continue
            try:
                record = MonsterRecord(read_json(monster_path), read_json(ai_path))
                self.repository.get_species(record.species_id)
            except (OSError, ValueError, KeyError):
                skipped += 1
                continue
            if record.monster_id in existing:
                skipped += 1
                continue
            shutil.copytree(monster_path.parent, self.root / record.monster_id)
            existing.add(record.monster_id)
            added += 1
        return added, skipped

    # {
    #   責務: [request_battle: simulation・所有個体台帳・serviceの要求・戦闘を求める]
    #   処理: [1: simulation・所有個体台帳・serviceの要求・戦闘を求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     monster_ids: モンスター・識別子一覧（Iterable[str]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def request_battle(self, monster_ids: Iterable[str]) -> None:
        selected: list[str] = []
        for monster_id in monster_ids:
            value = str(monster_id)
            if value in selected:
                continue
            if self.store.get(value) is None:
                raise KeyError(value)
            selected.append(value)
            if len(selected) == 4:
                break
        if not selected:
            raise ValueError("模擬戦の相手を1体以上選んでください。")
        write_json(self.request_path, {"schema_version": 1, "opponents": selected})

    # {
    #   責務: [consume_battle_request: 戦闘・要求を消費する]
    #   処理: [1: 戦闘・要求を消費する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 戦闘・要求を消費するための結果（list[MonsterRecord]）]
    # }
    def consume_battle_request(self) -> list[MonsterRecord]:
        if not self.request_path.is_file():
            return []
        try:
            data = read_json(self.request_path)
        finally:
            self.request_path.unlink(missing_ok=True)
        if not isinstance(data, dict):
            return []
        result: list[MonsterRecord] = []
        opponents = data.get("opponents", [])
        if not isinstance(opponents, list):
            return result
        for monster_id in opponents[:4]:
            record = self.store.get(str(monster_id))
            if record is not None:
                result.append(record)
        return result
