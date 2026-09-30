from __future__ import annotations

from copy import deepcopy

from kadoka_engine.field_ai import FIELD_AI_TYPES
from kadoka_engine.spawn_settings import validate_map_spawns
from kadoka_engine.spawn_table import prepare_spawn_entry, spawn_weight_ratios


def parse_map_spawn_controls(rate: str, weights: dict[str, str] | None) -> dict:
    """Parse a map-level draft; None explicitly restores AI inheritance."""
    try:
        controls = {
            "pop_rate": float(rate),
            "field_ai_weights": None if weights is None else {key: float(value) for key, value in weights.items()},
        }
    except (ValueError, OverflowError) as exc:
        raise ValueError("ポップ率とAI重みは有限数値で入力してください。") from exc
    issues = validate_map_spawns(controls)
    if issues:
        raise ValueError(issues[0]["message"])
    return controls


def map_ai_ratios(weights: dict) -> list[float] | None:
    """Ratios for an explicit map override, not a mixture of species overrides."""
    if not isinstance(weights, dict) or validate_map_spawns({"field_ai_weights": weights}):
        return None
    return spawn_weight_ratios([{"weight": weights.get(key, 0)} for key in FIELD_AI_TYPES])


def prepare_spawn_document(
    document: dict, species_ids: set[str], entry_draft: dict | None = None,
    controls_draft: dict | None = None,
) -> dict:
    """Prepare both tabs atomically, preserving unknown map and entry data."""
    result = deepcopy(document)
    if entry_draft is not None:
        entry = prepare_spawn_entry(result.get("spawns", []), species_ids=species_ids, **entry_draft)
        index = entry_draft["index"]
        spawns = result.setdefault("spawns", [])
        if 0 <= index < len(spawns):
            spawns[index] = entry
        else:
            spawns.append(entry)
    if controls_draft is not None:
        result.update(parse_map_spawn_controls(**controls_draft))
    issues = validate_map_spawns(result, species_ids)
    if issues:
        raise ValueError(f"{issues[0]['field']}: {issues[0]['message']}")
    return result
