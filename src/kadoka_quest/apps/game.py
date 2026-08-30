from __future__ import annotations

from datetime import datetime
import random
import subprocess
import sys
from uuid import uuid4

import pygame

from kadoka_quest.core.ai import TACTICS, default_ai
from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.core.field_engine import FieldEngine
from kadoka_quest.core.grid_movement import GridMovement
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.parties import PartyStore
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.data.state import StateStore
from kadoka_quest.paths import ASSET_ROOT, IMPORT_ROOT, PROJECT_ROOT
from kadoka_quest.ui.common import ACCENT, BAD, BG, GOOD, MUTED, PANEL, PANEL_ALT, SELECTED, TEXT, WARN, Button, draw_text, draw_wrapped, init_pygame, smoke_frames
from kadoka_quest.ui.field_renderer import FIELD_RECT, TILE, draw_field


SCREEN_SIZE = (1120, 740)
PASSWORD = "へいわなすみか"
KANA_KEYS = tuple("あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん")
MOVE_KEY_VECTORS = {
    pygame.K_LEFT: (-1, 0),
    pygame.K_a: (-1, 0),
    pygame.K_RIGHT: (1, 0),
    pygame.K_d: (1, 0),
    pygame.K_UP: (0, -1),
    pygame.K_w: (0, -1),
    pygame.K_DOWN: (0, 1),
    pygame.K_s: (0, 1),
}
MOVE_REPEAT_DELAY_MS = 180
MOVE_REPEAT_INTERVAL_MS = 90
PLAYER_MOVE_DURATION_MS = 120
FIXED_MOB_MOVE_DURATION_MS = 180
HOME_MARU_MOVE_INTERVAL_MS = 450
HOME_KADOKA_MOVE_INTERVAL_MS = 900
HIDDEN_CHASE_MOVE_INTERVAL_MS = 320
HIDDEN_WANDER_MOVE_INTERVAL_MS = 950
HIDDEN_VISION_RANGE = 8
BATTLE_LOG_INITIAL_DELAY_MS = 140
BATTLE_ACTION_DELAY_MS = 560
BATTLE_SHORT_LOG_DELAY_MS = 300
BATTLE_NEXT_ROUND_DELAY_MS = 600


def hex_color(value: str) -> tuple[int, int, int]:
    try:
        clean = value.lstrip("#")
        return tuple(int(clean[index:index + 2], 16) for index in (0, 2, 4))
    except (TypeError, ValueError):
        return (130, 130, 130)


