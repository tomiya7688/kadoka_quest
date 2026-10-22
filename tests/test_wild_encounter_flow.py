# {
#   責務: [test_wild_encounter_flow: test・wild・encounter・進行の公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import copy
from pathlib import Path
import random
from unittest import mock

import pytest

from kadoka_quest.apps.game import KadokaQuest
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.parties import PartyStore
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.data.state import StateStore


# {
#   責務: [game: test・wild・encounter・進行のゲームを求める]
#   処理: [1: test・wild・encounter・進行のゲームを求める]
#   引数: [tmp_path: tmp・パス]
#   戻り値: [result: 処理結果（型注釈なし）]
# }
@pytest.fixture
def game(tmp_path):
    repository = GameRepository(Path(__file__).resolve().parents[1] / "data")
    result = KadokaQuest(
        repository, MonsterStore(tmp_path / "monsters", repository),
        StateStore(tmp_path / "state.json"), PartyStore(tmp_path / "parties"), random.Random(149),
    )
    result.change_map("greenwood", 6, 6)
    result.player_direction = "right"
    result.home_npcs = []
    result.hidden_monsters = [wild(7, 6)] + [wild(20 + i, 20) for i in range(3)]
    return result


# {
#   責務: [wild: test・wild・encounter・進行のwildを求める]
#   処理: [1: test・wild・encounter・進行のwildを求める]
#   引数: [
#     x: X座標
#     y: Y座標
#     species: 種族
#     level: レベル
#     ai: AI
#   ]
#   戻り値: [result: test・wild・encounter・進行のwildを求めるための結果（型注釈なし）]
# }
def wild(x, y, species="ghost", level=7, ai="idle"):
    return {
        "x": x, "y": y, "ai": ai, "direction": "front", "next_move_tick": 1000,
        "spawn": {"species_id": species, "min_level": level, "max_level": level, "weight": 1},
    }


# {
#   責務: [test_contact_routes_to_matching_enemy_without_tile_overlap: 検証: contact routes to matching enemy without tile overlap]
#   処理: [1: 検証: contact routes to matching enemy without tile overlap]
#   引数: [
#     game: ゲーム
#     trigger: trigger
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("trigger", ["walk_into", "walk_near", "enemy_approach", "front_check"])
def test_contact_routes_to_matching_enemy_without_tile_overlap(game, trigger):
    target = game.hidden_monsters[0]
    original_spawn = copy.deepcopy(target["spawn"])
    if trigger == "enemy_approach":
        target.update(x=8, ai="chase")
        game.runtime.dispatch("field", "tick", now=1000)
    elif trigger == "walk_near":
        target["x"] = 8
        game.runtime.dispatch("field", "move.start", direction="right", now=1000)
    elif trigger == "walk_into":
        game.runtime.dispatch("field", "move.start", direction="right", now=1000)
    else:
        assert game.check_hidden_collision()
    assert game.mode == "battle"
    assert len(game.battle.enemies) == 1
    record = game.battle.enemies[0].record
    assert (record.species_id, record.level) == ("ghost", 7)
    assert "field_ai_weights" not in record.ai and "chase_target" not in record.ai
    assert (game.player_x, game.player_y) != (target["x"], target["y"])
    assert not any(enemy is target for enemy in game.hidden_monsters)
    assert target["spawn"] == original_spawn
    assert len(game.hidden_monsters) == 3


# {
#   責務: [test_non_front_enemy_does_not_trigger: 検証: non front enemy does not trigger]
#   処理: [1: 検証: non front enemy does not trigger]
#   引数: [
#     game: ゲーム
#     position: 座標
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("position", [(6, 7), (5, 6), (7, 7)])
def test_non_front_enemy_does_not_trigger(game, position):
    game.hidden_monsters[0].update(x=position[0], y=position[1])
    assert not game.check_hidden_collision()
    assert game.mode == "field" and game.battle is None


# {
#   責務: [test_no_party_does_not_report_start_or_consume_target: 検証: no party does not report start or consume target]
#   処理: [1: 検証: no party does not report start or consume target]
#   引数: [game: ゲーム]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_no_party_does_not_report_start_or_consume_target(game):
    game.state["current_party"] = []
    before = copy.deepcopy(game.hidden_monsters)
    assert not game.check_hidden_collision()
    assert game.hidden_monsters == before
    assert game.mode == "field" and game.battle is None


# {
#   責務: [test_password_mode_cannot_start_encounter: 検証: password mode cannot start encounter]
#   処理: [1: 検証: password mode cannot start encounter]
#   引数: [game: ゲーム]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_password_mode_cannot_start_encounter(game):
    game.mode = "password"
    target = game.hidden_monsters[0]
    assert not game.check_hidden_collision()
    assert not game.start_wild_battle(target["spawn"], target)
    assert game.battle is None and game.hidden_monsters[0] is target


# {
#   責務: [test_failed_battle_construction_keeps_field_individual: 検証: failed battle construction keeps field individual]
#   処理: [1: 検証: failed battle construction keeps field individual]
#   引数: [
#     game: ゲーム
#     failure: failure
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("failure", ["generation", "engine", "session"])
def test_failed_battle_construction_keeps_field_individual(game, failure):
    before = copy.deepcopy(game.hidden_monsters)
    patches = {
        "generation": mock.patch.object(game, "make_wild", side_effect=ValueError("test failure")),
        "engine": mock.patch("kadoka_quest.apps.game.BattleEngine", side_effect=ValueError("test failure")),
        "session": mock.patch.object(game.battle_session, "begin", side_effect=ValueError("test failure")),
    }
    with patches[failure], pytest.raises(ValueError, match="test failure"):
        game.check_hidden_collision()
    assert game.hidden_monsters == before
    assert game.mode == "field" and game.battle is None


