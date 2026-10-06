"""Issue #202: Given/When/Then journeys through Player input and real stores."""
# {
#   責務: [test_field_journeys: Issue #202: Given/When/Then journeys through Player input and real stores.]
#   フィールド: []
# }

import json

import pytest

from .harness import PROJECT_ROOT


# {
#   責務: [tap: test・フィールド・journeysのtapを求める]
#   処理: [1: test・フィールド・journeysのtapを求める]
#   引数: [key: キー]
#   戻り値: [result: test・フィールド・journeysのtapを求めるための結果（型注釈なし）]
# }
def tap(key):
    return [{"kind": "key_down", "key": key}, {"kind": "key_up", "key": key},
            {"kind": "advance", "ms": 120}]


# {
#   責務: [name_input: test・フィールド・journeysの名前・入力を求める]
#   処理: [1: test・フィールド・journeysの名前・入力を求める]
#   引数: [name: 名前]
#   戻り値: [result: test・フィールド・journeysの名前・入力を求めるための結果（型注釈なし）]
# }
def name_input(name):
    return [{"kind": "click", "pos": [100, 205]}] + [
        {"kind": "key", "key": "backspace"} for _ in range(40)
    ] + [{"kind": "text", "text": name}]


# {
#   責務: [new_game: ゲームを新規作成する]
#   処理: [1: ゲームを新規作成する]
#   引数: [
#     name: 名前
#     label: 表示名
#   ]
#   戻り値: [result: ゲームを新規作成するための結果（型注釈なし）]
# }
def new_game(name, label):
    return {"kind": "launcher", "label": label, "frames": [name_input(name) + [
        {"kind": "click", "pos": [100, 265]}, {"kind": "click", "pos": [500, 175]},
    ]]}


# {
#   責務: [load_game: ゲームを読み込む]
#   処理: [1: ゲームを読み込む]
#   引数: [
#     index: 位置番号
#     label: 表示名
#   ]
#   戻り値: [result: ゲームを読み込むための結果（型注釈なし）]
# }
def load_game(index, label):
    return {"kind": "launcher", "label": label, "frames": [[
        {"kind": "click", "pos": [100, 405 + index * 40]},
        {"kind": "click", "pos": [100, 322]}, {"kind": "click", "pos": [500, 175]},
    ]]}


# {
#   責務: [snapshot: test・フィールド・journeysを状態を複製する]
#   処理: [1: test・フィールド・journeysを状態を複製する]
#   引数: [label: 表示名]
#   戻り値: [result: test・フィールド・journeysを状態を複製するための結果（型注釈なし）]
# }
def snapshot(label):
    return {"kind": "snapshot", "label": label}


# {
#   責務: [xy: test・フィールド・journeysのxyを求める]
#   処理: [1: test・フィールド・journeysのxyを求める]
#   引数: [point: 地点]
#   戻り値: [result: test・フィールド・journeysのxyを求めるための結果（型注釈なし）]
# }
def xy(point):
    return {key: point["player"][key] for key in ("x", "y")}


# {
#   責務: [species: test・フィールド・journeysの種族を求める]
#   処理: [1: test・フィールド・journeysの種族を求める]
#   引数: [point: 地点]
#   戻り値: [result: test・フィールド・journeysの種族を求めるための結果（型注釈なし）]
# }
def species(point):
    return {record["monster"]["species_id"] for record in point["monsters"]}


# {
#   責務: [test_player_new_game_and_reload: KQ-P01/P02: Given empty names; When Player creates/starts/reloads; Then town/starters/UI persist.]
#   処理: [1: KQ-P01/P02: Given empty names; When Player creates/starts/reloads; Then town/starters/UI persist.]
#   引数: [scenario_runner: scenario・runner]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_player_new_game_and_reload(scenario_runner):
    """KQ-P01/P02: Given empty names; When Player creates/starts/reloads; Then town/starters/UI persist."""
    steps = [new_game("journey_01", "started"), {"kind": "render", "label": "displayed"},
             {"kind": "reload", "label": "loaded"}, {"kind": "render"}]
    reports = [scenario_runner.run(steps, seed=11) for _ in range(2)]
    assert reports[0]["checkpoints"] == reports[1]["checkpoints"]
    points = reports[0]["checkpoints"]
    started, loaded = points["started"], points["loaded"]
    assert started["mode"] == "field" and started["map_id"] == "starting_town"
    assert xy(started) == {"x": 18, "y": 14}
    assert started["active_save"] == "journey_01"
    assert species(started) == {"hero", "ball_slime"}
    assert len(started["party_ids"]) == 2
    assert loaded["party_ids"] == started["party_ids"]
    assert loaded["monsters"] == started["monsters"]
    assert loaded["state"] == started["state"]
    assert started["saved_files"]["state.json"]["player"] == xy(started)
    assert started["saved_files"]["meta.json"]["name"] == "journey_01"
    assert set(started["launcher_runs"][0]["controls"]) == {
        "新規作成", "別名保存", "選択データを読み込む", "ゲームを開始", "終了",
    }
    assert "はじまりの街" in points["displayed"]["render"]["texts"]
    assert not any("エディタ" in text or "開発用" in text for text in points["displayed"]["render"]["texts"])
    assert points["displayed"]["render"]["player_visual"] == [18.0, 14.0]


