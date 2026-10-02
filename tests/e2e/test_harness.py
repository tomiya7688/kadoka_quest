"""Issue #201 harness calibration; catalog user flows remain #202--#204."""

from pathlib import Path

import pytest

from .harness import PROJECT_ROOT


def test_headless_keyboard_clock_and_store_reload(scenario_runner):
    # Given canonical data and an empty isolated save. When real KEYDOWN/UP
    # events and exact frame time are fed. Then held movement and Store reload
    # agree; observation does not substitute for movement/save logic.
    report = scenario_runner.run([
        {"kind": "key_down", "key": "right", "label": "pressed"},
        {"kind": "advance", "ms": 200, "frame_ms": 20, "label": "held"},
        {"kind": "key_up", "key": "right"},
        {"kind": "advance", "ms": 500, "label": "released"},
        {"kind": "reload", "label": "loaded"},
    ], start_ms=123)
    points = report["checkpoints"]
    assert report["composition_root"] == "kadoka_quest.apps.game.KadokaQuest"
    assert report["input_adapter"].endswith("RuntimeInputAdapter")
    assert report["sdl_driver"] == "dummy"
    assert Path(report["data_root"]).resolve() == PROJECT_ROOT / "data"
    assert points["initial"]["player"] == {"x": 18, "y": 14, "direction": "front"}
    assert points["pressed"]["player"]["x"] == 19
    assert points["held"]["player"]["x"] == 20
    assert points["released"]["player"]["x"] == 20
    assert points["loaded"]["player"]["x"] == 20
    assert points["final"]["clock_ms"] == 823
    assert points["final"]["party_ids"] == points["initial"]["party_ids"]
    assert {record["monster"]["species_id"] for record in points["initial"]["monsters"]} == {"hero", "ball_slime"}
    saved = points["released"]["saved_files"]["state.json"]
    assert saved["player"] == {"x": 20, "y": 14}
    assert saved["current_party"] == points["loaded"]["party_ids"]


def test_same_seed_actions_repeat_identical_observations(scenario_runner):
    steps = [
        {"kind": "command", "target": "field", "action": "map.change",
         "payload": {"map_id": "greenwood", "x": 6, "y": 5}, "label": "spawned"},
        {"kind": "advance", "ms": 160, "frame_ms": 20, "label": "ticked"},
        {"kind": "key_down", "key": "f7", "label": "preset"},
        {"kind": "reload", "label": "loaded"},
        {"kind": "key_down", "key": "f7", "label": "second_preset"},
    ]
    reports = [scenario_runner.run(steps, seed=29, start_ms=4321) for _ in range(3)]
    assert len({report["paths"]["save"] for report in reports}) == 3
    assert all(report["checkpoints"] == reports[0]["checkpoints"] for report in reports[1:])
    points = reports[0]["checkpoints"]
    assert points["spawned"]["wild_mobs"]
    assert points["spawned"]["map_id"] == "greenwood"
    presets = [value for path, value in points["final"]["saved_files"].items()
               if path.startswith("parties/")]
    assert len(presets) == 2
    assert {preset["name"] for preset in presets} == {"フィールド編成_20000101_000004"}
    assert points["preset"]["saved_files"]["state.json"]["map_id"] == "greenwood"


def test_explicit_different_seed_changes_production_wild_spawn(scenario_runner):
    steps = [{"kind": "command", "target": "field", "action": "map.change",
              "payload": {"map_id": "greenwood", "x": 6, "y": 5}}]
    first = scenario_runner.run(steps, seed=7)
    second = scenario_runner.run(steps, seed=19)
    assert first["seed"] == 7
    assert second["seed"] == 19
    first_mobs = first["checkpoints"]["final"]["wild_mobs"]
    second_mobs = second["checkpoints"]["final"]["wild_mobs"]
    assert first_mobs and second_mobs
    assert first_mobs != second_mobs