# {
#   責務: [test_active_battle_cannot_be_replaced_and_field_actors_pause: 検証: active battle cannot be replaced and field actors pause]
#   処理: [1: 検証: active battle cannot be replaced and field actors pause]
#   引数: [game: ゲーム]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_active_battle_cannot_be_replaced_and_field_actors_pause(game):
    assert game.check_hidden_collision()
    original_battle = game.battle
    remaining = copy.deepcopy(game.hidden_monsters)
    game.hidden_monsters[0].update(x=7, y=6)
    other = game.hidden_monsters[0]
    assert not game.check_hidden_collision()
    assert not game.start_wild_battle(other["spawn"], other)
    assert game.battle is original_battle
    game.hidden_monsters = remaining
    before = copy.deepcopy(game.hidden_monsters)
    game.runtime.dispatch("field", "tick", now=5000)
    assert game.hidden_monsters == before


# {
#   責務: [test_contact_command_playback_finalize_and_return: 検証: contact command playback finalize and return]
#   処理: [1: 検証: contact command playback finalize and return]
#   引数: [
#     game: ゲーム
#     outcome: 結果
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("outcome", ["victory", "defeat", "escaped", "scouted", "enemies_fled"])
def test_contact_command_playback_finalize_and_return(game, outcome):
    target = game.hidden_monsters[0]
    survivors = game.hidden_monsters[1:]
    survivor_state = copy.deepcopy(survivors)
    game.state["revive_point"] = {"map_id": "rokuta_village", "x": 14, "y": 10, "name": "ロクター教会"}
    assert game.check_hidden_collision()
    battle = game.battle
    # Arrange a deterministic terminal round while retaining the real engine,
    # normal command routing, playback, persistence, and field-return path.
    command = "fight"
    if outcome == "victory":
        battle.enemies[0].hp = 0
    elif outcome == "defeat":
        for ally in battle.allies:
            ally.hp = 0
    elif outcome == "enemies_fled":
        battle.enemies[0].flee_rates["normal"] = 1.0
        battle.enemies[0].stats["speed"] = 100000
    else:
        command = "run" if outcome == "escaped" else "scout"
    with mock.patch.object(game.rng, "random", return_value=0.0):
        game.runtime.dispatch("battle", "execute", command=command, now=2000)
    assert battle.outcome == outcome
    assert game.battle_session.playback
    for tick in range(3000, 103000, 1000):
        game.runtime.dispatch("battle", "tick", now=tick)
        if not game.battle_session.playback:
            break
    assert game.battle_session.finalized
    assert not game.battle_session.playback
    saved_ai = copy.deepcopy([record.ai for record in game.monsters.list_records()])
    game.runtime.dispatch("battle", "tick", now=104000)
    assert [record.ai for record in game.monsters.list_records()] == saved_ai
    game.runtime.dispatch("battle", "return")
    assert game.mode == "field" and game.battle is None
    assert not any(enemy is target for enemy in game.hidden_monsters)
    assert not game.battle_session.playback and not game.battle_session.auto
    if outcome == "defeat":
        assert game.map_data["id"] == "rokuta_village"
        assert (game.player_x, game.player_y) == (14, 10)
    else:
        assert game.map_data["id"] == "greenwood"
        assert (game.player_x, game.player_y) == (6, 6)
        assert all(a is b for a, b in zip(game.hidden_monsters, survivors))
        assert game.hidden_monsters == survivor_state
    if outcome == "scouted":
        acquired = [record for record in game.monsters.list_records() if record.monster.get("source") == "scout"]
        assert [(record.species_id, record.level) for record in acquired] == [("ghost", 7)]


# {
#   責務: [test_small_remaining_population_replenishes_without_reusing_consumed_actor: 検証: small remaining population replenishes without reusing consumed actor]
#   処理: [1: 検証: small remaining population replenishes without reusing consumed actor]
#   引数: [game: ゲーム]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_small_remaining_population_replenishes_without_reusing_consumed_actor(game):
    target = game.hidden_monsters[0]
    game.hidden_monsters = [target]
    assert game.check_hidden_collision()
    with mock.patch.object(game.rng, "random", return_value=0.0):
        assert game.battle.try_run()
    game.return_to_field()
    assert len(game.hidden_monsters) >= 3
    assert all(enemy is not target for enemy in game.hidden_monsters)
    assert len({(m["x"], m["y"]) for m in game.hidden_monsters}) == len(game.hidden_monsters)


# {
#   責務: [test_consumed_actor_releases_chase_reservations: 検証: consumed actor releases chase reservations]
#   処理: [1: 検証: consumed actor releases chase reservations]
#   引数: [game: ゲーム]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_consumed_actor_releases_chase_reservations(game):
    target = game.hidden_monsters[0]
    traffic = game.hidden_enemies.traffic
    traffic.begin(1000, {id(target)})
    traffic.plan(id(target), (7, 6), (10, 6), set(), set(), 320)
    assert id(target) in traffic.plans
    assert game.check_hidden_collision()
    assert id(target) not in traffic.plans
    assert all(id(target) not in owners for owners in traffic.reserved.values())
