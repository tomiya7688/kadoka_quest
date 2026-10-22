# {
#   責務: [battle_progression_service: 戦闘・progression・serviceの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from kadoka_quest.apps.battle_flow_dependencies import BattleFlowDependencies
from kadoka_quest.core.battle_rewards import battle_experience


# {
#   責務: [BattleProgressionService: Own persistence effects caused by battle commands and battle completion.]
#   フィールド: [dependencies: dependencies]
# }
class BattleProgressionService:
    """Own persistence effects caused by battle commands and battle completion."""

    # {
    #   責務: [__init__: 戦闘・progression・serviceが利用する初期状態と依存を設定する]
    #   処理: [1: 戦闘・progression・serviceが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     dependencies: dependencies（BattleFlowDependencies）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def __init__(self, dependencies: BattleFlowDependencies) -> None:
        self.dependencies = dependencies

    # {
    #   責務: [scout: 戦闘・progression・serviceのscoutを求める]
    #   処理: [1: 戦闘・progression・serviceのscoutを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def scout(self) -> None:
        battle = self.dependencies.session.battle
        if battle is None:
            return
        success, target, _ = battle.try_scout()
        if not success or target is None:
            return
        acquired = self.dependencies.monsters.create(
            target.species_id,
            level=target.level,
            source="scout",
        )
        state = self.dependencies.state_provider()
        party = list(state.get("current_party", []))
        if len(party) < 4:
            party.append(acquired.monster_id)
            state["current_party"] = party
        self.dependencies.states.save(state)

    # {
    #   責務: [use_item: アイテムを使用する]
    #   処理: [1: アイテムを使用する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def use_item(self) -> None:
        battle = self.dependencies.session.battle
        if battle is None:
            return
        state = self.dependencies.state_provider()
        inventory = state.setdefault("inventory", {})
        if int(inventory.get("orange", 0)) <= 0:
            battle.log.append("みかんを持っていない。")
            return
        inventory["orange"] = int(inventory.get("orange", 0)) - 1
        self.dependencies.states.save(state)
        battle.use_party_item()
        battle.run_round()

    # {
    #   責務: [finalize_if_needed: 戦闘・progression・serviceのfinalize・if・neededを求める]
    #   処理: [1: 戦闘・progression・serviceのfinalize・if・neededを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def finalize_if_needed(self) -> None:
        session = self.dependencies.session
        if not session.mark_finalized():
            return
        battle = session.battle
        assert battle is not None
        battle.mark_battle_complete()
        if not battle.learning_enabled:
            return
        self.dependencies.monsters.save_all_ai(member.record for member in battle.allies)
        if battle.outcome == "victory":
            self.award_experience()

    # {
    #   責務: [award_experience: 戦闘・progression・serviceのaward・経験値を求める]
    #   処理: [1: 戦闘・progression・serviceのaward・経験値を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def award_experience(self) -> None:
        battle = self.dependencies.session.battle
        if battle is None or battle.outcome != "victory" or not battle.learning_enabled:
            return
        gained = battle_experience(battle.enemies)
        if gained <= 0:
            return
        for ally in battle.allies:
            record = self.dependencies.monsters.get(ally.record.monster_id)
            if not record or record.level >= 100:
                continue
            record.monster["experience"] = int(record.monster.get("experience", 0)) + gained
            while record.monster["level"] < 100:
                threshold = int(record.monster["level"]) * 24
                if record.monster["experience"] < threshold:
                    break
                record.monster["experience"] -= threshold
                record.monster["level"] += 1
                battle.log.append(f"{record.name}はLv{record.monster['level']}になった。")
            self.dependencies.monsters.save(record)
