# {
#   責務: [test_spawn_table_editor: test・出現・表・editorの公開機能・宣言を定義する]
#   フィールド: []
# }
from copy import deepcopy
from pathlib import Path
import shutil

import pygame
import pytest

from kadoka_engine.spawn_table import prepare_spawn_entry, spawn_weight_ratios
from kadoka_quest.apps.map_editor import MapEditor
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.ui.spawn_table_dialog import SpawnTableDialog, TABLE, SPECIES


ROOT = Path(__file__).resolve().parents[1]


# {
#   責務: [editor: test・出現・表・editorのeditorを求める]
#   処理: [1: test・出現・表・editorのeditorを求める]
#   引数: [tmp_path: tmp・パス]
#   戻り値: [result: 処理結果（型注釈なし）]
# }
@pytest.fixture
def editor(tmp_path):
    pygame.init()
    pygame.display.set_mode((1200, 760))
    shutil.copytree(ROOT / "data", tmp_path / "data")
    result = MapEditor(GameRepository(tmp_path / "data"))
    result.map_data["spawns"] = [
        {"species_id": "slime", "weight": 60, "min_level": 3, "max_level": 6,
         "requires_flag": "sample", "custom": {"notes": [1]}, "field_ai_weights": {"idle": 1}},
        {"species_id": "ghost", "weight": 30, "min_level": 4, "max_level": 7},
        {"species_id": "metal_slime", "weight": 1, "min_level": 8, "max_level": 12},
    ]
    result.select_species(result.species_ids.index("slime"))
    result.open_spawn_dialog()
    yield result
    pygame.quit()


# {
#   責務: [click: test・出現・表・editorのclickを求める]
#   処理: [1: test・出現・表・editorのclickを求める]
#   引数: [
#     dialog: dialog
#     position: 座標
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def click(dialog, position):
    dialog.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=position))


# {
#   責務: [type_value: test・出現・表・editorのtype・値を求める]
#   処理: [1: test・出現・表・editorのtype・値を求める]
#   引数: [
#     dialog: dialog
#     field: フィールド
#     text: 文字列
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def type_value(dialog, field, text):
    click(dialog, field.rect.center)
    for _ in field.value:
        dialog.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE, unicode="", mod=0))
    for character in text:
        dialog.handle(pygame.event.Event(pygame.KEYDOWN, key=ord(character), unicode=character, mod=0))


# {
#   責務: [choose_species: 種族を選択する]
#   処理: [1: 種族を選択する]
#   引数: [
#     dialog: dialog
#     species_id: 種族・識別子
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def choose_species(dialog, species_id):
    index = dialog.editor.species_ids.index(species_id)
    dialog.editor.spawn_species_offset = index
    dialog._configure()
    row = index - dialog.editor.spawn_species_offset
    click(dialog, (SPECIES.x + 10, SPECIES.y + row * 24 + 8))


# {
#   責務: [test_click_edit_species_weight_levels_and_save_reload: 検証: click edit species weight levels and save reload]
#   処理: [1: 検証: click edit species weight levels and save reload]
#   引数: [editor: editor]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_click_edit_species_weight_levels_and_save_reload(editor):
    dialog = SpawnTableDialog(editor)
    click(dialog, (TABLE.x + 20, TABLE.y + 12))
    choose_species(dialog, "dice_slime")
    type_value(dialog, editor.spawn_weight, "12.5")
    type_value(dialog, editor.spawn_min_level, "9")
    type_value(dialog, editor.spawn_max_level, "14")
    click(dialog, (680, 520))  # Apply.
    changed = editor.map_data["spawns"][0]
    assert changed["species_id"] == "dice_slime"
    assert (changed["weight"], changed["min_level"], changed["max_level"]) == (12.5, 9, 14)
    assert changed["requires_flag"] == "sample"
    assert changed["custom"] == {"notes": [1]}
    assert changed["field_ai_weights"] == {"idle": 1}
    click(dialog, (910, 575))  # Save map.
    assert not editor.dirty
    assert editor.repository.get_map(editor.map_id)["spawns"] == editor.map_data["spawns"]
    reloaded = MapEditor(editor.repository)
    assert reloaded.map_data["spawns"] == editor.map_data["spawns"]


