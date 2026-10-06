# {
#   責務: [combatant: 戦闘個体の公開機能・宣言を定義する]
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
#     stats: 能力値（dict[str, int]）
#     skills: スキル一覧（list[dict[str, Any]]）
#     resistances: resistances（dict[str, str]）
#     equipment: 装備（dict[str, Any] | None）
#     status_effects: 状態異常・effects（list[dict[str, Any] | str]）
#     status_resistances: 状態異常・resistances（dict[str, str]）
#     hp: HP
#     mp: MP
#     guard: 防御倍率（float）
#     evade_physical: evade・physical（bool）
#     evade_physical_source: evade・physical・元データ（str | None）
#     evade_element: evade・element（str | None）
#     speed_multiplier: 素早さ・multiplier（float）
#     attack_multiplier: 攻撃・multiplier（float）
#     physical_locked: physical・locked（int）
#     counter_ready: counter・ready（bool）
#     protect_ally: protect・味方（bool）
#     action_history: action・履歴（list[str]）
#     timed_buff_turns: timed・buff・turns（dict[str, int]）
#     timed_buff_baselines: timed・buff・baselines（dict[str, float]）
#     flee_rates: flee・rates（dict[str, float]）
#     fled: 逃走済み（bool）
#     experience_reward: 経験値・報酬（dict[str, int] | None）
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
