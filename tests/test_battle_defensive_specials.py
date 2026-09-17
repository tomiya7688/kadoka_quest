from __future__ import annotations

from pathlib import Path
import random
import sys
from types import SimpleNamespace
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.core.combatant import Combatant
from kadoka_quest.core.monster import MonsterRecord


ATTACK = {
    "id": "attack",
    "display_name": "こうげき",
    "kind": "physical",
    "power": 1.0,
    "mp_cost": 0,
}
DEFEND = {
    "id": "defend",
    "display_name": "ぼうぎょ",
    "kind": "defend",
    "damage_multiplier": 0.5,
    "mp_cost": 0,
}
COUNTER = {
    "id": "counter",
    "display_name": "反撃のかまえ",
    "kind": "defend",
    "damage_multiplier": 0.75,
    "counter": True,
    "mp_cost": 3,
}
PROTECT = {
    "id": "protect",
    "display_name": "かばう",
    "kind": "defend",
    "damage_multiplier": 0.75,
    "protect_ally": True,
    "mp_cost": 3,
}
AREA_ATTACK = {
    "id": "area_attack",
    "display_name": "全体攻撃",
    "kind": "physical",
    "power": 1.0,
    "target": "all",
    "mp_cost": 0,
}


class FirstUsableInference:
    @staticmethod
    def choose(_ai, skills, *_args):
        return skills[0] if skills else None


def make_combatant(
    name: str,
    skills: list[dict],
    *,
    hp: int = 100,
    speed: int = 10,
) -> Combatant:
    record = MonsterRecord(
        {"id": name, "species_id": "test", "name": name, "level": 1},
        {},
    )
    combatant = Combatant(
        record=record,
        stats={"hp": 100, "mp": 20, "attack": 20, "defense": 5, "magic": 10, "speed": speed},
        skills=skills,
        resistances={},
    )
    combatant.hp = hp
    return combatant


def make_engine() -> BattleEngine:
    engine = BattleEngine.__new__(BattleEngine)
    engine.rng = random.Random(7)
    engine.learning_enabled = False
    engine.inference = FirstUsableInference()
    engine.log = []
    engine.round_number = 0
    engine.outcome = None
    engine.data_loader = SimpleNamespace(species_definition=lambda _species_id: {})
    return engine


class DefensiveSpecialTests(unittest.TestCase):
    def test_counter_stance_retaliates_after_single_target_damage(self) -> None:
        engine = make_engine()
        defender = make_combatant("defender", [COUNTER, ATTACK])
        attacker = make_combatant("attacker", [ATTACK])

        engine._take_action(defender, [attacker], [defender])
        attacker_before = attacker.hp
        defender_before = defender.hp
        engine._attack(attacker, defender, ATTACK)

        self.assertTrue(defender.counter_ready)
        self.assertLess(defender.hp, defender_before)
        self.assertLess(attacker.hp, attacker_before)
        self.assertTrue(any("反撃！" in line for line in engine.log))

    def test_normal_defend_does_not_arm_counter_or_protection(self) -> None:
        engine = make_engine()
        defender = make_combatant("defender", [DEFEND, ATTACK])
        attacker = make_combatant("attacker", [ATTACK])

        engine._take_action(defender, [attacker], [defender])
        attacker_before = attacker.hp
        engine._attack(attacker, defender, ATTACK)

        self.assertFalse(defender.counter_ready)
        self.assertFalse(defender.protect_ally)
        self.assertEqual(attacker.hp, attacker_before)

    def test_protect_redirects_targetable_single_attack_to_protector(self) -> None:
        engine = make_engine()
        ally = make_combatant("ally", [ATTACK], hp=35)
        protector = make_combatant("protector", [PROTECT])
        attacker = make_combatant("attacker", [ATTACK])

        engine._take_action(protector, [attacker], [ally, protector])
        ally_before = ally.hp
        protector_before = protector.hp
        engine._take_action(attacker, [ally, protector], [attacker])

        self.assertTrue(protector.protect_ally)
        self.assertEqual(ally.hp, ally_before)
        self.assertLess(protector.hp, protector_before)
        self.assertTrue(any("protectorがallyをかばった" in line for line in engine.log))

    def test_area_attack_is_not_redirected_or_countered(self) -> None:
        engine = make_engine()
        ally = make_combatant("ally", [ATTACK], hp=35)
        protector = make_combatant("protector", [ATTACK])
        protector.protect_ally = True
        protector.counter_ready = True
        attacker = make_combatant("attacker", [ATTACK])

        resolved = engine._resolve_attack_target(ally, [ally, protector], AREA_ATTACK)
        attacker_before = attacker.hp
        engine._attack(attacker, protector, AREA_ATTACK)

        self.assertIs(resolved, ally)
        self.assertEqual(attacker.hp, attacker_before)
        self.assertFalse(any("反撃！" in line for line in engine.log))

    def test_counter_and_protection_state_expire_at_round_end(self) -> None:
        engine = make_engine()
        ally = make_combatant("ally", [ATTACK], speed=20)
        enemy = make_combatant("enemy", [ATTACK], speed=10)
        ally.counter_ready = True
        ally.protect_ally = True
        ally.guard = 0.75
        engine.allies = [ally]
        engine.enemies = [enemy]

        engine.run_round()

        self.assertFalse(ally.counter_ready)
        self.assertFalse(ally.protect_ally)
        self.assertEqual(ally.guard, 1.0)


if __name__ == "__main__":
    unittest.main()
