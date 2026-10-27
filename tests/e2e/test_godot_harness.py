"""Godot版E2E harnessが、未知の操作や到達しない画面を成功扱いにしないことを検証します。"""

# {
#   責務: [test_godot_harness: Godot版E2E harnessとe2e_driver.gdの失敗の扱いと、起動画面・入力経路の前提を検証します]
#   フィールド: []
# }
from __future__ import annotations

import pytest

from .godot_harness import GODOT, PROJECT_ROOT, GodotScenarioRunner


# {
#   責務: [test_driver_opens_main_scene_and_uses_real_input_path: driverが起動画面をproject.godotから読み、Inputの入力経路だけで操作することをソースから確認します]
#   処理: [1: driverのソースに起動画面の読込とInput.parse_input_eventがあり、ゲームの保存や移動を直接呼ばないことを確認します]
#   引数: []
#   戻り値: [result: なし（None）]
# }
def test_driver_opens_main_scene_and_uses_real_input_path():
    source = (PROJECT_ROOT / "gdscript/tests/e2e_driver.gd").read_text(encoding="utf-8")
    assert 'ProjectSettings.get_setting("application/run/main_scene")' in source
    assert "Input.parse_input_event" in source
    # 画面の操作を代わりに実行する呼出しがあると、実入力のE2Eではなくなります。
    for forbidden in ("save_current_position(", "move_player(", "start_new_game(", "continue_game(", "open_page("):
        assert forbidden not in source


# {
#   責務: [test_unknown_steps_and_unreached_scenes_fail: 未知の操作・到達しない画面・重複したlabelを、操作番号付きの失敗として報告することを確認します]
#   処理: [1: 失敗する操作だけを含むシナリオを実行し、RuntimeErrorと理由を確認します]
#   引数: [tmp_path: 実セーブと分離した一時フォルダ（Path）]
#   戻り値: [result: なし（None）]
# }
@pytest.mark.skipif(not GODOT, reason="KADOKA_GODOT_EXECUTABLEまたはGodotのPATH設定が必要です。")
def test_unknown_steps_and_unreached_scenes_fail(tmp_path):
    runner = GodotScenarioRunner(tmp_path)
    for steps, reason in (
        ([{"kind": "teleport"}], "操作0（teleport）: 未知の操作です。"),
        ([{"kind": "key", "key": "F12"}], "未対応のキーです"),
        ([{"kind": "wait_scene", "name": "FieldApplication", "max_frames": 5}], "切り替わりませんでした"),
        ([{"kind": "snapshot", "label": "a"}, {"kind": "snapshot", "label": "a"}], "操作1（snapshot）"),
    ):
        with pytest.raises(RuntimeError, match=reason):
            runner.run(steps)
    # 失敗したシナリオでも、セーブ名を入力していないため保存先は作られません。
    assert not runner.save_root.exists()