# {
#   責務: [test_add_and_delete_one_duplicate_candidate: 検証: add and delete one duplicate candidate]
#   処理: [1: 検証: add and delete one duplicate candidate]
#   引数: [editor: editor]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_add_and_delete_one_duplicate_candidate(editor):
    dialog = SpawnTableDialog(editor)
    click(dialog, (180, 570))  # New draft.
    choose_species(dialog, "slime")
    type_value(dialog, editor.spawn_weight, "15")
    click(dialog, (700, 520))
    assert len(editor.map_data["spawns"]) == 4
    assert editor.selected_spawn == 3
    click(dialog, (350, 570))
    assert len(editor.map_data["spawns"]) == 3
    assert editor.map_data["spawns"][0]["requires_flag"] == "sample"
    assert editor.current_spawn is None


# {
#   責務: [test_bad_draft_never_changes_memory_or_saved_json: 検証: bad draft never changes memory or saved json]
#   処理: [1: 検証: bad draft never changes memory or saved json]
#   引数: [
#     editor: editor
#     weight: 重み
#     minimum: minimum
#     maximum: maximum
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("weight,minimum,maximum", [
    ("-1", "1", "5"), ("nan", "1", "5"), ("inf", "1", "5"),
    ("", "1", "5"), ("abc", "1", "5"), ("1", "9", "3"),
    ("1", "0", "5"), ("1", "1", "101"), ("1", "2.5", "5"),
])
def test_bad_draft_never_changes_memory_or_saved_json(editor, weight, minimum, maximum):
    path = editor.repository.root / "maps" / editor.map_id / "map.json"
    disk_before = path.read_bytes()
    before = deepcopy(editor.map_data)
    editor.spawn_weight.value = weight
    editor.spawn_min_level.value = minimum
    editor.spawn_max_level.value = maximum
    editor.save()
    assert editor.map_data == before
    assert path.read_bytes() == disk_before
    assert "反映できません" in editor.status


# {
#   責務: [test_ctrl_s_applies_valid_pending_draft: 検証: ctrl s applies valid pending draft]
#   処理: [1: 検証: ctrl s applies valid pending draft]
#   引数: [editor: editor]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_ctrl_s_applies_valid_pending_draft(editor):
    dialog = SpawnTableDialog(editor)
    type_value(dialog, editor.spawn_weight, "8")
    dialog.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s, mod=pygame.KMOD_CTRL, unicode="s"))
    assert editor.repository.get_map(editor.map_id)["spawns"][0]["weight"] == 8
    assert not editor.spawn_draft_changed()


# {
#   責務: [test_invalid_saved_table_is_rejected_even_without_pending_fields: 検証: invalid saved table is rejected even without pending fields]
#   処理: [1: 検証: invalid saved table is rejected even without pending fields]
#   引数: [editor: editor]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_invalid_saved_table_is_rejected_even_without_pending_fields(editor):
    path = editor.repository.root / "maps" / editor.map_id / "map.json"
    before = path.read_bytes()
    for entry in editor.map_data["spawns"]:
        entry["weight"] = 0
    editor.load_spawn_fields()
    editor.save()
    assert path.read_bytes() == before
    assert "保存できません" in editor.status


# {
#   責務: [test_empty_table_can_be_saved: 検証: empty table can be saved]
#   処理: [1: 検証: empty table can be saved]
#   引数: [editor: editor]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_empty_table_can_be_saved(editor):
    editor.map_data["spawns"] = []
    editor.new_spawn()
    editor.save()
    assert editor.repository.get_map(editor.map_id)["spawns"] == []


# {
#   責務: [test_ball_slime_is_not_added: 検証: ball slime is not added]
#   処理: [1: 検証: ball slime is not added]
#   引数: [editor: editor]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_ball_slime_is_not_added(editor):
    editor.new_spawn()
    choose_species(SpawnTableDialog(editor), "ball_slime")
    assert not editor.apply_spawn_range()
    assert len(editor.map_data["spawns"]) == 3
    assert "初期獲得専用" in editor.status


