"""Godot版のタイトル画面からの起動・新規開始・保存・再起動・セーブ選択を、実入力と実プロセスの再起動で検証します。"""
# {
#   責務: [test_godot_title_journeys: E2EカタログKQ-G01〜G04のGiven/When/Thenを、本番の起動画面へ送る実入力と、同じ専用保存先でのGodot再起動で検証します]
#   フィールド: [
#     SAVE_IN_MENU: フィールドのメニューを開いて「冒険を保存する」を選ぶ操作列（list[dict]）
#   ]
# }
from __future__ import annotations

import pytest

from .godot_harness import GODOT, GodotScenarioRunner

pytestmark = pytest.mark.skipif(not GODOT, reason="KADOKA_GODOT_EXECUTABLEまたはGodotのPATH設定が必要です。")

# メニューの先頭は「なかま・パーティ」で、その次が「冒険を保存する」です。
SAVE_IN_MENU = [{"kind": "key", "key": "ESCAPE"}, {"kind": "key", "key": "DOWN"}, {"kind": "key", "key": "ENTER"}]


# {
#   責務: [new_game_steps: タイトル画面で「はじめから」を選び、セーブ名を入力してフィールドへ入る操作列を作ります]
#   処理: [1: はじめからへのフォーカス移動・決定・セーブ名入力・決定・フィールドへの切替待ちを並べます]
#   引数: [
#     name: 入力するセーブ名（str）
#     saves_exist: 保存済みのセーブがあり、最初のフォーカスが「つづきから」にあるか（bool）
#   ]
#   戻り値: [result: e2e_driver.gdへ渡す操作の一覧（list[dict]）]
# }
def new_game_steps(name: str, *, saves_exist: bool) -> list[dict]:
    # セーブがある場合は最初の選択が「つづきから」なので、一つ下の「はじめから」へ移ります。
    moves = [{"kind": "key", "key": "DOWN"}] if saves_exist else []
    return [*moves, {"kind": "key", "key": "ENTER"}, {"kind": "text", "value": name},
            {"kind": "key", "key": "ENTER"}, {"kind": "wait_scene", "name": "FieldApplication"}]


# {
#   責務: [test_godot_launch_without_saves_offers_only_new_game: KQ-G01 セーブがない起動で、タイトル画面が「はじめから」だけを選べる状態になることを確認します]
#   処理: [
#     1: Given 空の専用保存先、When 本番の起動画面を開き、Enterでセーブ名入力へ進んでEscで戻ります
#     2: Then つづきからが無効ではじめからに選択があり、Escで最初の枠へ戻り、保存先を作らないことを確認します
#   ]
#   引数: [tmp_path: 実セーブと分離した一時フォルダ（Path）]
#   戻り値: [result: なし（None）]
# }
def test_godot_launch_without_saves_offers_only_new_game(tmp_path):
    runner = GodotScenarioRunner(tmp_path)
    checkpoints = runner.run([
        {"kind": "key", "key": "ESCAPE"},
        {"kind": "snapshot", "label": "home_escape"},
        {"kind": "key", "key": "ENTER"},
        {"kind": "snapshot", "label": "new_page"},
        {"kind": "key", "key": "ESCAPE"},
    ])
    initial = checkpoints["initial"]
    assert initial["scene"] == "TitleApplication"
    assert initial["title"] == {"page": "home", "message": initial["title"]["message"],
                                "continue_disabled": True, "profiles": []}
    assert initial["focus"] == "Button:はじめから"
    # 最初の枠のEscは何も切り替えず、はじめからの決定でセーブ名入力へ進みます。
    assert checkpoints["home_escape"]["title"]["page"] == "home"
    assert checkpoints["new_page"]["title"]["page"] == "new"
    assert checkpoints["new_page"]["focus"] == "LineEdit:"
    assert checkpoints["final"]["title"]["page"] == "home"
    assert checkpoints["final"]["focus"] == "Button:はじめから"
    assert not runner.save_root.exists()


