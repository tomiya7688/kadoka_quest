from __future__ import annotations


def describe_battle_context(
    hp_ratio: float,
    ally_missing_hp_ratio: float,
    mp_ratio: float,
    living_allies: int,
    living_enemies: int,
    lowest_enemy_hp_ratio: float,
    actor_level: int,
    highest_enemy_level: int,
) -> tuple[str, ...]:
    if hp_ratio < 0.3:
        self_state = "self:critical"
    elif hp_ratio < 0.65:
        self_state = "self:hurt"
    else:
        self_state = "self:healthy"

    if ally_missing_hp_ratio > 0.65:
        ally_state = "allies:critical"
    elif ally_missing_hp_ratio > 0.25:
        ally_state = "allies:hurt"
    else:
        ally_state = "allies:stable"

    resource_state = "mp:low" if mp_ratio < 0.25 else "mp:ready"
    if living_allies < living_enemies:
        number_state = "numbers:outnumbered"
    elif living_allies > living_enemies:
        number_state = "numbers:advantage"
    else:
        number_state = "numbers:even"

    if lowest_enemy_hp_ratio < 0.3:
        target_state = "target:near_defeat"
    elif lowest_enemy_hp_ratio < 0.7:
        target_state = "target:hurt"
    else:
        target_state = "target:healthy"

    if actor_level + 3 < highest_enemy_level:
        threat_state = "threat:stronger"
    elif actor_level > highest_enemy_level + 3:
        threat_state = "threat:weaker"
    else:
        threat_state = "threat:even"

    return self_state, ally_state, resource_state, number_state, target_state, threat_state
