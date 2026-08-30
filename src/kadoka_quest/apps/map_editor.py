from __future__ import annotations

import re

import pygame

from kadoka_quest.data.map_presets import MapPresetStore
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.ui.common import ACCENT, BAD, BG, GOOD, MUTED, PANEL, PANEL_ALT, SELECTED, TEXT, WARN, Button, ScrollBar, TextField, draw_status_bar, draw_text, handle_fields, init_pygame, smoke_frames


TILE = 22
MAP_RECT = pygame.Rect(20, 85, 924, 616)
GRID_RECT = pygame.Rect(20, 85, 906, 600)
BLOCK_ROWS = 6
SPECIES_ROWS = 8


def hex_color(value: str) -> tuple[int, int, int]:
    try:
        value = value.lstrip("#")
        return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))
    except (TypeError, ValueError):
        return (120, 120, 120)


class MapEditor:
    def __init__(self, repository: GameRepository | None = None, preset_store: MapPresetStore | None = None) -> None:
        self.repository = repository or GameRepository()
        self.preset_store = preset_store or MapPresetStore(self.repository.root)
        self.map_ids = self.repository.list_maps()
        self.map_names = {map_id: self.repository.get_map(map_id).get("display_name", map_id) for map_id in self.map_ids}
        self.preset_ids = self.preset_store.list_ids()
        self.preset_names = {preset_id: self.preset_store.get(preset_id).get("display_name", preset_id) for preset_id in self.preset_ids}
        self.map_index = 0
        self.map_id = self.map_ids[self.map_index]
        self.map_data = self.repository.get_map(self.map_id)
        self.blocks = self.repository.list_blocks()
        self.block_by_id = {block["id"]: block for block in self.blocks}
        self.species_ids = self.repository.list_species_ids()
        self.selected_block = self.blocks[0]["id"]
        self.selected_species = 0
        self.block_offset = 0
        self.species_offset = 0
        self.map_offset = 0
        self.preset_offset = 0
        self.selected_preset = -1
        self.transition_offset = 0
        self.target_map_offset = 0
        self.camera_x = 0
        self.camera_y = 0
        self.map_picker_open = False
        self.new_map_dialog_open = False
        self.preset_dialog_open = False
        self.transition_dialog_open = False
        self.fixed_mob_dialog_open = False
        self.placement_layer = "block"
        self.transition_brush_activation = "step"
        self.selected_transition = -1
        self.transition_id = TextField(pygame.Rect(580, 210, 250, 38))
        self.transition_x = TextField(pygame.Rect(850, 210, 75, 38), numeric=True)
        self.transition_y = TextField(pygame.Rect(940, 210, 75, 38), numeric=True)
        self.target_x = TextField(pygame.Rect(850, 420, 75, 38), numeric=True)
        self.target_y = TextField(pygame.Rect(940, 420, 75, 38), numeric=True)
        self.transition_text = TextField(pygame.Rect(580, 500, 495, 38))
        self.selected_fixed_mob = -1
        self.fixed_mob_offset = 0
        self.fixed_mob_id = TextField(pygame.Rect(570, 205, 220, 38))
        self.fixed_mob_name = TextField(pygame.Rect(815, 205, 140, 38))
        self.fixed_mob_level = TextField(pygame.Rect(975, 205, 60, 38), "1", numeric=True)
        self.fixed_mob_x = TextField(pygame.Rect(570, 280, 90, 38), numeric=True)
        self.fixed_mob_y = TextField(pygame.Rect(680, 280, 90, 38), numeric=True)
        self.fixed_mob_interval = TextField(pygame.Rect(790, 280, 120, 38), "900", numeric=True)
        self.fixed_mob_chance = TextField(pygame.Rect(930, 280, 105, 38), "100", numeric=True)
        self.fixed_mob_dialogue = TextField(pygame.Rect(570, 490, 465, 42))
        self.new_map_id = TextField(pygame.Rect(435, 205, 330, 40))
        self.new_map_name = TextField(pygame.Rect(435, 285, 330, 40))
        self.new_map_width = TextField(pygame.Rect(435, 365, 150, 40), "48", numeric=True)
        self.new_map_height = TextField(pygame.Rect(615, 365, 150, 40), "32", numeric=True)
        self.new_map_fill_block = self.selected_block
        self.preset_id = TextField(pygame.Rect(570, 205, 465, 38))
        self.preset_name = TextField(pygame.Rect(570, 285, 465, 38))
        self.preset_map_id = TextField(pygame.Rect(570, 405, 465, 38))
        self.preset_map_name = TextField(pygame.Rect(570, 485, 465, 38))
        self.dirty = False
        self.status = "ドラッグで連続配置。右クリックでマップ上のブロックを選択できます。"

    def save(self) -> None:
        for event in self.transitions:
            event.setdefault("activation", "step")
        self.repository.save_map(self.map_data)
        self.dirty = False
        self.status = f"data/maps/{self.map_id}/map.json を保存しました。"

    @property
    def preset_fields(self) -> list[TextField]:
        return [self.preset_id, self.preset_name, self.preset_map_id, self.preset_map_name]

    def refresh_preset_catalog(self) -> None:
        self.preset_ids = self.preset_store.list_ids()
        self.preset_names = {
            preset_id: self.preset_store.get(preset_id).get("display_name", preset_id)
            for preset_id in self.preset_ids
        }

    def open_preset_dialog(self) -> None:
        self.map_picker_open = False
        self.preset_dialog_open = True
        if self.preset_ids and self.selected_preset < 0:
            self.select_preset(0)
        elif not self.preset_ids:
            self.preset_id.value = f"{self.map_id}_preset"
            self.preset_name.value = f"{self.map_data['display_name']}プリセット"

    def select_preset(self, index: int) -> None:
        if not 0 <= index < len(self.preset_ids):
            return
        self.selected_preset = index
        preset_id = self.preset_ids[index]
        preset = self.preset_store.get(preset_id)
        self.preset_id.value = preset_id
        self.preset_name.value = str(preset.get("display_name", preset_id))
        self.preset_map_id.value = f"{preset_id}_map"
        self.preset_map_name.value = str(preset.get("display_name", preset_id))

    def save_current_as_preset(self) -> bool:
        preset_id = self.preset_id.value.strip()
        overwrite = 0 <= self.selected_preset < len(self.preset_ids) and self.preset_ids[self.selected_preset] == preset_id
        try:
            self.preset_store.save_from_map(
                preset_id,
                self.preset_name.value,
                self.map_data,
                overwrite=overwrite,
            )
        except (KeyError, TypeError, ValueError, OSError) as exc:
            self.status = f"マッププリセットを保存できません: {exc}"
            return False
        self.refresh_preset_catalog()
        self.selected_preset = self.preset_ids.index(preset_id)
        self.status = f"data/map_presets/{preset_id}.json に現在のマップを保存しました。"
        return True

    def apply_selected_preset(self) -> bool:
        if self.dirty:
            self.status = "未保存の変更があります。現在のマップを保存してからプリセットを適用してください。"
            return False
        if not 0 <= self.selected_preset < len(self.preset_ids):
            self.status = "適用するマッププリセットを選択してください。"
            return False
        preset_id = self.preset_ids[self.selected_preset]
        try:
            self.map_data = self.preset_store.apply_to_map(preset_id, self.map_data)
        except (KeyError, TypeError, ValueError, OSError) as exc:
            self.status = f"マッププリセットを適用できません: {exc}"
            return False
        self.camera_x = self.camera_y = 0
        self.selected_transition = -1
        self.selected_fixed_mob = -1
        self.dirty = True
        self.preset_dialog_open = False
        self.status = f"{preset_id} を現在のマップへ適用しました。保存すると確定します。"
        return True

    def create_map_from_selected_preset(self) -> bool:
        if self.dirty:
            self.status = "現在のマップを保存してからプリセットから新規作成してください。"
            return False
        if not 0 <= self.selected_preset < len(self.preset_ids):
            self.status = "元にするマッププリセットを選択してください。"
            return False
        preset_id = self.preset_ids[self.selected_preset]
        try:
            payload = self.preset_store.build_map(
                preset_id,
                self.preset_map_id.value,
                self.preset_map_name.value,
            )
            self.repository.create_map_from_document(payload)
        except (KeyError, TypeError, ValueError, OSError) as exc:
            self.status = f"プリセットからマップを作成できません: {exc}"
            return False
        self.map_ids = self.repository.list_maps()
        self.map_names = {map_id: self.repository.get_map(map_id).get("display_name", map_id) for map_id in self.map_ids}
        self.map_index = self.map_ids.index(str(payload["id"]))
        self.map_id = str(payload["id"])
        self.map_data = payload
        self.camera_x = self.camera_y = 0
        self.selected_transition = -1
        self.selected_fixed_mob = -1
        self.preset_dialog_open = False
        self.dirty = False
        self.status = f"{preset_id} から {self.map_id} を新規作成しました。"
        return True

    @property
    def fixed_mobs(self) -> list[dict]:
        return self.map_data.setdefault("fixed_mobs", [])

    @property
    def current_fixed_mob(self) -> dict | None:
        return self.fixed_mobs[self.selected_fixed_mob] if 0 <= self.selected_fixed_mob < len(self.fixed_mobs) else None

    def fixed_mob_fields(self) -> list[TextField]:
        return [self.fixed_mob_id, self.fixed_mob_name, self.fixed_mob_level, self.fixed_mob_x, self.fixed_mob_y, self.fixed_mob_interval, self.fixed_mob_chance, self.fixed_mob_dialogue]

    def open_fixed_mob_dialog(self) -> None:
        self.fixed_mob_dialog_open = True
        if self.fixed_mobs and self.selected_fixed_mob < 0:
            self.select_fixed_mob(0)

    def select_fixed_mob(self, index: int) -> None:
        if not 0 <= index < len(self.fixed_mobs):
            return
        self.selected_fixed_mob = index
        item = self.fixed_mobs[index]
        self.fixed_mob_id.value = str(item.get("id", ""))
        self.fixed_mob_name.value = str(item.get("name", ""))
        self.fixed_mob_level.value = str(item.get("level", 1))
        self.fixed_mob_x.value = str(item.get("x", 0))
        self.fixed_mob_y.value = str(item.get("y", 0))
        self.fixed_mob_interval.value = str(item.get("move_interval_ms", 900))
        self.fixed_mob_chance.value = str(item.get("move_chance", 100))
        self.fixed_mob_dialogue.value = " | ".join(str(line) for line in item.get("dialogue", []))

    def select_fixed_mob_brush(self) -> None:
        self.placement_layer = "fixed_mob"
        self.status = f"固定モブ配置: {self.species_ids[self.selected_species]}。マップをクリックしてください。"

    def begin_fixed_mob_placement(self) -> None:
        self.fixed_mob_dialog_open = False
        self.select_fixed_mob_brush()

    def add_fixed_mob_at(self, x: int, y: int, *, open_editor: bool = False) -> bool:
        if any(int(item.get("x", -1)) == x and int(item.get("y", -1)) == y for item in self.fixed_mobs):
            self.status = "そのマスには既に固定モブがいます。"
            return False
        species_id = self.species_ids[self.selected_species]
        display_name = str(self.repository.get_species(species_id).definition.get("display_name", species_id))
        number = 1
        used = {str(item.get("id", "")) for item in self.fixed_mobs}
        while f"{species_id}_{number}" in used:
            number += 1
        item = {
            "id": f"{species_id}_{number}", "species_id": species_id, "name": display_name,
            "x": int(x), "y": int(y), "direction": "front", "enabled": True, "level": 1,
            "ai": "idle", "move_interval_ms": 900, "move_chance": 100,
            "interaction": "talk", "despawn_after_interaction": False, "respawn_on_map_enter": True,
            "dialogue": ["こんにちは。", "今日はいい天気ですね。", "気をつけて旅をしてください。"],
        }
        self.fixed_mobs.append(item)
        self.selected_fixed_mob = len(self.fixed_mobs) - 1
        self.select_fixed_mob(self.selected_fixed_mob)
        self.fixed_mob_dialog_open = open_editor
        self.dirty = True
        self.status = f"固定モブ {display_name} を ({x}, {y}) に配置しました。"
        return True

    def cycle_fixed_mob_ai(self) -> None:
        item = self.current_fixed_mob
        if not item:
            return
        choices = ("idle", "random", "chase")
        current = str(item.get("ai", "idle"))
        item["ai"] = choices[(choices.index(current) + 1) % len(choices)] if current in choices else "idle"
        self.dirty = True

    def cycle_fixed_mob_interaction(self) -> None:
        item = self.current_fixed_mob
        if item:
            item["interaction"] = "battle" if item.get("interaction", "talk") == "talk" else "talk"
            self.dirty = True

    def toggle_fixed_mob_option(self, key: str) -> None:
        if self.current_fixed_mob:
            self.current_fixed_mob[key] = not bool(self.current_fixed_mob.get(key, False))
            self.dirty = True

    def apply_fixed_mob(self) -> bool:
        item = self.current_fixed_mob
        if not item:
            self.status = "編集する固定モブを選択してください。"
            return False
        mob_id = self.fixed_mob_id.value.strip()
        if not mob_id or not re.fullmatch(r"[a-z0-9_-]+", mob_id):
            self.status = "固定モブIDは半角小文字・数字・_・-だけにしてください。"
            return False
        if any(other is not item and other.get("id") == mob_id for other in self.fixed_mobs):
            self.status = "同じ固定モブIDが既にあります。"
            return False
        try:
            x, y = int(self.fixed_mob_x.value), int(self.fixed_mob_y.value)
            level = max(1, min(100, int(self.fixed_mob_level.value)))
            interval = max(100, min(60000, int(self.fixed_mob_interval.value)))
            chance = max(0, min(100, int(self.fixed_mob_chance.value)))
        except ValueError:
            self.status = "座標・速度・移動頻度は数字で入力してください。"
            return False
        if not (0 <= x < self.map_data["width"] and 0 <= y < self.map_data["height"]):
            self.status = "固定モブの座標がマップ外です。"
            return False
        dialogue = [line.strip() for line in self.fixed_mob_dialogue.value.split("|") if line.strip()]
        item.update({
            "id": mob_id, "name": self.fixed_mob_name.value.strip() or str(item["species_id"]),
            "x": x, "y": y, "level": level, "move_interval_ms": interval, "move_chance": chance,
            "dialogue": dialogue or ["……"],
        })
        self.fixed_mob_interval.value = str(interval)
        self.fixed_mob_chance.value = str(chance)
        self.fixed_mob_level.value = str(level)
        self.dirty = True
        self.status = f"固定モブ {mob_id} の設定を反映しました。"
        return True

    def delete_fixed_mob(self) -> None:
        item = self.current_fixed_mob
        if not item:
            return
        self.fixed_mobs.remove(item)
        self.selected_fixed_mob = min(self.selected_fixed_mob, len(self.fixed_mobs) - 1)
        if self.current_fixed_mob:
            self.select_fixed_mob(self.selected_fixed_mob)
        self.dirty = True
        self.status = "固定モブを削除しました。"

    def add_spawn(self) -> None:
        species_id = self.species_ids[self.selected_species]
        if species_id == "ball_slime":
            self.status = "ボールスライムは初期獲得専用なので出現表へ追加できません。"
            return
        if any(item.get("species_id") == species_id for item in self.map_data.get("spawns", [])):
            self.status = f"{species_id} は既に出現表へ入っています。"
            return
        self.map_data.setdefault("spawns", []).append({"species_id": species_id, "weight": 10, "min_level": 1, "max_level": 5})
        self.dirty = True
        self.status = f"{species_id} を出現表へ追加しました（重み10）。"

    def remove_spawn(self) -> None:
        species_id = self.species_ids[self.selected_species]
        old = len(self.map_data.get("spawns", []))
        self.map_data["spawns"] = [item for item in self.map_data.get("spawns", []) if item.get("species_id") != species_id]
        if len(self.map_data["spawns"]) < old:
            self.dirty = True
        self.status = f"{species_id} を出現表から削除しました。" if len(self.map_data["spawns"]) < old else "対象は出現表にありません。"

    def move_camera(self, dx: int, dy: int) -> None:
        visible_x = GRID_RECT.width // TILE
        visible_y = GRID_RECT.height // TILE
        self.camera_x = max(0, min(int(self.map_data["width"]) - visible_x, self.camera_x + dx))
        self.camera_y = max(0, min(int(self.map_data["height"]) - visible_y, self.camera_y + dy))

    def select_map(self, index: int) -> bool:
        if self.dirty:
            self.status = "未保存の変更があります。保存してから一覧で別のマップを選んでください。"
            return False
        if not 0 <= index < len(self.map_ids):
            return False
        self.map_index = index
        self.map_id = self.map_ids[self.map_index]
        self.map_data = self.repository.get_map(self.map_id)
        self.camera_x = 0
        self.camera_y = 0
        self.selected_transition = -1
        self.transition_offset = 0
        self.selected_fixed_mob = -1
        self.fixed_mob_offset = 0
        self.status = f"{self.map_data['display_name']}を一覧から開きました。"
        return True

    @property
    def new_map_fields(self) -> list[TextField]:
        return [self.new_map_id, self.new_map_name, self.new_map_width, self.new_map_height]

    def open_new_map_dialog(self) -> None:
        if self.dirty:
            self.status = "現在のマップを保存してから新しいマップを作成してください。"
            self.map_picker_open = False
            return
        self.map_picker_open = False
        self.new_map_dialog_open = True
        self.new_map_fill_block = self.selected_block

    def create_new_map(self) -> bool:
        try:
            payload = self.repository.create_map(
                self.new_map_id.value,
                self.new_map_name.value,
                int(self.new_map_width.value),
                int(self.new_map_height.value),
                self.new_map_fill_block,
            )
        except (ValueError, OSError) as exc:
            self.status = f"新しいマップを作成できません: {exc}"
            return False
        self.map_ids = self.repository.list_maps()
        self.map_names = {map_id: self.repository.get_map(map_id).get("display_name", map_id) for map_id in self.map_ids}
        self.map_index = self.map_ids.index(str(payload["id"]))
        self.map_id = str(payload["id"])
        self.map_data = payload
        self.camera_x = self.camera_y = 0
        self.selected_transition = -1
        self.selected_fixed_mob = -1
        self.new_map_dialog_open = False
        self.new_map_id.value = ""
        self.new_map_name.value = ""
        self.dirty = False
        self.status = f"{payload['display_name']}を新規作成し、data/maps/{self.map_id}/map.json に保存しました。"
        return True

    def grid_position(self, position: tuple[int, int]) -> tuple[int, int] | None:
        if not GRID_RECT.collidepoint(position):
            return None
        grid_x = self.camera_x + (position[0] - MAP_RECT.x) // TILE
        grid_y = self.camera_y + (position[1] - MAP_RECT.y) // TILE
        if 0 <= grid_x < self.map_data["width"] and 0 <= grid_y < self.map_data["height"]:
            return grid_x, grid_y
        return None

    def paint(self, position: tuple[int, int]) -> bool:
        grid = self.grid_position(position)
        if grid is None:
            return False
        grid_x, grid_y = grid
        if self.map_data["tiles"][grid_y][grid_x] != self.selected_block:
            self.map_data["tiles"][grid_y][grid_x] = self.selected_block
            self.dirty = True
            self.status = f"({grid_x}, {grid_y}) に {self.selected_block} を配置。"
        return True

    def pick_block(self, position: tuple[int, int]) -> bool:
        grid = self.grid_position(position)
        if grid is None:
            return False
        grid_x, grid_y = grid
        self.select_block_brush(self.map_data["tiles"][grid_y][grid_x])
        self.status = f"({grid_x}, {grid_y}) から {self.selected_block} を選択。"
        return True

    @property
    def transitions(self) -> list[dict]:
        return [event for event in self.map_data.get("events", []) if event.get("type") == "transition"]

    @property
    def current_transition(self) -> dict | None:
        return self.transitions[self.selected_transition] if 0 <= self.selected_transition < len(self.transitions) else None

    @property
    def transition_fields(self) -> list[TextField]:
        return [self.transition_id, self.transition_x, self.transition_y, self.target_x, self.target_y, self.transition_text]

    def open_transition_dialog(self) -> None:
        self.transition_dialog_open = True
        if self.transitions and self.selected_transition < 0:
            self.select_transition(0)

    def select_transition(self, index: int) -> None:
        if not 0 <= index < len(self.transitions):
            return
        self.selected_transition = index
        item = self.transitions[index]
        target = item.get("target", {})
        target_id = str(target.get("map_id", ""))
        if target_id in self.map_ids:
            target_index = self.map_ids.index(target_id)
            if target_index < self.target_map_offset:
                self.target_map_offset = target_index
            elif target_index >= self.target_map_offset + 6:
                self.target_map_offset = target_index - 5
        self.transition_id.value = str(item.get("id", ""))
        self.transition_x.value = str(item.get("x", 0))
        self.transition_y.value = str(item.get("y", 0))
        self.target_x.value = str(target.get("x", 0))
        self.target_y.value = str(target.get("y", 0))
        self.transition_text.value = str(item.get("text", "移動しました。"))

    def begin_transition_placement(self) -> None:
        self.transition_dialog_open = False
        self.select_transition_brush("step")

    def select_block_brush(self, block_id: str) -> None:
        self.selected_block = block_id
        self.placement_layer = "block"
        self.status = f"地形ブロック {block_id} を選択しました。"

    def select_transition_brush(self, activation: str) -> None:
        self.placement_layer = "transition"
        self.transition_brush_activation = activation
        label = "触れたら" if activation == "step" else "調べたら"
        self.status = f"移動ポイント［{label}］を選択しました。地形に重ねて配置できます。"

    def add_transition_at(self, x: int, y: int, activation: str | None = None, *, open_editor: bool = False) -> bool:
        activation = activation or self.transition_brush_activation
        if any(int(item.get("x", -1)) == int(x) and int(item.get("y", -1)) == int(y) and item.get("activation", "step") == activation for item in self.transitions):
            return False
        used = {str(item.get("id", "")) for item in self.map_data.get("events", [])}
        number = 1
        while f"move_point_{number}" in used:
            number += 1
        item = {
            "id": f"move_point_{number}", "x": int(x), "y": int(y), "type": "transition",
            "activation": activation, "text": "移動しました。",
            "target": {"map_id": self.map_id, "x": int(x), "y": int(y)},
        }
        self.map_data.setdefault("events", []).append(item)
        self.selected_transition = len(self.transitions) - 1
        self.select_transition(self.selected_transition)
        self.transition_dialog_open = open_editor
        self.dirty = True
        label = "触れたら" if activation == "step" else "調べたら"
        self.status = f"({x}, {y}) に移動ポイント［{label}］を地形へ重ねて配置しました。"
        return True

    def set_transition_activation(self, activation: str) -> None:
        if not self.current_transition:
            self.status = "先に移動ポイントを選択してください。"
            return
        self.current_transition["activation"] = activation
        self.dirty = True

    def set_transition_target(self, map_id: str) -> None:
        if not self.current_transition:
            self.status = "先に移動ポイントを選択してください。"
            return
        self.current_transition.setdefault("target", {})["map_id"] = map_id
        self.dirty = True

    def apply_transition(self) -> bool:
        item = self.current_transition
        if not item:
            self.status = "先に移動ポイントを選択してください。"
            return False
        event_id = self.transition_id.value.strip()
        if not re.fullmatch(r"[a-z0-9_-]+", event_id):
            self.status = "移動ポイントIDは半角小文字・数字・_・-だけで入力してください。"
            return False
        if any(other is not item and other.get("id") == event_id for other in self.map_data.get("events", [])):
            self.status = "同じイベントIDが既にあります。"
            return False
        try:
            x, y = int(self.transition_x.value), int(self.transition_y.value)
            target_x, target_y = int(self.target_x.value), int(self.target_y.value)
        except ValueError:
            self.status = "座標は整数で入力してください。"
            return False
        target_id = str(item.get("target", {}).get("map_id", self.map_id))
        target_map = self.repository.get_map(target_id)
        if not (0 <= x < int(self.map_data["width"]) and 0 <= y < int(self.map_data["height"])):
            self.status = "配置座標が現在のマップ範囲外です。"
            return False
        if not (0 <= target_x < int(target_map["width"]) and 0 <= target_y < int(target_map["height"])):
            self.status = "移動先座標が移動先マップの範囲外です。"
            return False
        item.update({"id": event_id, "x": x, "y": y, "text": self.transition_text.value})
        item.setdefault("activation", "step")
        item["target"] = {"map_id": target_id, "x": target_x, "y": target_y}
        self.dirty = True
        self.status = f"移動ポイント {event_id} の編集を反映しました。"
        return True

    def delete_transition(self) -> None:
        item = self.current_transition
        if not item:
            self.status = "削除する移動ポイントを選択してください。"
            return
        event_id = str(item.get("id", ""))
        self.map_data["events"].remove(item)
        self.selected_transition = min(self.selected_transition, len(self.transitions) - 1)
        if self.current_transition:
            self.select_transition(self.selected_transition)
        self.dirty = True
        self.status = f"移動ポイント {event_id} を削除しました。"


