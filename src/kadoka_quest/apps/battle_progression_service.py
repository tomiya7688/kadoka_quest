from __future__ import annotations

from kadoka_quest.apps.battle_flow_dependencies import BattleFlowDependencies


class BattleProgressionService:
    """Own persistence effects caused by battle commands and battle completion."""

    def __init__(self, dependencies: BattleFlowDependencies) -> None:
        self.dependencies = dependencies

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

    def award_experience(self) -> None:
        battle = self.dependencies.session.battle
        if battle is None:
            return
        gained = 8 + sum(enemy.record.level * 3 for enemy in battle.enemies)
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
