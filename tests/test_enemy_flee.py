from __future__ import annotations

import copy
from pathlib import Path
import random
from types import SimpleNamespace
from unittest import mock

import pytest

from kadoka_quest.apps.battle_flow_dependencies import BattleFlowDependencies
from kadoka_quest.apps.battle_progression_service import BattleProgressionService
from kadoka_quest.apps.battle_session import BattleSession
from kadoka_quest.apps.game import KadokaQuest
from kadoka_quest.core.ai import default_ai
from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.repository import GameRepository


def record(species, name):
    return MonsterRecord({
        "id": name, "name": name, "species_id": species, "level": 10,
        "experience": 0, "plus_choices": [], "equipment_id": None,
    }, default_ai())


def battle(context="normal", *, learning=True, species="metal_slime"):
    repository = GameRepository(Path(__file__).resolve().parents[1] / "data")
    engine = BattleEngine(
        repository, [record("metal_slime", "味方")], [record(species, "敵")],
        random.Random(142), learning_enabled=learning, encounter_context=context,
    )
    engine.allies[0].stats["speed"] = 1
    engine.enemies[0].stats["speed"] = 1000
    return engine


@pytest.mark.parametrize("context,chance", [("normal", 0.15), ("metal_area", 0.60)])
@pytest.mark.parametrize("below", [True, False])
def test_escape_boundary_runs_once_in_enemy_action_slot(context, chance, below):
    engine = battle(context)
    enemy = engine.enemies[0]
    before = copy.deepcopy(enemy.record)
    hp = enemy.hp
    with mock.patch.object(engine.rng, "random", return_value=chance - 0.000001 if below else chance) as roll, \
         mock.patch.object(engine, "_take_action") as action:
        lines = engine.run_round()
    roll.assert_called_once_with()
    assert enemy.fled is below
    assert enemy.hp == hp  # Escape is not death or damage.
    assert enemy.record == before
    if below:
        assert engine.outcome == "enemies_fled"
        assert "敵は逃げ出した！" in lines
        action.assert_not_called()
        assert engine.try_scout() == (False, None, 0.0)
        assert engine.run_round() == []
    else:
        assert engine.outcome is None
        assert action.call_count == 2


@pytest.mark.parametrize("context,learning,species", [
    (None, True, "metal_slime"), ("normal", False, "metal_slime"),
    ("metal_area", False, "metal_slime"), ("normal", True, "slime"),
    ("unknown", True, "metal_slime"),
])
def test_no_escape_or_extra_rng_for_nonparticipating_battles(context, learning, species):
    engine = battle(context, learning=learning, species=species)
    with mock.patch.object(engine.rng, "random", return_value=0.0) as roll, \
         mock.patch.object(engine, "_take_action") as action:
        engine.run_round()
    roll.assert_not_called()
    assert action.call_count == 2
    assert not engine.enemies[0].fled and not engine.allies[0].fled


def test_escape_retries_each_round_but_never_after_departure():
    engine = battle()
    with mock.patch.object(engine.rng, "random", side_effect=[0.9, 0.1]) as roll, \
         mock.patch.object(engine, "_take_action"):
        engine.run_round()
        engine.run_round()
        engine.run_round()
    assert roll.call_count == 2
    assert engine.round_number == 2
    assert engine.outcome == "enemies_fled"


def test_fled_enemy_is_not_targeted_or_ticked_and_mixed_defeat_is_victory():
    engine = battle()
    other = engine.data_loader.build_combatant(record("slime", "残る敵"))
    engine.enemies.append(other)
    escaped = engine.enemies[0]
    escaped.status_effects = [{"id": "bleeding", "damage_ratio": 0.5}]
    hp = escaped.hp
    with mock.patch.object(engine.rng, "random", return_value=0.0), \
         mock.patch.object(engine, "_take_action") as action:
        engine.run_round()
        engine.run_round()
    assert escaped.fled and escaped.hp == hp
    assert engine.outcome is None
    for call in action.call_args_list:
        assert call.args[0] is not escaped
        assert escaped not in call.args[1] and escaped not in call.args[2]
    other.hp = 0
    engine._check_end()
    assert engine.outcome == "victory"


def test_enemy_killed_before_its_action_does_not_roll_to_flee():
    engine = battle()
    engine.allies[0].stats["speed"] = 2000
    def kill(actor, foes, friends):
        foes[0].hp = 0
    with mock.patch.object(engine.rng, "random") as roll, \
         mock.patch.object(engine, "_take_action", side_effect=kill):
        engine.run_round()
    roll.assert_not_called()
    assert engine.outcome == "victory"


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("all_fled", [False, True])
def test_rewards_exclude_fled_enemies_in_both_entrypoints(legacy, all_fled):
    engine = battle()
    engine.enemies[0].fled = True
    if not all_fled:
        killed = engine.data_loader.build_combatant(record("slime", "倒した敵"))
        killed.hp = 0
        engine.enemies.append(killed)
    engine._check_end()
    session = BattleSession()
    session.begin(engine, 0)
    owned = copy.deepcopy(engine.allies[0].record)
    monsters = mock.Mock()
    monsters.get.return_value = owned
    if legacy:
        KadokaQuest.award_experience(SimpleNamespace(battle=engine, monsters=monsters))
    else:
        service = BattleProgressionService(BattleFlowDependencies(
            session=session, monsters=monsters, states=mock.Mock(), state_provider=lambda: {},
        ))
        service.finalize_if_needed()
    assert owned.monster["experience"] == (0 if all_fled else 38)
    assert monsters.save.call_count == (0 if all_fled else 1)


@pytest.mark.parametrize("context", [None, "normal", "metal_area"])
def test_wild_battle_receives_current_map_context(context):
    engine = battle()
    world = {} if context is None else {"encounter_context": context}
    game = SimpleNamespace(
        spawn_options=lambda: [], party=lambda: [engine.allies[0].record],
        mode="field",
        make_wild=lambda spawn: engine.enemies[0].record,
        repository=engine.repository, rng=random.Random(1),
        field_session=SimpleNamespace(map_data=world), battle_session=BattleSession(),
    )
    KadokaQuest.start_wild_battle(game, {"species_id": "metal_slime"})
    assert game.battle_session.battle.encounter_context == (context or "normal")
    assert "encounter_context" not in engine.enemies[0].record.monster


@pytest.mark.parametrize("value", [-1, 2, "bad", None, float("nan"), float("inf")])
def test_invalid_rate_never_consumes_randomness(value):
    engine = battle()
    engine.enemies[0].flee_rates["normal"] = value
    with mock.patch.object(engine.rng, "random") as roll:
        assert not engine._try_enemy_flee(engine.enemies[0])
    roll.assert_not_called()


def test_fled_card_displays_departure_instead_of_portrait():
    import pygame
    from kadoka_quest.ui.battle_renderer import BattleRenderer

    engine = battle()
    enemy = engine.enemies[0]
    enemy.fled = True
    session = BattleSession()
    session.begin(engine, 0)
    images = mock.Mock()
    with mock.patch("kadoka_quest.ui.battle_renderer.draw_text") as text:
        BattleRenderer(images)._draw_combatant(
            pygame.Surface((320, 110)), session, enemy, pygame.Rect(0, 0, 310, 100), False,
        )
    assert any(call.args[1] == "敵：逃走済み" for call in text.call_args_list)
    images.get.assert_not_called()
    images.appearance.assert_not_called()
