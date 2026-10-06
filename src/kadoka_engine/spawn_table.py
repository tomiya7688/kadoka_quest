# {
#   責務: [spawn_table: 出現・表の公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from copy import deepcopy
import math

from kadoka_engine.spawn_settings import validate_map_spawns


# {
#   責務: [prepare_spawn_entry: Validate an editor draft before mutating any map entry.]
#   処理: [1: Validate an editor draft before mutating any map entry.]
#   引数: [
#     spawns: spawns（list[dict]）
#     index: 位置番号（int）
#     species_id: 種族・識別子（str）
#     weight_text: 重み・文字列（str）
#     minimum_text: minimum・文字列（str）
#     maximum_text: maximum・文字列（str）
#     species_ids: 種族・識別子一覧（set[str]）
#   ]
#   戻り値: [result: 項目（dict）]
# }
def prepare_spawn_entry(
    spawns: list[dict], index: int, species_id: str, weight_text: str,
    minimum_text: str, maximum_text: str, species_ids: set[str],
) -> dict:
    """Validate an editor draft before mutating any map entry."""
    try:
        weight = float(weight_text)
        minimum, maximum = int(minimum_text), int(maximum_text)
    except (ValueError, OverflowError) as exc:
        raise ValueError("重みは数値、最小/最大Lvは1〜100の整数で入力してください。") from exc
    entry = deepcopy(spawns[index]) if 0 <= index < len(spawns) else {}
    entry.update(species_id=species_id, weight=weight, min_level=minimum, max_level=maximum)
    candidate = list(spawns)
    if 0 <= index < len(candidate):
        candidate[index] = entry
    else:
        candidate.append(entry)
    issues = validate_map_spawns({"spawns": candidate}, species_ids)
    if issues:
        raise ValueError(issues[0]["message"])
    return entry


# {
#   責務: [spawn_weight_ratios: Table-only ratios; conditional flags and map pop rate are not included.]
#   処理: [1: Table-only ratios; conditional flags and map pop rate are not included.]
#   引数: [spawns: spawns（list[dict]）]
#   戻り値: [result: Table-only ratios; conditional flags and map pop rate are not included.ための結果（list[float] | None）]
# }
def spawn_weight_ratios(spawns: list[dict]) -> list[float] | None:
    """Table-only ratios; conditional flags and map pop rate are not included."""
    if not spawns:
        return []
    try:
        raw = [item.get("weight", 1) for item in spawns]
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in raw):
            return None
        weights = [float(value) for value in raw]
        if any(not math.isfinite(value) or value < 0 for value in weights) or max(weights) <= 0:
            return None
        largest = max(weights)
        scaled = [value / largest for value in weights]
        total = sum(scaled)
        return [value / total for value in scaled]
    except (TypeError, ValueError, OverflowError, AttributeError):
        return None
