from __future__ import annotations

from kadoka_quest.apps.battle_flow_dependencies import BattleFlowDependencies


class BattleFlowService:
    """Own battle command execution, playback timing, auto flow, and progression persistence."""

    def __init__(self, dependencies: BattleFlowDependencies) -> None:
        self.dependencies = dependencies

    @property
    def session(self):
        return self.dependencies.session

    def execute(self, command: str, now: int) -> None:
        battle = self.session.battle
        if not battle or battle.outcome or self.session.playback:
            return

        log_start = len(battle.log)
        if self.session.simulation and command in {"scout", "item"}:
            battle.log.append(
                "模擬戦ではスカウトできない。"
                if command == "scout"
                else "模擬戦では消費アイテムを使用できない。"
            )
        elif command == "fight":
            battle.run_round()
        elif command == "scout":
            self._scout()
        elif command == "item":
            self._use_item()
        elif command == "run":
            if self.session.simulation:
                battle.log.append("模擬戦から退出した。")
                battle.outcome = "escaped"
            else:
                battle.try_run()
                if not battle.outcome:
                    battle.run_round()
        else:
            raise ValueError(f"戦闘コマンド {command} は未対応です。")

        self.session.start_playback(log_start, int(now))
        if not self.session.playback:
            self.finalize_if_needed()

    def _scout(self) -> None:
        battle = self.session.battle
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

    def _use_item(self) -> None:
        battle = self.session.battle
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
        if not self.session.mark_finalized():
            return
        battle = self.session.battle
        assert battle is not None
        battle.mark_battle_complete()
        if not battle.learning_enabled:
            return
        self.dependencies.monsters.save_all_ai(member.record for member in battle.allies)
        if battle.outcome == "victory":
            self.award_experience()

    def award_experience(self) -> None:
        battle = self.session.battle
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

    def update_playback(self, now: int) -> bool:
        result = self.session.update_playback(int(now))
        if result["completed"]:
            self.finalize_if_needed()
        return bool(result["changed"])

    def selected_command(self) -> str:
        return self.session.selected_command()

    def move_selection(self, amount: int) -> int:
        return self.session.move_selection(amount)

    def set_selection(self, index: int) -> int:
        return self.session.set_selection(index)

    def stop_auto(self) -> None:
        self.session.stop_auto()

    def toggle_auto(self, now: int) -> str | None:
        enabled = self.session.toggle_auto(int(now))
        if enabled is None:
            return None
        return "オート戦闘を開始しました。" if enabled else "オート戦闘を停止しました。"

    def update_auto(self, now: int, *, battle_mode: bool) -> None:
        if not self.session.auto_command_due(int(now), battle_mode=battle_mode):
            return
        self.execute("fight", int(now))
        battle = self.session.battle
        if battle and battle.outcome:
            self.session.stop_auto()
