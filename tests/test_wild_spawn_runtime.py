# {
#   責務: [test_wild_spawn_runtime: test・wild・出現・実行時の公開機能・宣言を定義する]
#   フィールド: []
# }
from collections import Counter
from copy import deepcopy
from pathlib import Path
import random
import shutil
from unittest import mock

import pytest

from kadoka_engine.field_engine import FieldEngine
from kadoka_engine.hidden_enemy_controller import HiddenEnemyController
from kadoka_engine.wild_spawn import draw_wild_spawn, pop_allowed, relative_spawn_weights
from kadoka_quest.apps.game import KadokaQuest
from kadoka_quest.core.spawn_levels import wild_encounter_level
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.parties import PartyStore
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.data.state import StateStore
from kadoka_quest.apps.map_editor import MapEditor


# {
#   責務: [controller: test・wild・出現・実行時のcontrollerを求める]
#   処理: [1: test・wild・出現・実行時のcontrollerを求める]
#   引数: [
#     rate: rate
#     seed: seed
#     entries: 項目一覧
#   ]
#   戻り値: [result: 処理結果（型注釈なし）]
# }
def controller(rate=100, seed=153, entries=None):
    world = {"width": 12, "height": 12, "tiles": [["floor"] * 12 for _ in range(12)],
             "pop_rate": rate, "spawns": entries if entries is not None else [
                 {"species_id": "slime", "weight": 0.1, "min_level": 3, "max_level": 9}]}
    blocks = {"floor": {"enemy_spawnable": True, "enemy_walkable": True}}
    result = HiddenEnemyController(FieldEngine(world, blocks), random.Random(seed))
    result.set_world(world, blocks)
    return result


# {
#   責務: [test_zero_or_invalid_pop_rate_never_spawns: 検証: zero or invalid pop rate never spawns]
#   処理: [1: 検証: zero or invalid pop rate never spawns]
#   引数: [rate: rate]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("rate", [0, -1, 101, True, "50", None, float("nan"), float("inf")])
def test_zero_or_invalid_pop_rate_never_spawns(rate):
    result = controller(rate)
    for now in range(5):
        result.reset((0, 0), {}, now)
        assert result.monsters == []


# {
#   責務: [test_full_population_levels_unique_positions_and_unmodified_map: 検証: full population levels unique positions and unmodified map]
#   処理: [1: 検証: full population levels unique positions and unmodified map]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_full_population_levels_unique_positions_and_unmodified_map():
    result = controller()
    before = deepcopy(result.map_data)
    result.reset((0, 0), {}, 100)
    assert len(result.monsters) == 12
    assert len({(mob["x"], mob["y"]) for mob in result.monsters}) == 12
    assert all((mob["x"], mob["y"]) != (0, 0) for mob in result.monsters)
    assert all(3 <= mob["spawn"]["rolled_level"] <= 9 for mob in result.monsters)
    assert result.map_data == before


# {
#   責務: [test_missing_rate_defaults_to_full_population: 検証: missing rate defaults to full population]
#   処理: [1: 検証: missing rate defaults to full population]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_missing_rate_defaults_to_full_population():
    result = controller()
    result.map_data.pop("pop_rate")
    result.reset((0, 0), {}, 100)
    assert len(result.monsters) == 12


# {
#   責務: [test_failed_slots_are_not_retried_until_population_is_full: 検証: failed slots are not retried until population is full]
#   処理: [1: 検証: failed slots are not retried until population is full]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_failed_slots_are_not_retried_until_population_is_full():
    result = controller(50)
    with mock.patch("kadoka_engine.wild_spawn.pop_allowed", side_effect=[True, False] * 6) as roll:
        result.reset((0, 0), {}, 100)
    assert roll.call_count == 12
    assert len(result.monsters) == 6


# {
#   責務: [test_pop_species_level_ai_order: 検証: pop species level ai order]
#   処理: [1: 検証: pop species level ai order]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_pop_species_level_ai_order():
    result = controller(50)
    events = []
    result.rng.shuffle = lambda values: None
    result.rng.random = lambda: events.append("pop") or 0.1
    # {
    #   責務: [choose: test・wild・出現・実行時を選択する]
    #   処理: [1: test・wild・出現・実行時を選択する]
    #   引数: [
    #     options: options
    #     kwargs: kwargs
    #   ]
    #   戻り値: [result: test・wild・出現・実行時を選択するための結果（型注釈なし）]
    # }
    def choose(options, **kwargs):
        events.append("species" if isinstance(options[0], dict) else "ai")
        return [options[0]]
    result.rng.choices = choose
    result.rng.randint = lambda low, high: events.append("level") or high
    result.reset((0, 0), {}, 100)
    assert events == ["pop", "species", "level", "ai"] * 12
    assert {mob["spawn"]["rolled_level"] for mob in result.monsters} == {9}


