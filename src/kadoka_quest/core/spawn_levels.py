from __future__ import annotations

from collections.abc import Sequence
import random
from typing import Any

from kadoka_quest.core.monster import MonsterRecord


def metal_area_level_range(party: Sequence[MonsterRecord]) -> tuple[int, int]:
    """Use only the four active combat slots, without changing owned records."""
    levels = sorted(
        (max(1, member.level - (10 if member.species_id in {"kadoka", "maru"} else 0))
         for member in party[:4]),
        reverse=True,
    )
    if not levels:
        raise ValueError("メタルエリアの出現Lv計算にはパーティが必要です。")
    use_highest = len(levels) == 1 or levels[0] - levels[1] >= 20
    base = levels[0] if use_highest else levels[1]
    spread = 5 if use_highest else 3
    return max(1, min(100, base - spread)), max(1, min(100, base + spread))


def spawn_level_range(
    spawn: dict[str, Any],
    party: Sequence[MonsterRecord],
    encounter_context: str = "normal",
) -> tuple[int, int]:
    """Metal areas scale at encounter time; other areas keep their static table."""
    if encounter_context == "metal_area":
        return metal_area_level_range(party)
    return int(spawn.get("min_level", 1)), int(spawn.get("max_level", 1))


def wild_encounter_level(
    spawn: dict[str, Any], party: Sequence[MonsterRecord],
    encounter_context: str, rng: random.Random,
) -> int:
    """Keep normal field levels; metal areas still scale at encounter time."""
    low, high = spawn_level_range(spawn, party, encounter_context)
    rolled = spawn.get("rolled_level")
    if (encounter_context != "metal_area" and isinstance(rolled, int)
            and not isinstance(rolled, bool) and low <= rolled <= high):
        return rolled
    return rng.randint(low, high)
