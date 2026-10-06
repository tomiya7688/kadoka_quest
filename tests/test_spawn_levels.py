# {
#   責務: [test_spawn_levels: test・出現・レベル一覧の公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import copy
from itertools import permutations
from pathlib import Path
import random
from types import SimpleNamespace
from unittest import mock

import pytest

from kadoka_quest.apps.battle_session import BattleSession
from kadoka_quest.apps.game import KadokaQuest
from kadoka_quest.core.ai import default_ai
from kadoka_quest.core.battle_rewards import battle_experience
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.core.spawn_levels import metal_area_level_range, spawn_level_range
from kadoka_quest.data.repository import GameRepository


# {
#   責務: [member: test・出現・レベル一覧の個体を求める]
#   処理: [1: test・出現・レベル一覧の個体を求める]
#   引数: [
#     level: レベル
#     species: 種族
#   ]
#   戻り値: [result: test・出現・レベル一覧の個体を求めるための結果（型注釈なし）]
# }
def member(level, species="slime"):
    return MonsterRecord({
        "id": f"{species}_{level}", "name": species, "species_id": species,
        "level": level, "experience": 0, "plus_choices": [], "equipment_id": None,
    }, default_ai())


# {
#   責務: [test_reference_cases_and_boundaries: 検証: reference cases and boundaries]
#   処理: [1: 検証: reference cases and boundaries]
#   引数: [
#     levels: レベル一覧
#     expected: expected
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("levels,expected", [
    ([62, 58, 43, 21], (55, 61)),
    ([80, 65, 40, 20], (62, 68)),
    ([100, 1, 1, 1], (95, 100)),
    ([80, 61], (58, 64)),  # Difference 19: use second.
    ([80, 60], (75, 85)),  # Difference 20: use first.
    ([80, 59], (75, 85)),
    ([50], (45, 55)),
    ([50, 50], (47, 53)),
    ([1], (1, 6)),
    ([1, 1], (1, 4)),
    ([100], (95, 100)),
    ([100, 100], (97, 100)),
])
def test_reference_cases_and_boundaries(levels, expected):
    assert metal_area_level_range([member(level) for level in levels]) == expected


# {
#   責務: [test_ghost_conversion_precedes_ranking_and_gap_check: 検証: ghost conversion precedes ranking and gap check]
#   処理: [1: 検証: ghost conversion precedes ranking and gap check]
#   引数: [species: 種族]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("species", ["maru", "kadoka"])
def test_ghost_conversion_precedes_ranking_and_gap_check(species):
    assert metal_area_level_range([member(80, species), member(60)]) == (57, 63)
    assert metal_area_level_range([member(80), member(70, species)]) == (75, 85)
    assert metal_area_level_range([member(62, species), member(58)]) == (49, 55)
    assert metal_area_level_range([member(10, species)]) == (1, 6)
    assert metal_area_level_range([member(1, species)]) == (1, 6)
    assert metal_area_level_range([member(100, species)]) == (85, 95)


# {
#   責務: [test_both_ghosts_convert_but_normal_ghost_does_not: 検証: both ghosts convert but normal ghost does not]
#   処理: [1: 検証: both ghosts convert but normal ghost does not]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_both_ghosts_convert_but_normal_ghost_does_not():
    assert metal_area_level_range([member(80, "maru"), member(75, "kadoka")]) == (62, 68)
    assert metal_area_level_range([member(80, "ghost"), member(60)]) == (75, 85)


# {
#   責務: [test_party_order_does_not_change_result_or_mutate_records: 検証: party order does not change result or mutate records]
#   処理: [1: 検証: party order does not change result or mutate records]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_party_order_does_not_change_result_or_mutate_records():
    party = [member(62), member(58), member(53, "maru"), member(31, "kadoka")]
    before = copy.deepcopy(party)
    for ordering in permutations(party):
        assert metal_area_level_range(ordering) == (55, 61)
    assert party == before


# {
#   責務: [test_only_battle_participants_count_and_empty_party_is_rejected: 検証: only battle participants count and empty party is rejected]
#   処理: [1: 検証: only battle participants count and empty party is rejected]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_only_battle_participants_count_and_empty_party_is_rejected():
    assert metal_area_level_range([member(10)] * 4 + [member(100)]) == (7, 13)
    with pytest.raises(ValueError, match="パーティ"):
        metal_area_level_range([])


# {
#   責務: [test_other_contexts_keep_static_level_range: 検証: other contexts keep static level range]
#   処理: [1: 検証: other contexts keep static level range]
#   引数: [context: 判断用コンテキスト]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("context", ["normal", "", "unknown"])
def test_other_contexts_keep_static_level_range(context):
    spawn = {"species_id": "metal_slime", "min_level": 20, "max_level": 25}
    assert spawn_level_range(spawn, [member(100)], context) == (20, 25)
    assert spawn_level_range(spawn, [], context) == (20, 25)
    assert spawn_level_range({}, [], context) == (1, 1)