# {
#   責務: [test_relative_fractional_and_huge_weights_and_zero_candidates: 検証: relative fractional and huge weights and zero candidates]
#   処理: [1: 検証: relative fractional and huge weights and zero candidates]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_relative_fractional_and_huge_weights_and_zero_candidates():
    for values in ((60, 30, 1), (0.6, 0.3, 0.01)):
        options = [{"species_id": str(i), "weight": value} for i, value in enumerate(values)]
        rng = random.Random(153)
        weights = relative_spawn_weights(options)
        counts = Counter(draw_wild_spawn(rng, options, weights)["species_id"] for _ in range(12000))
        for i, expected in enumerate((60/91, 30/91, 1/91)):
            assert abs(counts[str(i)] / 12000 - expected) < 0.015
    assert relative_spawn_weights([{"weight": 1e308}, {"weight": 1e308}]) == [1, 1]
    result = controller(entries=[{"species_id": "ghost", "weight": 0}, {"species_id": "slime", "weight": 0.01}])
    result.reset((0, 0), {}, 0)
    assert {mob["spawn"]["species_id"] for mob in result.monsters} == {"slime"}


# {
#   責務: [test_bad_or_all_zero_species_weights_are_safe: 検証: bad or all zero species weights are safe]
#   処理: [1: 検証: bad or all zero species weights are safe]
#   引数: [weight: 重み]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("weight", [0, -1, True, "1", float("nan"), float("inf"), 10**1000])
def test_bad_or_all_zero_species_weights_are_safe(weight):
    result = controller(entries=[{"species_id": "slime", "weight": weight}])
    result.reset((0, 0), {}, 0)
    assert result.monsters == []


# {
#   責務: [test_flags_and_starter_filter_precede_weight_normalization: 検証: flags and starter filter precede weight normalization]
#   処理: [1: 検証: flags and starter filter precede weight normalization]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_flags_and_starter_filter_precede_weight_normalization():
    result = controller(entries=[
        {"species_id": "ball_slime", "weight": 100},
        {"species_id": "ghost", "weight": 100, "requires_flag": "open"},
        {"species_id": "slime", "weight": 0.1},
    ])
    result.reset((0, 0), {}, 0)
    assert {mob["spawn"]["species_id"] for mob in result.monsters} == {"slime"}


# {
#   責務: [test_empty_or_blocked_map_has_no_population: 検証: empty or blocked map has no population]
#   処理: [1: 検証: empty or blocked map has no population]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_empty_or_blocked_map_has_no_population():
    for result in (controller(entries=[]), controller()):
        result.blocks["floor"]["enemy_spawnable"] = False
        result.reset((0, 0), {}, 0)
        assert result.monsters == []


# {
#   責務: [test_probability_boundary_and_zero_do_not_draw_species: 検証: probability boundary and zero do not draw species]
#   処理: [1: 検証: probability boundary and zero do not draw species]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_probability_boundary_and_zero_do_not_draw_species():
    rng = mock.Mock()
    rng.random.return_value = 0.25
    assert not pop_allowed(rng, 25)
    rng.random.return_value = 0.249
    assert pop_allowed(rng, 25)
    assert draw_wild_spawn(rng, [{"species_id": "slime"}], [1], 0) is None
    rng.choices.assert_not_called()


# {
#   責務: [test_normal_encounter_reuses_level_without_reroll_but_legacy_still_rolls: 検証: normal encounter reuses level without reroll but legacy still rolls]
#   処理: [1: 検証: normal encounter reuses level without reroll but legacy still rolls]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_normal_encounter_reuses_level_without_reroll_but_legacy_still_rolls():
    rng = mock.Mock()
    spawn = {"min_level": 3, "max_level": 9, "rolled_level": 7}
    assert wild_encounter_level(spawn, [], "normal", rng) == 7
    rng.randint.assert_not_called()
    spawn.pop("rolled_level")
    rng.randint.return_value = 9
    assert wild_encounter_level(spawn, [], "normal", rng) == 9
    rng.randint.assert_called_once_with(3, 9)


