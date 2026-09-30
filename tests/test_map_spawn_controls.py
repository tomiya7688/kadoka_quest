from copy import deepcopy
from pathlib import Path
import shutil

import pygame
import pytest

from kadoka_engine.spawn_controls import map_ai_ratios, parse_map_spawn_controls, prepare_spawn_document
from kadoka_quest.apps.map_editor import MapEditor
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.ui.spawn_table_dialog import SpawnTableDialog


@pytest.fixture
def editor(tmp_path):
    pygame.init()
    pygame.display.set_mode((1200, 760))
    shutil.copytree(Path(__file__).resolve().parents[1] / "data", tmp_path / "data")
    result = MapEditor(GameRepository(tmp_path / "data"))
    result.select_species(result.species_ids.index("slime"))
    result.open_spawn_dialog()
    yield result
    pygame.quit()


def click(dialog, position):
    dialog.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=position))


def type_value(dialog, field, value):
    click(dialog, field.rect.center)
    for _ in field.value:
        dialog.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE, unicode="", mod=0))
    for character in value:
        dialog.handle(pygame.event.Event(pygame.KEYDOWN, key=ord(character), unicode=character, mod=0))


def test_ui_tabs_edit_save_and_reload(editor):
    dialog = SpawnTableDialog(editor)
    form = editor.map_spawn_form
    click(dialog, (450, 155))
    assert dialog.tab == "map"
    type_value(dialog, form.rate, "12.5")
    if form.inherit:
        click(dialog, (220, 345))
    for name, text in zip(("random", "chase", "idle"), ("60", "30", "1")):
        type_value(dialog, form.weights[name], text)
    assert map_ai_ratios(parse_map_spawn_controls(**form.draft)["field_ai_weights"]) == pytest.approx([60/91, 30/91, 1/91])
    dialog.draw(pygame.display.get_surface(), (0, 0))
    click(dialog, (220, 575))  # Apply.
    assert editor.map_data["pop_rate"] == 12.5
    assert editor.dirty
    click(dialog, (910, 575))  # Save.
    stored = editor.repository.get_map(editor.map_id)
    assert stored["field_ai_weights"] == {"random": 60, "chase": 30, "idle": 1}
    assert stored["pop_rate"] == 12.5
    reloaded = MapEditor(editor.repository)
    reloaded.open_spawn_dialog()
    assert not reloaded.map_spawn_form.inherit
    assert reloaded.map_spawn_form.rate.value == "12.5"
    assert not reloaded.map_spawn_form.changed


@pytest.mark.parametrize("rate", ["0", "100"])
def test_pop_rate_boundaries_round_trip(editor, rate):
    editor.map_data["pop_rate"] = 50
    editor.map_spawn_form.load(editor.map_data)
    editor.map_spawn_form.rate.value = rate
    editor.save()
    assert editor.repository.get_map(editor.map_id)["pop_rate"] == float(rate)


@pytest.mark.parametrize("rate,weights", [
    ("-1", None), ("101", None), ("nan", None), ("inf", None), ("", None),
    ("10", {"random": "-1"}), ("10", {"chase": "nan"}),
    ("10", {"idle": "inf"}), ("10", {"random": ""}),
    ("10", {"random": "0", "chase": "0", "idle": "0"}),
])
def test_invalid_map_draft_does_not_save_or_apply_pending_row(editor, rate, weights):
    form = editor.map_spawn_form
    before = deepcopy(editor.map_data)
    path = editor.repository.root / "maps" / editor.map_id / "map.json"
    disk_before = path.read_bytes()
    editor.spawn_weight.value = "77"
    form.rate.value = rate
    form.inherit = weights is None
    for name, field in form.weights.items():
        field.value = (weights or {}).get(name, "0")
    editor.save()
    assert editor.map_data == before
    assert path.read_bytes() == disk_before
    assert editor.spawn_weight.value == "77"
    assert "保存できません" in editor.status


def test_invalid_row_does_not_apply_valid_map_draft(editor):
    before = deepcopy(editor.map_data)
    editor.spawn_weight.value = "-1"
    editor.map_spawn_form.rate.value = "15"
    editor.save()
    assert editor.map_data == before
    assert editor.map_spawn_form.changed


