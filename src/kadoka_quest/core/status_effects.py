# {
#   責務: [status_effects: 状態異常ID・付与確率と、出血による能力値倍率/ターン末ダメージを計算します]
#   フィールド: []
# }
from __future__ import annotations

from typing import Any, Iterable


STATUS_RESISTANCE_CHANCE_MULTIPLIER = {
    "very_weak": 1.5,
    "weak": 1.25,
    "normal": 1.0,
    "resist": 0.75,
    "strong": 0.5,
    "immune": 0.0,
}
VALID_STATUS_RESISTANCE_LEVELS = frozenset(STATUS_RESISTANCE_CHANCE_MULTIPLIER)
FORBIDDEN_STATUS_RESISTANCE_LEVELS = frozenset({"absorb", "reflect"})
KNOWN_STATUS_IDS = frozenset(
    {
        "poison",
        "paralysis",
        "sleep",
        "confusion",
        "bind",
        "curse_bind",
        "curse",
        "bleeding",
    }
)

BLEEDING_ID = "bleeding"
BLEEDING_SPEED_MULTIPLIER = 0.9
BLEEDING_DEFENSE_MULTIPLIER = 0.9
BLEEDING_DAMAGE_RATIO = 0.02


# {
#   責務: [status_effect_id: 辞書または文字列で保持された状態異常から比較用のIDを取り出します]
#   処理: [1: 辞書のidを使い、辞書でなければ状態名自体を文字列にします]
#   引数: [effect: 状態異常の辞書または文字列ID（dict[str, Any] | str）]
#   戻り値: [result: 比較用ID。辞書にidがなければ空文字列（str）]
# }
def status_effect_id(effect: dict[str, Any] | str) -> str:
    if isinstance(effect, dict):
        return str(effect.get("id", ""))
    return str(effect)


# {
#   責務: [has_status: 状態異常一覧に指定IDが一つでも含まれるか確認します]
#   処理: [1: 各状態から取り出したIDを指定IDと比較します]
#   引数: [
#     effects: 辞書または文字列で保持された状態異常の一覧（Iterable[dict[str, Any] | str]）
#     status_id: 存在を確認する状態異常ID。例えばbleeding（str）
#   ]
#   戻り値: [result: 指定IDが含まれればTrue、なければFalse（bool）]
# }
def has_status(effects: Iterable[dict[str, Any] | str], status_id: str) -> bool:
    return any(status_effect_id(effect) == status_id for effect in effects)


# {
#   責務: [status_apply_chance: 基本付与確率へ状態耐性倍率を適用し、最終確率を0〜1に制限します]
#   処理: [1: ダメージ専用耐性absorb/reflectは0とし、それ以外は状態耐性倍率を適用します]
#   引数: [
#     base_chance: 状態異常の基本付与確率（float）
#     resistance_level: very_weak〜immuneの状態耐性。未定義値は等倍です（str）
#   ]
#   戻り値: [result: 状態耐性を反映した0以上1以下の付与確率（float）]
# }
def status_apply_chance(base_chance: float, resistance_level: str) -> float:
    """status_apply_chanceは状態付与の基礎確率を耐性で補正し、0〜1へ制限します。

    状態耐性へ誤指定されたダメージ専用absorb/reflectは確率0になります。
    データ検査はabsorb/reflectを状態耐性のエラーとして報告します。
    未知の耐性名はPython runtimeの互換動作として等倍になります。
    """

    level = str(resistance_level or "normal")
    if level in FORBIDDEN_STATUS_RESISTANCE_LEVELS:
        return 0.0
    multiplier = STATUS_RESISTANCE_CHANCE_MULTIPLIER.get(level, 1.0)
    return min(1.0, max(0.0, float(base_chance)) * multiplier)


# {
#   責務: [status_stat_multiplier: 出血中だけ速度/防御の倍率を0.9へ下げ、他の能力値は等倍にします]
#   処理: [1: 出血の有無と能力値名から倍率を選びます]
#   引数: [
#     effects: 現在付いている状態異常一覧（Iterable[dict[str, Any] | str]）
#     stat: 倍率を求める能力値名。speed/defenseだけが出血の影響を受けます（str）
#   ]
#   戻り値: [result: 出血中のspeed/defenseなら0.9、それ以外なら1.0（float）]
# }
def status_stat_multiplier(effects: Iterable[dict[str, Any] | str], stat: str) -> float:
    if not has_status(effects, BLEEDING_ID):
        return 1.0
    if stat == "speed":
        return BLEEDING_SPEED_MULTIPLIER
    if stat == "defense":
        return BLEEDING_DEFENSE_MULTIPLIER
    return 1.0


# {
#   責務: [end_turn_status_damage: 出血のターン末ダメージを最大HPの2%から計算します]
#   処理: [1: 出血なら正の最大HP基準の2%を切り捨てて最低1とし、他状態なら0を返します]
#   引数: [
#     effect: ターン末ダメージを求める状態異常（dict[str, Any] | str）
#     max_hp: 対象の最大HP。整数化して最低1を計算基準にします（int）
#   ]
#   戻り値: [result: 出血なら最低1のHPダメージ、他状態なら0。実HPは更新しません（int）]
# }
def end_turn_status_damage(effect: dict[str, Any] | str, max_hp: int) -> int:
    if status_effect_id(effect) != BLEEDING_ID:
        return 0
    return max(1, int(max(1, int(max_hp)) * BLEEDING_DAMAGE_RATIO))
