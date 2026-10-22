# {
#   責務: [battle_data: 保存個体から、能力補正・習得・装備許可・耐性を反映した戦闘個体を再構築します]
#   フィールド: []
# }
from __future__ import annotations

from typing import Any

from kadoka_quest.core.combatant import Combatant
from kadoka_quest.core.monster import MonsterRecord, available_skill_ids, calculate_stats, equipment_allows_species
from kadoka_quest.data.repository import GameRepository


# {
#   責務: [BattleDataLoader: 指定した正規データ取得先とカタログを保持し、保存個体を戦闘用に再構築します]
#   フィールド: [
#     repository: 種族・能力値・習得・装備を取得する正規リポジトリ（GameRepository）
#     skill_catalog: 構築時に取得したID別のスキル定義（dict）
#     equipment_catalog: 構築時に取得したID別の装備定義（dict）
#   ]
# }
class BattleDataLoader:
    """Loads combat-ready species, skill, resistance, stat and equipment data."""

    # {
    #   責務: [__init__: 戦闘個体の再構築に使う取得先とスキル・装備一覧を保持します]
    #   処理: [1: 取得先の参照を保持し、スキルと装備のID別定義を取得します]
    #   引数: [
    #     self: 正規データ取得先とスキル/装備カタログを保持するBattleDataLoader
    #     repository: 戦闘個体を再構築する正規データの取得先（GameRepository）
    #   ]
    #   戻り値: [result: なし（None）。取得先とカタログをselfへ保持します]
    # }
    def __init__(self, repository: GameRepository) -> None:
        # 行動ごとの再読込を避け、正規データ取得先と共用カタログだけを保持します。
        self.repository = repository
        self.skill_catalog = repository.get_skills()
        self.equipment_catalog = repository.get_equipment()

    # {
    #   責務: [species_definition: 指定種族の耐性・逃走率・経験値などを持つ種族定義を取得します]
    #   処理: [1: 種族IDの読込をrepositoryへ委譲し、種族定義を返します]
    #   引数: [
    #     self: 正規データ取得先とスキル/装備カタログを保持するBattleDataLoader
    #     species_id: 取得する正規種族定義のID（str）
    #   ]
    #   戻り値: [result: 正規データから読み込んだ種族定義（dict[str, Any]）]
    # }
    def species_definition(self, species_id: str) -> dict[str, Any]:
        # 種族の定義をこの層で取得し、core側の戦闘処理へファイルI/Oを持ち込みません。
        return self.repository.get_species(species_id).definition

    # {
    #   責務: [build_combatant: 保存個体のLv・＋選択・装備から、満HP/MPの戦闘個体を構築します]
    #   処理: [
    #     1: 種族とLv別習得を読み、装備の種族許可を確認します
    #     2: 許可装備の耐性段階と能力補正を反映します
    #     3: 元レコードを保存せず、満HP/MPの戦闘個体を返します
    #   ]
    #   引数: [
    #     self: 正規データ取得先とスキル/装備カタログを保持するBattleDataLoader
    #     record: 種族・Lv・＋選択・装備IDと学習AIを持つ保存個体（MonsterRecord）
    #   ]
    #   戻り値: [result: 補正後能力・習得・許可装備・耐性と満HP/MPを持つ戦闘個体（Combatant）]
    # }
    def build_combatant(self, record: MonsterRecord) -> Combatant:
        # 保存個体の習得と種族許可済み装備を構築し、元レコードやAIへ書き戻しません。
        definition = self.species_definition(record.species_id)
        skill_ids = available_skill_ids(self.repository, record)
        skills = [self.skill_catalog[item] for item in skill_ids if item in self.skill_catalog]
        equipment = self.equipment_catalog.get(record.equipment_id or "")
        if equipment and not equipment_allows_species(equipment, record.species_id):
            equipment = None
        # 状態耐性は種族だけから取得し、装備の属性耐性段階とは混ぜません。
        resistances = dict(definition.get("resistances", {}))
        status_resistances = dict(definition.get("status_resistances", {}))
        # MOD検証の診断後でも遭遇は継続するため、逃走率の非オブジェクトは逃走なしへ退避します。
        flee_rates = definition.get("flee_rates", {})
        flee_rates = dict(flee_rates) if isinstance(flee_rates, dict) else {}
        if equipment:
            scale = ["weak", "normal", "strong", "immune", "absorb"]
            for element, steps in equipment.get("resistance_steps", {}).items():
                current = resistances.get(element, "normal")
                index = scale.index(current) if current in scale else 1
                resistances[element] = scale[max(0, min(len(scale) - 1, index + int(steps)))]
        # 補正後の能力と耐性を新規の戦闘個体へ渡し、戦闘中の資源を分離します。
        return Combatant(
            record=record,
            stats=calculate_stats(self.repository, record),
            skills=skills,
            resistances=resistances,
            equipment=equipment,
            status_resistances=status_resistances,
            flee_rates=flee_rates,
            experience_reward=definition.get("experience_reward"),
        )
