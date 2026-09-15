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
from kadoka_quest.core.status_effects import has_status, status_apply_chance


BLEEDING_EFFECT = {
    "id": "bleeding",
    "display_name": "出血",
    "chance": 1.0,
    "removable": True,
}
BLEEDING_ATTACK = {
    "id": "test_bleeding_attack",
    "display_name": "テストひっかき",
    "kind": "physical",
    "power": 0.8,
    "mp_cost": 0,
    "status_effect": BLEEDING_EFFECT,
}


class FixedRng:
    @staticmethod
    def random() -> float:
        return 0.0

    @staticmethod
    def uniform(_low: float, _high: float) -> float:
        return 1.0

    @staticmethod
    def randint(low: int, _high: int) -> int:
        return low

    @staticmethod
    def shuffle(_items: list) -> None:
        return None


def make_combatant(
    name: str,
    *,
    status_resistances: dict[str, str] | None = None,
) -> Combatant:
    return Combatant(
        record=MonsterRecord(
            {"id": name, "species_id": "test", "name": name, "level": 1},
            {},
        ),
        stats={"hp": 100, "mp": 20, "attack": 40, "defense": 50, "magic": 20, "speed": 40},
        skills=[],
        resistances={},
        status_resistances=dict(status_resistances or {}),
    )


def make_engine() -> BattleEngine:
    engine = BattleEngine.__new__(BattleEngine)
    engine.rng = FixedRng()
    engine.log = []
    engine.data_loader = SimpleNamespace(species_definition=lambda _species_id: {})
    return engine


class BleedingStatusTests(unittest.TestCase):
    def test_status_resistance_levels_scale_application_chance(self) -> None:
        expected = {
            "very_weak": 0.60,
            "weak": 0.50,
            "normal": 0.40,
            "resist": 0.30,
            "strong": 0.20,
            "immune": 0.00,
        }
        for level, chance in expected.items():
            with self.subTest(level=level):
                self.assertAlmostEqual(status_apply_chance(0.4, level), chance)

    def test_bleeding_immune_target_cannot_be_inflicted(self) -> None:
        engine = make_engine()
        actor = make_combatant("actor")
        target = make_combatant("target", status_resistances={"bleeding": "immune"})

        engine._attack(actor, target, BLEEDING_ATTACK)

        self.assertFalse(has_status(target.status_effects, "bleeding"))
        self.assertTrue(any("出血が効かなかった" in line for line in engine.log))

    def test_bleeding_reduces_speed_and_defense_and_deals_small_turn_damage(self) -> None:
        engine = make_engine()
        actor = make_combatant("actor")
        target = make_combatant("target")

        engine._attack(actor, target, BLEEDING_ATTACK)

        self.assertTrue(has_status(target.status_effects, "bleeding"))
        self.assertEqual(target.speed, 36)
        self.assertEqual(target.defense, 45)

        before = target.hp
        engine._tick_end_turn_status(target)
        self.assertEqual(before - target.hp, 2)

    def test_bleeding_does_not_stack_and_cure_restores_stats(self) -> None:
        engine = make_engine()
        target = make_combatant("target")

        self.assertTrue(engine._try_apply_status(target, BLEEDING_EFFECT))
        self.assertFalse(engine._try_apply_status(target, BLEEDING_EFFECT))
        self.assertEqual(sum(1 for effect in target.status_effects if effect.get("id") == "bleeding"), 1)
        self.assertEqual(target.speed, 36)
        self.assertEqual(target.defense, 45)

        cured = engine._try_cure_status(target, 1.0)

        self.assertEqual(cured, "出血")
        self.assertFalse(has_status(target.status_effects, "bleeding"))
        self.assertEqual(target.speed, 40)
        self.assertEqual(target.defense, 50)


if __name__ == "__main__":
    unittest.main()
