from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

from kadoka_quest.apps.battle_flow_dependencies import BattleFlowDependencies
from kadoka_quest.apps.battle_progression_service import BattleProgressionService
from kadoka_quest.apps.battle_session import BattleSession
from kadoka_quest.apps.game import KadokaQuest
from kadoka_quest.core import battle_rewards
from kadoka_quest.core.ai import default_ai
from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.core.battle_rewards import battle_experience, custom_defeat_experience
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.battle_data import BattleDataLoader
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.repository import GameRepository


@pytest.fixture
def repository():
    return GameRepository(Path(__file__).resolve().parents[1] / "data")


def enemy(repository, species="metal_slime", level=10):
    record = MonsterRecord({
        "id": f"{species}_{level}", "name": species, "species_id": species,
        "level": level, "plus_choices": [], "equipment_id": None,
    }, default_ai())
    result = BattleDataLoader(repository).build_combatant(record)
    result.hp = 0
    return result


@pytest.mark.parametrize("level,expected", [
    (1, 335), (10, 660), (11, 697), (20, 1040), (30, 1440),
    (50, 2300), (70, 3240), (100, 4800),
])
def test_canonical_metal_reward_and_integer_floor(repository, level, expected):
    target = enemy(repository, level=level)
    assert custom_defeat_experience(level, target.experience_reward) == expected
    assert battle_experience([target]) == expected


def test_ordinary_formula_stays_unchanged_and_mixed_rewards_add(repository):
    slime = enemy(repository, "slime", 10)
    ghost = enemy(repository, "ghost", 20)
    metal = enemy(repository)
    assert battle_experience([slime]) == 38
    assert battle_experience([slime, ghost]) == 98
    assert battle_experience([slime, ghost, metal]) == 758
    assert battle_experience([metal, enemy(repository, level=20)]) == 1700


def test_custom_formula_is_independent_of_normal_balance(repository, monkeypatch):
    monkeypatch.setattr(battle_rewards, "NORMAL_VICTORY_BONUS", 1000)
    monkeypatch.setattr(battle_rewards, "NORMAL_EXPERIENCE_PER_LEVEL", 900)
    assert battle_experience([enemy(repository)]) == 660


def test_coefficients_are_editable_without_species_id_checks(repository):
    target = enemy(repository, "slime", 11)
    target.experience_reward = {"base": 7, "per_level": 2, "squared_divisor": 3}
    assert battle_experience([target]) == 69
    assert custom_defeat_experience(11, {"base": 0, "per_level": 0, "squared_divisor": 1000}) == 0


@pytest.mark.parametrize("rule", [
    None, {}, "300 + level * 35", [],
    {"base": -1, "per_level": 35, "squared_divisor": 10},
    {"base": 300, "per_level": -1, "squared_divisor": 10},
    {"base": 300, "per_level": 35, "squared_divisor": 0},
    {"base": 300, "per_level": 35, "squared_divisor": -10},
    {"base": 300.0, "per_level": 35, "squared_divisor": 10},
    {"base": True, "per_level": 35, "squared_divisor": 10},
])
def test_missing_or_invalid_rule_uses_safe_ordinary_fallback(repository, rule):
    target = enemy(repository)
    target.experience_reward = rule
    assert custom_defeat_experience(10, rule) is None
    assert battle_experience([target]) == 38


def test_living_or_fled_enemies_never_pay_rewards(repository):
    fled = enemy(repository)
    fled.fled = True
    living = enemy(repository)
    living.hp = 1
    assert battle_experience([]) == 0
    assert battle_experience([fled, living]) == 0
    assert battle_experience([fled, enemy(repository, "slime")]) == 38


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("species", ["slime", "maru", "kadoka"])
def test_reward_persists_and_growth_thresholds_are_unchanged(repository, tmp_path, legacy, species):
    store = MonsterStore(tmp_path / "monsters", repository)
    ally = store.create(species, level=10)
    engine = BattleEngine(repository, [ally], [enemy(repository).record])
    engine.enemies[0].hp = 0
    engine.outcome = "victory"
    session = BattleSession()
    session.begin(engine, 0)
    if legacy:
        game = SimpleNamespace(battle=engine, monsters=store, battle_session=session)
        game.award_experience = lambda: KadokaQuest.award_experience(game)
        finish = lambda: KadokaQuest.finalize_battle_if_needed(game)
    else:
        service = BattleProgressionService(BattleFlowDependencies(
            session=session, monsters=store, states=mock.Mock(), state_provider=lambda: {},
        ))
        finish = service.finalize_if_needed
    session.playback = True
    finish()
    assert store.get(ally.monster_id).level == 10
    session.playback = False
    finish()
    saved = store.get(ally.monster_id)
    assert saved.level == 12
    assert saved.monster["experience"] == 156  # 660 - 10*24 - 11*24
    assert saved.ai["battles"] == 1
    assert "experience_reward" not in saved.monster
    snapshot = copy.deepcopy(saved)
    finish()
    assert store.get(ally.monster_id) == snapshot


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("outcome,learning", [
    (None, True), ("enemies_fled", True), ("escaped", True),
    ("defeat", True), ("scouted", True), ("victory", False),
])
def test_reward_entrypoints_refuse_nonwinning_or_simulated_battles(repository, legacy, outcome, learning):
    engine = BattleEngine(repository, [], [enemy(repository).record], learning_enabled=learning)
    engine.enemies[0].hp = 0
    engine.outcome = outcome
    store = mock.Mock()
    session = BattleSession()
    session.begin(engine, 0)
    if legacy:
        KadokaQuest.award_experience(SimpleNamespace(battle=engine, monsters=store))
    else:
        BattleProgressionService(BattleFlowDependencies(
            session=session, monsters=store, states=mock.Mock(), state_provider=lambda: {},
        )).award_experience()
    store.get.assert_not_called()
    store.save.assert_not_called()


@pytest.mark.parametrize("legacy", [False, True])
def test_level_cap_and_absent_owned_monsters_are_preserved(repository, tmp_path, legacy):
    store = MonsterStore(tmp_path / "monsters", repository)
    capped = store.create("slime", level=100)
    growing = store.create("slime", level=99)
    missing = enemy(repository, "slime").record
    engine = BattleEngine(repository, [capped, growing, missing], [enemy(repository, level=100).record])
    engine.enemies[0].hp = 0
    engine.outcome = "victory"
    session = BattleSession()
    session.begin(engine, 0)
    if legacy:
        KadokaQuest.award_experience(SimpleNamespace(battle=engine, monsters=store))
    else:
        BattleProgressionService(BattleFlowDependencies(
            session=session, monsters=store, states=mock.Mock(), state_provider=lambda: {},
        )).award_experience()
    assert store.get(capped.monster_id) == capped
    assert store.get(growing.monster_id).level == 100
    assert store.get(growing.monster_id).monster["experience"] == 2424
    assert store.get(missing.monster_id) is None
