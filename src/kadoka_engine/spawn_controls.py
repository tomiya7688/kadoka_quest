# {
#   責務: [spawn_controls: 出現・controlsの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from copy import deepcopy

from kadoka_engine.field_ai import FIELD_AI_TYPES
from kadoka_engine.spawn_settings import validate_map_spawns
from kadoka_engine.spawn_table import prepare_spawn_entry, spawn_weight_ratios


# {
#   責務: [parse_map_spawn_controls: Parse a map-level draft; None explicitly restores AI inheritance.]
#   処理: [1: Parse a map-level draft; None explicitly restores AI inheritance.]
#   引数: [
#     rate: rate（str）
#     weights: 重み一覧（dict[str, str] | None）
#   ]
#   戻り値: [result: controls（dict）]
# }
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


# {
#   責務: [map_ai_ratios: Ratios for an explicit map override, not a mixture of species overrides.]
#   処理: [1: Ratios for an explicit map override, not a mixture of species overrides.]
#   引数: [weights: 重み一覧（dict）]
#   戻り値: [result: Ratios for an explicit map override, not a mixture of species overrides.ための結果（list[float] | None）]
# }
def map_ai_ratios(weights: dict) -> list[float] | None:
    """Ratios for an explicit map override, not a mixture of species overrides."""
    if not isinstance(weights, dict) or validate_map_spawns({"field_ai_weights": weights}):
        return None
    return spawn_weight_ratios([{"weight": weights.get(key, 0)} for key in FIELD_AI_TYPES])


# {
#   責務: [prepare_spawn_document: Prepare both tabs atomically, preserving unknown map and entry data.]
#   処理: [1: Prepare both tabs atomically, preserving unknown map and entry data.]
#   引数: [
#     document: 文書（dict）
#     species_ids: 種族・識別子一覧（set[str]）
#     entry_draft: 項目・下書き（dict | None）
#     controls_draft: controls・下書き（dict | None）
#   ]
#   戻り値: [result: 処理結果（dict）]
# }
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
