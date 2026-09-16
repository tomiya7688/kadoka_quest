from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from kadoka_quest.apps.battle_session import BattleSession
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.state import StateStore


@dataclass(frozen=True)
class BattleFlowDependencies:
    """Dependencies needed by battle application flow without depending on KadokaQuest."""

    session: BattleSession
    monsters: MonsterStore
    states: StateStore
    state_provider: Callable[[], dict]
    clock: Callable[[], int]
