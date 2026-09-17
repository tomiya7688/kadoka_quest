from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_quest.application.app_command import AppCommand
from kadoka_quest.apps.battle_command_app import BattleCommandApplication
from kadoka_quest.apps.battle_flow_dependencies import BattleFlowDependencies
from kadoka_quest.apps.battle_flow_service import BattleFlowService
from kadoka_quest.apps.battle_session import BattleSession


class BattleFlowServiceTests(unittest.TestCase):
    def make_service(self, *, simulation: bool = False, state: dict | None = None):
        session = BattleSession(initial_log_delay_ms=10)
        battle = SimpleNamespace(
            outcome=None,
            log=[],
            learning_enabled=False,
            allies=[],
            enemies=[],
            run_round=mock.Mock(),
            try_scout=mock.Mock(return_value=(False, None, 0.0)),
            try_run=mock.Mock(return_value=False),
            use_party_item=mock.Mock(),
            mark_battle_complete=mock.Mock(),
        )
        session.begin(battle, 0, simulation=simulation)
        monsters = mock.Mock()
        states = mock.Mock()
        current_state = state if state is not None else {"inventory": {}, "current_party": []}
        service = BattleFlowService(
            BattleFlowDependencies(
                session=session,
                monsters=monsters,
                states=states,
                state_provider=lambda: current_state,
            )
        )
        return service, session, battle, monsters, states, current_state

    def test_fight_runs_round_and_starts_playback_at_supplied_tick(self) -> None:
        service, session, battle, _, _, _ = self.make_service()
        battle.run_round.side_effect = lambda: battle.log.append("攻撃した。")

        service.execute("fight", 120)

        battle.run_round.assert_called_once_with()
        self.assertTrue(session.playback)
        self.assertEqual(session.next_log_tick, 130)

    def test_simulation_blocks_scout_before_persistence(self) -> None:
        service, _, battle, monsters, states, _ = self.make_service(simulation=True)

        service.execute("scout", 20)

        self.assertIn("模擬戦ではスカウトできない。", battle.log)
        battle.try_scout.assert_not_called()
        monsters.create.assert_not_called()
        states.save.assert_not_called()

    def test_simulation_blocks_consumable_item_before_inventory_mutation(self) -> None:
        state = {"inventory": {"orange": 2}, "current_party": []}
        service, _, battle, _, states, current_state = self.make_service(simulation=True, state=state)

        service.execute("item", 20)

        self.assertIn("模擬戦では消費アイテムを使用できない。", battle.log)
        self.assertEqual(current_state["inventory"]["orange"], 2)
        battle.use_party_item.assert_not_called()
        states.save.assert_not_called()

    def test_normal_item_consumes_inventory_and_runs_round(self) -> None:
        state = {"inventory": {"orange": 1}, "current_party": []}
        service, _, battle, _, states, current_state = self.make_service(state=state)

        service.execute("item", 30)

        self.assertEqual(current_state["inventory"]["orange"], 0)
        states.save.assert_called_once_with(current_state)
        battle.use_party_item.assert_called_once_with()
        battle.run_round.assert_called_once_with()

    def test_non_learning_battle_finalization_never_persists_ai_or_experience(self) -> None:
        service, session, battle, monsters, _, _ = self.make_service()
        battle.outcome = "victory"

        service.progression.finalize_if_needed()

        self.assertTrue(session.finalized)
        battle.mark_battle_complete.assert_called_once_with()
        monsters.save_all_ai.assert_not_called()
        monsters.get.assert_not_called()

    def test_command_application_uses_flow_service_instead_of_legacy_game_handler(self) -> None:
        _, session, battle, monsters, states, state = self.make_service()
        battle.run_round.side_effect = lambda: battle.log.append("攻撃した。")
        game = SimpleNamespace(
            battle_session=session,
            monsters=monsters,
            states=states,
            state=state,
            status="",
            mode="battle",
            handle_battle_command=mock.Mock(),
            selected_battle_command=mock.Mock(return_value="run"),
        )
        app = BattleCommandApplication(game)

        app.handle(AppCommand("battle", "execute", {"command": "fight", "now": 77}))

        battle.run_round.assert_called_once_with()
        game.handle_battle_command.assert_not_called()
        self.assertEqual(session.next_log_tick, 87)


if __name__ == "__main__":
    unittest.main()
