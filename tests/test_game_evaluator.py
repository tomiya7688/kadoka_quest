from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_quest.devtools.field_explorer import FieldExplorer
from kadoka_quest.devtools.game_evaluator import GameEvaluationRunner


class _Repository:
    def list_maps(self) -> list[str]:
        return ["first", "second"]


class _Runtime:
    def __init__(self, game: "_Game") -> None:
        self.game = game

    def dispatch(self, target: str, action: str, **payload: object) -> object:
        if target == "field" and action == "move.start":
            field = self.game.field_session
            player = field.player
            direction = str(payload["direction"])
            dx, dy = {"left": (-1, 0), "right": (1, 0), "back": (0, -1), "front": (0, 1)}[direction]
            next_x, next_y = player.x + dx, player.y + dy
            if 0 <= next_x < field.map_data["width"] and 0 <= next_y < field.map_data["height"]:
                player.x, player.y = next_x, next_y
            for event in field.map_data.get("events", []):
                if (event["x"], event["y"]) == (player.x, player.y) and event.get("activation") == "step":
                    field.map_data = self.game.maps[event["target"]["map_id"]]
                    player.x, player.y = 0, 0
            return True
        if target == "field" and action == "interact":
            self.game.interactions += 1
        if target == "battle" and action == "return":
            self.game.battle_session.battle = None
            self.game.mode = "field"
        return True


class _Game:
    def __init__(self) -> None:
        self.maps = {
            "first": {
                "id": "first", "width": 3, "height": 1, "tiles": [["floor", "floor", "floor"]],
                "events": [
                    {"id": "local", "type": "message", "x": 0, "y": 0, "activation": "interact"},
                    {"id": "to_second", "type": "transition", "x": 2, "y": 0, "activation": "step", "target": {"map_id": "second"}},
                ],
            },
            "second": {"id": "second", "width": 1, "height": 1, "tiles": [["floor"]], "events": []},
        }
        self.field_session = SimpleNamespace(
            map_data=self.maps["first"],
            blocks={"floor": {"player_walkable": True}, "wall": {"player_walkable": False}},
            player=SimpleNamespace(x=0, y=0),
        )
        self.mode = "field"
        self.runtime = _Runtime(self)
        self.repository = _Repository()
        self.interactions = 0
        self.battle_session = SimpleNamespace(battle=None)


class FieldExplorerTests(unittest.TestCase):
    def test_unvisited_transition_is_prioritized_over_local_event(self) -> None:
        game = _Game()
        plan = FieldExplorer().next_plan(game.field_session.map_data, game.field_session.blocks, (0, 0), {"first"}, set())

        self.assertEqual(plan["event_key"], "first:to_second")
        self.assertEqual(plan["directions"], ["right", "right"])

    def test_planner_routes_around_blocking_event(self) -> None:
        map_data = {
            "id": "route", "width": 3, "height": 2,
            "tiles": [["floor", "floor", "floor"], ["floor", "floor", "floor"]],
            "events": [
                {"id": "sign", "type": "message", "x": 1, "y": 0, "blocking": True},
                {"id": "exit", "type": "transition", "x": 2, "y": 0, "activation": "step", "target": {"map_id": "next"}},
            ],
        }
        plan = FieldExplorer().next_plan(map_data, {"floor": {"player_walkable": True}}, (0, 0), {"route"}, set())

        self.assertEqual(plan["directions"], ["front", "right", "right", "back"])

    def test_runner_visits_connected_map_and_logs_stall(self) -> None:
        game = _Game()
        report = GameEvaluationRunner(game).run(max_steps=10)

        self.assertEqual(report["status"], "no_reachable_event")
        self.assertEqual(report["visited_maps"], ["first", "second"])
        self.assertTrue(any(entry["kind"] == "map_entered" and entry["map_id"] == "second" for entry in report["entries"]))
        self.assertTrue(any(entry["kind"] == "stalled" for entry in report["entries"]))

    def test_runner_rejects_zero_steps(self) -> None:
        with self.assertRaises(ValueError):
            GameEvaluationRunner(_Game()).run(0)

    def test_battle_result_is_recorded_before_return_clears_session(self) -> None:
        game = _Game()
        game.mode = "battle"
        game.battle_session.battle = SimpleNamespace(outcome="victory")
        report = GameEvaluationRunner(game).run(max_steps=1)
        self.assertIsNone(game.battle_session.battle)
        self.assertTrue(any(entry["kind"] == "battle_finished" and entry["outcome"] == "victory" for entry in report["entries"]))

    def test_blocked_route_is_logged_once_then_abandoned(self) -> None:
        game = _Game()
        original_dispatch = game.runtime.dispatch

        def blocked_dispatch(target: str, action: str, **payload: object) -> object:
            if target == "field" and action == "move.start":
                return True
            return original_dispatch(target, action, **payload)

        game.runtime.dispatch = blocked_dispatch
        report = GameEvaluationRunner(game).run(max_steps=10)

        blocked = [entry for entry in report["entries"] if entry["kind"] == "blocked"]
        self.assertEqual(len(blocked), 1)
        self.assertIn("first:to_second", report["attempted_events"])


if __name__ == "__main__":
    unittest.main()