def main() -> None:
    screen = init_pygame("kadoka quest - マップエディタ", (1200, 760))
    clock = pygame.time.Clock()
    editor = MapEditor()
    running = True
    smoke = smoke_frames()
    frames = 0
    buttons = [
        Button(pygame.Rect(975, 625, 95, 42), "保存", editor.save),
        Button(pygame.Rect(1080, 625, 95, 42), "終了", lambda: None),
        Button(pygame.Rect(975, 590, 95, 38), "出現追加", editor.add_spawn),
        Button(pygame.Rect(1080, 590, 95, 38), "出現削除", editor.remove_spawn),
        Button(pygame.Rect(670, 20, 125, 38), "プリセット", editor.open_preset_dialog),
        Button(pygame.Rect(940, 20, 115, 38), "マップ一覧", lambda: setattr(editor, "map_picker_open", True)),
        Button(pygame.Rect(1065, 20, 120, 38), "移動ポイント", editor.open_transition_dialog),
        Button(pygame.Rect(805, 20, 125, 38), "固定モブ", editor.open_fixed_mob_dialog),
    ]
    horizontal_scroll = ScrollBar(pygame.Rect(GRID_RECT.x, GRID_RECT.bottom + 4, GRID_RECT.width, 10), "horizontal")
    vertical_scroll = ScrollBar(pygame.Rect(GRID_RECT.right + 4, GRID_RECT.y, 10, GRID_RECT.height), "vertical")
    block_scroll = ScrollBar(pygame.Rect(1176, 220, 7, BLOCK_ROWS * 32 - 4), "vertical")
    species_scroll = ScrollBar(pygame.Rect(1176, 425, 7, SPECIES_ROWS * 20 - 2), "vertical")
    preset_scroll = ScrollBar(pygame.Rect(505, 190, 10, 353), "vertical")

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if editor.new_map_dialog_open:
                field_handled = handle_fields(editor.new_map_fields, event)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    editor.new_map_dialog_open = False
                elif not field_handled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if pygame.Rect(800, 105, 120, 36).collidepoint(event.pos):
                        editor.new_map_dialog_open = False
                    elif pygame.Rect(510, 610, 180, 44).collidepoint(event.pos):
                        editor.create_new_map()
                    else:
                        for index, block in enumerate(editor.blocks):
                            rect = pygame.Rect(435 + (index % 3) * 112, 470 + (index // 3) * 32, 106, 27)
                            if rect.collidepoint(event.pos):
                                editor.new_map_fill_block = block["id"]
                                break
                continue
            if editor.preset_dialog_open:
                if preset_scroll.handle(event):
                    editor.preset_offset = preset_scroll.value
                    continue
                field_handled = handle_fields(editor.preset_fields, event)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    editor.preset_dialog_open = False
                elif not field_handled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if pygame.Rect(1020, 100, 110, 36).collidepoint(event.pos):
                        editor.preset_dialog_open = False
                    elif pygame.Rect(570, 550, 180, 42).collidepoint(event.pos):
                        editor.save_current_as_preset()
                    elif pygame.Rect(760, 550, 160, 42).collidepoint(event.pos):
                        editor.apply_selected_preset()
                    elif pygame.Rect(930, 550, 160, 42).collidepoint(event.pos):
                        editor.create_map_from_selected_preset()
                    else:
                        for row, preset_id in enumerate(editor.preset_ids[editor.preset_offset:editor.preset_offset + 8]):
                            if pygame.Rect(100, 190 + row * 45, 400, 38).collidepoint(event.pos):
                                editor.select_preset(editor.preset_offset + row)
                                break
                elif event.type == pygame.MOUSEWHEEL:
                    editor.preset_offset = max(0, min(max(0, len(editor.preset_ids) - 8), editor.preset_offset - event.y))
                continue
            if editor.map_picker_open:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    editor.map_picker_open = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if pygame.Rect(790, 635, 130, 36).collidepoint(event.pos):
                        editor.map_picker_open = False
                    elif pygame.Rect(650, 635, 130, 36).collidepoint(event.pos):
                        editor.open_new_map_dialog()
                    for row, map_id in enumerate(editor.map_ids[editor.map_offset:editor.map_offset + 10]):
                        if pygame.Rect(270, 150 + row * 48, 660, 40).collidepoint(event.pos):
                            if editor.select_map(editor.map_offset + row):
                                editor.map_picker_open = False
                elif event.type == pygame.MOUSEWHEEL:
                    editor.map_offset = max(0, min(max(0, len(editor.map_ids) - 10), editor.map_offset - event.y))
                continue
            if editor.fixed_mob_dialog_open:
                field_handled = handle_fields(editor.fixed_mob_fields(), event)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    editor.fixed_mob_dialog_open = False
                    continue
                if not field_handled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if pygame.Rect(1020, 100, 110, 36).collidepoint(event.pos):
                        editor.fixed_mob_dialog_open = False
                    elif pygame.Rect(100, 590, 180, 40).collidepoint(event.pos):
                        editor.begin_fixed_mob_placement()
                    elif pygame.Rect(570, 350, 150, 40).collidepoint(event.pos):
                        editor.cycle_fixed_mob_ai()
                    elif pygame.Rect(735, 350, 150, 40).collidepoint(event.pos):
                        editor.cycle_fixed_mob_interaction()
                    elif pygame.Rect(900, 350, 135, 40).collidepoint(event.pos):
                        editor.toggle_fixed_mob_option("enabled")
                    elif pygame.Rect(570, 410, 220, 40).collidepoint(event.pos):
                        editor.toggle_fixed_mob_option("despawn_after_interaction")
                    elif pygame.Rect(805, 410, 230, 40).collidepoint(event.pos):
                        editor.toggle_fixed_mob_option("respawn_on_map_enter")
                    elif pygame.Rect(570, 570, 180, 42).collidepoint(event.pos):
                        editor.apply_fixed_mob()
                    elif pygame.Rect(775, 570, 150, 42).collidepoint(event.pos):
                        editor.delete_fixed_mob()
                    else:
                        for row, item in enumerate(editor.fixed_mobs[editor.fixed_mob_offset:editor.fixed_mob_offset + 8]):
                            if pygame.Rect(100, 205 + row * 43, 400, 36).collidepoint(event.pos):
                                editor.select_fixed_mob(editor.fixed_mob_offset + row)
                                break
                if event.type == pygame.MOUSEWHEEL:
                    editor.fixed_mob_offset = max(0, min(max(0, len(editor.fixed_mobs) - 8), editor.fixed_mob_offset - event.y))
                continue
            if editor.transition_dialog_open:
                field_handled = handle_fields(editor.transition_fields, event)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    editor.transition_dialog_open = False
                    continue
                if not field_handled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if pygame.Rect(1020, 100, 110, 36).collidepoint(event.pos):
                        editor.transition_dialog_open = False
                    elif pygame.Rect(100, 590, 180, 40).collidepoint(event.pos):
                        editor.begin_transition_placement()
                    elif pygame.Rect(580, 280, 150, 38).collidepoint(event.pos):
                        editor.set_transition_activation("step")
                    elif pygame.Rect(740, 280, 150, 38).collidepoint(event.pos):
                        editor.set_transition_activation("interact")
                    elif pygame.Rect(580, 570, 180, 42).collidepoint(event.pos):
                        editor.apply_transition()
                    elif pygame.Rect(775, 570, 150, 42).collidepoint(event.pos):
                        editor.delete_transition()
                    else:
                        for row, item in enumerate(editor.transitions[editor.transition_offset:editor.transition_offset + 8]):
                            if pygame.Rect(100, 205 + row * 43, 400, 36).collidepoint(event.pos):
                                editor.select_transition(editor.transition_offset + row)
                                break
                        for index, map_id in enumerate(editor.map_ids[editor.target_map_offset:editor.target_map_offset + 6]):
                            target_rect = pygame.Rect(580 + (index % 2) * 130, 350 + (index // 2) * 28, 125, 24)
                            if target_rect.collidepoint(event.pos):
                                editor.set_transition_target(map_id)
                                break
                if event.type == pygame.MOUSEWHEEL:
                    if pygame.mouse.get_pos()[0] < 530:
                        editor.transition_offset = max(0, min(max(0, len(editor.transitions) - 8), editor.transition_offset - event.y))
                    else:
                        editor.target_map_offset = max(0, min(max(0, len(editor.map_ids) - 6), editor.target_map_offset - event.y))
                continue
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_LEFT:
                    editor.move_camera(-3, 0)
                elif event.key == pygame.K_RIGHT:
                    editor.move_camera(3, 0)
                elif event.key == pygame.K_UP:
                    editor.move_camera(0, -3)
                elif event.key == pygame.K_DOWN:
                    editor.move_camera(0, 3)
                elif event.key == pygame.K_s and event.mod & pygame.KMOD_CTRL:
                    editor.save()
            visible_x = GRID_RECT.width // TILE
            visible_y = GRID_RECT.height // TILE
            horizontal_scroll.configure(int(editor.map_data["width"]), visible_x)
            vertical_scroll.configure(int(editor.map_data["height"]), visible_y)
            block_scroll.configure(len(editor.blocks), BLOCK_ROWS)
            species_scroll.configure(len(editor.species_ids), SPECIES_ROWS)
            horizontal_scroll.value = editor.camera_x
            vertical_scroll.value = editor.camera_y
            block_scroll.value = editor.block_offset
            species_scroll.value = editor.species_offset
            scroll_handled = False
            for scroll in (horizontal_scroll, vertical_scroll, block_scroll, species_scroll):
                scroll_handled = scroll.handle(event) or scroll_handled
            editor.camera_x = horizontal_scroll.value
            editor.camera_y = vertical_scroll.value
            editor.block_offset = block_scroll.value
            editor.species_offset = species_scroll.value
            if not scroll_handled and event.type == pygame.MOUSEBUTTONDOWN and event.button in {1, 3}:
                if event.button == 1:
                    grid = editor.grid_position(event.pos)
                    if editor.placement_layer == "transition" and grid:
                        editor.add_transition_at(*grid, editor.transition_brush_activation)
                    elif editor.placement_layer == "fixed_mob" and grid:
                        editor.add_fixed_mob_at(*grid, open_editor=True)
                    else:
                        editor.paint(event.pos)
                else:
                    editor.pick_block(event.pos)
            if not scroll_handled and event.type == pygame.MOUSEMOTION and event.buttons[0]:
                grid = editor.grid_position(event.pos)
                if editor.placement_layer == "transition" and grid:
                    editor.add_transition_at(*grid, editor.transition_brush_activation)
                elif editor.placement_layer == "fixed_mob":
                    pass
                else:
                    editor.paint(event.pos)
            if not scroll_handled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if pygame.Rect(970, 105, 198, 28).collidepoint(event.pos):
                    editor.select_transition_brush("step")
                elif pygame.Rect(970, 137, 198, 28).collidepoint(event.pos):
                    editor.select_transition_brush("interact")
                elif pygame.Rect(970, 168, 198, 28).collidepoint(event.pos):
                    editor.select_fixed_mob_brush()
                for row, block in enumerate(editor.blocks[editor.block_offset:editor.block_offset + BLOCK_ROWS]):
                    rect = pygame.Rect(970, 220 + row * 32, 198, 28)
                    if rect.collidepoint(event.pos):
                        editor.select_block_brush(block["id"])
                for row, species_id in enumerate(editor.species_ids[editor.species_offset:editor.species_offset + SPECIES_ROWS]):
                    index = editor.species_offset + row
                    rect = pygame.Rect(970, 425 + row * 20, 198, 18)
                    if rect.collidepoint(event.pos):
                        editor.selected_species = index
                if buttons[1].rect.collidepoint(event.pos):
                    running = False
                else:
                    for button in buttons:
                        button.handle(event)
            if event.type == pygame.MOUSEWHEEL:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                if mouse_x >= 960 and 215 <= mouse_y < 415:
                    editor.block_offset = max(0, min(block_scroll.maximum, editor.block_offset - event.y))
                elif mouse_x >= 960 and 420 <= mouse_y < 590:
                    editor.species_offset = max(0, min(species_scroll.maximum, editor.species_offset - event.y))
                elif GRID_RECT.collidepoint((mouse_x, mouse_y)):
                    editor.move_camera(0, -event.y * 3)

        screen.fill(BG)
        dirty_mark = "  ●未保存" if editor.dirty else ""
        draw_text(screen, f"マップエディタ：{editor.map_data['display_name']}{dirty_mark}", (22, 22), 32, WARN if editor.dirty else ACCENT, True)
        hover_grid = editor.grid_position(pygame.mouse.get_pos())
        hover_text = f"  カーソル {hover_grid[0]}, {hover_grid[1]}" if hover_grid else ""
        draw_text(screen, f"表示原点 {editor.camera_x}, {editor.camera_y}{hover_text}", (590, 35), 16, MUTED)
        layer_label = {"transition": "移動ポイント", "fixed_mob": "固定モブ"}.get(editor.placement_layer, "地形ブロック")
        draw_text(screen, f"配置中: {layer_label}  /  ドラッグ: 連続配置  /  右クリック: スポイト", (500, 58), 14, MUTED)
        pygame.draw.rect(screen, PANEL, MAP_RECT.inflate(8, 8), border_radius=8)
        visible_x = GRID_RECT.width // TILE
        visible_y = GRID_RECT.height // TILE
        for screen_y in range(visible_y):
            grid_y = editor.camera_y + screen_y
            if grid_y >= editor.map_data["height"]:
                break
            for screen_x in range(visible_x):
                grid_x = editor.camera_x + screen_x
                if grid_x >= editor.map_data["width"]:
                    break
                block_id = editor.map_data["tiles"][grid_y][grid_x]
                block = editor.block_by_id.get(block_id, {})
                appearance = block.get("appearance", {})
                override = editor.map_data.get("block_color_overrides", {}).get(block_id)
                color = hex_color(override) if override else (hex_color(appearance.get("value", "#777777")) if appearance.get("type") == "color" else (110, 95, 125))
                rect = pygame.Rect(GRID_RECT.x + screen_x * TILE, GRID_RECT.y + screen_y * TILE, TILE, TILE)
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, (0, 0, 0), rect, 1)
        if hover_grid:
            hover_x = MAP_RECT.x + (hover_grid[0] - editor.camera_x) * TILE
            hover_y = MAP_RECT.y + (hover_grid[1] - editor.camera_y) * TILE
            pygame.draw.rect(screen, ACCENT, pygame.Rect(hover_x, hover_y, TILE, TILE), 2)
        for event_data in editor.map_data.get("events", []):
            sx = (int(event_data["x"]) - editor.camera_x) * TILE + GRID_RECT.x
            sy = (int(event_data["y"]) - editor.camera_y) * TILE + GRID_RECT.y
            if GRID_RECT.collidepoint((sx + 2, sy + 2)):
                if event_data.get("type") == "transition":
                    color = GOOD if event_data.get("activation", "step") == "step" else WARN
                    pygame.draw.polygon(screen, color, [(sx + TILE // 2, sy + 3), (sx + TILE - 3, sy + TILE // 2), (sx + TILE // 2, sy + TILE - 3), (sx + 3, sy + TILE // 2)])
                else:
                    pygame.draw.rect(screen, (190, 130, 240), pygame.Rect(sx + 5, sy + 5, TILE - 10, TILE - 10), border_radius=3)
        for mob in editor.fixed_mobs:
            sx = (int(mob["x"]) - editor.camera_x) * TILE + GRID_RECT.x
            sy = (int(mob["y"]) - editor.camera_y) * TILE + GRID_RECT.y
            if GRID_RECT.collidepoint((sx + TILE // 2, sy + TILE // 2)):
                color = GOOD if mob.get("enabled", True) else MUTED
                pygame.draw.circle(screen, color, (sx + TILE // 2, sy + TILE // 2), TILE // 2 - 3)
                draw_text(screen, str(mob.get("name", "?"))[:1], (sx + 6, sy + 3), 13, BG, True)

        horizontal_scroll.configure(int(editor.map_data["width"]), visible_x)
        vertical_scroll.configure(int(editor.map_data["height"]), visible_y)
        horizontal_scroll.value = editor.camera_x
        vertical_scroll.value = editor.camera_y
        if horizontal_scroll.maximum:
            horizontal_scroll.draw(screen, pygame.mouse.get_pos())
        if vertical_scroll.maximum:
            vertical_scroll.draw(screen, pygame.mouse.get_pos())

        pygame.draw.rect(screen, PANEL, pygame.Rect(960, 75, 225, 635), border_radius=10)
        draw_text(screen, "配置ツール（重ね置き対応）", (975, 80), 16, MUTED, True)
        transition_tools = (("step", "◆ 触れたら移動", GOOD, 105), ("interact", "◆ 調べたら移動", WARN, 137))
        for activation, label, color, y in transition_tools:
            selected = editor.placement_layer == "transition" and editor.transition_brush_activation == activation
            rect = pygame.Rect(970, y, 198, 28)
            pygame.draw.rect(screen, SELECTED if selected else PANEL_ALT, rect, border_radius=6)
            draw_text(screen, label, (rect.x + 10, rect.y + 5), 14, color, selected)
        mob_tool = pygame.Rect(970, 168, 198, 28)
        pygame.draw.rect(screen, SELECTED if editor.placement_layer == "fixed_mob" else PANEL_ALT, mob_tool, border_radius=6)
        draw_text(screen, "● 固定モブ配置", (mob_tool.x + 10, mob_tool.y + 5), 14, ACCENT, editor.placement_layer == "fixed_mob")
        draw_text(screen, "地形ブロック", (975, 201), 15, MUTED, True)
        for row, block in enumerate(editor.blocks[editor.block_offset:editor.block_offset + BLOCK_ROWS]):
            rect = pygame.Rect(970, 220 + row * 32, 198, 28)
            selected = editor.placement_layer == "block" and block["id"] == editor.selected_block
            pygame.draw.rect(screen, SELECTED if selected else PANEL_ALT, rect, border_radius=6)
            appearance = block.get("appearance", {})
            swatch = hex_color(appearance.get("value", "#777777")) if appearance.get("type") == "color" else (110, 95, 125)
            pygame.draw.rect(screen, swatch, pygame.Rect(rect.x + 6, rect.y + 5, 18, 18), border_radius=3)
            draw_text(screen, block.get("display_name", block["id"]), (rect.x + 32, rect.y + 5), 14)

        draw_text(screen, "生息モンスター", (975, 400), 17, MUTED, True)
        active_spawns = {item.get("species_id") for item in editor.map_data.get("spawns", [])}
        for row, species_id in enumerate(editor.species_ids[editor.species_offset:editor.species_offset + SPECIES_ROWS]):
            index = editor.species_offset + row
            rect = pygame.Rect(970, 425 + row * 20, 198, 18)
            if index == editor.selected_species:
                pygame.draw.rect(screen, SELECTED, rect, border_radius=4)
            draw_text(screen, ("● " if species_id in active_spawns else "○ ") + species_id, (975, rect.y), 13, GOOD if species_id in active_spawns else MUTED)
        block_scroll.configure(len(editor.blocks), BLOCK_ROWS)
        species_scroll.configure(len(editor.species_ids), SPECIES_ROWS)
        block_scroll.value = editor.block_offset
        species_scroll.value = editor.species_offset
        if block_scroll.maximum:
            block_scroll.draw(screen, pygame.mouse.get_pos())
        if species_scroll.maximum:
            species_scroll.draw(screen, pygame.mouse.get_pos())

        mouse = pygame.mouse.get_pos()
        for button in buttons:
            button.draw(screen, mouse)
        draw_status_bar(screen, editor.status, pygame.Rect(25, 710, 1150, 42), warning="未保存" in editor.status)

        if editor.map_picker_open:
            pygame.draw.rect(screen, (8, 12, 20), screen.get_rect())
            panel = pygame.Rect(240, 70, 720, 620)
            pygame.draw.rect(screen, PANEL, panel, border_radius=14)
            pygame.draw.rect(screen, ACCENT, panel, 2, border_radius=14)
            draw_text(screen, "編集するマップを一覧から選択", (270, 95), 28, ACCENT, True)
            draw_text(screen, "未保存の変更がある場合は切り替えません。", (270, 126), 15, MUTED)
            Button(pygame.Rect(650, 635, 130, 36), "新規マップ", editor.open_new_map_dialog).draw(screen, mouse)
            Button(pygame.Rect(790, 635, 130, 36), "閉じる", lambda: None).draw(screen, mouse)
            for row, map_id in enumerate(editor.map_ids[editor.map_offset:editor.map_offset + 10]):
                index = editor.map_offset + row
                rect = pygame.Rect(270, 150 + row * 48, 660, 40)
                pygame.draw.rect(screen, SELECTED if index == editor.map_index else PANEL_ALT, rect, border_radius=7)
                draw_text(screen, editor.map_names[map_id], (rect.x + 14, rect.y + 8), 18, TEXT, index == editor.map_index)
                draw_text(screen, map_id, (rect.x + 390, rect.y + 10), 15, ACCENT if index == editor.map_index else MUTED)

        if editor.new_map_dialog_open:
            pygame.draw.rect(screen, (8, 12, 20), screen.get_rect())
            panel = pygame.Rect(250, 70, 700, 620)
            pygame.draw.rect(screen, PANEL, panel, border_radius=14)
            pygame.draw.rect(screen, ACCENT, panel, 2, border_radius=14)
            draw_text(screen, "新しいマップを作成", (285, 98), 29, ACCENT, True)
            draw_text(screen, "作成直後から一覧と移動先候補へ追加されます。", (285, 135), 15, MUTED)
            Button(pygame.Rect(800, 105, 120, 36), "閉じる", lambda: None).draw(screen, mouse)
            editor.new_map_id.draw(screen, "マップID（半角小文字・数字・_・-）")
            editor.new_map_name.draw(screen, "画面に表示するマップ名")
            editor.new_map_width.draw(screen, "横幅 5～200")
            editor.new_map_height.draw(screen, "縦幅 5～200")
            draw_text(screen, "最初に敷き詰める地形ブロック", (435, 435), 17, MUTED, True)
            for index, block in enumerate(editor.blocks):
                rect = pygame.Rect(435 + (index % 3) * 112, 470 + (index // 3) * 32, 106, 27)
                selected = block["id"] == editor.new_map_fill_block
                pygame.draw.rect(screen, SELECTED if selected else PANEL_ALT, rect, border_radius=5)
                draw_text(screen, block.get("display_name", block["id"]), (rect.x + 6, rect.y + 5), 13, ACCENT if selected else MUTED, selected)
            Button(pygame.Rect(510, 610, 180, 44), "作成して開く", editor.create_new_map).draw(screen, mouse)

        if editor.preset_dialog_open:
            pygame.draw.rect(screen, (8, 12, 20), screen.get_rect())
            panel = pygame.Rect(65, 65, 1070, 625)
            pygame.draw.rect(screen, PANEL, panel, border_radius=14)
            pygame.draw.rect(screen, ACCENT, panel, 2, border_radius=14)
            draw_text(screen, "マッププリセット", (100, 92), 28, ACCENT, True)
            draw_text(screen, "通常マップと同じJSON形式で相互に読み込めます。", (100, 127), 15, MUTED)
            Button(pygame.Rect(1020, 100, 110, 36), "閉じる", lambda: None).draw(screen, mouse)
            draw_text(screen, f"保存済みプリセット  {len(editor.preset_ids)}件", (100, 157), 18, MUTED, True)
            for row, preset_id in enumerate(editor.preset_ids[editor.preset_offset:editor.preset_offset + 8]):
                index = editor.preset_offset + row
                rect = pygame.Rect(100, 190 + row * 45, 400, 38)
                pygame.draw.rect(screen, SELECTED if index == editor.selected_preset else PANEL_ALT, rect, border_radius=6)
                draw_text(screen, editor.preset_names[preset_id], (rect.x + 10, rect.y + 7), 16, TEXT, index == editor.selected_preset)
                draw_text(screen, preset_id, (rect.x + 245, rect.y + 9), 14, ACCENT if index == editor.selected_preset else MUTED)
            preset_scroll.configure(len(editor.preset_ids), 8)
            preset_scroll.value = editor.preset_offset
            if preset_scroll.maximum:
                preset_scroll.draw(screen, mouse)

            draw_text(screen, "現在のマップをプリセットとして保存", (570, 165), 18, MUTED, True)
            editor.preset_id.draw(screen, "プリセットID（半角小文字・数字・_・-）")
            editor.preset_name.draw(screen, "プリセット表示名")
            draw_text(screen, "選択プリセットから新規マップを作成", (570, 365), 18, MUTED, True)
            editor.preset_map_id.draw(screen, "新しいマップID")
            editor.preset_map_name.draw(screen, "新しいマップ表示名")
            Button(pygame.Rect(570, 550, 180, 42), "現在→保存", editor.save_current_as_preset).draw(screen, mouse)
            Button(pygame.Rect(760, 550, 160, 42), "現在へ適用", editor.apply_selected_preset).draw(screen, mouse)
            Button(pygame.Rect(930, 550, 160, 42), "新規マップ", editor.create_map_from_selected_preset).draw(screen, mouse)

        if editor.fixed_mob_dialog_open:
            pygame.draw.rect(screen, (8, 12, 20), screen.get_rect())
            panel = pygame.Rect(65, 65, 1070, 625)
            pygame.draw.rect(screen, PANEL, panel, border_radius=14)
            pygame.draw.rect(screen, ACCENT, panel, 2, border_radius=14)
            draw_text(screen, f"固定モブ編集：{editor.map_data['display_name']}", (100, 92), 28, ACCENT, True)
            Button(pygame.Rect(1020, 100, 110, 36), "閉じる", lambda: None).draw(screen, mouse)
            draw_text(screen, f"このマップの固定モブ  {len(editor.fixed_mobs)}体", (100, 165), 18, MUTED, True)
            for row, item in enumerate(editor.fixed_mobs[editor.fixed_mob_offset:editor.fixed_mob_offset + 8]):
                index = editor.fixed_mob_offset + row
                rect = pygame.Rect(100, 205 + row * 43, 400, 36)
                pygame.draw.rect(screen, SELECTED if index == editor.selected_fixed_mob else PANEL_ALT, rect, border_radius=6)
                ai_label = {"idle": "停止", "random": "ランダム", "chase": "追跡"}.get(str(item.get("ai", "idle")), "停止")
                draw_text(screen, f"{item.get('name', item.get('id', '?'))}  [{ai_label}]  ({item.get('x')}, {item.get('y')})", (rect.x + 10, rect.y + 8), 15, GOOD if item.get("enabled", True) else MUTED)
            Button(pygame.Rect(100, 590, 180, 40), "マップ上へ新規配置", editor.begin_fixed_mob_placement).draw(screen, mouse)

            draw_text(screen, "選択した固定モブ", (570, 165), 18, MUTED, True)
            editor.fixed_mob_id.draw(screen, "固定モブID")
            editor.fixed_mob_name.draw(screen, "表示名")
            editor.fixed_mob_level.draw(screen, "Lv")
            editor.fixed_mob_x.draw(screen, "初期 X")
            editor.fixed_mob_y.draw(screen, "初期 Y")
            editor.fixed_mob_interval.draw(screen, "移動間隔ms")
            editor.fixed_mob_chance.draw(screen, "移動頻度%")
            current_mob = editor.current_fixed_mob or {}
            ai_label = {"idle": "立ち止まる", "random": "ランダム移動", "chase": "プレイヤーへ向かう"}.get(str(current_mob.get("ai", "idle")), "立ち止まる")
            ai_rect = pygame.Rect(570, 350, 150, 40)
            interaction_rect = pygame.Rect(735, 350, 150, 40)
            enabled_rect = pygame.Rect(900, 350, 135, 40)
            despawn_rect = pygame.Rect(570, 410, 220, 40)
            respawn_rect = pygame.Rect(805, 410, 230, 40)
            pygame.draw.rect(screen, SELECTED, ai_rect, border_radius=7)
            pygame.draw.rect(screen, SELECTED, interaction_rect, border_radius=7)
            pygame.draw.rect(screen, GOOD if current_mob.get("enabled", True) else BAD, enabled_rect, border_radius=7)
            pygame.draw.rect(screen, WARN if current_mob.get("despawn_after_interaction", current_mob.get("despawn_after_talk", False)) else PANEL_ALT, despawn_rect, border_radius=7)
            pygame.draw.rect(screen, GOOD if current_mob.get("respawn_on_map_enter", True) else PANEL_ALT, respawn_rect, border_radius=7)
            draw_text(screen, f"AI: {ai_label}", (ai_rect.x + 10, ai_rect.y + 10), 14, TEXT, True)
            interaction_label = "戦闘" if current_mob.get("interaction", "talk") == "battle" else "会話"
            draw_text(screen, f"接触: {interaction_label}", (interaction_rect.x + 12, interaction_rect.y + 10), 14, TEXT, True)
            draw_text(screen, "出現する" if current_mob.get("enabled", True) else "出現しない", (enabled_rect.x + 24, enabled_rect.y + 10), 14, BG, True)
            despawns = current_mob.get("despawn_after_interaction", current_mob.get("despawn_after_talk", False))
            draw_text(screen, "会話/勝利後に消える: ON" if despawns else "会話/勝利後に消える: OFF", (despawn_rect.x + 12, despawn_rect.y + 10), 14, TEXT, True)
            draw_text(screen, "マップ再訪で復活: ON" if current_mob.get("respawn_on_map_enter", True) else "マップ再訪で復活: OFF", (respawn_rect.x + 12, respawn_rect.y + 10), 14, TEXT, True)
            editor.fixed_mob_dialogue.draw(screen, "会話デッキ（ | で区切る。3～5個推奨）")
            draw_text(screen, "移動間隔が速度、移動頻度が各タイミングで動く確率です。", (570, 545), 14, MUTED)
            Button(pygame.Rect(570, 570, 180, 42), "編集を反映", editor.apply_fixed_mob).draw(screen, mouse)
            Button(pygame.Rect(775, 570, 150, 42), "削除", editor.delete_fixed_mob).draw(screen, mouse)

        if editor.transition_dialog_open:
            pygame.draw.rect(screen, (8, 12, 20), screen.get_rect())
            panel = pygame.Rect(65, 65, 1070, 625)
            pygame.draw.rect(screen, PANEL, panel, border_radius=14)
            pygame.draw.rect(screen, ACCENT, panel, 2, border_radius=14)
            draw_text(screen, f"移動ポイント編集：{editor.map_data['display_name']}", (100, 92), 28, ACCENT, True)
            Button(pygame.Rect(1020, 100, 110, 36), "閉じる", lambda: None).draw(screen, mouse)
            draw_text(screen, "このマップの移動ポイント", (100, 165), 18, MUTED, True)
            for row, item in enumerate(editor.transitions[editor.transition_offset:editor.transition_offset + 8]):
                index = editor.transition_offset + row
                rect = pygame.Rect(100, 205 + row * 43, 400, 36)
                pygame.draw.rect(screen, SELECTED if index == editor.selected_transition else PANEL_ALT, rect, border_radius=6)
                condition = "触れたら" if item.get("activation", "step") == "step" else "調べたら"
                draw_text(screen, f"{item.get('id', '?')}  [{condition}]", (rect.x + 10, rect.y + 8), 15, GOOD if condition == "触れたら" else WARN)
            Button(pygame.Rect(100, 590, 180, 40), "マップ上へ新規配置", editor.begin_transition_placement).draw(screen, mouse)
            draw_text(screen, "選択した移動ポイント", (580, 165), 18, MUTED, True)
            editor.transition_id.draw(screen, "イベントID")
            editor.transition_x.draw(screen, "配置 X")
            editor.transition_y.draw(screen, "配置 Y")
            current = editor.current_transition
            activation = current.get("activation", "step") if current else ""
            step_rect = pygame.Rect(580, 280, 150, 38)
            interact_rect = pygame.Rect(740, 280, 150, 38)
            pygame.draw.rect(screen, GOOD if activation == "step" else PANEL_ALT, step_rect, border_radius=7)
            pygame.draw.rect(screen, WARN if activation == "interact" else PANEL_ALT, interact_rect, border_radius=7)
            draw_text(screen, "触れたら", (step_rect.x + 37, step_rect.y + 9), 17, BG if activation == "step" else TEXT, True)
            draw_text(screen, "調べたら", (interact_rect.x + 37, interact_rect.y + 9), 17, BG if activation == "interact" else TEXT, True)
            draw_text(screen, "移動先マップ（一覧上でホイール移動）", (580, 328), 16, MUTED)
            target_id = str(current.get("target", {}).get("map_id", "")) if current else ""
            for index, map_id in enumerate(editor.map_ids[editor.target_map_offset:editor.target_map_offset + 6]):
                rect = pygame.Rect(580 + (index % 2) * 130, 350 + (index // 2) * 28, 125, 24)
                pygame.draw.rect(screen, SELECTED if map_id == target_id else PANEL_ALT, rect, border_radius=5)
                draw_text(screen, editor.map_names[map_id], (rect.x + 6, rect.y + 4), 13, ACCENT if map_id == target_id else MUTED)
            editor.target_x.draw(screen, "移動先 X")
            editor.target_y.draw(screen, "移動先 Y")
            editor.transition_text.draw(screen, "移動時のメッセージ")
            Button(pygame.Rect(580, 570, 180, 42), "編集を反映", editor.apply_transition).draw(screen, mouse)
            Button(pygame.Rect(775, 570, 150, 42), "削除", editor.delete_transition).draw(screen, mouse)
            draw_text(screen, "緑=触れたら / 黄=調べたら", (580, 628), 15, GOOD)
        pygame.display.flip()
        clock.tick(60)
        frames += 1
        if smoke is not None and frames >= smoke:
            running = False
    pygame.quit()


if __name__ == "__main__":
    main()

