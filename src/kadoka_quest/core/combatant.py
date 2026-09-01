from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kadoka_quest.core.monster import MonsterRecord


@dataclass
class Combatant:
    record: MonsterRecord
    stats: dict[str, int]
    skills: list[dict[str, Any]]
    resistances: dict[str, str]
    equipment: dict[str, Any] | None = None
    hp: int = 0
    mp: int = 0
    guard: float = 1.0
    evade_physical: bool = False
    evade_physical_source: str | None = None
    evade_element: str | None = None
    speed_multiplier: float = 1.0
    attack_multiplier: float = 1.0
    physical_locked: int = 0
    action_history: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.hp = self.hp or self.stats["hp"]
        self.mp = self.mp or self.stats["mp"]

    @property
    def alive(self) -> bool:
        return self.hp > 0

    @property
    def name(self) -> str:
        return self.record.name

    @property
    def speed(self) -> int:
        return max(1, int(self.stats["speed"] * self.speed_multiplier))
