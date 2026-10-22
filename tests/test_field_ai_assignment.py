# {
#   責務: [test_field_ai_assignment: test・フィールド・AI・assignmentの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import copy
from pathlib import Path
import random
from types import SimpleNamespace
from unittest import mock

import pytest

from kadoka_engine.field_ai import FIELD_AI_TYPES, choose_field_ai
from kadoka_engine.field_engine import FieldEngine
from kadoka_engine.hidden_enemy_controller import HiddenEnemyController
from kadoka_quest.data.field_data import FieldDataLoader
from kadoka_quest.data.repository import GameRepository


# {
#   責務: [test_single_positive_weight_selects_only_that_ai: 検証: single positive weight selects only that ai]
#   処理: [1: 検証: single positive weight selects only that ai]
#   引数: [kind: 種別]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("kind", FIELD_AI_TYPES)
def test_single_positive_weight_selects_only_that_ai(kind):
    rng = random.Random(146)
    assert {choose_field_ai(rng, {kind: 0.25}) for _ in range(100)} == {kind}


# {
#   責務: [test_invalid_table_falls_back_as_a_whole: 検証: invalid table falls back as a whole]
#   処理: [1: 検証: invalid table falls back as a whole]
#   引数: [invalid: invalid]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("invalid", [
    None, {}, [], "idle", {"unknown": 1}, {"random": -1, "chase": 2},
    {"random": 0, "idle": 0}, {"random": True}, {"random": "5"},
    {"random": float("nan")}, {"idle": float("inf")}, {"chase": 10 ** 400},
])
def test_invalid_table_falls_back_as_a_whole(invalid):
    assert choose_field_ai(random.Random(1), invalid, {"idle": 1}) == "idle"


# {
#   責務: [test_first_valid_table_wins_without_merging_missing_keys: 検証: first valid table wins without merging missing keys]
#   処理: [1: 検証: first valid table wins without merging missing keys]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_first_valid_table_wins_without_merging_missing_keys():
    assert choose_field_ai(random.Random(1), {"chase": 1}, {"idle": 99}) == "chase"


# {
#   責務: [test_relative_weights_and_default_are_reproducible: 検証: relative weights and default are reproducible]
#   処理: [1: 検証: relative weights and default are reproducible]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_relative_weights_and_default_are_reproducible():
    # {
    #   責務: [draws: test・フィールド・AI・assignmentのdrawsを求める]
    #   処理: [1: test・フィールド・AI・assignmentのdrawsを求める]
    #   引数: [weights: 重み一覧]
    #   戻り値: [result: test・フィールド・AI・assignmentのdrawsを求めるための結果（型注釈なし）]
    # }
    def draws(weights):
        rng = random.Random(146)
        return [choose_field_ai(rng, weights) for _ in range(1000)]
    assert draws(None) == draws({"random": 70, "chase": 25, "idle": 5})
    assert draws({"random": 7, "chase": 7, "idle": 0}) == draws({"random": 1, "chase": 1})
    assert draws({"random": 1e308, "chase": 1e308}) == draws({"random": 1, "chase": 1})
    assert set(draws(None)) == set(FIELD_AI_TYPES)


# {
#   責務: [population: test・フィールド・AI・assignmentのpopulationを求める]
#   処理: [1: test・フィールド・AI・assignmentのpopulationを求める]
#   引数: [
#     seed: seed
#     entry_weights: 項目・重み一覧
#     map_weights: マップ・重み一覧
#     species_weights: 種族・重み一覧
#   ]
#   戻り値: [result: controller（型注釈なし）]
# }
def population(seed=146, entry_weights=None, map_weights=None, species_weights=None):
    world = {
        "width": 12, "height": 12, "tiles": [["floor"] * 12 for _ in range(12)],
        "spawns": [{"species_id": "slime", "weight": 1, "field_ai_weights": entry_weights}],
        "field_ai_weights": map_weights,
    }
    blocks = {"floor": {"enemy_spawnable": True, "enemy_walkable": True}}
    before = copy.deepcopy((world, blocks, species_weights))
    controller = HiddenEnemyController(FieldEngine(world, blocks), random.Random(seed))
    controller.set_world(world, blocks)
    controller.reset((0, 0), {}, 100, species_ai_weights={"slime": species_weights})
    assert (world, blocks, species_weights) == before
    return controller


