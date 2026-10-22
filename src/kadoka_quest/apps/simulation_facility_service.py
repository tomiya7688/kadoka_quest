# {
#   責務: [simulation_facility_service: simulation・facility・serviceの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
import random

from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.jsonio import read_json, write_json
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.repository import GameRepository


# {
#   責務: [SimulationFacilityService: Own the isolated roster used by the in-world simulation facility.]
#   フィールド: [
#     repository: データ取得先
#     root: 基準ディレクトリ
#     store: 保存先
#     party_path: パーティ・パス
#     battle_factory: 戦闘・factory
#   ]
# }
class SimulationFacilityService:
    """Own the isolated roster used by the in-world simulation facility."""

    # {
    #   責務: [__init__: simulation・facility・serviceが利用する初期状態と依存を設定する]
    #   処理: [1: simulation・facility・serviceが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     repository: データ取得先（GameRepository）
    #     simulation_root: simulation・基準ディレクトリ（Path）
    #     battle_factory: 戦闘・factory（Callable[..., BattleEngine]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(
        self,
        repository: GameRepository,
        simulation_root: Path,
        battle_factory: Callable[..., BattleEngine] = BattleEngine,
    ) -> None:
        self.repository = repository
        self.root = Path(simulation_root)
        self.store = MonsterStore(self.root, repository)
        self.party_path = self.root / "simulation_party.json"
        self.battle_factory = battle_factory

    # {
    #   責務: [list_individuals: individualsを列挙する]
    #   処理: [1: individualsを列挙する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: individualsを列挙するための結果（list[MonsterRecord]）]
    # }
    def list_individuals(self) -> list[MonsterRecord]:
        return self.store.list_records()

    # {
    #   責務: [create_individual: individualを作成する]
    #   処理: [1: individualを作成する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     species_id: 種族・識別子（str）
    #     level: レベル（int）
    #     name: 名前（str | None）
    #   ]
    #   戻り値: [result: individualを作成するための結果（MonsterRecord）]
    # }
    def create_individual(self, species_id: str, level: int = 1, name: str | None = None) -> MonsterRecord:
        return self.store.create(species_id, name=name, level=level, source="simulation_facility")

    # {
    #   責務: [delete_individual: individualを削除する]
    #   処理: [1: individualを削除する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     monster_id: モンスター・識別子（str）
    #   ]
    #   戻り値: [result: individualを削除するための結果（bool）]
    # }
    def delete_individual(self, monster_id: str) -> bool:
        if self.store.get(monster_id) is None:
            return False
        self.store.delete(monster_id)
        self._save_opponent_ids([item for item in self.opponent_ids() if item != monster_id])
        return True

    # {
    #   責務: [opponent_ids: simulation・facility・serviceのopponent・識別子一覧を求める]
    #   処理: [1: simulation・facility・serviceのopponent・識別子一覧を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: simulation・facility・serviceのopponent・識別子一覧を求めるための結果（list[str]）]
    # }
    def opponent_ids(self) -> list[str]:
        try:
            value = read_json(self.party_path)
            identifiers = value.get("monster_ids", [])
        except (OSError, ValueError, TypeError):
            return []
        if not isinstance(identifiers, list):
            return []
        return [str(identifier) for identifier in identifiers]

    # {
    #   責務: [set_opponents: opponentsを設定する]
    #   処理: [1: opponentsを設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     monster_ids: モンスター・識別子一覧（Sequence[str]）
    #   ]
    #   戻り値: [result: 選択中（list[MonsterRecord]）]
    # }
    def set_opponents(self, monster_ids: Sequence[str]) -> list[MonsterRecord]:
        records = {record.monster_id: record for record in self.list_individuals()}
        unique_ids = list(dict.fromkeys(str(identifier) for identifier in monster_ids))
        selected = [records[identifier] for identifier in unique_ids if identifier in records]
        if not selected:
            raise ValueError("模擬戦相手を1体以上選択してください。")
        self._save_opponent_ids([record.monster_id for record in selected])
        return selected

    # {
    #   責務: [clear_opponents: opponentsを消去する]
    #   処理: [1: opponentsを消去する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def clear_opponents(self) -> None:
        self._save_opponent_ids([])

    # {
    #   責務: [opponents: simulation・facility・serviceのopponentsを求める]
    #   処理: [1: simulation・facility・serviceのopponentsを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: simulation・facility・serviceのopponentsを求めるための結果（list[MonsterRecord]）]
    # }
    def opponents(self) -> list[MonsterRecord]:
        records = {record.monster_id: record for record in self.list_individuals()}
        return [records[identifier] for identifier in self.opponent_ids() if identifier in records]

    # {
    #   責務: [create_battle: 戦闘を作成する]
    #   処理: [1: 戦闘を作成する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     allies: 味方（Sequence[MonsterRecord]）
    #     rng: 乱数供給元（random.Random）
    #   ]
    #   戻り値: [result: 戦闘を作成するための結果（tuple[BattleEngine | None, str]）]
    # }
    def create_battle(
        self, allies: Sequence[MonsterRecord], rng: random.Random
    ) -> tuple[BattleEngine | None, str]:
        opponents = self.opponents()
        if not opponents:
            return None, "模擬戦施設で相手パーティを編成してください。"
        try:
            battle = self.battle_factory(
                self.repository, list(allies), opponents, rng, learning_enabled=False
            )
        except (OSError, ValueError, KeyError) as exc:
            return None, f"模擬戦個体を読めません: {exc}"
        return battle, "模擬戦を開始。双方のAIは更新されず、報酬も発生しません。"

    # {
    #   責務: [_save_opponent_ids: opponent・識別子一覧を保存する]
    #   処理: [1: opponent・識別子一覧を保存する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     monster_ids: モンスター・識別子一覧（list[str]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def _save_opponent_ids(self, monster_ids: list[str]) -> None:
        write_json(self.party_path, {"schema_version": 1, "monster_ids": monster_ids})
