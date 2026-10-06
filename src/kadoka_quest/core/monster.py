# {
#   責務: [monster: モンスターの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kadoka_quest.data.repository import GameRepository, STAT_KEYS


# {
#   責務: [MonsterRecord: モンスター・個体レコードの状態と振る舞いを担当する]
#   フィールド: [
#     monster: モンスター（dict[str, Any]）
#     ai: AI（dict[str, Any]）
#   ]
# }
@dataclass
class MonsterRecord:
    monster: dict[str, Any]
    ai: dict[str, Any]

    # {
    #   責務: [monster_id: モンスター・個体レコードのモンスター・識別子を求める]
    #   処理: [1: モンスター・個体レコードのモンスター・識別子を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: モンスター・個体レコードのモンスター・識別子を求めるための結果（str）]
    # }
    @property
    def monster_id(self) -> str:
        return str(self.monster["id"])

    # {
    #   責務: [species_id: モンスター・個体レコードの種族・識別子を求める]
    #   処理: [1: モンスター・個体レコードの種族・識別子を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: モンスター・個体レコードの種族・識別子を求めるための結果（str）]
    # }
    @property
    def species_id(self) -> str:
        return str(self.monster["species_id"])

    # {
    #   責務: [name: モンスター・個体レコードの名前を求める]
    #   処理: [1: モンスター・個体レコードの名前を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: モンスター・個体レコードの名前を求めるための結果（str）]
    # }
    @property
    def name(self) -> str:
        return str(self.monster["name"])

    # {
    #   責務: [level: モンスター・個体レコードのレベルを求める]
    #   処理: [1: モンスター・個体レコードのレベルを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: モンスター・個体レコードのレベルを求めるための結果（int）]
    # }
    @property
    def level(self) -> int:
        return int(self.monster.get("level", 1))

    # {
    #   責務: [plus_choices: モンスター・個体レコードの＋選択・choicesを求める]
    #   処理: [1: モンスター・個体レコードの＋選択・choicesを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: モンスター・個体レコードの＋選択・choicesを求めるための結果（list[str]）]
    # }
    @property
    def plus_choices(self) -> list[str]:
        return [str(item) for item in self.monster.get("plus_choices", [])]

    # {
    #   責務: [equipment_id: モンスター・個体レコードの装備・識別子を求める]
    #   処理: [1: モンスター・個体レコードの装備・識別子を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: モンスター・個体レコードの装備・識別子を求めるための結果（str | None）]
    # }
    @property
    def equipment_id(self) -> str | None:
        value = self.monster.get("equipment_id")
        return str(value) if value else None


# {
#   責務: [equipment_allows_species: 装備品側の許可リストだけを装備可否の正とする。]
#   処理: [1: 装備品側の許可リストだけを装備可否の正とする。]
#   引数: [
#     equipment: 装備（dict[str, Any]）
#     species_id: 種族・識別子（str）
#   ]
#   戻り値: [result: 装備品側の許可リストだけを装備可否の正とするための結果（bool）]
# }
def equipment_allows_species(equipment: dict[str, Any], species_id: str) -> bool:
    """装備品側の許可リストだけを装備可否の正とする。"""
    return str(species_id) in {str(item) for item in equipment.get("allowed_species_ids", [])}


# {
#   責務: [
#     calculate_stats: レベル表へ＋選択と許可された装備補正を順に適用する
#   ]
#   処理: [
#     1: 種族/Lvの基礎能力値を取得する
#     2: 選択済み＋効果を定義順に反映する
#     3: 装備側whitelistに合う装備だけを適用し、6能力値を整数・最低1へ整える
#   ]
#   引数: [
#     repository: データ取得先（GameRepository）
#     record: 個体レコード（MonsterRecord）
#   ]
#   戻り値: [
#     result: 補正後の6能力値。個体レコードや正規JSONは変更しない
#   ]
# }
def calculate_stats(repository: GameRepository, record: MonsterRecord) -> dict[str, int]:
    stats = repository.stats_at(record.species_id, record.level)
    bundle = repository.get_species(record.species_id)
    selected = set(record.plus_choices)

    for stage in bundle.plus.get("stages", []):
        for option in stage.get("options", []):
            if option.get("id") not in selected:
                continue
            kind = option.get("kind")
            stat = option.get("stat")
            if stat not in STAT_KEYS:
                continue
            if kind == "stat_add":
                stats[stat] += int(option.get("value", 0))
            elif kind == "stat_multiplier":
                stats[stat] = round(stats[stat] * float(option.get("value", 1.0)))

    if record.equipment_id:
        equipment = repository.get_equipment().get(record.equipment_id)
        if equipment and equipment_allows_species(equipment, record.species_id):
            for stat, multiplier in equipment.get("stat_multipliers", {}).items():
                if stat in stats:
                    stats[stat] = round(stats[stat] * float(multiplier))

    return {key: max(1, int(stats[key])) for key in STAT_KEYS}


# {
#   責務: [available_skill_ids: スキル・識別子一覧を利用可能な値を求める]
#   処理: [1: スキル・識別子一覧を利用可能な値を求める]
#   引数: [
#     repository: データ取得先（GameRepository）
#     record: 個体レコード（MonsterRecord）
#   ]
#   戻り値: [result: スキル・識別子一覧を利用可能な値を求めるための結果（list[str]）]
# }
def available_skill_ids(repository: GameRepository, record: MonsterRecord) -> list[str]:
    return repository.skill_ids_at(record.species_id, record.level, record.plus_choices)


