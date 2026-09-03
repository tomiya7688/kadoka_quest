from __future__ import annotations

from typing import Any


class BattleSession:
    """Owns battle lifecycle, command selection, playback, and auto timing state."""

    COMMANDS = ("fight", "scout", "item", "run")

    def __init__(
        self,
        initial_log_delay_ms: int = 140,
        action_log_delay_ms: int = 560,
        short_log_delay_ms: int = 300,
        next_round_delay_ms: int = 600,
    ) -> None:
        self.initial_log_delay_ms = int(initial_log_delay_ms)
        self.action_log_delay_ms = int(action_log_delay_ms)
        self.short_log_delay_ms = int(short_log_delay_ms)
        self.next_round_delay_ms = int(next_round_delay_ms)
        self.battle: Any | None = None
        self.finalized = False
        self.selection = 0
        self.auto = False
        self.last_auto_tick = 0
        self.playback = False
        self.visible_log_count = 0
        self.next_log_tick = 0
        self.action_line = ""
        self.focus_id: str | None = None
        self.simulation = False
        self.fixed_mob_id: str | None = None

    def begin(
        self,
        battle: Any,
        now: int,
        *,
        simulation: bool = False,
        fixed_mob_id: str | None = None,
    ) -> None:
        self.battle = battle
        self.finalized = False
        self.selection = 0
        self.auto = False
        self.last_auto_tick = int(now)
        self.simulation = bool(simulation)
        self.fixed_mob_id = fixed_mob_id
        self.reset_presentation()

    def clear(self) -> dict[str, Any]:
        result = {
            "outcome": self.battle.outcome if self.battle else None,
            "simulation": self.simulation,
            "fixed_mob_id": self.fixed_mob_id,
        }
        self.battle = None
        self.finalized = False
        self.auto = False
        self.simulation = False
        self.fixed_mob_id = None
        self.reset_presentation()
        return result

    def reset_presentation(self) -> None:
        self.playback = False
        self.visible_log_count = len(self.battle.log) if self.battle else 0
        self.next_log_tick = 0
        self.action_line = ""
        self.focus_id = None

    def start_playback(self, log_start: int, now: int) -> bool:
        if not self.battle or len(self.battle.log) <= int(log_start):
            return False
        self.visible_log_count = min(self.visible_log_count, int(log_start))
        self.playback = True
        self.action_line = "行動を開始します……"
        self.focus_id = None
        self.next_log_tick = int(now) + self.initial_log_delay_ms
        return True

    def log_delay(self, line: str) -> int:
        if line.startswith(("---", "会心！")) or line in {"勝利した！", "パーティは戦闘不能になった。"} or "たおれた" in line:
            return self.short_log_delay_ms
        return self.action_log_delay_ms

    def update_playback(self, now: int) -> dict[str, bool]:
        if not self.playback or not self.battle or int(now) < self.next_log_tick:
            return {"changed": False, "completed": False}
        if self.visible_log_count < len(self.battle.log):
            line = self.battle.log[self.visible_log_count]
            self.visible_log_count += 1
            self.action_line = line
            self.focus_id = self._focus_for_log(line)
            self.next_log_tick = int(now) + self.log_delay(line)
            return {"changed": True, "completed": False}
        self.playback = False
        self.focus_id = None
        self.last_auto_tick = int(now)
        self.visible_log_count = len(self.battle.log)
        return {"changed": True, "completed": True}

    def _focus_for_log(self, line: str) -> str | None:
        if not self.battle or line.startswith("---"):
            return None
        for member in [*self.battle.allies, *self.battle.enemies]:
            if line.startswith(member.name):
                return str(member.record.monster_id)
        return None

    def move_selection(self, amount: int) -> int:
        self.selection = (self.selection + int(amount)) % len(self.COMMANDS)
        return self.selection

    def set_selection(self, index: int) -> int:
        self.selection = max(0, min(len(self.COMMANDS) - 1, int(index)))
        return self.selection

    def selected_command(self) -> str:
        return self.COMMANDS[self.selection % len(self.COMMANDS)]

    def toggle_auto(self, now: int) -> bool | None:
        if not self.battle or self.battle.outcome:
            return None
        self.auto = not self.auto
        self.last_auto_tick = int(now)
        return self.auto

    def stop_auto(self) -> None:
        self.auto = False

    def auto_command_due(self, now: int, *, battle_mode: bool) -> bool:
        if not self.auto or self.playback or not battle_mode or not self.battle or self.battle.outcome:
            return False
        if int(now) - self.last_auto_tick < self.next_round_delay_ms:
            return False
        self.last_auto_tick = int(now)
        return True

    def mark_finalized(self) -> bool:
        if not self.battle or not self.battle.outcome or self.finalized or self.playback:
            return False
        self.finalized = True
        self.auto = False
        return True
