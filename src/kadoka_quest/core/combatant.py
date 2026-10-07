# {
#   責務: [combatant: 元個体から分離した戦闘資源・一時効果と、有効な能力値を持つCombatantを定義します]
#   フィールド: []
# }
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.core.status_effects import status_stat_multiplier


# {
#   責務: [Combatant: 元の個体レコードと区別して戦闘中の資源・一時効果を保持する]
#   フィールド: [
#     record: 個体レコード（MonsterRecord）
#     stats: 最大HP・最大MPを含む、この戦闘個体の能力値（dict[str, int]）
#     skills: スキル一覧（list[dict[str, Any]]）
#     resistances: 属性名ごとのダメージ耐性。normal/weak/strong/immune/absorbを使います（dict[str, str]）
#     equipment: 装備（dict[str, Any] | None）
#     status_effects: この戦闘個体へ適用中の状態異常（list[dict[str, Any] | str]）
#     status_resistances: 状態異常名ごとの付与に対する耐性（dict[str, str]）
#     hp: この戦闘個体の現在HP
#     mp: この戦闘個体の現在MP
#     guard: この戦闘個体が受ける物理ダメージに掛ける防御倍率。魔法には適用しません（float）
#     evade_physical: 物理攻撃を回避する状態かどうか（bool）
#     evade_physical_source: 物理回避を付与したスキルID。回避ログの表現に使います（str | None）
#     evade_element: 回避する属性名。Noneなら属性回避はありません（str | None）
#     speed_multiplier: 戦闘中の素早さへ掛ける一時倍率（float）
#     attack_multiplier: 次の物理攻撃力へ掛ける一時倍率（float）
#     physical_locked: 物理行動が禁止される残りターン数（int）
#     counter_ready: 単体攻撃による被弾後に反撃を判定する待機状態の有無（bool）
#     protect_ally: 味方の身代わり候補になるかどうか（bool）
#     action_history: この戦闘個体が選択した行動IDの履歴（list[str]）
#     timed_buff_turns: 一時強化する各能力値の残りターン数（dict[str, int]）
#     timed_buff_baselines: 一時強化が切れたときに戻す能力倍率（dict[str, float]）
#     flee_rates: 野生遭遇の文脈名ごとの、行動前に敵が逃走する確率（dict[str, float]）
#     fled: 逃走済み（bool）
#     experience_reward: base/per_level/squared_divisorを持つ種族固有の撃破経験値係数。Noneなら通常報酬です（dict[str, int] | None）
#   ]
# }
@dataclass
class Combatant:
    record: MonsterRecord
    stats: dict[str, int]
    skills: list[dict[str, Any]]
    resistances: dict[str, str]
    equipment: dict[str, Any] | None = None
    status_effects: list[dict[str, Any] | str] = field(default_factory=list)
    status_resistances: dict[str, str] = field(default_factory=dict)
    hp: int = 0
    mp: int = 0
    guard: float = 1.0
    evade_physical: bool = False
    evade_physical_source: str | None = None
    evade_element: str | None = None
    speed_multiplier: float = 1.0
    attack_multiplier: float = 1.0
    physical_locked: int = 0
    counter_ready: bool = False
    protect_ally: bool = False
    action_history: list[str] = field(default_factory=list)
    timed_buff_turns: dict[str, int] = field(default_factory=dict)
    timed_buff_baselines: dict[str, float] = field(default_factory=dict)
    flee_rates: dict[str, float] = field(default_factory=dict)
    fled: bool = False
    experience_reward: dict[str, int] | None = None

    # {
    #   責務: [__post_init__: 戦闘個体が利用する初期状態と依存を設定する]
    #   処理: [1: 戦闘個体が利用する初期状態と依存を設定する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __post_init__(self) -> None:
        self.hp = self.hp or self.stats["hp"]
        self.mp = self.mp or self.stats["mp"]

    # {
    #   責務: [alive: HPが正で逃走していない戦闘個体だけを生存と判定する]
    #   処理: [1: 現在HPとfledを読み、生存条件を評価する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 生存ならTrue]
    # }
    @property
    def alive(self) -> bool:
        return self.hp > 0 and not self.fled

    # {
    #   責務: [name: 戦闘個体の名前を求める]
    #   処理: [1: 戦闘個体の名前を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.record.name（str）]
    # }
    @property
    def name(self) -> str:
        return self.record.name

    # {
    #   責務: [speed: 戦闘個体の素早さを求める]
    #   処理: [1: 戦闘個体の素早さを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 戦闘個体の素早さを求めるための結果（int）]
    # }
    @property
    def speed(self) -> int:
        status_multiplier = status_stat_multiplier(self.status_effects, "speed")
        return max(1, int(self.stats["speed"] * self.speed_multiplier * status_multiplier))

    # {
    #   責務: [defense: 戦闘個体の防御力を求める]
    #   処理: [1: 戦闘個体の防御力を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 戦闘個体の防御力を求めるための結果（int）]
    # }
    @property
    def defense(self) -> int:
        status_multiplier = status_stat_multiplier(self.status_effects, "defense")
        return max(0, int(self.stats["defense"] * status_multiplier))