# {
#   責務: [test_named_load_restores_selected_profile_without_changing_other: KQ-P03: Given distinct A/B; When launcher selects A and reloads; Then all A state and untouched B.]
#   処理: [1: KQ-P03: Given distinct A/B; When launcher selects A and reloads; Then all A state and untouched B.]
#   引数: [scenario_runner: scenario・runner]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_named_load_restores_selected_profile_without_changing_other(scenario_runner):
    """KQ-P03: Given distinct A/B; When launcher selects A and reloads; Then all A state and untouched B."""
    change_map = {"kind": "command", "target": "field", "action": "map.change",
                  "payload": {"map_id": "ghost_home", "x": 2, "y": 9}}
    steps = [new_game("slot_a", "a_start"), change_map, *tap("t"), *tap("f7"), snapshot("a_saved"),
             new_game("slot_b", "b_start"), *tap("down"), snapshot("b_saved"),
             load_game(1, "a_loaded"), {"kind": "reload", "label": "a_reloaded"}]
    points = scenario_runner.run(steps, seed=31)["checkpoints"]
    before, after = points["a_saved"], points["a_reloaded"]
    assert xy(before) == xy(after) == {"x": 2, "y": 9}
    assert before["map_id"] == after["map_id"] == "ghost_home"
    assert after["active_save"] == "slot_a"
    assert after["state"] == before["state"]
    assert after["monsters"] == before["monsters"]  # includes individual IDs and AI
    assert after["saved_files"] == before["saved_files"]  # includes items and party presets
    assert points["b_saved"]["state"]["player"] == {"x": 18, "y": 15}
    assert points["b_saved"]["map_id"] == "starting_town"
    assert points["b_saved"]["party_ids"] != before["party_ids"]
    assert after["saved_profiles"]["slot_b"] == points["b_saved"]["saved_profiles"]["slot_b"]
    assert after["launcher_runs"][-1]["launched_name"] == "slot_a"


# {
#   責務: [test_save_as_copies_owned_data_and_keeps_source_independent: KQ-P04: Given saved A with AI/items/preset; When UI copies to B; Then IDs persist and later B edits spare A.]
#   処理: [1: KQ-P04: Given saved A with AI/items/preset; When UI copies to B; Then IDs persist and later B edits spare A.]
#   引数: [scenario_runner: scenario・runner]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_save_as_copies_owned_data_and_keeps_source_independent(scenario_runner):
    """KQ-P04: Given saved A with AI/items/preset; When UI copies to B; Then IDs persist and later B edits spare A."""
    copy = {"kind": "launcher", "label": "copied", "frames": [name_input("copy_b") + [
        {"kind": "click", "pos": [250, 265]}, {"kind": "click", "pos": [500, 175]},
    ]]}
    gain = {"kind": "command", "target": "field", "action": "item.gain", "payload": {"item_id": "orange"}}
    points = scenario_runner.run([
        new_game("copy_a", "a_start"), *tap("right"), *tap("t"), *tap("f7"), gain, snapshot("a_saved"),
        copy, *tap("down"), gain, {"kind": "reload", "label": "b_reloaded"},
    ], seed=41)["checkpoints"]
    source, copied, edited = points["a_saved"], points["copied"], points["b_reloaded"]
    assert copied["active_save"] == "copy_b"
    assert copied["state"] == source["state"]
    assert copied["monsters"] == source["monsters"]
    for path, value in source["saved_files"].items():
        if path != "meta.json":
            assert copied["saved_files"][path] == value
    assert copied["saved_files"]["meta.json"]["copied_from"] == "copy_a"
    assert edited["saved_profiles"]["copy_a"] == source["saved_profiles"]["copy_a"]
    assert xy(edited) == {"x": 19, "y": 15}
    assert edited["state"]["inventory"]["orange"] == 5
    assert source["state"]["inventory"]["orange"] == 4
    assert edited["party_ids"] == source["party_ids"]