def test_battle_input_and_playback_use_the_same_clock(scenario_runner):
    # Calibrate battle driving/observation through production commands. Actual
    # encounter/victory/defeat catalog scenarios are still Issue #203.
    steps = [
        {"kind": "command", "target": "battle", "action": "start.wild",
         "payload": {"spawn": {"species_id": "slime", "level_min": 1, "level_max": 1},
                     "fixed_mob_id": ""}, "label": "battle"},
        {"kind": "key_down", "key": "a", "label": "auto"},
        {"kind": "advance", "ms": 600, "frame_ms": 20, "label": "acted"},
        {"kind": "advance", "ms": 200, "frame_ms": 20, "label": "playback"},
    ]
    reports = [scenario_runner.run(steps, seed=53) for _ in range(2)]
    assert reports[0]["checkpoints"] == reports[1]["checkpoints"]
    points = reports[0]["checkpoints"]
    assert points["battle"]["mode"] == "battle"
    assert points["battle"]["battle"]["enemies"][0]["monster"]["species_id"] == "slime"
    assert points["auto"]["battle"]["auto"]
    assert points["acted"]["clock_ms"] == 600
    assert points["acted"]["battle"]["round_number"] > points["battle"]["battle"]["round_number"]
    assert points["acted"]["battle"]["playback"]
    assert points["playback"]["battle"]["visible_log_count"] > points["acted"]["battle"]["visible_log_count"]


def test_inherited_user_paths_are_not_touched(scenario_runner, tmp_path, monkeypatch):
    sentinels = {}
    for variable in ("KADOKA_SAVE_DIR", "KADOKA_SAVEDATA_ROOT", "KADOKA_IMPORT_DIR"):
        user_dir = tmp_path / "pretend-user-data" / variable
        user_dir.mkdir(parents=True)
        sentinel = user_dir / "state.json"
        sentinel.write_text('{"do_not_change": "利用者セーブ"}', encoding="utf-8")
        sentinels[sentinel] = sentinel.read_bytes()
        monkeypatch.setenv(variable, str(user_dir))
    report = scenario_runner.run([
        {"kind": "launcher", "frames": [[{"kind": "click", "pos": [500, 175]}]]},
        {"kind": "key_down", "key": "right"},
    ])
    for path, content in sentinels.items():
        assert path.read_bytes() == content
        assert list(path.parent.iterdir()) == [path]
    for path in report["paths"].values():
        assert Path(path).is_relative_to(scenario_runner.base_dir)
    assert "state.json" in report["checkpoints"]["final"]["saved_files"]


@pytest.mark.parametrize("step, message", [
    ({"kind": "advance", "ms": -1}, "ms must be a nonnegative integer"),
    ({"kind": "advance", "ms": 20, "frame_ms": 0}, "frame_ms must be positive"),
    ({"kind": "command", "target": "field", "action": "tick", "payload": {"now": 99}},
     "command now must match the scenario clock"),
    ({"kind": "command", "target": "field", "action": "not-a-real-action"}, "not-a-real-action"),
    ({"kind": "command", "target": "manager", "action": "open"}, "multi-app E2E driver"),
])
def test_invalid_steps_fail_with_context(scenario_runner, step, message):
    with pytest.raises(RuntimeError) as raised:
        scenario_runner.run([{**step, "label": "bad-action"}])
    assert "Step 0 (bad-action) failed" in str(raised.value)
    assert message in str(raised.value)


def test_save_fixture_is_copied_not_changed(scenario_runner):
    first = scenario_runner.run([{"kind": "key_down", "key": "right"}])
    fixture = Path(first["paths"]["save"])
    before = {path.relative_to(fixture): path.read_bytes() for path in fixture.rglob("*.json")}
    second = scenario_runner.run([
        {"kind": "key_down", "key": "right"},
        {"kind": "command", "target": "password", "action": "open"},
        {"kind": "text", "text": "へいわなすみか"},
        {"kind": "key_down", "key": "return"},
        {"kind": "reload"},
    ], save_fixture=fixture)
    assert second["checkpoints"]["initial"]["player"]["x"] == 19
    assert second["checkpoints"]["final"]["player"]["x"] == 20
    assert fixture != Path(second["paths"]["save"])
    assert len(second["checkpoints"]["final"]["monsters"]) == 4
    assert {record["monster"]["species_id"] for record in second["checkpoints"]["final"]["monsters"]} == {
        "hero", "ball_slime", "maru", "kadoka",
    }
    assert {path.relative_to(fixture): path.read_bytes() for path in fixture.rglob("*.json")} == before
