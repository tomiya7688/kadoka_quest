from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime

from kadoka_quest.apps.field_party_session import FieldPartySession
from kadoka_quest.core.ai import TACTICS
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.parties import PartyStore
from kadoka_quest.data.state import StateStore


class FieldPartyService:
    """Coordinates field quick-party operations through the existing stores."""

    def __init__(
        self,
        session: FieldPartySession,
        parties: PartyStore,
        monsters: MonsterStore,
        states: StateStore,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.session = session
        self.parties = parties
        self.monsters = monsters
        self.states = states
        self.now = now or datetime.now

    def select(self, index: int) -> bool:
        self.session.select(index)
        return True

    def save_preset(self, state: dict) -> str:
        name = "フィールド編成_" + self.now().strftime("%Y%m%d_%H%M%S")
        path = self.parties.save(name, list(state.get("current_party", [])))
        return f"{path.name} を保存しました。"

    def load_next_preset(self, state: dict) -> str:
        path = self.session.next_preset(self.parties.list_presets())
        if path is None:
            return "保存パーティがありません。"
        loaded = self.parties.load(path, self.monsters)
        state["current_party"] = [record.monster_id for record in loaded if record]
        self.states.save(state)
        return f"{path.name} を読み込みました。欠損IDは空き枠です。"

    def cycle_tactic(self, party: Sequence[MonsterRecord]) -> str | None:
        record = self.session.selected(party)
        if record is None:
            return None
        current = str(record.ai.get("tactic", "balanced"))
        index = TACTICS.index(current) if current in TACTICS else 0
        next_value = TACTICS[(index + 1) % len(TACTICS)]
        self.monsters.set_tactic(record.monster_id, next_value)
        return f"{record.name} の行動指針: {next_value}"

    def reset_selected_ai(self, party: Sequence[MonsterRecord]) -> str | None:
        record = self.session.selected(party)
        if record is None:
            return None
        self.monsters.reset_ai(record.monster_id)
        return f"{record.name} のAIのみリセットしました。"