# {
#   責務: [test_walk_and_visual_position_survive_reload: KQ-P05: Given clear town path; When right input/time/reload; Then grid, visual and saved integer coords agree.]
#   処理: [1: KQ-P05: Given clear town path; When right input/time/reload; Then grid, visual and saved integer coords agree.]
#   引数: [scenario_runner: scenario・runner]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_walk_and_visual_position_survive_reload(scenario_runner):
    """KQ-P05: Given clear town path; When right input/time/reload; Then grid, visual and saved integer coords agree."""
    points = scenario_runner.run([
        *tap("right"), {"kind": "render", "label": "walked"},
        {"kind": "reload"}, {"kind": "render", "label": "loaded"},
    ])["checkpoints"]
    assert xy(points["walked"]) == xy(points["loaded"]) == {"x": 19, "y": 14}
    assert points["walked"]["player"]["direction"] == "right"
    assert points["walked"]["render"]["player_visual"] == [19.0, 14.0]
    assert {"species_id": "hero", "pose": "field_right", "loaded": True} in points["walked"]["render"]["images"]
    assert points["loaded"]["render"]["player_visual"] == [19.0, 14.0]
    assert points["walked"]["saved_files"]["state.json"]["player"] == {"x": 19, "y": 14}


# {
#   責務: [test_collision_does_not_overlap: KQ-P06: Given each obstacle ahead; When right input; Then no overlapping tile (wild contact starts battle).]
#   処理: [1: KQ-P06: Given each obstacle ahead; When right input; Then no overlapping tile (wild contact starts battle).]
#   引数: [
#     scenario_runner: scenario・runner
#     saved_start: saved・start
#     field_data_fixture: フィールド・データ・fixture
#     obstacle: obstacle
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("obstacle", ["wall", "rock", "sign", "fixed_mob", "wild_mob"])
def test_collision_does_not_overlap(scenario_runner, saved_start, field_data_fixture, obstacle):
    """KQ-P06: Given each obstacle ahead; When right input; Then no overlapping tile (wild contact starts battle)."""
    report = scenario_runner.run([*tap("right"), snapshot("blocked")],
                                 data_dir=field_data_fixture(obstacle=obstacle),
                                 save_fixture=saved_start("e2e_field", 2, 3))
    initial, blocked = report["checkpoints"]["initial"], report["checkpoints"]["blocked"]
    assert xy(initial) == xy(blocked) == {"x": 2, "y": 3}
    assert blocked["saved_files"]["state.json"]["player"] == {"x": 2, "y": 3}
    if obstacle == "wild_mob":
        assert [(mob["x"], mob["y"]) for mob in initial["wild_mobs"]] == [(3, 3)]
        assert blocked["mode"] == "battle"
    else:
        assert blocked["mode"] == "field"
        assert "移動できません" in blocked["status"] or "通れません" in blocked["status"]


# {
#   責務: [test_hold_repeat_stops_when_released: KQ-P07: Given path/fixed time; When hold past repeat delays then release; Then repeats cease.]
#   処理: [1: KQ-P07: Given path/fixed time; When hold past repeat delays then release; Then repeats cease.]
#   引数: [scenario_runner: scenario・runner]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_hold_repeat_stops_when_released(scenario_runner):
    """KQ-P07: Given path/fixed time; When hold past repeat delays then release; Then repeats cease."""
    points = scenario_runner.run([
        {"kind": "key_down", "key": "right", "label": "first"},
        {"kind": "advance", "ms": 179, "frame_ms": 1, "label": "waiting"},
        {"kind": "advance", "ms": 1, "label": "repeated"},
        {"kind": "advance", "ms": 90, "frame_ms": 10, "label": "again"},
        {"kind": "key_up", "key": "right"},
        {"kind": "advance", "ms": 500, "label": "stopped"},
    ])["checkpoints"]
    assert [points[label]["player"]["x"] for label in ("first", "waiting", "repeated", "again", "stopped")] == [
        19, 19, 20, 21, 21,
    ]