# {
#   責務: [game: test・出現・レベル一覧のゲームを求める]
#   処理: [1: test・出現・レベル一覧のゲームを求める]
#   引数: []
#   戻り値: [result: ゲーム（型注釈なし）]
# }
@pytest.fixture
def game():
    repository = GameRepository(Path(__file__).resolve().parents[1] / "data")
    party = [member(level) for level in (62, 58, 43, 21)]
    game = SimpleNamespace(
        repository=repository, rng=random.Random(144), party=mock.Mock(return_value=party),
        mode="field",
        field_session=SimpleNamespace(map_data={"encounter_context": "metal_area"}),
        spawn_options=lambda: [], hidden_enemies=mock.Mock(), battle_session=BattleSession(),
    )
    game.make_wild = lambda spawn: KadokaQuest.make_wild(game, spawn)
    return game


# {
#   責務: [test_encounter_roll_uses_dynamic_inclusive_bounds_without_editing_data: 検証: encounter roll uses dynamic inclusive bounds without editing data]
#   処理: [1: 検証: encounter roll uses dynamic inclusive bounds without editing data]
#   引数: [
#     game: ゲーム
#     species: 種族
#     endpoint: endpoint
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("species", ["metal_slime", "slime", "ghost"])
@pytest.mark.parametrize("endpoint", [0, 1])
def test_encounter_roll_uses_dynamic_inclusive_bounds_without_editing_data(game, species, endpoint):
    spawn = {"species_id": species, "weight": 1, "min_level": 1, "max_level": 1}
    before = copy.deepcopy((spawn, game.field_session.map_data, game.party.return_value))
    with mock.patch.object(game.rng, "randint", side_effect=lambda low, high: (low, high)[endpoint]) as roll:
        result = game.make_wild(spawn)
    roll.assert_called_once_with(55, 61)
    assert result.level == (55, 61)[endpoint]
    assert result.species_id == species
    assert result.monster["source"] == "wild"
    assert set(result.monster) == {
        "schema_version", "id", "species_id", "name", "level", "experience",
        "plus_choices", "equipment_id", "source",
    }
    assert (spawn, game.field_session.map_data, game.party.return_value) == before


# {
#   責務: [test_level_is_recomputed_after_party_change_and_map_change: 検証: level is recomputed after party change and map change]
#   処理: [1: 検証: level is recomputed after party change and map change]
#   引数: [game: ゲーム]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_level_is_recomputed_after_party_change_and_map_change(game):
    spawn = {"species_id": "metal_slime", "min_level": 20, "max_level": 25}
    with mock.patch.object(game.rng, "randint", side_effect=lambda low, high: low) as roll:
        assert game.make_wild(spawn).level == 55
        game.party.return_value = [member(100), member(1), member(1), member(1)]
        assert game.make_wild(spawn).level == 95
        game.field_session.map_data = {}
        game.party.reset_mock()
        assert game.make_wild(spawn).level == 20
        game.party.assert_not_called()
    assert roll.call_args_list == [mock.call(55, 61), mock.call(95, 100), mock.call(20, 25)]


# {
#   責務: [test_wild_battle_combines_scaled_level_flee_rate_and_reward: 検証: wild battle combines scaled level flee rate and reward]
#   処理: [1: 検証: wild battle combines scaled level flee rate and reward]
#   引数: [game: ゲーム]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_wild_battle_combines_scaled_level_flee_rate_and_reward(game):
    spawn = {"species_id": "metal_slime", "min_level": 1, "max_level": 1}
    hidden = {"spawn": spawn}
    game.party.return_value = [member(100), member(1), member(1), member(1)]
    with mock.patch.object(game.rng, "randint", return_value=100) as roll:
        KadokaQuest.start_wild_battle(game, spawn, hidden)
    roll.assert_called_once_with(95, 100)
    game.hidden_enemies.remove.assert_called_once_with(hidden)
    battle = game.battle_session.battle
    assert battle.encounter_context == "metal_area"
    assert battle.enemies[0].record.level == 100
    assert battle.enemies[0].flee_rates[battle.encounter_context] == 0.6
    battle.enemies[0].hp = 0
    assert battle_experience(battle.enemies) == 4800


# {
#   責務: [test_empty_party_does_not_start_or_consume_hidden_encounter: 検証: empty party does not start or consume hidden encounter]
#   処理: [1: 検証: empty party does not start or consume hidden encounter]
#   引数: [game: ゲーム]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_empty_party_does_not_start_or_consume_hidden_encounter(game):
    game.party.return_value = []
    spawn = {"species_id": "metal_slime"}
    with mock.patch.object(game, "make_wild") as create:
        KadokaQuest.start_wild_battle(game, spawn, {"spawn": spawn})
    create.assert_not_called()
    game.hidden_enemies.remove.assert_not_called()
    assert game.battle_session.battle is None