# {
#   責務: [test_population_reproducibility_and_ai_fallback: 検証: population reproducibility and ai fallback]
#   処理: [1: 検証: population reproducibility and ai fallback]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_population_reproducibility_and_ai_fallback():
    # {
    #   責務: [run: test・wild・出現・実行時を実行する]
    #   処理: [1: test・wild・出現・実行時を実行する]
    #   引数: []
    #   戻り値: [result: result.monsters（型注釈なし）]
    # }
    def run():
        result = controller(75)
        result.reset((0, 0), {}, 0, {"slime": {"idle": 2}})
        return result.monsters
    assert run() == run()
    assert run() and {mob["ai"] for mob in run()} == {"idle"}


# {
#   責務: [game: test・wild・出現・実行時のゲームを求める]
#   処理: [1: test・wild・出現・実行時のゲームを求める]
#   引数: [tmp_path: tmp・パス]
#   戻り値: [result: 処理結果（型注釈なし）]
# }
@pytest.fixture
def game(tmp_path):
    repository = GameRepository(Path(__file__).resolve().parents[1] / "data")
    result = KadokaQuest(repository, MonsterStore(tmp_path / "monsters", repository),
                         StateStore(tmp_path / "state.json"), PartyStore(tmp_path / "parties"), random.Random(153))
    result.change_map("greenwood", 6, 6)
    result.mode = "field"
    return result


# {
#   責務: [test_runtime_population_to_battle_preserves_rolled_level: 検証: runtime population to battle preserves rolled level]
#   処理: [1: 検証: runtime population to battle preserves rolled level]
#   引数: [game: ゲーム]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_runtime_population_to_battle_preserves_rolled_level(game):
    game.map_data["pop_rate"] = 100
    game.map_data["spawns"] = [{"species_id": "slime", "weight": 0.5, "min_level": 3, "max_level": 9}]
    game.reset_hidden_monsters(now=100)
    target = game.hidden_monsters[0]
    with mock.patch.object(game.rng, "randint", side_effect=AssertionError("level rerolled")):
        assert game.start_wild_battle(target["spawn"], target)
    assert game.battle.enemies[0].record.level == target["spawn"]["rolled_level"]
    assert "rolled_level" not in game.battle.enemies[0].record.monster


# {
#   責務: [test_zero_rate_blocks_population_and_implicit_encounter: 検証: zero rate blocks population and implicit encounter]
#   処理: [1: 検証: zero rate blocks population and implicit encounter]
#   引数: [game: ゲーム]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_zero_rate_blocks_population_and_implicit_encounter(game):
    game.map_data["pop_rate"] = 0
    game.reset_hidden_monsters(now=100)
    assert game.hidden_monsters == []
    assert not game.start_wild_battle()
    assert game.mode == "field"


# {
#   責務: [test_metal_context_ignores_population_level: 検証: metal context ignores population level]
#   処理: [1: 検証: metal context ignores population level]
#   引数: [game: ゲーム]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_metal_context_ignores_population_level(game):
    game.map_data["encounter_context"] = "metal_area"
    spawn = {"species_id": "metal_slime", "min_level": 1, "max_level": 100, "rolled_level": 99}
    with mock.patch.object(game.rng, "randint", return_value=5) as roll:
        record = game.make_wild(spawn)
    assert record.level == 5
    roll.assert_called_once()


# {
#   責務: [test_editor_saved_settings_reach_runtime_after_reload: 検証: editor saved settings reach runtime after reload]
#   処理: [1: 検証: editor saved settings reach runtime after reload]
#   引数: [
#     tmp_path: tmp・パス
#     rate: rate
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("rate", [0, 100])
def test_editor_saved_settings_reach_runtime_after_reload(tmp_path, rate):
    root = tmp_path / "data"
    shutil.copytree(Path(__file__).resolve().parents[1] / "data", root)
    repository = GameRepository(root)
    editor = MapEditor(repository)
    editor.map_data["spawns"] = [
        {"species_id": "slime", "weight": 0.01, "min_level": 8, "max_level": 8},
    ]
    editor.open_spawn_dialog()
    editor.map_spawn_form.rate.value = str(rate)
    editor.map_spawn_form.inherit = False
    for name, field in editor.map_spawn_form.weights.items():
        field.value = "1" if name == "idle" else "0"
    editor.save()
    assert not editor.dirty
    runtime = KadokaQuest(repository, MonsterStore(tmp_path / "monsters", repository),
                          StateStore(tmp_path / "state.json"), PartyStore(tmp_path / "parties"), random.Random(153))
    runtime.change_map(editor.map_id, 6, 6)
    assert bool(runtime.hidden_monsters) == bool(rate)
    assert all(mob["ai"] == "idle" and mob["spawn"]["rolled_level"] == 8 for mob in runtime.hidden_monsters)