class KadokaQuest:
    def __init__(
        self,
        repository: GameRepository | None = None,
        monsters: MonsterStore | None = None,
        states: StateStore | None = None,
        parties: PartyStore | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.repository = repository or GameRepository()
        self.monsters = monsters or MonsterStore(repository=self.repository)
        self.states = states or StateStore()
        self.state = self.states.load()
        self.states.ensure_starters(self.state, self.monsters)
        self.parties = parties or PartyStore()
        self.rng = rng or random.Random()
        self.map_data = self.repository.get_map(str(self.state.get("map_id", "starting_town")))
        self.blocks = {item["id"]: item for item in self.repository.list_blocks()}
        self.field = FieldEngine(self.map_data, self.blocks)
        self.player_x = int(self.state.get("player", {}).get("x", self.map_data["start"]["x"]))
        self.player_y = int(self.state.get("player", {}).get("y", self.map_data["start"]["y"]))
        self.player_movement = GridMovement(self.player_x, self.player_y, PLAYER_MOVE_DURATION_MS)
        self.player_direction = "front"
        self.mode = "field"
        self.battle: BattleEngine | None = None
        self.battle_finalized = False
        self.battle_selection = 0
        self.auto_battle = False
        self.last_auto_tick = 0
        self.battle_playback = False
        self.battle_visible_log_count = 0
        self.battle_next_log_tick = 0
        self.battle_action_line = ""
        self.battle_focus_id: str | None = None
        self.simulation = False
        self.status = "矢印/WASDで移動（長押し対応）。見えない野生モンスターも裏で歩いています。"
        self.selected_party = 0
        self.preset_index = 0
        self.hidden_monsters: list[dict] = []
        self.home_npcs: list[dict] = []
        self.fixed_mob_battle_id: str | None = None
        self.password_input = ""
        self.password_message = ""
        self.image_cache: dict[tuple[str, str, int, int], pygame.Surface | None] = {}
        self.manager_process: subprocess.Popen | None = None
        self.held_move_key: int | None = None
        self.next_move_tick = 0
        self.reset_hidden_monsters()
        self.reset_home_npcs()

    def party(self) -> list[MonsterRecord]:
        return StateStore.party_records(self.state, self.monsters)

    def save_position(self) -> None:
        self.state["map_id"] = str(self.map_data["id"])
        self.state["player"] = {"x": self.player_x, "y": self.player_y}
        self.states.save(self.state)

    def change_map(self, map_id: str, x: int, y: int, message: str | None = None) -> None:
        self.map_data = self.repository.get_map(map_id)
        self.field.set_world(self.map_data, self.blocks)
        self.player_x = max(0, min(int(self.map_data["width"]) - 1, int(x)))
        self.player_y = max(0, min(int(self.map_data["height"]) - 1, int(y)))
        self.player_movement.snap(self.player_x, self.player_y)
        self.save_position()
        self.reset_hidden_monsters()
        self.reset_home_npcs()
        self.status = message or f"{self.map_data['display_name']}へ入りました。"

    def move(self, dx: int, dy: int, now: int | None = None) -> None:
        now = pygame.time.get_ticks() if now is None else int(now)
        self.field.set_world(self.map_data, self.blocks)
        result = self.field.resolve_player_move(
            self.player_x,
            self.player_y,
            dx,
            dy,
            self.player_direction,
            self.home_npcs,
            self.hidden_monsters,
        )
        self.player_direction = str(result["direction"])
        reason = result["reason"]
        if reason == "hidden_character":
            hidden = result["character"]
            self.start_wild_battle(hidden["spawn"], hidden)
            return
        if reason == "visible_character":
            self.status = "そこにはキャラクターがいるため移動できません。"
            return
        if reason == "blocking_event":
            blocking_event = result["event"]
            self.status = str(blocking_event.get("blocked_text", "そこには障害物があり、通り抜けられません。"))
            return
        if reason == "blocked_tile":
            block_id = result["block_id"]
            block = result["block"]
            self.status = f"{block.get('display_name', block_id)} は通れません。"
            return
        if result["kind"] != "moved":
            return
        self.player_x, self.player_y = int(result["x"]), int(result["y"])
        self.player_movement.move_to(self.player_x, self.player_y, now)
        self.save_position()
        if self.handle_step_event():
            return
        if self.check_hidden_collision():
            return

    def character_at(self, x: int, y: int, *, include_hidden: bool = True, include_home: bool = True) -> dict | None:
        if include_home:
            found = next((npc for npc in self.home_npcs if (int(npc["x"]), int(npc["y"])) == (int(x), int(y))), None)
            if found:
                return found
        if include_hidden:
            return next((monster for monster in self.hidden_monsters if (int(monster["x"]), int(monster["y"])) == (int(x), int(y))), None)
        return None

    def player_front_position(self) -> tuple[int, int]:
        self.field.set_world(self.map_data, self.blocks)
        return self.field.front_position(self.player_x, self.player_y, self.player_direction)

    def start_held_move(self, key: int, now: int) -> bool:
        vector = MOVE_KEY_VECTORS.get(key)
        if vector is None or self.mode != "field":
            return False
        self.held_move_key = key
        self.next_move_tick = int(now) + MOVE_REPEAT_DELAY_MS
        self.move(*vector, now=now)
        return True

    def stop_held_move(self, key: int) -> None:
        if key == self.held_move_key:
            self.held_move_key = None

    def update_held_move(self, now: int) -> bool:
        if self.mode != "field" or self.held_move_key not in MOVE_KEY_VECTORS:
            self.held_move_key = None
            return False
        if int(now) < self.next_move_tick:
            return False
        self.move(*MOVE_KEY_VECTORS[self.held_move_key], now=now)
        self.next_move_tick = int(now) + MOVE_REPEAT_INTERVAL_MS
        return True

    def handle_step_event(self) -> bool:
        self.field.set_world(self.map_data, self.blocks)
        event = self.field.step_transition_at(self.player_x, self.player_y)
        if event is None:
            return False
        target = event["target"]
        self.change_map(str(target["map_id"]), int(target["x"]), int(target["y"]))
        return True

    def nearby_event(self) -> dict | None:
        self.field.set_world(self.map_data, self.blocks)
        return self.field.nearby_event(self.player_x, self.player_y)

    def interact(self) -> None:
        npc = self.nearby_home_npc()
        if npc:
            npc["direction"] = {"left": "right", "right": "left", "back": "front", "front": "back"}.get(self.player_direction, "front")
            self.status = f"{npc.get('name', npc['species_id'])}『{self.next_npc_dialogue(npc)}』"
            if npc.get("interaction", "talk") == "battle":
                level = max(1, min(100, int(npc.get("level", 1))))
                self.start_wild_battle({"species_id": npc["species_id"], "min_level": level, "max_level": level})
                if self.mode == "battle":
                    self.fixed_mob_battle_id = str(npc["id"])
            elif npc.get("despawn_after_interaction", npc.get("despawn_after_talk", False)):
                self.despawn_fixed_mob(npc)
            return
        event = self.nearby_event()
        if not event:
            self.status = "近くに調べられるものはありません。"
            return
        event_type = str(event.get("type", "message"))
        self.status = str(event.get("text", "何もない。"))
        if event_type == "transition" and event.get("activation") == "interact":
            target = event["target"]
            message = self.status
            self.change_map(str(target["map_id"]), int(target["x"]), int(target["y"]), message)
        elif event_type == "church":
            self.state["revive_point"] = dict(event["revive"])
            self.states.save(self.state)
        elif event_type == "password_spring":
            self.open_password_input()
        elif event_type == "open_manager":
            self.open_manager()
        elif event.get("id") == "orange_tree":
            inventory = self.state.setdefault("inventory", {})
            inventory["orange"] = int(inventory.get("orange", 0)) + 1
            self.states.save(self.state)

    def reacquire_ghosts(self) -> None:
        added = []
        for species_id in ("maru", "kadoka"):
            if not any(record.species_id == species_id for record in self.monsters.list_records()):
                record = self.monsters.create(species_id, level=1, source="ghost_home_password")
                added.append(record.name)
        self.state.setdefault("flags", {})["ghost_entrance_open"] = True
        self.states.save(self.state)
        self.status = "へいわなすみか。" + (f" 牧場に {'・'.join(added)} が増えました。" if added else " 2匹とも既にいます。")

    def open_password_input(self) -> None:
        self.mode = "password"
        self.password_input = ""
        self.password_message = "7文字のあいことばを入力してください。"

    def append_password(self, character: str) -> None:
        if character in KANA_KEYS and len(self.password_input) < 7:
            self.password_input += character
            self.password_message = ""

    def backspace_password(self) -> None:
        self.password_input = self.password_input[:-1]
        self.password_message = ""

    def submit_password(self) -> bool:
        if self.password_input != PASSWORD:
            self.password_message = "あいことばが違います。"
            return False
        self.mode = "field"
        self.reacquire_ghosts()
        return True

    def cancel_password(self) -> None:
        self.mode = "field"
        self.password_input = ""
        self.status = "水の湧き場から離れました。"

    def reset_home_npcs(self) -> None:
        self.home_npcs = []
        now = pygame.time.get_ticks()
        despawned = set(self.state.get("despawned_fixed_mobs", []))
        for source in self.map_data.get("fixed_mobs", []):
            key = f"{self.map_data['id']}:{source.get('id', '')}"
            if not source.get("enabled", True) or (not source.get("respawn_on_map_enter", True) and key in despawned):
                continue
            npc = dict(source)
            npc.setdefault("id", f"fixed_mob_{len(self.home_npcs) + 1}")
            npc.setdefault("name", self.repository.get_species(str(npc["species_id"])).definition.get("display_name", npc["species_id"]))
            npc.setdefault("direction", "front")
            npc.setdefault("ai", "idle")
            npc.setdefault("move_interval_ms", 900)
            npc.setdefault("move_chance", 100)
            npc.setdefault("dialogue", ["……"])
            npc["move_count"] = 0
            npc["next_move_tick"] = now + max(100, int(npc["move_interval_ms"]))
            npc["dialogue_remaining"] = []
            npc["last_dialogue"] = None
            self.home_npcs.append(npc)

        occupied = {(self.player_x, self.player_y)}
        for npc in self.home_npcs:
            if (int(npc["x"]), int(npc["y"])) in occupied:
                replacement = next((
                    (x, y)
                    for y, row in enumerate(self.map_data["tiles"])
                    for x, block_id in enumerate(row)
                    if self.blocks.get(block_id, {}).get("player_walkable") and (x, y) not in occupied
                ), None)
                if replacement:
                    npc["x"], npc["y"] = replacement
            occupied.add((int(npc["x"]), int(npc["y"])))
        for npc in self.home_npcs:
            npc["_movement"] = GridMovement(int(npc["x"]), int(npc["y"]), FIXED_MOB_MOVE_DURATION_MS)

    def nearby_home_npc(self) -> dict | None:
        front = self.player_front_position()
        return next((npc for npc in self.home_npcs if (int(npc["x"]), int(npc["y"])) == front), None)

    def next_npc_dialogue(self, npc: dict) -> str:
        deck = [str(line).strip() for line in npc.get("dialogue", []) if str(line).strip()] or ["……"]
        remaining = npc.setdefault("dialogue_remaining", [])
        if not remaining:
            remaining.extend(deck)
            self.rng.shuffle(remaining)
            if len(remaining) > 1 and remaining[-1] == npc.get("last_dialogue"):
                remaining[0], remaining[-1] = remaining[-1], remaining[0]
        line = remaining.pop()
        npc["last_dialogue"] = line
        return line

    def despawn_fixed_mob(self, npc: dict) -> None:
        if npc in self.home_npcs:
            self.home_npcs.remove(npc)
        if not npc.get("respawn_on_map_enter", True):
            key = f"{self.map_data['id']}:{npc['id']}"
            despawned = self.state.setdefault("despawned_fixed_mobs", [])
            if key not in despawned:
                despawned.append(key)
            self.states.save(self.state)

    @staticmethod
    def npc_front_position(npc: dict) -> tuple[int, int]:
        vectors = {"left": (-1, 0), "right": (1, 0), "back": (0, -1), "front": (0, 1)}
        dx, dy = vectors.get(str(npc.get("direction", "front")), (0, 1))
        return int(npc["x"]) + dx, int(npc["y"]) + dy

    def npc_faces_player(self, npc: dict) -> bool:
        return self.npc_front_position(npc) == (self.player_x, self.player_y)

    def move_home_npcs(self) -> None:
        if self.mode != "field" or not self.home_npcs:
            return
        for npc in self.home_npcs:
            self.move_home_npc(npc)

    def move_home_npc(self, npc: dict, now: int | None = None) -> bool:
        now = pygame.time.get_ticks() if now is None else int(now)
        ai = str(npc.get("ai", "idle"))
        if ai == "idle" or self.npc_faces_player(npc):
            return False
        chance = max(0, min(100, int(npc.get("move_chance", 100))))
        if self.rng.randrange(100) >= chance:
            return False
        occupied = {(self.player_x, self.player_y)} | {
            (int(other["x"]), int(other["y"])) for other in self.home_npcs if other is not npc
        }
        if ai == "chase":
            mx, my = int(npc["x"]), int(npc["y"])
            horizontal = (1 if self.player_x > mx else -1 if self.player_x < mx else 0, 0)
            vertical = (0, 1 if self.player_y > my else -1 if self.player_y < my else 0)
            directions = [direction for direction in (horizontal, vertical) if direction != (0, 0)]
            fallback = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            self.rng.shuffle(fallback)
            directions.extend(direction for direction in fallback if direction not in directions)
        else:
            directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            self.rng.shuffle(directions)
        for dx, dy in directions:
            x, y = int(npc["x"]) + dx, int(npc["y"]) + dy
            self.field.set_world(self.map_data, self.blocks)
            if self.field.tile_allows(x, y, "player_walkable") and (x, y) not in occupied:
                npc["x"], npc["y"] = x, y
                movement = npc.get("_movement")
                if not isinstance(movement, GridMovement):
                    movement = GridMovement(x - dx, y - dy, FIXED_MOB_MOVE_DURATION_MS)
                    npc["_movement"] = movement
                movement.move_to(x, y, now)
                if dx or dy:
                    npc["move_count"] = int(npc.get("move_count", 0)) + 1
                if dx < 0:
                    npc["direction"] = "left"
                elif dx > 0:
                    npc["direction"] = "right"
                elif dy < 0:
                    npc["direction"] = "back"
                elif dy > 0:
                    npc["direction"] = "front"
                return bool(dx or dy)
        return False

    def character_image(self, species_id: str, kind: str, size: tuple[int, int]) -> pygame.Surface | None:
        key = (species_id, kind, size[0], size[1])
        if key in self.image_cache:
            return self.image_cache[key]
        definition = self.repository.get_species(species_id).definition
        if kind.startswith("field"):
            direction = kind.removeprefix("field_") if kind != "field" else "front"
            relative = definition.get("field_sprites", {}).get(direction) or definition.get("field_sprite_path")
        else:
            relative = definition.get("portrait_path")
        if not relative:
            self.image_cache[key] = None
            return None
        try:
            source = pygame.image.load(str(ASSET_ROOT / str(relative))).convert_alpha()
            if kind.startswith("field"):
                bounds = source.get_bounding_rect(min_alpha=8)
                if bounds.width and bounds.height:
                    source = source.subsurface(bounds).copy()
            ratio = min(size[0] / source.get_width(), size[1] / source.get_height())
            # Pixel art is always enlarged with nearest-neighbour sampling.
            scaled = pygame.transform.scale(source, (max(1, round(source.get_width() * ratio)), max(1, round(source.get_height() * ratio))))
        except (OSError, pygame.error, ValueError):
            scaled = None
        self.image_cache[key] = scaled
        return scaled

    def field_pickup(self) -> None:
        picker = next((record for record in self.party() if record.species_id in {"maru", "kadoka"}), None)
        if not picker:
            self.status = "まるかかどかをパーティに入れると『ものを拾う』を使えます。"
            return
        inventory = self.state.setdefault("inventory", {})
        if picker.species_id == "maru":
            item = self.rng.choice(["小石", "曲がった釘", "空き瓶", "変な布", "木の枝"])
        else:
            roll = self.rng.random()
            item = "柿" if roll < 0.05 else "みかん" if roll < 0.8 else "小石"
        inventory[item] = int(inventory.get(item, 0)) + 1
        self.states.save(self.state)
        self.status = f"{picker.name}が{item}を拾ってきました。"

    def spawn_options(self) -> list[dict]:
        flags = self.state.get("flags", {})
        return [
            entry for entry in self.map_data.get("spawns", [])
            if entry.get("species_id") != "ball_slime"
            and (not entry.get("requires_flag") or flags.get(entry["requires_flag"], False))
        ]

    def reset_hidden_monsters(self) -> None:
        self.hidden_monsters = []
        options = self.spawn_options()
        if not options:
            return
        spawn_tiles = [
            (x, y)
            for y, row in enumerate(self.map_data["tiles"])
            for x, block_id in enumerate(row)
            if self.blocks.get(block_id, {}).get("enemy_spawnable")
            and self.blocks.get(block_id, {}).get("enemy_walkable")
            and (x, y) != (self.player_x, self.player_y)
        ]
        self.rng.shuffle(spawn_tiles)
        population = min(len(spawn_tiles), max(12, min(24, int(self.map_data["width"] * self.map_data["height"]) // 60)))
        weights = [int(item.get("weight", 1)) for item in options]
        for x, y in spawn_tiles[:population]:
            spawn = self.rng.choices(options, weights=weights)[0]
            self.hidden_monsters.append({"x": x, "y": y, "spawn": dict(spawn), "next_move_tick": pygame.time.get_ticks() + HIDDEN_WANDER_MOVE_INTERVAL_MS})

    def move_hidden_monsters(self) -> None:
        if self.mode != "field":
            return
        for monster in list(self.hidden_monsters):
            self.move_hidden_monster(monster)
            if self.check_hidden_collision():
                return

    def monster_sees_player(self, monster: dict) -> bool:
        mx, my = int(monster["x"]), int(monster["y"])
        if mx != self.player_x and my != self.player_y:
            return False
        distance = abs(mx - self.player_x) + abs(my - self.player_y)
        if distance > HIDDEN_VISION_RANGE:
            return False
        self.field.set_world(self.map_data, self.blocks)
        return self.field.has_clear_axis_path((mx, my), (self.player_x, self.player_y), "enemy_walkable")

    def move_hidden_monster(self, monster: dict) -> bool:
        sees_player = self.monster_sees_player(monster)
        mx, my = int(monster["x"]), int(monster["y"])
        if sees_player:
            dx = 0 if mx == self.player_x else (1 if self.player_x > mx else -1)
            dy = 0 if my == self.player_y else (1 if self.player_y > my else -1)
            directions = [(dx, dy), (0, 0)]
        else:
            directions = [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]
            self.rng.shuffle(directions)
        occupied = {(self.player_x, self.player_y)} | {
            (int(other["x"]), int(other["y"])) for other in self.hidden_monsters if other is not monster
        } | {(int(npc["x"]), int(npc["y"])) for npc in self.home_npcs}
        for dx, dy in directions:
            x, y = mx + dx, my + dy
            self.field.set_world(self.map_data, self.blocks)
            if self.field.tile_allows(x, y, "enemy_walkable") and (x, y) not in occupied:
                monster["x"], monster["y"] = x, y
                monster["sees_player"] = sees_player
                return bool(dx or dy)
        monster["sees_player"] = sees_player
        return False

    def update_field_mobs(self, now: int) -> bool:
        if self.mode != "field":
            return False
        moved = False
        for npc in self.home_npcs:
            interval = max(100, int(npc.get("move_interval_ms", 900)))
            if int(now) >= int(npc.get("next_move_tick", 0)):
                moved = self.move_home_npc(npc, now) or moved
                npc["next_move_tick"] = int(now) + interval
        for monster in list(self.hidden_monsters):
            if int(now) < int(monster.get("next_move_tick", 0)):
                continue
            moved = self.move_hidden_monster(monster) or moved
            interval = HIDDEN_CHASE_MOVE_INTERVAL_MS if monster.get("sees_player") else HIDDEN_WANDER_MOVE_INTERVAL_MS
            monster["next_move_tick"] = int(now) + interval
            if self.check_hidden_collision():
                return True
        return moved

    def check_hidden_collision(self) -> bool:
        front = self.player_front_position()
        for monster in self.hidden_monsters:
            if (int(monster["x"]), int(monster["y"])) == front:
                self.start_wild_battle(monster["spawn"], monster)
                return True
        return False

    def make_wild(self, spawn: dict) -> MonsterRecord:
        species_id = str(spawn["species_id"])
        bundle = self.repository.get_species(species_id)
        level = self.rng.randint(int(spawn.get("min_level", 1)), int(spawn.get("max_level", 1)))
        monster = {
            "schema_version": 1,
            "id": f"wild_{uuid4().hex[:10]}",
            "species_id": species_id,
            "name": str(bundle.definition["display_name"]),
            "level": level,
            "experience": 0,
            "plus_choices": [],
            "equipment_id": None,
            "source": "wild",
        }
        return MonsterRecord(monster, default_ai(str(bundle.definition.get("ai_profile", "normal"))))

    def start_wild_battle(self, spawn: dict | None = None, hidden_monster: dict | None = None) -> None:
        options = self.spawn_options()
        if (not spawn and not options) or not self.party():
            return
        if spawn is None:
            spawn = self.rng.choices(options, weights=[int(item.get("weight", 1)) for item in options])[0]
        enemies = [self.make_wild(spawn)]
        if hidden_monster in self.hidden_monsters:
            self.hidden_monsters.remove(hidden_monster)
        self.battle = BattleEngine(self.repository, self.party(), enemies, self.rng, learning_enabled=True)
        self.reset_battle_presentation()
        self.mode = "battle"
        self.battle_selection = 0
        self.auto_battle = False
        self.last_auto_tick = pygame.time.get_ticks()
        self.simulation = False
        self.battle_finalized = False
        self.status = f"{', '.join(record.name for record in enemies)} が現れた。"

    def start_simulation(self) -> None:
        imported = self.monsters.discover_external(IMPORT_ROOT / "simulation")
        if not imported:
            self.status = "imports/simulation に個体フォルダを置いてください。"
            return
        try:
            self.battle = BattleEngine(self.repository, self.party(), imported, self.rng, learning_enabled=False)
        except (OSError, ValueError, KeyError) as exc:
            self.status = f"模擬戦個体を読めません: {exc}"
            return
        self.reset_battle_presentation()
        self.mode = "battle"
        self.battle_selection = 0
        self.auto_battle = False
        self.last_auto_tick = pygame.time.get_ticks()
        self.simulation = True
        self.battle_finalized = False
        self.status = "模擬戦を開始。双方のAIは更新されません。"

    def handle_battle_command(self, command: str) -> None:
        if not self.battle or self.battle.outcome or self.battle_playback:
            return
        log_start = len(self.battle.log)
        if command == "fight":
            self.battle.run_round()
        elif command == "scout":
            success, target, _ = self.battle.try_scout()
            if success and target:
                acquired = self.monsters.create(target.species_id, level=target.level, source="scout")
                party = list(self.state.get("current_party", []))
                if len(party) < 4:
                    party.append(acquired.monster_id)
                    self.state["current_party"] = party
                self.states.save(self.state)
        elif command == "item":
            inventory = self.state.setdefault("inventory", {})
            if int(inventory.get("orange", 0)) <= 0:
                self.battle.log.append("みかんを持っていない。")
            else:
                inventory["orange"] = int(inventory.get("orange", 0)) - 1
                self.states.save(self.state)
                self.battle.use_party_item()
                self.battle.run_round()
        elif command == "run":
            if self.simulation:
                self.battle.log.append("模擬戦から退出した。")
                self.battle.outcome = "escaped"
            else:
                self.battle.try_run()
                if not self.battle.outcome:
                    self.battle.run_round()
        self.start_battle_playback(log_start)
        if not self.battle_playback:
            self.finalize_battle_if_needed()

    def reset_battle_presentation(self) -> None:
        self.battle_playback = False
        self.battle_visible_log_count = len(self.battle.log) if self.battle else 0
        self.battle_next_log_tick = 0
        self.battle_action_line = ""
        self.battle_focus_id = None

    def start_battle_playback(self, log_start: int) -> None:
        if not self.battle or len(self.battle.log) <= log_start:
            return
        self.battle_visible_log_count = min(self.battle_visible_log_count, log_start)
        self.battle_playback = True
        self.battle_action_line = "行動を開始します……"
        self.battle_focus_id = None
        self.battle_next_log_tick = pygame.time.get_ticks() + BATTLE_LOG_INITIAL_DELAY_MS

    @staticmethod
    def battle_log_delay(line: str) -> int:
        if line.startswith(("---", "会心！")) or line in {"勝利した！", "パーティは戦闘不能になった。"} or "たおれた" in line:
            return BATTLE_SHORT_LOG_DELAY_MS
        return BATTLE_ACTION_DELAY_MS

    def update_battle_playback(self, now: int | None = None) -> bool:
        if not self.battle_playback or not self.battle:
            return False
        now = pygame.time.get_ticks() if now is None else int(now)
        if now < self.battle_next_log_tick:
            return False
        if self.battle_visible_log_count < len(self.battle.log):
            line = self.battle.log[self.battle_visible_log_count]
            self.battle_visible_log_count += 1
            self.battle_action_line = line
            if line.startswith("---"):
                self.battle_focus_id = None
            else:
                for member in [*self.battle.allies, *self.battle.enemies]:
                    if line.startswith(member.name):
                        self.battle_focus_id = member.record.monster_id
                        break
            self.battle_next_log_tick = now + self.battle_log_delay(line)
            return True
        self.battle_playback = False
        self.battle_focus_id = None
        self.last_auto_tick = now
        self.finalize_battle_if_needed()
        self.battle_visible_log_count = len(self.battle.log)
        return True

    def selected_battle_command(self) -> str:
        return ("fight", "scout", "item", "run")[self.battle_selection % 4]

    def toggle_auto_battle(self) -> None:
        if not self.battle or self.battle.outcome:
            return
        self.auto_battle = not self.auto_battle
        self.last_auto_tick = pygame.time.get_ticks()
        self.status = "オート戦闘を開始しました。" if self.auto_battle else "オート戦闘を停止しました。"

    def update_auto_battle(self) -> None:
        if not self.auto_battle or self.battle_playback or self.mode != "battle" or not self.battle or self.battle.outcome:
            return
        now = pygame.time.get_ticks()
        if now - self.last_auto_tick < BATTLE_NEXT_ROUND_DELAY_MS:
            return
        self.last_auto_tick = now
        self.handle_battle_command("fight")
        if self.battle and self.battle.outcome:
            self.auto_battle = False

    def finalize_battle_if_needed(self) -> None:
        if not self.battle or not self.battle.outcome or self.battle_finalized or self.battle_playback:
            return
        self.battle_finalized = True
        self.auto_battle = False
        self.battle.mark_battle_complete()
        if self.battle.learning_enabled:
            self.monsters.save_all_ai(member.record for member in self.battle.allies)
            if self.battle.outcome == "victory":
                self.award_experience()

    def award_experience(self) -> None:
        if not self.battle:
            return
        gained = 8 + sum(enemy.record.level * 3 for enemy in self.battle.enemies)
        for ally in self.battle.allies:
            record = self.monsters.get(ally.record.monster_id)
            if not record or record.level >= 100:
                continue
            record.monster["experience"] = int(record.monster.get("experience", 0)) + gained
            while record.monster["level"] < 100:
                threshold = int(record.monster["level"]) * 24
                if record.monster["experience"] < threshold:
                    break
                record.monster["experience"] -= threshold
                record.monster["level"] += 1
                self.battle.log.append(f"{record.name}はLv{record.monster['level']}になった。")
            self.monsters.save(record)

    def return_to_field(self) -> None:
        outcome = self.battle.outcome if self.battle else None
        was_simulation = self.simulation
        fixed_mob_battle_id = self.fixed_mob_battle_id
        self.mode = "field"
        self.battle = None
        self.simulation = False
        self.fixed_mob_battle_id = None
        if outcome == "defeat" and not was_simulation:
            self.revive_at_church()
        else:
            if outcome == "victory" and fixed_mob_battle_id:
                fixed_mob = next((npc for npc in self.home_npcs if str(npc.get("id")) == fixed_mob_battle_id), None)
                if fixed_mob and fixed_mob.get("despawn_after_interaction", fixed_mob.get("despawn_after_talk", False)):
                    self.despawn_fixed_mob(fixed_mob)
            self.status = "フィールドへ戻りました。"
            if self.spawn_options() and len(self.hidden_monsters) < 3:
                self.reset_hidden_monsters()

    def revive_at_church(self) -> None:
        revive = self.state.get("revive_point", {"map_id": "starting_town", "x": 18, "y": 11, "name": "はじまりの街の教会"})
        self.change_map(str(revive["map_id"]), int(revive["x"]), int(revive["y"]), f"全滅しました。{revive.get('name', '教会')}から復活しました。")

    def scan_acquire(self) -> None:
        added, skipped = self.monsters.acquire_from_scan(IMPORT_ROOT / "acquire")
        self.status = f"個体再走査：{added}体を獲得、{skipped}件をスキップ。"

    def open_manager(self) -> None:
        if self.manager_process and self.manager_process.poll() is None:
            self.status = "牧場台帳は既に開いています。"
            return
        self.manager_process = subprocess.Popen([sys.executable, str(PROJECT_ROOT / "manage.py")], cwd=PROJECT_ROOT)
        self.status = "牧場台帳を開きました。個体管理とパーティ編成ができます。"

    def refresh_manager_if_closed(self) -> None:
        if not self.manager_process or self.manager_process.poll() is None:
            return
        self.manager_process = None
        self.state = self.states.load()
        self.status = "牧場台帳の変更をゲームへ反映しました。"

    def save_preset(self) -> None:
        name = "フィールド編成_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.parties.save(name, list(self.state.get("current_party", [])))
        self.status = f"{path.name} を保存しました。"

    def load_next_preset(self) -> None:
        presets = self.parties.list_presets()
        if not presets:
            self.status = "保存パーティがありません。"
            return
        path = presets[self.preset_index % len(presets)]
        self.preset_index += 1
        loaded = self.parties.load(path, self.monsters)
        self.state["current_party"] = [record.monster_id for record in loaded if record]
        self.states.save(self.state)
        self.status = f"{path.name} を読み込みました。欠損IDは空き枠です。"

    def cycle_tactic(self) -> None:
        party = self.party()
        if not party:
            return
        self.selected_party %= len(party)
        record = party[self.selected_party]
        current = str(record.ai.get("tactic", "balanced"))
        index = TACTICS.index(current) if current in TACTICS else 0
        next_value = TACTICS[(index + 1) % len(TACTICS)]
        self.monsters.set_tactic(record.monster_id, next_value)
        self.status = f"{record.name} の行動指針: {next_value}"

    def reset_selected_ai(self) -> None:
        party = self.party()
        if not party:
            return
        self.selected_party %= len(party)
        record = party[self.selected_party]
        self.monsters.reset_ai(record.monster_id)
        self.status = f"{record.name} のAIのみリセットしました。"


def draw_combatant(screen: pygame.Surface, game: KadokaQuest, member, rect: pygame.Rect, ally: bool) -> None:
    pygame.draw.rect(screen, PANEL_ALT, rect, border_radius=10)
    focused = game.battle_focus_id == member.record.monster_id
    if focused:
        pygame.draw.rect(screen, WARN if not ally else GOOD, rect, 4, border_radius=10)
    definition = game.repository.get_species(member.record.species_id).definition
    color = hex_color(definition.get("appearance", {}).get("value", "#888888"))
    center = (rect.x + 47 if ally else rect.right - 47, rect.y + 55)
    portrait = game.character_image(member.record.species_id, "portrait", (82, 82))
    if portrait:
        screen.blit(portrait, portrait.get_rect(center=center))
    else:
        pygame.draw.circle(screen, color, center, 35)
        symbol = definition.get("appearance", {}).get("symbol", "?")
        symbol_image = pygame.font.SysFont(["Meiryo", "Arial"], 24, bold=True).render(str(symbol), True, BG)
        screen.blit(symbol_image, symbol_image.get_rect(center=center))
    text_x = rect.x + 95 if ally else rect.x + 12
    draw_text(screen, f"{member.name} Lv{member.record.level}", (text_x, rect.y + 13), 18, TEXT, True)
    hp_color = GOOD if member.hp / member.stats["hp"] > 0.35 else BAD
    draw_text(screen, f"HP {member.hp}/{member.stats['hp']}", (text_x, rect.y + 46), 15, hp_color)
    draw_text(screen, f"MP {member.mp}/{member.stats['mp']}", (text_x, rect.y + 69), 15, ACCENT)
    if focused:
        draw_text(screen, "行動中", (rect.right - 65, rect.y + 75), 13, WARN if not ally else GOOD, True)


def draw_battle(screen: pygame.Surface, game: KadokaQuest, buttons: list[Button]) -> None:
    battle = game.battle
    if not battle:
        return
    draw_text(screen, "模擬戦（AI更新なし）" if game.simulation else "コマンドバトル", (25, 20), 32, ACCENT, True)
    draw_text(screen, "←→で選択 / Enterで決定 / 1〜4で直接実行 / Aでオート", (360, 27), 16, MUTED)
    mode_label = "行動演出中" if game.battle_playback else ("オート戦闘中" if game.auto_battle else "手動戦闘")
    draw_text(screen, mode_label, (360, 50), 15, WARN if game.battle_playback else (GOOD if game.auto_battle else ACCENT), True)
    draw_text(screen, "味方", (25, 70), 20, GOOD, True)
    draw_text(screen, "相手", (790, 70), 20, WARN, True)
    for index, member in enumerate(battle.allies):
        draw_combatant(screen, game, member, pygame.Rect(25, 100 + index * 115, 310, 100), True)
    for index, member in enumerate(battle.enemies):
        draw_combatant(screen, game, member, pygame.Rect(785, 100 + index * 115, 310, 100), False)
    pygame.draw.rect(screen, PANEL, pygame.Rect(355, 90, 410, 490), border_radius=10)
    draw_text(screen, f"戦闘ログ / {battle.round_number}ターン", (372, 108), 18, MUTED, True)
    pygame.draw.rect(screen, SELECTED, pygame.Rect(370, 138, 380, 68), border_radius=8)
    draw_text(screen, "いまの行動", (383, 145), 14, WARN if game.battle_playback else MUTED, True)
    current_action = game.battle_action_line or "コマンドを選んでください。"
    draw_wrapped(screen, current_action, pygame.Rect(383, 168, 354, 34), 16, TEXT)
    draw_text(screen, "履歴", (372, 218), 14, MUTED, True)
    visible_logs = battle.log[:game.battle_visible_log_count]
    for index, line in enumerate(visible_logs[-13:]):
        draw_wrapped(screen, line, pygame.Rect(372, 240 + index * 25, 375, 24), 14, TEXT)
    if battle.outcome and not game.battle_playback:
        pygame.draw.rect(screen, (55, 94, 122), pygame.Rect(355, 590, 410, 42), border_radius=8)
        draw_text(screen, f"結果: {battle.outcome}　Enterでフィールドへ", (375, 600), 17, GOOD, True)
    mouse = pygame.mouse.get_pos()
    for index, button in enumerate(buttons):
        button.enabled = battle.outcome is None and not game.battle_playback
        button.draw(screen, mouse)
        if index == game.battle_selection and not battle.outcome and not game.battle_playback:
            pygame.draw.rect(screen, ACCENT, button.rect.inflate(6, 6), 3, border_radius=9)


def password_controls() -> tuple[list[tuple[str, pygame.Rect]], pygame.Rect, pygame.Rect, pygame.Rect]:
    keys: list[tuple[str, pygame.Rect]] = []
    columns = 10
    key_width, key_height = 82, 52
    start_x, start_y = 108, 245
    for index, character in enumerate(KANA_KEYS):
        x = start_x + (index % columns) * (key_width + 7)
        y = start_y + (index // columns) * (key_height + 8)
        keys.append((character, pygame.Rect(x, y, key_width, key_height)))
    return keys, pygame.Rect(350, 565, 130, 54), pygame.Rect(495, 565, 130, 54), pygame.Rect(640, 565, 130, 54)


def draw_password(screen: pygame.Surface, game: KadokaQuest) -> None:
    draw_text(screen, "水の湧き場", (455, 34), 36, (100, 210, 255), True)
    draw_text(screen, "7文字のあいことば", (457, 84), 21, MUTED, True)
    slot_x = 306
    for index in range(7):
        rect = pygame.Rect(slot_x + index * 74, 135, 62, 70)
        pygame.draw.rect(screen, PANEL_ALT, rect, border_radius=8)
        pygame.draw.rect(screen, ACCENT if index == len(game.password_input) and index < 7 else MUTED, rect, 2, border_radius=8)
        if index < len(game.password_input):
            draw_text(screen, game.password_input[index], (rect.x + 14, rect.y + 14), 31, TEXT, True)
    keys, erase, decide, cancel = password_controls()
    mouse = pygame.mouse.get_pos()
    for label, rect in keys:
        pygame.draw.rect(screen, (60, 102, 132) if rect.collidepoint(mouse) else PANEL_ALT, rect, border_radius=7)
        draw_text(screen, label, (rect.x + 26, rect.y + 11), 23, TEXT, True)
    for label, rect, color in (("けす", erase, WARN), ("決定", decide, GOOD), ("やめる", cancel, MUTED)):
        pygame.draw.rect(screen, color if rect.collidepoint(mouse) else PANEL_ALT, rect, border_radius=8)
        draw_text(screen, label, (rect.x + 29, rect.y + 13), 20, TEXT, True)
    if game.password_message:
        draw_text(screen, game.password_message, (390, 645), 18, WARN if "違" in game.password_message else MUTED, True)


def main() -> None:
    screen = init_pygame("kadoka quest", SCREEN_SIZE)
    clock = pygame.time.Clock()
    game = KadokaQuest()
    running = True
    smoke = smoke_frames()
    frames = 0
    battle_buttons = [
        Button(pygame.Rect(355, 650, 95, 48), "戦う", lambda: game.handle_battle_command("fight")),
        Button(pygame.Rect(460, 650, 95, 48), "スカウト", lambda: game.handle_battle_command("scout")),
        Button(pygame.Rect(565, 650, 95, 48), "道具", lambda: game.handle_battle_command("item")),
        Button(pygame.Rect(670, 650, 95, 48), "逃げる", lambda: game.handle_battle_command("run")),
    ]

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if game.mode == "password":
                        game.cancel_password()
                    elif game.mode == "battle":
                        if game.battle and game.battle.outcome and not game.battle_playback:
                            game.return_to_field()
                        else:
                            game.auto_battle = False
                            game.status = "戦闘中です。Aでオート戦闘を切り替えられます。"
                    else:
                        running = False
                elif game.mode == "field":
                    if event.key in MOVE_KEY_VECTORS:
                        if not getattr(event, "repeat", False):
                            game.start_held_move(event.key, pygame.time.get_ticks())
                    elif event.key == pygame.K_SPACE:
                        game.interact()
                    elif event.key == pygame.K_l:
                        game.field_pickup()
                    elif pygame.K_1 <= event.key <= pygame.K_4:
                        game.selected_party = event.key - pygame.K_1
                    elif event.key == pygame.K_t:
                        game.cycle_tactic()
                    elif event.key == pygame.K_r:
                        game.reset_selected_ai()
                    elif event.key == pygame.K_F5:
                        game.scan_acquire()
                    elif event.key == pygame.K_F6:
                        game.start_simulation()
                    elif event.key == pygame.K_F7:
                        game.save_preset()
                    elif event.key == pygame.K_F8:
                        game.load_next_preset()
                elif game.mode == "battle":
                    if game.battle and game.battle.outcome and not game.battle_playback and event.key in {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE}:
                        game.return_to_field()
                    elif event.key == pygame.K_a:
                        game.toggle_auto_battle()
                    elif event.key in {pygame.K_LEFT, pygame.K_UP}:
                        game.battle_selection = (game.battle_selection - 1) % 4
                    elif event.key in {pygame.K_RIGHT, pygame.K_DOWN}:
                        game.battle_selection = (game.battle_selection + 1) % 4
                    elif event.key in {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE}:
                        game.handle_battle_command(game.selected_battle_command())
                    elif pygame.K_1 <= event.key <= pygame.K_4:
                        game.battle_selection = event.key - pygame.K_1
                        game.handle_battle_command(game.selected_battle_command())
                elif game.mode == "password":
                    if event.key == pygame.K_BACKSPACE:
                        game.backspace_password()
                    elif event.key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
                        game.submit_password()
                    elif event.unicode:
                        game.append_password(event.unicode)
            if event.type == pygame.KEYUP and event.key in MOVE_KEY_VECTORS:
                game.stop_held_move(event.key)
            if game.mode == "password" and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                keys, erase, decide, cancel = password_controls()
                for character, rect in keys:
                    if rect.collidepoint(event.pos):
                        game.append_password(character)
                        break
                if erase.collidepoint(event.pos):
                    game.backspace_password()
                elif decide.collidepoint(event.pos):
                    game.submit_password()
                elif cancel.collidepoint(event.pos):
                    game.cancel_password()
            elif game.mode == "battle":
                for button in battle_buttons:
                    button.handle(event)

        game.refresh_manager_if_closed()
        now = pygame.time.get_ticks()
        game.update_field_mobs(now)
        game.update_held_move(now)
        game.update_battle_playback()
        game.update_auto_battle()
        screen.fill(BG)
        if game.mode == "field":
            draw_text(screen, "kadoka quest", (20, 18), 34, ACCENT, True)
            draw_field(screen, game, now)
        elif game.mode == "battle":
            draw_battle(screen, game, battle_buttons)
        else:
            draw_password(screen, game)
        if game.mode != "password":
            pygame.draw.rect(screen, PANEL_ALT, pygame.Rect(20, 665 if game.mode == "field" else 710, 1080, 48 if game.mode == "field" else 25), border_radius=8)
            draw_wrapped(screen, game.status, pygame.Rect(35, 674 if game.mode == "field" else 714, 1050, 32), 16)
        pygame.display.flip()
        clock.tick(60)
        frames += 1
        if smoke is not None and frames >= smoke:
            running = False
    pygame.quit()


if __name__ == "__main__":
    main()