# {
#   責務: [test_godot_new_game_save_and_restart_resumes_position: KQ-G02 新しいセーブ名で始めて移動・保存し、再起動後のつづきからで同じ位置へ戻ることを確認します]
#   処理: [
#     1: Given 空の専用保存先、When はじめからで「冒険A」を始め、右へ長押しして移動し、メニューから保存します
#     2: Then state.jsonが移動後の地図・座標・向きになります
#     3: When Godotを再起動し、つづきからで冒険Aを選びます。Then 保存した地図・座標・向きでフィールドが始まります
#   ]
#   引数: [tmp_path: 実セーブと分離した一時フォルダ（Path）]
#   戻り値: [result: なし（None）]
# }
def test_godot_new_game_save_and_restart_resumes_position(tmp_path):
    runner = GodotScenarioRunner(tmp_path)
    first = runner.run([
        *new_game_steps("冒険A", saves_exist=False),
        {"kind": "snapshot", "label": "started"},
        {"kind": "hold", "key": "RIGHT", "frames": 20},
        {"kind": "frames", "count": 30},
        *SAVE_IN_MENU,
    ])
    started, saved = first["started"]["field"], first["final"]["field"]
    assert started["profile"] == "冒険A" and started["map_id"] == "starting_town"
    assert saved["x"] != started["x"] and saved["direction"] == "right"
    assert saved["status"] == "保存しました: 冒険A"
    state = runner.saved_states()["冒険A"]
    assert (state["map_id"], state["player"]["x"], state["player"]["y"], state["player"]["direction"]) == (
        saved["map_id"], saved["x"], saved["y"], saved["direction"])
    # 同じ保存先で新しいGodotプロセスを起動し、タイトル画面から再開します。
    second = runner.run([
        {"kind": "key", "key": "ENTER"},
        {"kind": "snapshot", "label": "profiles"},
        {"kind": "key", "key": "ENTER"},
        {"kind": "wait_scene", "name": "FieldApplication"},
    ])
    assert second["initial"]["title"]["profiles"] == ["冒険A"]
    assert second["initial"]["focus"] == "Button:つづきから"
    assert second["profiles"]["focus"] == "ItemList:冒険A"
    resumed = second["final"]["field"]
    assert (resumed["profile"], resumed["map_id"], resumed["x"], resumed["y"], resumed["direction"]) == (
        "冒険A", saved["map_id"], saved["x"], saved["y"], saved["direction"])


# {
#   責務: [test_godot_continue_selects_one_of_several_saves: KQ-G03 位置の違う二つのセーブから一つを選んで再開し、どちらのセーブも変更しないことを確認します]
#   処理: [
#     1: Given 冒険2をはじめの位置で、冒険10を右へ移動した位置で保存します
#     2: When 再起動してつづきからの一覧で二番目を選びます
#     3: Then 一覧は冒険2・冒険10の自然順で、冒険10の位置から始まり、保存先のファイルは一つも変わりません
#   ]
#   引数: [tmp_path: 実セーブと分離した一時フォルダ（Path）]
#   戻り値: [result: なし（None）]
# }
def test_godot_continue_selects_one_of_several_saves(tmp_path):
    runner = GodotScenarioRunner(tmp_path)
    near = runner.run([*new_game_steps("冒険2", saves_exist=False), *SAVE_IN_MENU])["final"]["field"]
    far = runner.run([
        *new_game_steps("冒険10", saves_exist=True),
        {"kind": "hold", "key": "RIGHT", "frames": 20},
        {"kind": "frames", "count": 30},
        *SAVE_IN_MENU,
    ])["final"]["field"]
    assert (near["x"], near["y"]) != (far["x"], far["y"])
    before = runner.saved_files()
    loaded = runner.run([
        {"kind": "key", "key": "ENTER"},
        {"kind": "key", "key": "DOWN"},
        {"kind": "snapshot", "label": "selected"},
        {"kind": "key", "key": "ENTER"},
        {"kind": "wait_scene", "name": "FieldApplication"},
    ])
    assert loaded["initial"]["title"]["profiles"] == ["冒険2", "冒険10"]
    assert loaded["selected"]["focus"] == "ItemList:冒険10"
    resumed = loaded["final"]["field"]
    assert (resumed["profile"], resumed["x"], resumed["y"], resumed["direction"]) == (
        "冒険10", far["x"], far["y"], far["direction"])
    # 再開は読み込みだけで、選んだセーブも選ばなかったセーブも書き換えません。
    assert runner.saved_files() == before


# {
#   責務: [test_godot_new_game_rejects_existing_save_name: KQ-G04 既存と同じセーブ名での新規開始を、タイトル画面に留まったまま拒否することを確認します]
#   処理: [
#     1: Given 冒険Aを保存済みの専用保存先、When 再起動後にはじめからで同じ「冒険A」を入力して決定します
#     2: Then タイトル画面のセーブ名入力に留まり、同じ名前の理由を表示し、Escで最初の枠へ戻り、保存先は変わりません
#   ]
#   引数: [tmp_path: 実セーブと分離した一時フォルダ（Path）]
#   戻り値: [result: なし（None）]
# }
def test_godot_new_game_rejects_existing_save_name(tmp_path):
    runner = GodotScenarioRunner(tmp_path)
    runner.run([*new_game_steps("冒険A", saves_exist=False), *SAVE_IN_MENU])
    before = runner.saved_files()
    checkpoints = runner.run([
        {"kind": "key", "key": "DOWN"},
        {"kind": "key", "key": "ENTER"},
        {"kind": "text", "value": "冒険A"},
        {"kind": "key", "key": "ENTER"},
        {"kind": "frames", "count": 10},
        {"kind": "snapshot", "label": "rejected"},
        {"kind": "key", "key": "ESCAPE"},
    ])
    rejected = checkpoints["rejected"]
    assert rejected["scene"] == "TitleApplication"
    assert rejected["title"]["page"] == "new"
    assert "同じ名前" in rejected["title"]["message"]
    assert checkpoints["final"]["title"]["page"] == "home"
    assert runner.saved_files() == before
