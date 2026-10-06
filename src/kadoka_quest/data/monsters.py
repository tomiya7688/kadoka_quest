# {
#   責務: [monsters: モンスター一覧の公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from kadoka_quest.core.ai import default_ai
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.jsonio import read_json, write_json
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.paths import SAVE_ROOT, ensure_runtime_directories


# {
#   責務: [MonsterStore: One directory per individual. There is intentionally no ownership limit.]
#   フィールド: [
#     root: 基準ディレクトリ
#     repository: データ取得先
#   ]
# }
class MonsterStore:
    """One directory per individual. There is intentionally no ownership limit."""

    # {
    #   責務: [__init__: モンスター・保存先が利用する初期状態と依存を設定する]
    #   処理: [1: モンスター・保存先が利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     root: 基準ディレクトリ（Path | None）
    #     repository: データ取得先（GameRepository | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, root: Path | None = None, repository: GameRepository | None = None) -> None:
        if root is None:
            ensure_runtime_directories()
        self.root = Path(root or (SAVE_ROOT / "monsters"))
        self.root.mkdir(parents=True, exist_ok=True)
        self.repository = repository or GameRepository()

    # {
    #   責務: [_folder: モンスター・保存先のフォルダを求める]
    #   処理: [1: モンスター・保存先のフォルダを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     monster_id: モンスター・識別子（str）
    #   ]
    #   戻り値: [result: モンスター・保存先のフォルダを求めるための結果（Path）]
    # }
    def _folder(self, monster_id: str) -> Path:
        return self.root / monster_id

    # {
    #   責務: [list_records: 個体レコード一覧を列挙する]
    #   処理: [1: 個体レコード一覧を列挙する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 個体レコード一覧（list[MonsterRecord]）]
    # }
    def list_records(self) -> list[MonsterRecord]:
        records: list[MonsterRecord] = []
        for path in sorted(self.root.glob("*/monster.json")):
            try:
                record = MonsterRecord(read_json(path), read_json(path.parent / "ai.json"))
                self.repository.get_species(record.species_id)
            except (OSError, ValueError, KeyError):
                continue
            records.append(record)
        return records

    # {
    #   責務: [get: モンスター・保存先を取得する]
    #   処理: [1: モンスター・保存先を取得する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     monster_id: モンスター・識別子（str）
    #   ]
    #   戻り値: [result: モンスター・保存先を取得するための結果（MonsterRecord | None）]
    # }
    def get(self, monster_id: str) -> MonsterRecord | None:
        folder = self._folder(monster_id)
        try:
            return MonsterRecord(read_json(folder / "monster.json"), read_json(folder / "ai.json"))
        except (OSError, ValueError, KeyError):
            return None

    # {
    #   責務: [create: モンスター・保存先を作成する]
    #   処理: [1: モンスター・保存先を作成する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     species_id: 種族・識別子（str）
    #     name: 名前（str | None）
    #     level: レベル（int）
    #     source: 元データ（str）
    #     monster_id: モンスター・識別子（str | None）
    #   ]
    #   戻り値: [result: モンスター・保存先を作成するための結果（MonsterRecord）]
    # }
    def create(
        self,
        species_id: str,
        name: str | None = None,
        level: int = 1,
        source: str = "game",
        monster_id: str | None = None,
    ) -> MonsterRecord:
        bundle = self.repository.get_species(species_id)
        monster_id = monster_id or f"monster_{uuid4().hex[:12]}"
        if self._folder(monster_id).exists():
            raise FileExistsError(monster_id)
        profile = str(bundle.definition.get("ai_profile", "normal"))
        monster = {
            "schema_version": 1,
            "id": monster_id,
            "species_id": species_id,
            "name": name or str(bundle.definition["display_name"]),
            "level": max(1, min(100, int(level))),
            "experience": 0,
            "plus_choices": [],
            "equipment_id": None,
            "source": source,
        }
        ai = default_ai(profile)
        write_json(self._folder(monster_id) / "monster.json", monster)
        write_json(self._folder(monster_id) / "ai.json", ai)
        return MonsterRecord(monster, ai)

    # {
    #   責務: [
    #     save: 個体フォルダの個体JSONと学習済みAIを保存する
    #   ]
    #   処理: [
    #     1: 個体IDに対応するmonster.jsonを書き込む
    #     2: 同じフォルダのai.jsonを書き込む
    #   ]
    #   引数: [
    #     self: 処理対象インスタンス
    #     record: 個体レコード（MonsterRecord）
    #   ]
    #   戻り値: [
    #     result: なし（None）。2ファイル全体の原子的保存を保証しない
    #   ]
    # }
    def save(self, record: MonsterRecord) -> None:
        write_json(self._folder(record.monster_id) / "monster.json", record.monster)
        write_json(self._folder(record.monster_id) / "ai.json", record.ai)

    # {
    #   責務: [save_ai: AIを保存する]
    #   処理: [1: AIを保存する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     monster_id: モンスター・識別子（str）
    #     ai: AI（dict）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def save_ai(self, monster_id: str, ai: dict) -> None:
        write_json(self._folder(monster_id) / "ai.json", ai)

    # {
    #   責務: [reset_ai: AIの初期状態へ戻す]
    #   処理: [1: AIの初期状態へ戻す]
    #   引数: [
    #     self: 処理対象インスタンス
    #     monster_id: モンスター・識別子（str）
    #   ]
    #   戻り値: [result: 個体レコード（MonsterRecord）]
    # }
    def reset_ai(self, monster_id: str) -> MonsterRecord:
        record = self.get(monster_id)
        if not record:
            raise KeyError(monster_id)
        profile = str(self.repository.get_species(record.species_id).definition.get("ai_profile", "normal"))
        record.ai = default_ai(profile, str(record.ai.get("tactic", "balanced")))
        self.save_ai(monster_id, record.ai)
        return record

    # {
    #   責務: [set_tactic: tacticを設定する]
    #   処理: [1: tacticを設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     monster_id: モンスター・識別子（str）
    #     tactic: tactic（str）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def set_tactic(self, monster_id: str, tactic: str) -> None:
        record = self.get(monster_id)
        if not record:
            raise KeyError(monster_id)
        record.ai["tactic"] = tactic
        self.save_ai(monster_id, record.ai)

    # {
    #   責務: [discover_external: externalを検出する]
    #   処理: [1: externalを検出する]
    #   引数: [root: 基準ディレクトリ（Path）]
    #   戻り値: [result: 個体レコード一覧（list[MonsterRecord]）]
    # }
    @staticmethod
    def discover_external(root: Path) -> list[MonsterRecord]:
        records: list[MonsterRecord] = []
        if not root.exists():
            return records
        for path in sorted(root.rglob("monster.json")):
            ai_path = path.parent / "ai.json"
            if not ai_path.exists():
                continue
            try:
                records.append(MonsterRecord(read_json(path), read_json(ai_path)))
            except (OSError, ValueError, KeyError):
                continue
        return records

    # {
    #   責務: [acquire_from_scan: モンスター・保存先のacquire・from・scanを求める]
    #   処理: [1: モンスター・保存先のacquire・from・scanを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     source_root: 元データ・基準ディレクトリ（Path）
    #   ]
    #   戻り値: [result: モンスター・保存先のacquire・from・scanを求めるための結果（tuple[int, int]）]
    # }
    def acquire_from_scan(self, source_root: Path) -> tuple[int, int]:
        existing = {record.monster_id for record in self.list_records()}
        added = 0
        skipped = 0
        source_root = Path(source_root)
        if not source_root.exists():
            return 0, 0
        for monster_path in sorted(source_root.rglob("monster.json")):
            ai_path = monster_path.parent / "ai.json"
            if not ai_path.exists():
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
            shutil.copytree(monster_path.parent, self._folder(record.monster_id))
            existing.add(record.monster_id)
            added += 1
        return added, skipped

    # {
    #   責務: [ensure_species: 種族を必要な状態を用意する]
    #   処理: [1: 種族を必要な状態を用意する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     species_id: 種族・識別子（str）
    #     name: 名前（str | None）
    #   ]
    #   戻り値: [result: 種族を必要な状態を用意するための結果（MonsterRecord）]
    # }
    def ensure_species(self, species_id: str, name: str | None = None) -> MonsterRecord:
        for record in self.list_records():
            if record.species_id == species_id:
                return record
        return self.create(species_id, name=name, source="starter")

    # {
    #   責務: [delete: モンスター・保存先を削除する]
    #   処理: [1: モンスター・保存先を削除する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     monster_id: モンスター・識別子（str）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def delete(self, monster_id: str) -> None:
        folder = self._folder(monster_id)
        if folder.exists():
            shutil.rmtree(folder)

    # {
    #   責務: [save_all_ai: all・AIを保存する]
    #   処理: [1: all・AIを保存する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     records: 個体レコード一覧（Iterable[MonsterRecord]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def save_all_ai(self, records: Iterable[MonsterRecord]) -> None:
        owned = {record.monster_id for record in self.list_records()}
        for record in records:
            if record.monster_id in owned:
                self.save_ai(record.monster_id, record.ai)