# {
#   責務: [test_canonical_step_transition_and_reload: KQ-P08: Given real town edge; When walk onto overlapping transition; Then enter exact target once and reload.]
#   処理: [1: KQ-P08: Given real town edge; When walk onto overlapping transition; Then enter exact target once and reload.]
#   引数: [
#     scenario_runner: scenario・runner
#     saved_start: saved・start
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_canonical_step_transition_and_reload(scenario_runner, saved_start):
    """KQ-P08: Given real town edge; When walk onto overlapping transition; Then enter exact target once and reload."""
    points = scenario_runner.run([
        *tap("right"), snapshot("entered"), {"kind": "reload", "label": "loaded"},
    ], save_fixture=saved_start("starting_town", 34, 14))["checkpoints"]
    for label in ("entered", "loaded"):
        assert points[label]["map_id"] == "greenwood"
        assert xy(points[label]) == {"x": 1, "y": 6}
        assert points[label]["saved_files"]["state.json"]["map_id"] == "greenwood"
        assert points[label]["saved_files"]["state.json"]["player"] == {"x": 1, "y": 6}


# {
#   責務: [test_interact_transition_is_not_a_step_transition: KQ-P09: Given passable interact point; When walk across/back then Space; Then only interaction transitions.]
#   処理: [1: KQ-P09: Given passable interact point; When walk across/back then Space; Then only interaction transitions.]
#   引数: [
#     scenario_runner: scenario・runner
#     saved_start: saved・start
#     field_data_fixture: フィールド・データ・fixture
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_interact_transition_is_not_a_step_transition(scenario_runner, saved_start, field_data_fixture):
    """KQ-P09: Given passable interact point; When walk across/back then Space; Then only interaction transitions."""
    points = scenario_runner.run([
        *tap("right"), snapshot("crossed"), *tap("left"), *tap("space"),
        {"kind": "reload", "label": "loaded"},
    ], data_dir=field_data_fixture(door="interact"),
       save_fixture=saved_start("e2e_field", 2, 3))["checkpoints"]
    assert points["crossed"]["map_id"] == "e2e_field" and xy(points["crossed"]) == {"x": 3, "y": 3}
    assert points["loaded"]["map_id"] == "starting_town" and xy(points["loaded"]) == {"x": 18, "y": 14}
    assert points["loaded"]["saved_files"]["state.json"]["map_id"] == "starting_town"


# {
#   責務: [test_fresh_forest_rock_blocks_and_enters_ghost_home: KQ-P09: Given actual fresh-forest entrance; When pass beside, attempt rock, then investigate; Then home/reload.]
#   処理: [1: KQ-P09: Given actual fresh-forest entrance; When pass beside, attempt rock, then investigate; Then home/reload.]
#   引数: [
#     scenario_runner: scenario・runner
#     saved_start: saved・start
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_fresh_forest_rock_blocks_and_enters_ghost_home(scenario_runner, saved_start):
    """KQ-P09: Given actual fresh-forest entrance; When pass beside, attempt rock, then investigate; Then home/reload."""
    points = scenario_runner.run([
        *tap("right"), snapshot("passed"), *tap("left"), *tap("down"), snapshot("blocked"),
        *tap("space"), snapshot("entered"), {"kind": "reload", "label": "loaded"},
    ], save_fixture=saved_start("fresh_forest", 22, 26))["checkpoints"]
    assert points["passed"]["map_id"] == "fresh_forest" and xy(points["passed"]) == {"x": 23, "y": 26}
    assert points["blocked"]["map_id"] == "fresh_forest" and xy(points["blocked"]) == {"x": 22, "y": 26}
    for label in ("entered", "loaded"):
        assert points[label]["map_id"] == "ghost_home" and xy(points[label]) == {"x": 2, "y": 9}
        assert points[label]["saved_files"]["state.json"]["map_id"] == "ghost_home"


# {
#   責務: [test_maru_dialogue_deck_and_facing_pause: KQ-P10: Given Maru in front; When talk across movement periods; Then deck cycles and talking NPC stays.]
#   処理: [1: KQ-P10: Given Maru in front; When talk across movement periods; Then deck cycles and talking NPC stays.]
#   引数: [
#     scenario_runner: scenario・runner
#     saved_start: saved・start
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_maru_dialogue_deck_and_facing_pause(scenario_runner, saved_start):
    """KQ-P10: Given Maru in front; When talk across movement periods; Then deck cycles and talking NPC stays."""
    steps = tap("up")  # blocked by Maru: face the real NPC without moving into it
    for index in range(6):
        steps.extend(tap("space"))
        steps.append({"kind": "advance", "ms": 900, "label": f"talk_{index}"})
    points = scenario_runner.run(steps, save_fixture=saved_start("ghost_home", 10, 8))["checkpoints"]
    lines = []
    for index in range(6):
        point = points[f"talk_{index}"]
        maru = next(mob for mob in point["fixed_mobs"] if mob["id"] == "maru_home")
        assert (maru["x"], maru["y"], maru["direction"]) == (10, 7, "front")
        assert xy(point) == {"x": 10, "y": 8}
        lines.append(point["status"].split("『", 1)[1].removesuffix("』"))
    world = json.loads((PROJECT_ROOT / "data/maps/ghost_home/map.json").read_text(encoding="utf-8"))
    deck = next(mob["dialogue"] for mob in world["fixed_mobs"] if mob["id"] == "maru_home")
    assert set(lines[:5]) == set(deck) and len(set(lines[:5])) == 5
    assert lines[5] in deck and lines[5] != lines[4]


