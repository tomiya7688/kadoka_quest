from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.core.combatant import Combatant
from kadoka_quest.core.monster import MonsterRecord


PIO = {
    "id": "piora",
    "display_name": "ピオラ",
    "kind": "buff",
    "speed_multiplier": 1.5,
    "duration": [3, 6],
    "mp_cost": 5,
}
CHEER = {
    "id": "cheer",
    "display_name": "おうえん",
    "kind": "buff",
    "attack_multiplier": 1.2,
    "mp_cost": 3,
}
ATTACK = {
    "id": "attack",
    "display_name": "こうげき",
    "kind": "physical",
    "power": 1.0,
    "mp_cost": 0,
}


class SequenceRng:
    def __init__(self, durations: list[int]) -> None:
        self.durations = list(durations)

    def randint(self, low: int, high: int) -> int:
        value = self.durations.pop(0)
        if not low <= value <= high:
            raise AssertionError(f"duration {value} outside {low}..{high}")
        return value

    @staticmethod
    def random() -> float:
        return 1.0

    @staticmethod
    def uniform(_low: float, _high: float) -> float:
        return 1.0

    @staticmethod
    def shuffle(_items: list) -> None:
        return None


class FirstUsableInference:
    @staticmethod
    def choose(_ai, skills, *_args):
        return skills[0] if skills else None


def make_combatant(name: str, skills: list[dict]) -> Combatant:
    return Combatant(
        record=MonsterRecord(
            {"id": name, "species_id": "test", "name": name, "level": 1},
            {},
        ),
        stats={"hp": 100, "mp": 20, "attack": 20, "defense": 5, "magic": 10, "speed": 10},
        skills=skills,
        resistances={},
    )


def make_engine(durations: list[int]) -> BattleEngine:
    engine = BattleEngine.__new__(BattleEngine)
    engine.rng = SequenceRng(durations)
    engine.learning_enabled = False
    engine.inference = FirstUsableInference()
    engine.log = []
    engine.round_number = 0
    engine.outcome = None
    engine.data_loader = SimpleNamespace(species_definition=lambda _species_id: {})
    return engine


class BuffDurationTests(unittest.TestCase):
    def test_piora_minimum_duration_expires_after_three_turn_ticks(self) -> None:
        engine = make_engine([3])
        caster = make_combatant("caster", [PIO])
        target = make_combatant("target", [ATTACK])
        foe = make_combatant("foe", [ATTACK])

        engine._take_action(caster, [foe], [target])

        self.assertEqual(target.speed_multiplier, 1.5)
        self.assertEqual(target.timed_buff_turns["speed_multiplier"], 3)
        self.assertEqual(target.speed, 15)

        engine._tick_timed_buffs(target)
        engine._tick_timed_buffs(target)
        self.assertEqual(target.speed_multiplier, 1.5)
        self.assertEqual(target.timed_buff_turns["speed_multiplier"], 1)

        engine._tick_timed_buffs(target)
        self.assertEqual(target.speed_multiplier, 1.0)
        self.assertEqual(target.speed, 10)
        self.assertNotIn("speed_multiplier", target.timed_buff_turns)

    def test_piora_maximum_duration_accepts_six_turn_boundary(self) -> None:
        engine = make_engine([6])
        caster = make_combatant("caster", [PIO])
        target = make_combatant("target", [ATTACK])
        foe = make_combatant("foe", [ATTACK])

        engine._take_action(caster, [foe], [target])

        self.assertEqual(target.timed_buff_turns["speed_multiplier"], 6)
        for _ in range(5):
            engine._tick_timed_buffs(target)
        self.assertEqual(target.speed_multiplier, 1.5)
        self.assertEqual(target.timed_buff_turns["speed_multiplier"], 1)

        engine._tick_timed_buffs(target)
        self.assertEqual(target.speed_multiplier, 1.0)

    def test_reusing_same_timed_buff_never_shortens_multiplier_or_duration(self) -> None:
        engine = make_engine([3, 6])
        caster = make_combatant("caster", [PIO])
        target = make_combatant("target", [ATTACK])
        foe = make_combatant("foe", [ATTACK])

        engine._take_action(caster, [foe], [target])
        engine._tick_timed_buffs(target)
        self.assertEqual(target.timed_buff_turns["speed_multiplier"], 2)

        engine._take_action(caster, [foe], [target])

        self.assertEqual(target.speed_multiplier, 1.5)
        self.assertEqual(target.timed_buff_turns["speed_multiplier"], 6)

    def test_durationless_attack_buff_keeps_existing_until-next-attack_behavior(self) -> None:
        engine = make_engine([])
        caster = make_combatant("caster", [CHEER])
        target = make_combatant("target", [ATTACK])
        foe = make_combatant("foe", [ATTACK])

        engine._take_action(caster, [foe], [target])

        self.assertEqual(target.attack_multiplier, 1.2)
        self.assertNotIn("attack_multiplier", target.timed_buff_turns)
        for _ in range(8):
            engine._tick_timed_buffs(target)
        self.assertEqual(target.attack_multiplier, 1.2)

        engine._attack(target, foe, ATTACK)
        self.assertEqual(target.attack_multiplier, 1.0)

    def test_timed_buff_restores_preexisting_untimed_baseline(self) -> None:
        engine = make_engine([3])
        target = make_combatant("target", [ATTACK])
        target.speed_multiplier = 1.2

        BattleEngine._apply_multiplier(target, "speed_multiplier", 1.5, 3)
        self.assertEqual(target.timed_buff_baselines["speed_multiplier"], 1.2)

        for _ in range(3):
            engine._tick_timed_buffs(target)

        self.assertEqual(target.speed_multiplier, 1.2)
        self.assertNotIn("speed_multiplier", target.timed_buff_baselines)


if __name__ == "__main__":
    unittest.main()
