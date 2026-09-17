from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
import random

from kadoka_quest.apps.legacy_simulation_import_service import LegacySimulationImportService
from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.repository import GameRepository


class MonsterImportService:
    """Own acquisition scans while retaining a temporary legacy simulation bridge."""

    def __init__(
        self,
        monsters: MonsterStore,
        repository: GameRepository,
        import_root: Path,
        battle_factory: Callable[..., BattleEngine] = BattleEngine,
    ) -> None:
        self.monsters = monsters
        self.acquire_root = Path(import_root) / "acquire"
        self.legacy_simulation = LegacySimulationImportService(
            monsters,
            repository,
            Path(import_root) / "simulation",
            battle_factory,
        )

    def scan_acquire(self) -> str:
        added, skipped = self.monsters.acquire_from_scan(self.acquire_root)
        return f"個体再走査：{added}体を獲得、{skipped}件をスキップ。"

    def create_simulation(
        self,
        allies: Sequence[MonsterRecord],
        rng: random.Random,
    ) -> tuple[BattleEngine | None, str]:
        """Compatibility bridge for the retired direct simulation API."""
        return self.legacy_simulation.create(allies, rng)
