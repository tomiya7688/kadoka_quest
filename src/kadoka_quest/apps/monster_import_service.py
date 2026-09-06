from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
import random

from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.repository import GameRepository


class MonsterImportService:
    """Owns acquisition scans and simulation imports from external folders."""

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

    def scan_acquire(self) -> str:
        added, skipped = self.monsters.acquire_from_scan(self.acquire_root)
        return f"個体再走査：{added}体を獲得、{skipped}件をスキップ。"

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
