# {
#   責務: [monster_import_service: モンスター・import・serviceの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
import random

from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.repository import GameRepository


# {
#   責務: [MonsterImportService: Owns acquisition scans and simulation imports from external folders.]
#   フィールド: [
#     monsters: モンスター一覧
#     repository: データ取得先
#     acquire_root: acquire・基準ディレクトリ
#     simulation_root: simulation・基準ディレクトリ
#     battle_factory: 戦闘・factory
#   ]
# }
class MonsterImportService:
    """Owns acquisition scans and simulation imports from external folders."""

    # {
    #   責務: [__init__: モンスター・import・serviceが利用する初期状態と依存を設定する]
    #   処理: [1: モンスター・import・serviceが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     monsters: モンスター一覧（MonsterStore）
    #     repository: データ取得先（GameRepository）
    #     import_root: import・基準ディレクトリ（Path）
    #     battle_factory: 戦闘・factory（Callable[..., BattleEngine]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(
        self,
        monsters: MonsterStore,
        repository: GameRepository,
        import_root: Path,
        battle_factory: Callable[..., BattleEngine] = BattleEngine,
    ) -> None:
        self.monsters = monsters
        self.repository = repository
        self.acquire_root = Path(import_root) / "acquire"
        self.simulation_root = Path(import_root) / "simulation"
        self.battle_factory = battle_factory

    # {
    #   責務: [scan_acquire: acquireを再走査する]
    #   処理: [1: acquireを再走査する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: acquireを再走査するための結果（str）]
    # }
    def scan_acquire(self) -> str:
        added, skipped = self.monsters.acquire_from_scan(self.acquire_root)
        return f"個体再走査：{added}体を獲得、{skipped}件をスキップ。"

    # {
    #   責務: [create_simulation: simulationを作成する]
    #   処理: [1: simulationを作成する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     allies: 味方（Sequence[MonsterRecord]）
    #     rng: 乱数供給元（random.Random）
    #   ]
    #   戻り値: [result: simulationを作成するための結果（tuple[BattleEngine | None, str]）]
    # }
    def create_simulation(
        self,
        allies: Sequence[MonsterRecord],
        rng: random.Random,
    ) -> tuple[BattleEngine | None, str]:
        imported = self.monsters.discover_external(self.simulation_root)
        if not imported:
            return None, "imports/simulation に個体フォルダを置いてください。"
        try:
            battle = self.battle_factory(
                self.repository,
                list(allies),
                imported,
                rng,
                learning_enabled=False,
            )
        except (OSError, ValueError, KeyError) as exc:
            return None, f"模擬戦個体を読めません: {exc}"
        return battle, "模擬戦を開始。双方のAIは更新されません。"