# {
#   責務: [test_population_uses_entry_then_map_then_species: 検証: population uses entry then map then species]
#   処理: [1: 検証: population uses entry then map then species]
#   引数: [
#     entry: 項目
#     world: マップ状態
#     species: 種族
#     expected: expected
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("entry,world,species,expected", [
    ({"idle": 1}, {"chase": 1}, {"random": 1}, "idle"),
    (None, {"chase": 1}, {"random": 1}, "chase"),
    (None, None, {"random": 1}, "random"),
    ({"idle": -1}, {"chase": 0}, {"random": 1}, "random"),
])
def test_population_uses_entry_then_map_then_species(entry, world, species, expected):
    controller = population(entry_weights=entry, map_weights=world, species_weights=species)
    assert len(controller.monsters) == 12
    assert {enemy["ai"] for enemy in controller.monsters} == {expected}


# {
#   責務: [test_same_species_can_have_different_ai_and_seed_replays_population: 検証: same species can have different ai and seed replays population]
#   処理: [1: 検証: same species can have different ai and seed replays population]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_same_species_can_have_different_ai_and_seed_replays_population():
    controller = population()
    assert controller.monsters == population().monsters
    assert {enemy["spawn"]["species_id"] for enemy in controller.monsters} == {"slime"}
    assert len({enemy["ai"] for enemy in controller.monsters}) > 1
    before = [enemy["ai"] for enemy in controller.monsters]
    for tick in (1000, 2000, 3000):
        controller.update((0, 0), set(), tick)
    assert [enemy["ai"] for enemy in controller.monsters] == before
    assert all("ai" not in enemy["spawn"] for enemy in controller.monsters)


# {
#   責務: [test_loader_reads_only_unique_referenced_species_and_preserves_battle_ai: 検証: loader reads only unique referenced species and preserves battle ai]
#   処理: [1: 検証: loader reads only unique referenced species and preserves battle ai]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_loader_reads_only_unique_referenced_species_and_preserves_battle_ai():
    definitions = {
        "slime": {"field_ai_weights": {"random": 7}, "ai_profile": "normal"},
        "ghost": {"ai_profile": "trickster"},
    }
    repository = mock.Mock(spec=GameRepository)
    repository.get_species.side_effect = lambda name: SimpleNamespace(definition=definitions[name])
    before = copy.deepcopy(definitions)
    loader = FieldDataLoader(repository)
    assert loader.species_ai_weights({"spawns": []}) == {}
    repository.get_species.assert_not_called()
    assert loader.species_ai_weights({"spawns": [
        {"species_id": "slime"}, {"species_id": "ghost"}, {"species_id": "slime"},
    ]}) == {"slime": {"random": 7}, "ghost": None}
    assert repository.get_species.call_args_list == [mock.call("ghost"), mock.call("slime")]
    assert definitions == before


# {
#   責務: [test_canonical_species_weights_and_runtime_wiring: 検証: canonical species weights and runtime wiring]
#   処理: [1: 検証: canonical species weights and runtime wiring]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_canonical_species_weights_and_runtime_wiring():
    from kadoka_quest.apps.game import KadokaQuest

    loader = FieldDataLoader(GameRepository(Path(__file__).resolve().parents[1] / "data"))
    world = {"spawns": [{"species_id": name} for name in ("slime", "ghost", "metal_slime")]}
    weights = loader.species_ai_weights(world)
    assert weights == {
        "slime": {"random": 70, "chase": 25, "idle": 5},
        "ghost": {"random": 40, "chase": 50, "idle": 10},
        "metal_slime": {"random": 85, "chase": 5, "idle": 10},
    }
    runtime = SimpleNamespace(
        hidden_enemies=mock.Mock(), map_data=world, blocks={}, field_data=loader,
        player_x=1, player_y=2, state={"flags": {"story_complete": True}},
    )
    KadokaQuest.reset_hidden_monsters(runtime, now=123)
    runtime.hidden_enemies.set_world.assert_called_once_with(world, {})
    runtime.hidden_enemies.reset.assert_called_once_with(
        (1, 2), {"story_complete": True}, 123, species_ai_weights=weights,
    )