# {
#   責務: [test_spring_virtual_keyboard_acquisition_persists: KQ-P11: Given no ghosts at the actual spring; When investigate/type/submit/reload; Then ownership/flag/NPCs.]
#   処理: [1: KQ-P11: Given no ghosts at the actual spring; When investigate/type/submit/reload; Then ownership/flag/NPCs.]
#   引数: [
#     scenario_runner: scenario・runner
#     saved_start: saved・start
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_spring_virtual_keyboard_acquisition_persists(scenario_runner, saved_start):
    """KQ-P11: Given no ghosts at the actual spring; When investigate/type/submit/reload; Then ownership/flag/NPCs."""
    steps = [*tap("space"), {"kind": "render", "label": "opened"}]
    steps.extend({"kind": "password_click", "value": character} for character in "へいわなすみか")
    steps.extend([snapshot("typed"), {"kind": "password_click", "value": "submit", "label": "acquired"},
                  {"kind": "reload", "label": "loaded"}])
    reports = [scenario_runner.run(steps, seed=17, save_fixture=saved_start("ghost_home", 17, 8)) for _ in range(2)]
    assert reports[0]["checkpoints"] == reports[1]["checkpoints"]
    points = reports[0]["checkpoints"]
    assert species(points["initial"]) == {"hero", "ball_slime"}
    assert points["opened"]["mode"] == "password"
    assert "7文字のあいことば" in points["opened"]["render"]["texts"]
    assert points["typed"]["password"]["input"] == "へいわなすみか"
    for label in ("acquired", "loaded"):
        assert points[label]["mode"] == "field"
        assert species(points[label]) == {"hero", "ball_slime", "maru", "kadoka"}
        assert points[label]["saved_files"]["state.json"]["flags"]["ghost_entrance_open"] is True
        assert {mob["id"] for mob in points[label]["fixed_mobs"]} == {"maru_home", "kadoka_home"}
    assert points["loaded"]["monsters"] == points["acquired"]["monsters"]
    for record in points["loaded"]["monsters"]:
        folder = "monsters/" + record["monster"]["id"]
        assert points["loaded"]["saved_files"][folder + "/monster.json"] == record["monster"]
        assert points["loaded"]["saved_files"][folder + "/ai.json"] == record["ai"]


# {
#   責務: [test_wrong_password_length_erase_and_cancel: KQ-P12: Given spring input; When eight keys/wrong submit/erase/cancel; Then bounded input, no acquisition.]
#   処理: [1: KQ-P12: Given spring input; When eight keys/wrong submit/erase/cancel; Then bounded input, no acquisition.]
#   引数: [
#     scenario_runner: scenario・runner
#     saved_start: saved・start
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_wrong_password_length_erase_and_cancel(scenario_runner, saved_start):
    """KQ-P12: Given spring input; When eight keys/wrong submit/erase/cancel; Then bounded input, no acquisition."""
    points = scenario_runner.run([
        *tap("space"), {"kind": "text", "text": "あいうえおかきく", "label": "bounded"},
        {"kind": "key_down", "key": "return", "label": "wrong"},
        {"kind": "password_click", "value": "backspace", "label": "erased"},
        {"kind": "key_down", "key": "escape", "label": "cancelled"},
        *tap("space"), {"kind": "password_click", "value": "cancel", "label": "mouse_cancelled"},
        {"kind": "reload", "label": "loaded"},
    ], save_fixture=saved_start("ghost_home", 17, 8))["checkpoints"]
    assert points["bounded"]["password"]["input"] == "あいうえおかき"
    assert points["wrong"]["mode"] == "password" and "違います" in points["wrong"]["password"]["message"]
    assert points["erased"]["password"]["input"] == "あいうえおか"
    for label in ("wrong", "cancelled", "mouse_cancelled", "loaded"):
        assert species(points[label]) == {"hero", "ball_slime"}
        assert points[label]["state"]["flags"]["ghost_entrance_open"] is False
    for label in ("cancelled", "mouse_cancelled"):
        assert points[label]["mode"] == "field" and points[label]["password"]["input"] == ""
