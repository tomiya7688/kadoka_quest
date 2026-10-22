# {
#   責務: [field_party_session: フィールド・パーティ・セッションの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar


T = TypeVar("T")


# {
#   責務: [FieldPartySession: Owns the field quick-party selection and preset-cycle cursors.]
#   フィールド: [
#     party_slot_count: パーティ・編成枠・count
#     selected_index: 選択中・位置番号
#     preset_cursor: プリセット・カーソル
#   ]
# }
class FieldPartySession:
    """Owns the field quick-party selection and preset-cycle cursors."""

    # {
    #   責務: [__init__: フィールド・パーティ・セッションが利用する初期状態と依存を設定する]
    #   処理: [1: フィールド・パーティ・セッションが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     party_slot_count: パーティ・編成枠・count（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, party_slot_count: int = 4) -> None:
        self.party_slot_count = max(1, int(party_slot_count))
        self.selected_index = 0
        self.preset_cursor = 0

    # {
    #   責務: [select: フィールド・パーティ・セッションを選択する]
    #   処理: [1: フィールド・パーティ・セッションを選択する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     index: 位置番号（int）
    #   ]
    #   戻り値: [result: self.selected・位置番号（int）]
    # }
    def select(self, index: int) -> int:
        self.selected_index = max(0, min(self.party_slot_count - 1, int(index)))
        return self.selected_index

    # {
    #   責務: [selected: フィールド・パーティ・セッションの選択中を求める]
    #   処理: [1: フィールド・パーティ・セッションの選択中を求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     party: パーティ（Sequence[T]）
    #   ]
    #   戻り値: [result: フィールド・パーティ・セッションの選択中を求めるための結果（T | None）]
    # }
    def selected(self, party: Sequence[T]) -> T | None:
        if not party:
            return None
        self.selected_index %= len(party)
        return party[self.selected_index]

    # {
    #   責務: [next_preset: プリセットを次の値を求める]
    #   処理: [1: プリセットを次の値を求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     presets: プリセット一覧（Sequence[T]）
    #   ]
    #   戻り値: [result: プリセットを次の値を求めるための結果（T | None）]
    # }
    def next_preset(self, presets: Sequence[T]) -> T | None:
        if not presets:
            return None
        selected = presets[self.preset_cursor % len(presets)]
        self.preset_cursor += 1
        return selected
