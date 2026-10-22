# {
#   責務: [field_party_service: フィールド・パーティ・serviceの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime

from kadoka_quest.apps.field_party_session import FieldPartySession
from kadoka_quest.core.ai import TACTICS
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.parties import PartyStore
from kadoka_quest.data.state import StateStore


# {
#   責務: [FieldPartyService: Coordinates field quick-party operations through the existing stores.]
#   フィールド: [
#     session: セッション
#     parties: parties
#     monsters: モンスター一覧
#     states: states
#     now: 現在時刻
#   ]
# }
class FieldPartyService:
    """Coordinates field quick-party operations through the existing stores."""

    # {
    #   責務: [__init__: フィールド・パーティ・serviceが利用する初期状態と依存を設定する]
    #   処理: [1: フィールド・パーティ・serviceが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     session: セッション（FieldPartySession）
    #     parties: parties（PartyStore）
    #     monsters: モンスター一覧（MonsterStore）
    #     states: states（StateStore）
    #     now: 現在時刻（Callable[[], datetime] | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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

    # {
    #   責務: [select: フィールド・パーティ・serviceを選択する]
    #   処理: [1: フィールド・パーティ・serviceを選択する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     index: 位置番号（int）
    #   ]
    #   戻り値: [result: フィールド・パーティ・serviceを選択するための結果（bool）]
    # }
    def select(self, index: int) -> bool:
        self.session.select(index)
        return True

    # {
    #   責務: [save_preset: プリセットを保存する]
    #   処理: [1: プリセットを保存する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     state: 状態（dict）
    #   ]
    #   戻り値: [result: プリセットを保存するための結果（str）]
    # }
    def save_preset(self, state: dict) -> str:
        name = "フィールド編成_" + self.now().strftime("%Y%m%d_%H%M%S")
        path = self.parties.save(name, list(state.get("current_party", [])))
        return f"{path.name} を保存しました。"

    # {
    #   責務: [load_next_preset: next・プリセットを読み込む]
    #   処理: [1: next・プリセットを読み込む]
    #   引数: [
    #     self: 処理対象インスタンス
    #     state: 状態（dict）
    #   ]
    #   戻り値: [result: next・プリセットを読み込むための結果（str）]
    # }
    def load_next_preset(self, state: dict) -> str:
        path = self.session.next_preset(self.parties.list_presets())
        if path is None:
            return "保存パーティがありません。"
        loaded = self.parties.load(path, self.monsters)
        state["current_party"] = [record.monster_id for record in loaded if record]
        self.states.save(state)
        return f"{path.name} を読み込みました。欠損IDは空き枠です。"

    # {
    #   責務: [cycle_tactic: tacticを順に切り替える]
    #   処理: [1: tacticを順に切り替える]
    #   引数: [
    #     self: 処理対象インスタンス
    #     party: パーティ（Sequence[MonsterRecord]）
    #   ]
    #   戻り値: [result: tacticを順に切り替えるための結果（str | None）]
    # }
    def cycle_tactic(self, party: Sequence[MonsterRecord]) -> str | None:
        record = self.session.selected(party)
        if record is None:
            return None
        current = str(record.ai.get("tactic", "balanced"))
        index = TACTICS.index(current) if current in TACTICS else 0
        next_value = TACTICS[(index + 1) % len(TACTICS)]
        self.monsters.set_tactic(record.monster_id, next_value)
        return f"{record.name} の行動指針: {next_value}"

    # {
    #   責務: [reset_selected_ai: 選択中・AIの初期状態へ戻す]
    #   処理: [1: 選択中・AIの初期状態へ戻す]
    #   引数: [
    #     self: 処理対象インスタンス
    #     party: パーティ（Sequence[MonsterRecord]）
    #   ]
    #   戻り値: [result: 選択中・AIの初期状態へ戻すための結果（str | None）]
    # }
    def reset_selected_ai(self, party: Sequence[MonsterRecord]) -> str | None:
        record = self.session.selected(party)
        if record is None:
            return None
        self.monsters.reset_ai(record.monster_id)
        return f"{record.name} のAIのみリセットしました。"
