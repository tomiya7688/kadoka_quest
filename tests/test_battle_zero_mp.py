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
PAID_MAGIC = {
    "id": "paid_magic",
    "display_name": "有料魔法",
    "kind": "magic",
    "element": "fire",
    "power": 1.0,
    "mp_cost": 5,
}


class FirstUsableInference:
    def __init__(self) -> None:
        self.last_candidates: list[dict] = []

    def choose(self, _ai, skills, *_args):
        self.last_candidates = list(skills)
        return self.last_candidates[0] if self.last_candidates else None


def make_combatant(name: str, skills: list[dict], mp: int = 0) -> Combatant:
    record = MonsterRecord(
        {"id": name, "species_id": "test", "name": name, "level": 1},
        {},
    )
    combatant = Combatant(
        record=record,
        stats={"hp": 100, "mp": 10, "attack": 20, "defense": 5, "magic": 10, "speed": 10},
        skills=skills,
        resistances={},
    )
    # Combatant initializes a falsy MP value to max MP, so set the runtime state afterwards.
    combatant.mp = mp
    return combatant


def make_engine() -> BattleEngine:
    engine = BattleEngine.__new__(BattleEngine)
    engine.rng = random.Random(1)
    engine.learning_enabled = False
    engine.inference = FirstUsableInference()
    engine.log = []
    engine.round_number = 0
    engine.outcome = None
    engine.data_loader = SimpleNamespace(species_definition=lambda _species_id: {})
    return engine


class ZeroMpActionTests(unittest.TestCase):
    def test_zero_mp_actor_can_attack_with_zero_cost_skill(self) -> None:
        engine = make_engine()
        actor = make_combatant("actor", [ATTACK], mp=0)
        foe = make_combatant("foe", [ATTACK], mp=0)

        engine._take_action(actor, [foe], [actor])

        self.assertEqual(actor.mp, 0)
        self.assertEqual(actor.action_history, ["attack"])
        self.assertLess(foe.hp, foe.stats["hp"])
        self.assertNotIn("MPが尽きて動けない", "\n".join(engine.log))

    def test_zero_mp_actor_can_defend_with_zero_cost_skill(self) -> None:
        engine = make_engine()
        actor = make_combatant("actor", [DEFEND], mp=0)
        foe = make_combatant("foe", [ATTACK], mp=0)

        engine._take_action(actor, [foe], [actor])

        self.assertEqual(actor.mp, 0)
        self.assertEqual(actor.action_history, ["defend"])
        self.assertEqual(actor.guard, 0.5)

    def test_skills_above_current_mp_are_not_candidates(self) -> None:
        engine = make_engine()
        actor = make_combatant("actor", [PAID_MAGIC, ATTACK], mp=0)
        foe = make_combatant("foe", [ATTACK], mp=0)

        engine._take_action(actor, [foe], [actor])

        self.assertEqual([skill["id"] for skill in engine.inference.last_candidates], ["attack"])
        self.assertEqual(actor.action_history, ["attack"])

    def test_actor_waits_only_when_no_affordable_skill_exists(self) -> None:
        engine = make_engine()
        actor = make_combatant("actor", [PAID_MAGIC], mp=0)
        foe = make_combatant("foe", [ATTACK], mp=0)

        engine._take_action(actor, [foe], [actor])

        self.assertEqual(engine.inference.last_candidates, [])
        self.assertEqual(actor.action_history, [])
        self.assertIn("actorは様子を見ている。", engine.log)

    def test_zero_mp_combatants_keep_battle_progressing(self) -> None:
        engine = make_engine()
        ally = make_combatant("ally", [ATTACK], mp=0)
        enemy = make_combatant("enemy", [ATTACK], mp=0)
        engine.allies = [ally]
        engine.enemies = [enemy]

        round_log = engine.run_round()

        self.assertLess(ally.hp, ally.stats["hp"])
        self.assertLess(enemy.hp, enemy.stats["hp"])
        self.assertTrue(any("ダメージ" in line for line in round_log))
        self.assertNotIn("MPが尽きて動けない", "\n".join(round_log))


if __name__ == "__main__":
    unittest.main()