def test_inherit_toggle_preserves_entry_override_and_mod_keys(editor):
    editor.map_data["field_ai_weights"] = {"idle": 2}
    editor.map_data["custom"] = {"notes": ["keep"]}
    editor.current_spawn["field_ai_weights"] = {"chase": 9}
    editor.map_spawn_form.load(editor.map_data)
    original_spawns = deepcopy(editor.map_data["spawns"])
    dialog = SpawnTableDialog(editor)
    click(dialog, (450, 155))
    click(dialog, (220, 345))  # Switch explicit map settings to inheritance.
    assert editor.map_spawn_form.inherit
    # Hidden inactive AI input must not consume typing.
    editor.map_spawn_form.weights["idle"].active = True
    dialog.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_5, unicode="5", mod=0))
    assert editor.map_spawn_form.weights["idle"].value == "2"
    dialog.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s, unicode="s", mod=pygame.KMOD_CTRL))
    stored = editor.repository.get_map(editor.map_id)
    assert stored["field_ai_weights"] is None
    assert stored["spawns"] == original_spawns
    assert stored["custom"] == {"notes": ["keep"]}


def test_missing_legacy_controls_stay_missing_without_changes(editor):
    editor.map_data.pop("pop_rate", None)
    editor.map_data.pop("field_ai_weights", None)
    editor.map_spawn_form.load(editor.map_data)
    assert editor.map_spawn_form.inherit
    assert editor.map_spawn_form.rate.value == "100"
    editor.save()
    stored = editor.repository.get_map(editor.map_id)
    assert "pop_rate" not in stored
    assert "field_ai_weights" not in stored


def test_tab_switch_preserves_both_drafts_ctrl_s_saves_both(editor):
    dialog = SpawnTableDialog(editor)
    editor.spawn_weight.value = "72"
    editor.spawn_weight.active = True
    click(dialog, (450, 155))
    assert not editor.spawn_weight.active
    type_value(dialog, editor.map_spawn_form.rate, "9")
    click(dialog, (200, 155))
    assert editor.map_spawn_form.rate.value == "9"
    assert editor.spawn_weight.value == "72"
    assert not editor.map_spawn_form.rate.active
    dialog.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s, unicode="s", mod=pygame.KMOD_CTRL))
    stored = editor.repository.get_map(editor.map_id)
    assert stored["pop_rate"] == 9
    assert stored["spawns"][editor.selected_spawn]["weight"] == 72
    assert not editor.map_spawn_form.changed
    assert not editor.spawn_draft_changed()


def test_close_guards_hidden_draft_and_revert_is_tab_local(editor):
    dialog = SpawnTableDialog(editor)
    editor.map_spawn_form.rate.value = "55"
    dialog.close()
    assert editor.spawn_dialog_open
    editor.spawn_weight.value = "77"
    click(dialog, (450, 155))
    click(dialog, (420, 575))  # Revert only map controls.
    assert not editor.map_spawn_form.changed
    assert editor.spawn_weight.value == "77"
    dialog.close()
    assert editor.spawn_dialog_open
    click(dialog, (200, 155))
    click(dialog, (900, 520))  # Revert candidate.
    dialog.close()
    assert not editor.spawn_dialog_open


def test_ratios_and_preparation_preserve_documents():
    assert map_ai_ratios({"idle": 3}) == [0, 0, 1]
    assert map_ai_ratios({"random": 1e308, "chase": 1e308}) == [0.5, 0.5, 0]
    assert map_ai_ratios({"unknown": 1}) is None
    assert map_ai_ratios({}) is None
    assert map_ai_ratios(None) is None
    document = {"custom": [1], "spawns": [{"species_id": "slime", "weight": 1}]}
    before = deepcopy(document)
    changed = prepare_spawn_document(document, {"slime"}, controls_draft={"rate": "0", "weights": None})
    assert document == before
    assert changed["pop_rate"] == 0
    changed["custom"].append(2)
    assert document == before
