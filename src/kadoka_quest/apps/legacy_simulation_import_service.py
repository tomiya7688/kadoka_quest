from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
import random

from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.repository import GameRepository


class LegacySimulationImportService:
    """Build the retired imports/simulation battle path for compatibility only."""

    def __init__(
        self,
        monsters: MonsterStore,
        repository: GameRepository,
        simulation_root: Path,
        battle_factory: Callable[..., BattleEngine] = BattleEngine,
    ) -> None:
        self.monsters = monsters
        self.repository = repository
        self.simulation_root = Path(simulation_root)
        self.battle_factory = battle_factory

    def create(
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
