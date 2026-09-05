from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar


T = TypeVar("T")


class FieldPartySession:
    """Owns the field quick-party selection and preset-cycle cursors."""

    def __init__(self, party_slot_count: int = 4) -> None:
        self.party_slot_count = max(1, int(party_slot_count))
        self.selected_index = 0
        self.preset_cursor = 0

    def select(self, index: int) -> int:
        self.selected_index = max(0, min(self.party_slot_count - 1, int(index)))
        return self.selected_index

    def selected(self, party: Sequence[T]) -> T | None:
        if not party:
            return None
        self.selected_index %= len(party)
        return party[self.selected_index]

    def next_preset(self, presets: Sequence[T]) -> T | None:
        if not presets:
            return None
        selected = presets[self.preset_cursor % len(presets)]
        self.preset_cursor += 1
        return selected
