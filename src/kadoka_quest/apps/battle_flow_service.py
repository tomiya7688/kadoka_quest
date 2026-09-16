from __future__ import annotations

from kadoka_quest.apps.battle_flow_dependencies import BattleFlowDependencies
from kadoka_quest.apps.battle_progression_service import BattleProgressionService


class BattleFlowService:
    """Own battle command orchestration, playback timing, and auto flow."""

    def __init__(self, dependencies: BattleFlowDependencies) -> None:
        self.dependencies = dependencies
        self.progression = BattleProgressionService(dependencies)

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
            self.progression.scout()
        elif command == "item":
            self.progression.use_item()
        elif command == "run":
            self._run()
        else:
            raise ValueError(f"戦闘コマンド {command} は未対応です。")

        self.session.start_playback(log_start, int(now))
        if not self.session.playback:
            self.progression.finalize_if_needed()

    def _run(self) -> None:
        battle = self.session.battle
        if battle is None:
            return
        if self.session.simulation:
            battle.log.append("模擬戦から退出した。")
            battle.outcome = "escaped"
            return
        battle.try_run()
        if not battle.outcome:
            battle.run_round()

    def update_playback(self, now: int) -> bool:
        result = self.session.update_playback(int(now))
        if result["completed"]:
            self.progression.finalize_if_needed()
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
