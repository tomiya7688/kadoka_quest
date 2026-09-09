from __future__ import annotations

from typing import Any, Callable

from kadoka_quest.devtools.evaluation_log import EvaluationLog
from kadoka_quest.devtools.field_explorer import FieldExplorer


class GameEvaluationRunner:
    """Drive a KadokaQuest-compatible session through its semantic command boundary."""

    def __init__(self, game: Any, explorer: FieldExplorer | None = None, log: EvaluationLog | None = None) -> None:
        self.game = game
        self.explorer = explorer or FieldExplorer()
        self.log = log or EvaluationLog()
        self.visited_maps: set[str] = set()
        self.attempted_events: set[str] = set()
        self.now = 0

    @classmethod
    def from_default_game(cls) -> "GameEvaluationRunner":
        from kadoka_quest.apps.game import KadokaQuest

        return cls(KadokaQuest())

    def run(self, max_steps: int = 2_000) -> dict[str, Any]:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        status = "step_limit"
        for step in range(1, max_steps + 1):
            self._observe_map(step)
            if self.game.mode == "battle":
                self._resolve_battle(step)
                continue
            if self.game.mode == "password":
                self._dispatch("password", "cancel")
                self.log.add("password_cancelled", step)
                continue
            plan = self.explorer.next_plan(
                self.game.map_data,
                self.game.blocks,
                (int(self.game.player_x), int(self.game.player_y)),
                self.visited_maps,
                self.attempted_events,
            )
            if plan is None:
                status = "no_reachable_event"
                self.log.add("stalled", step, reason=status, map_id=str(self.game.map_data["id"]))
                break
            directions = list(plan["directions"])
            if directions:
                self._move(step, str(directions[0]), str(plan["event_key"]), len(directions) == 1)
                continue
            self._interact(step, plan)
        return self.log.report(status=status, visited_maps=self.visited_maps, attempted_events=self.attempted_events)

    def _observe_map(self, step: int) -> None:
        map_id = str(self.game.map_data["id"])
        if map_id not in self.visited_maps:
            self.visited_maps.add(map_id)
            self.log.add("map_entered", step, map_id=map_id)

    def _move(self, step: int, direction: str, event_key: str, reaches_target: bool) -> None:
        before = (int(self.game.player_x), int(self.game.player_y))
        self.now += 100
        if reaches_target:
            self.attempted_events.add(event_key)
        self._dispatch("field", "move.start", direction=direction, now=self.now)
        self._dispatch("field", "move.stop", direction=direction)
        after = (int(self.game.player_x), int(self.game.player_y))
        if after == before:
            self.attempted_events.add(event_key)
            self.log.add("blocked", step, direction=direction, position=list(before), event_key=event_key)
        else:
            self.log.add("move", step, direction=direction, from_position=list(before), to_position=list(after))

    def _interact(self, step: int, plan: dict[str, Any]) -> None:
        event_key = str(plan["event_key"])
        self.attempted_events.add(event_key)
        event = dict(plan["event"])
        self._dispatch("field", "interact")
        self.log.add("event_attempted", step, event_key=event_key, event_type=str(event.get("type", "message")))

    def _resolve_battle(self, step: int) -> None:
        self.log.add("battle_started", step)
        for _ in range(120):
            if self.game.battle and self.game.battle.outcome:
                self._dispatch("battle", "return")
                self.log.add("battle_finished", step, outcome=str(self.game.battle.outcome))
                return
            self.now += 1_000
            self._dispatch("battle", "execute", command="fight")
            self._dispatch("battle", "tick", now=self.now)
        self.log.add("stalled", step, reason="battle_round_limit")

    def _dispatch(self, target: str, action: str, **payload: Any) -> Any:
        return self.game.runtime.dispatch(target, action, **payload)
