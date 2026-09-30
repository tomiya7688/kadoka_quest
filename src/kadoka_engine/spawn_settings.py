from __future__ import annotations

from copy import deepcopy
import math

from kadoka_engine.field_ai import is_valid_field_ai_weights


DEFAULT_POP_RATE = 100


def _nonnegative_number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value) and value >= 0
    except OverflowError:
        return False


def validate_map_spawns(map_data: dict, species_ids: set[str] | None = None) -> list[dict[str, str]]:
    """Validate spawn settings without I/O, mutation, or runtime fallback."""
    issues: list[dict[str, str]] = []

    def issue(code: str, field: str, message: str) -> None:
        issues.append({"code": code, "field": field, "message": message})

    def validate_ai(source: dict, field: str) -> None:
        weights = source.get("field_ai_weights")
        if weights is not None and not is_valid_field_ai_weights(weights):
            issue("map.spawn_ai_weights_invalid", field,
                  "AI重みはrandom/chase/idleの非負の有限数値で、少なくとも1つを正にしてください。")

    rate = map_data.get("pop_rate", DEFAULT_POP_RATE)
    if not _nonnegative_number(rate) or rate > 100:
        issue("map.pop_rate_invalid", "pop_rate", "pop_rateは0〜100の有限数値にしてください。")
    validate_ai(map_data, "field_ai_weights")
    spawns = map_data.get("spawns", [])
    if not isinstance(spawns, list):
        issue("map.spawns_invalid", "spawns", "spawnsは配列にしてください。")
        return issues
    weights = []
    for index, spawn in enumerate(spawns):
        prefix = f"spawns[{index}]"
        if not isinstance(spawn, dict):
            issue("map.spawn_invalid", prefix, "出現項目はオブジェクトにしてください。")
            continue
        species = spawn.get("species_id")
        if not isinstance(species, str) or not species.strip() or (species_ids is not None and species not in species_ids):
            issue("map.spawn_species_unknown", prefix + ".species_id", "存在する種族IDを指定してください。")
        if species == "ball_slime":
            issue("map.spawn_starter_only", prefix + ".species_id", "ボールスライムは初期獲得専用です。")
        weight = spawn.get("weight", 1)
        if not _nonnegative_number(weight):
            issue("map.spawn_weight_invalid", prefix + ".weight", "weightは0以上の有限数値にしてください。")
        else:
            weights.append(weight)
        minimum, maximum = spawn.get("min_level", 1), spawn.get("max_level", 1)
        if any(isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 100 for value in (minimum, maximum)):
            issue("map.spawn_level_invalid", prefix, "出現Lvは1〜100の整数にしてください。")
        elif minimum > maximum:
            issue("map.spawn_level_range", prefix, "最小Lvは最大Lv以下にしてください。")
        validate_ai(spawn, prefix + ".field_ai_weights")
    if spawns and len(weights) == len(spawns) and not any(weights):
        issue("map.spawn_weights_zero", "spawns", "出現候補のweightを少なくとも1つ正にしてください。")
    return issues


def normalize_map_spawns(map_data: dict, species_ids: set[str] | None = None) -> dict:
    """Return a detached document with legacy defaults; keep unknown mod keys."""
    issues = validate_map_spawns(map_data, species_ids)
    if issues:
        raise ValueError("; ".join(f"{issue['field']}: {issue['message']}" for issue in issues))
    result = deepcopy(map_data)
    result.setdefault("pop_rate", DEFAULT_POP_RATE)
    for spawn in result.setdefault("spawns", []):
        spawn.setdefault("weight", 1)
        spawn.setdefault("min_level", 1)
        spawn.setdefault("max_level", 1)
    return result
