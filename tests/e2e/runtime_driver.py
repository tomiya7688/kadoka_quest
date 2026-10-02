"""Feed events/commands and frames to production routing, not game rules."""

from __future__ import annotations

import random
from pathlib import Path

import pygame

from kadoka_quest.apps.game import KadokaQuest, MOVE_KEY_DIRECTIONS, password_controls
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.parties import PartyStore
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.data.state import StateStore
from kadoka_quest.paths import SAVE_ROOT, SAVEDATA_ROOT
from kadoka_quest.ui.runtime_input_adapter import RuntimeInputAdapter
from kadoka_quest.ui.runtime_mouse_adapter import RuntimeMouseAdapter
from launcher_driver import drive_launcher
from render_observation import render
from scenario_clock import ScenarioClock, nonnegative_integer


TIMED_COMMANDS = {
    ("field", "move.start"), ("field", "tick"),
    ("battle", "execute"), ("battle", "execute.selected"),
    ("battle", "auto.toggle"), ("battle", "tick"),
}


class RuntimeDriver:
    """Mirror keyboard and frame routing from apps.game.main without rendering."""

    def __init__(self, seed: int, clock: ScenarioClock) -> None:
        self.seed = seed
        self.clock = clock
        self.input = RuntimeInputAdapter(MOVE_KEY_DIRECTIONS)
        keys, erase, decide, cancel = password_controls()
        self.mouse = RuntimeMouseAdapter(keys, {"backspace": erase, "submit": decide, "cancel": cancel}, [])
        self.save_root = SAVE_ROOT
        self.launcher_runs = []
        self.frames = 0
        self.reload()

    def reload(self) -> None:
        repository = GameRepository()
        self.game = KadokaQuest(
            repository=repository,
            monsters=MonsterStore(self.save_root / "monsters", repository),
            states=StateStore(self.save_root / "state.json"),
            parties=PartyStore(self.save_root / "parties"),
            rng=random.Random(self.seed),
        )
        self.game.field_party_service.now = self.clock.datetime_now
        self.running = True
        self.last_render = None

    def launcher(self, step: dict) -> None:
        result = drive_launcher(step["frames"], self.clock, SAVEDATA_ROOT.parent)
        self.launcher_runs.append({key: value for key, value in result.items() if key != "save_root"})
        if result["save_root"] is not None:
            self.save_root = Path(result["save_root"])
            self.reload()

    def password_click(self, value: str) -> None:
        if self.game.mode != "password":
            raise ValueError("Password controls are not visible")
        controls = dict(self.mouse.password_keys) | self.mouse.password_actions
        if value not in controls:
            raise ValueError(f"Unknown password control: {value}")
        self.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=controls[value].center))

    def frame(self) -> None:
        if not self.running:
            return
        self.frames += 1
        if self.frames > 50000:
            raise ValueError("Scenario frame budget exceeded")
        self.game.runtime.dispatch("manager", "refresh")
        if self.game.mode in {"field", "battle"}:
            self.game.runtime.dispatch(self.game.mode, "tick", now=self.clock.now)

    def event(self, event: pygame.event.Event) -> None:
        pygame.event.post(event)
        for queued in pygame.event.get():
            battle = self.game.battle_session.battle
            requests = self.input.translate(
                queued, self.game.mode, self.clock.now,
                battle_finished=bool(battle and battle.outcome),
                battle_playback=self.game.battle_session.playback,
            )
            for request in requests:
                if request["kind"] == "quit":
                    self.running = False
                elif request["kind"] == "command":
                    self.game.runtime.dispatch(
                        request["target"], request["action"], **request["payload"]
                    )
            battle = self.game.battle_session.battle
            enabled = bool(battle and not battle.outcome and not self.game.battle_session.playback)
            for request in self.mouse.translate(queued, self.game.mode, battle_enabled=enabled, now=self.clock.now):
                self.game.runtime.dispatch(request["target"], request["action"], **request["payload"])
        self.frame()

    def command(self, step: dict) -> None:
        target, action = step["target"], step["action"]
        payload = dict(step.get("payload", {}))
        if "now" in payload:
            if nonnegative_integer(payload["now"], "command now") != self.clock.now:
                raise ValueError("command now must match the scenario clock")
        if (target, action) in TIMED_COMMANDS:
            payload["now"] = self.clock.now
        self.game.runtime.dispatch(target, action, **payload)
        self.frame()

    def advance(self, step: dict) -> None:
        remaining = nonnegative_integer(step["ms"], "ms")
        quantum = nonnegative_integer(step.get("frame_ms", 16), "frame_ms")
        if quantum == 0:
            raise ValueError("frame_ms must be positive")
        if remaining == 0:
            self.frame()
        while remaining:
            delta = min(remaining, quantum)
            self.clock.advance(delta)
            self.frame()
            remaining -= delta

    def execute(self, step: dict) -> None:
        kind = step["kind"]
        if kind == "snapshot":
            return
        if kind == "reload":
            self.reload()
            return
        if kind == "launcher":
            self.launcher(step)
            return
        if not self.running:
            raise ValueError("Runtime quit; reload before further input")
        if kind in {"key_down", "key_up"}:
            event_type = pygame.KEYDOWN if kind == "key_down" else pygame.KEYUP
            self.event(pygame.event.Event(
                event_type, key=pygame.key.key_code(step["key"]),
                unicode=str(step.get("unicode", "")), repeat=False,
            ))
        elif kind == "text":
            for character in step["text"]:
                self.event(pygame.event.Event(pygame.KEYDOWN, key=0, unicode=character))
        elif kind == "command":
            self.command(step)
        elif kind == "advance":
            self.advance(step)
        elif kind == "password_click":
            self.password_click(step["value"])
        elif kind == "render":
            self.last_render = render(self)
        else:
            raise ValueError(f"Unsupported step kind: {kind}")