# {
#   責務: [test_unapplied_inputs_are_not_lost_on_row_switch_or_close: 検証: unapplied inputs are not lost on row switch or close]
#   処理: [1: 検証: unapplied inputs are not lost on row switch or close]
#   引数: [editor: editor]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_unapplied_inputs_are_not_lost_on_row_switch_or_close(editor):
    dialog = SpawnTableDialog(editor)
    editor.spawn_weight.value = "33"
    click(dialog, (TABLE.x + 10, TABLE.y + 45))
    assert editor.selected_spawn == 0
    dialog.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode="", mod=0))
    assert editor.spawn_dialog_open
    click(dialog, (900, 520))  # Revert.
    assert editor.spawn_weight.value == "60"
    dialog.close()
    assert not editor.spawn_dialog_open


# {
#   責務: [test_vertical_scrollbars_and_wheel_select_offscreen_rows: 検証: vertical scrollbars and wheel select offscreen rows]
#   処理: [1: 検証: vertical scrollbars and wheel select offscreen rows]
#   引数: [editor: editor]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_vertical_scrollbars_and_wheel_select_offscreen_rows(editor):
    editor.map_data["spawns"] *= 8
    dialog = SpawnTableDialog(editor)
    dialog.draw(pygame.display.get_surface(), (0, 0))
    dialog.handle(pygame.event.Event(pygame.MOUSEWHEEL, y=-6), TABLE.center)
    assert editor.spawn_table_offset == 6
    click(dialog, (TABLE.x + 10, TABLE.y + 10))
    assert editor.selected_spawn == 6
    click(dialog, (dialog.table_scroll.rect.centerx, dialog.table_scroll.rect.bottom - 2))
    dialog.handle(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(0, 0)))
    assert editor.spawn_table_offset == len(editor.map_data["spawns"]) - 9
    editor.spawn_species_offset = 0
    dialog.handle(pygame.event.Event(pygame.MOUSEWHEEL, y=-1), SPECIES.center)
    assert editor.spawn_species_offset == 1


# {
#   責務: [test_default_levels_and_weight_match_legacy_contract: 検証: default levels and weight match legacy contract]
#   処理: [1: 検証: default levels and weight match legacy contract]
#   引数: [editor: editor]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_default_levels_and_weight_match_legacy_contract(editor):
    editor.map_data["spawns"] = [{"species_id": "slime"}]
    editor.select_spawn(0)
    assert [field.value for field in editor.spawn_fields] == ["1", "1", "1"]


# {
#   責務: [test_relative_ratios_are_overflow_safe_and_invalid_is_explicit: 検証: relative ratios are overflow safe and invalid is explicit]
#   処理: [1: 検証: relative ratios are overflow safe and invalid is explicit]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_relative_ratios_are_overflow_safe_and_invalid_is_explicit():
    assert spawn_weight_ratios([{"weight": n} for n in (60, 30, 1)]) == pytest.approx([60/91, 30/91, 1/91])
    assert spawn_weight_ratios([{"weight": 1e308}, {"weight": 1e308}]) == [0.5, 0.5]
    assert spawn_weight_ratios([{"weight": 0}, {"weight": 1}]) == [0, 1]
    assert spawn_weight_ratios([]) == []
    for weight in (0, -1, True, "1", float("nan"), float("inf"), 10**1000):
        assert spawn_weight_ratios([{"weight": weight}]) is None


# {
#   責務: [test_preparation_does_not_mutate_and_rejects_all_zero: 検証: preparation does not mutate and rejects all zero]
#   処理: [1: 検証: preparation does not mutate and rejects all zero]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_preparation_does_not_mutate_and_rejects_all_zero():
    original = [{"species_id": "slime", "weight": 1, "custom": {"tags": ["x"]}}]
    before = deepcopy(original)
    result = prepare_spawn_entry(original, 0, "ghost", "0.5", "2", "9", {"ghost", "slime"})
    result["custom"]["tags"].append("y")
    assert original == before
    with pytest.raises(ValueError):
        prepare_spawn_entry(original, 0, "slime", "0", "1", "2", {"slime"})
