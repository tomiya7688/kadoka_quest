# {
#   責務: [battle_flow_dependencies: 戦闘・進行・dependenciesの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from kadoka_quest.apps.battle_session import BattleSession
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.state import StateStore


# {
#   責務: [BattleFlowDependencies: Dependencies needed by battle application flow without depending on KadokaQuest.]
#   フィールド: [
#     session: セッション（BattleSession）
#     monsters: モンスター一覧（MonsterStore）
#     states: states（StateStore）
#     state_provider: 状態・provider（Callable[[], dict]）
#   ]
# }
@dataclass(frozen=True)
class BattleFlowDependencies:
    """Dependencies needed by battle application flow without depending on KadokaQuest."""

    session: BattleSession
    monsters: MonsterStore
    states: StateStore
    state_provider: Callable[[], dict]
