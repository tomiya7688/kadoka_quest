from __future__ import annotations

from datetime import datetime
import random
import subprocess
import sys
from uuid import uuid4

import pygame

from kadoka_quest.core.ai import TACTICS, default_ai
from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.parties import PartyStore
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.data.state import StateStore
from kadoka_quest.paths import ASSET_ROOT, IMPORT_ROOT, PROJECT_ROOT
from kadoka_quest.ui.common import ACCENT, BAD, BG, GOOD, MUTED, PANEL, PANEL_ALT, TEXT, WARN, Button, draw_text, draw_wrapped, init_pygame, smoke_frames


SCREEN_SIZE = (1120, 740)
FIELD_RECT = pygame.Rect(20, 70, 800, 576)
TILE = 32
PASSWORD = "へいわなすみか"
KANA_KEYS = tuple("あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん")


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
        self.player_x = int(self.state.get("player", {}).get("x", self.map_data["start"]["x"]))
        self.player_y = int(self.state.get("player", {}).get("y", self.map_data["start"]["y"]))
        self.player_direction = "front"
        self.mode = "field"
        self.battle: BattleEngine | None = None
        self.battle_finalized = False
        self.battle_selection = 0
        self.auto_battle = False
        self.last_auto_tick = 0
        self.simulation = False
        self.status = "矢印/WASDで移動。見えない野生モンスターも裏で歩いています。"
        self.selected_party = 0
        self.preset_index = 0
        self.hidden_monsters: list[dict] = []
        self.home_npcs: list[dict] = []
        self.password_input = ""
        self.password_message = ""
        self.image_cache: dict[tuple[str, str, int, int], pygame.Surface | None] = {}
        self.manager_process: subprocess.Popen | None = None
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
        self.player_x = max(0, min(int(self.map_data["width"]) - 1, int(x)))
        self.player_y = max(0, min(int(self.map_data["height"]) - 1, int(y)))
        self.save_position()
        self.reset_hidden_monsters()
        self.reset_home_npcs()
        self.status = message or f"{self.map_data['display_name']}へ入りました。"

    def move(self, dx: int, dy: int) -> None:
        if dx < 0:
            self.player_direction = "left"
        elif dx > 0:
            self.player_direction = "right"
        elif dy < 0:
            self.player_direction = "back"
        elif dy > 0:
            self.player_direction = "front"
        new_x, new_y = self.player_x + dx, self.player_y + dy
        if not (0 <= new_x < self.map_data["width"] and 0 <= new_y < self.map_data["height"]):
            return
        blocking_event = next((
            event for event in self.map_data.get("events", [])
            if int(event["x"]) == new_x and int(event["y"]) == new_y and event.get("blocking")
        ), None)
        if blocking_event:
            self.status = str(blocking_event.get("blocked_text", "そこには障害物があり、通り抜けられません。"))
            return
        block_id = self.map_data["tiles"][new_y][new_x]
        block = self.blocks.get(block_id, {})
        if not bool(block.get("player_walkable", False)):
            self.status = f"{block.get('display_name', block_id)} は通れません。"
            return
        self.player_x, self.player_y = new_x, new_y
        self.save_position()
        if self.handle_step_event():
            return
        if self.check_hidden_collision():
            return
        self.move_home_npcs()
        self.move_hidden_monsters()

    def handle_step_event(self) -> bool:
        for event in self.map_data.get("events", []):
            if int(event["x"]) != self.player_x or int(event["y"]) != self.player_y:
                continue
            if event.get("type") == "transition" and event.get("activation", "step") == "step":
                target = event["target"]
                self.change_map(str(target["map_id"]), int(target["x"]), int(target["y"]))
                return True
        return False

    def nearby_event(self) -> dict | None:
        candidates = []
        for index, item in enumerate(self.map_data.get("events", [])):
            distance = abs(int(item["x"]) - self.player_x) + abs(int(item["y"]) - self.player_y)
            if distance <= 1:
                candidates.append((distance, index, item))
        return min(candidates, default=(0, 0, None))[2]

    def interact(self) -> None:
        event = self.nearby_event()
        if not event:
            npc = self.nearby_home_npc()
            if npc:
                self.status = "まる『これひろった』" if npc["species_id"] == "maru" else "かどか『こんなもの拾ったのだ』"
                return
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
        if self.map_data["id"] == "ghost_home":
            self.home_npcs = [
                {"species_id": "maru", "x": 10, "y": 7, "direction": "front", "move_count": 0},
                {"species_id": "kadoka", "x": 12, "y": 10, "direction": "front", "move_count": 0},
            ]

    def nearby_home_npc(self) -> dict | None:
        return next((npc for npc in self.home_npcs if abs(int(npc["x"]) - self.player_x) + abs(int(npc["y"]) - self.player_y) <= 1), None)

    def move_home_npcs(self) -> None:
        if self.mode != "field" or not self.home_npcs:
            return
        occupied = {(self.player_x, self.player_y)}
        for npc in self.home_npcs:
            is_maru = npc["species_id"] == "maru"
            attempts = 2 if is_maru else (1 if self.rng.random() < 0.45 else 0)
            for _ in range(attempts):
                directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (0, 0)]
                self.rng.shuffle(directions)
                for dx, dy in directions:
                    x, y = int(npc["x"]) + dx, int(npc["y"]) + dy
                    if not (0 <= x < self.map_data["width"] and 0 <= y < self.map_data["height"]):
                        continue
                    block_id = self.map_data["tiles"][y][x]
                    if self.blocks.get(block_id, {}).get("player_walkable") and (x, y) not in occupied:
                        npc["x"], npc["y"] = x, y
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
                        break
            occupied.add((int(npc["x"]), int(npc["y"])))

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
            self.hidden_monsters.append({"x": x, "y": y, "spawn": dict(spawn)})

    def move_hidden_monsters(self) -> None:
        if self.mode != "field":
            return
        occupied: set[tuple[int, int]] = set()
        for monster in self.hidden_monsters:
            directions = [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]
            self.rng.shuffle(directions)
            for dx, dy in directions:
                x, y = int(monster["x"]) + dx, int(monster["y"]) + dy
                if not (0 <= x < self.map_data["width"] and 0 <= y < self.map_data["height"]):
                    continue
                block_id = self.map_data["tiles"][y][x]
                if self.blocks.get(block_id, {}).get("enemy_walkable") and (x, y) not in occupied:
                    monster["x"], monster["y"] = x, y
                    occupied.add((x, y))
                    break
            if (monster["x"], monster["y"]) == (self.player_x, self.player_y):
                self.start_wild_battle(monster["spawn"], monster)
                return

    def check_hidden_collision(self) -> bool:
        for monster in self.hidden_monsters:
            if (monster["x"], monster["y"]) == (self.player_x, self.player_y):
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
        self.mode = "battle"
        self.battle_selection = 0
        self.auto_battle = False
        self.last_auto_tick = pygame.time.get_ticks()
        self.simulation = True
        self.battle_finalized = False
        self.status = "模擬戦を開始。双方のAIは更新されません。"

    def handle_battle_command(self, command: str) -> None:
        if not self.battle or self.battle.outcome:
            return
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
        self.finalize_battle_if_needed()

    def selected_battle_command(self) -> str:
        return ("fight", "scout", "item", "run")[self.battle_selection % 4]

    def toggle_auto_battle(self) -> None:
        if not self.battle or self.battle.outcome:
            return
        self.auto_battle = not self.auto_battle
        self.last_auto_tick = pygame.time.get_ticks()
        self.status = "オート戦闘を開始しました。" if self.auto_battle else "オート戦闘を停止しました。"

    def update_auto_battle(self) -> None:
        if not self.auto_battle or self.mode != "battle" or not self.battle or self.battle.outcome:
            return
        now = pygame.time.get_ticks()
        if now - self.last_auto_tick < 450:
            return
        self.last_auto_tick = now
        self.handle_battle_command("fight")
        if self.battle and self.battle.outcome:
            self.auto_battle = False

    def finalize_battle_if_needed(self) -> None:
        if not self.battle or not self.battle.outcome or self.battle_finalized:
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
        self.mode = "field"
        self.battle = None
        self.simulation = False
        if outcome == "defeat" and not was_simulation:
            self.revive_at_church()
        else:
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


def draw_field(screen: pygame.Surface, game: KadokaQuest) -> None:
    visible_x = min(FIELD_RECT.width // TILE, int(game.map_data["width"]))
    visible_y = min(FIELD_RECT.height // TILE, int(game.map_data["height"]))
    camera_x = max(0, min(game.map_data["width"] - visible_x, game.player_x - visible_x // 2))
    camera_y = max(0, min(game.map_data["height"] - visible_y, game.player_y - visible_y // 2))
    pygame.draw.rect(screen, PANEL, FIELD_RECT.inflate(8, 8), border_radius=8)
    for sy in range(visible_y):
        gy = camera_y + sy
        for sx in range(visible_x):
            gx = camera_x + sx
            block_id = game.map_data["tiles"][gy][gx]
            block = game.blocks.get(block_id, {})
            appearance = block.get("appearance", {})
            color = hex_color(appearance.get("value", "#777777")) if appearance.get("type") == "color" else (110, 95, 125)
            rect = pygame.Rect(FIELD_RECT.x + sx * TILE, FIELD_RECT.y + sy * TILE, TILE, TILE)
            pygame.draw.rect(screen, color, rect)
    for item in game.map_data.get("events", []):
        sx = (int(item["x"]) - camera_x) * TILE + FIELD_RECT.x
        sy = (int(item["y"]) - camera_y) * TILE + FIELD_RECT.y
        if FIELD_RECT.collidepoint((sx + TILE // 2, sy + TILE // 2)):
            color = (100, 210, 255) if item.get("type") == "password_spring" else WARN
            pygame.draw.rect(screen, color, pygame.Rect(sx + 8, sy + 8, 16, 16), border_radius=4)
    for npc in game.home_npcs:
        sx = (int(npc["x"]) - camera_x) * TILE + FIELD_RECT.x
        sy = (int(npc["y"]) - camera_y) * TILE + FIELD_RECT.y
        if FIELD_RECT.collidepoint((sx + TILE // 2, sy + TILE // 2)):
            sprite = game.character_image(str(npc["species_id"]), f"field_{npc.get('direction', 'front')}", (48, 48))
            if sprite:
                screen.blit(sprite, sprite.get_rect(center=(sx + TILE // 2, sy + TILE // 2 - 7)))
    px = (game.player_x - camera_x) * TILE + FIELD_RECT.x
    py = (game.player_y - camera_y) * TILE + FIELD_RECT.y
    player_sprite = game.character_image("hero", f"field_{game.player_direction}", (48, 48))
    if player_sprite:
        screen.blit(player_sprite, player_sprite.get_rect(center=(px + 16, py + 9)))
    else:
        pygame.draw.circle(screen, (255, 238, 125), (px + 16, py + 16), 12)
        pygame.draw.circle(screen, BG, (px + 16, py + 16), 12, 2)

    pygame.draw.rect(screen, PANEL, pygame.Rect(840, 70, 260, 576), border_radius=10)
    draw_text(screen, game.map_data["display_name"], (855, 85), 23, ACCENT, True)
    draw_text(screen, f"座標 {game.player_x}, {game.player_y}", (855, 118), 16, MUTED)
    draw_text(screen, "パーティ", (855, 155), 20, MUTED, True)
    for index in range(4):
        rect = pygame.Rect(852, 185 + index * 67, 235, 58)
        pygame.draw.rect(screen, (55, 94, 122) if index == game.selected_party else PANEL_ALT, rect, border_radius=7)
        party = game.party()
        if index < len(party):
            record = party[index]
            icon = game.character_image(record.species_id, "portrait", (30, 30))
            if icon:
                screen.blit(icon, icon.get_rect(center=(872, rect.centery)))
            else:
                color = hex_color(game.repository.get_species(record.species_id).definition["appearance"]["value"])
                pygame.draw.circle(screen, color, (872, rect.centery), 13)
            draw_text(screen, record.name, (893, rect.y + 8), 17)
            draw_text(screen, f"Lv{record.level} / {record.ai.get('tactic', 'balanced')}", (893, rect.y + 31), 13, MUTED)
        else:
            draw_text(screen, f"{index + 1}. 空き", (868, rect.y + 18), 16, MUTED)
    draw_text(screen, "操作", (855, 475), 19, MUTED, True)
    controls = "Space 調べる・岩に入る\nL ものを拾う / 1-4 個体選択\nT 行動指針 / R AIリセット\nF5 個体獲得 / F6 模擬戦\nF7 編成保存 / F8 編成読込\n管理は街のモンスター牧場で行う"
    for line_index, line in enumerate(controls.splitlines()):
        draw_text(screen, line, (855, 505 + line_index * 20), 13, MUTED)


def draw_combatant(screen: pygame.Surface, game: KadokaQuest, member, rect: pygame.Rect, ally: bool) -> None:
    pygame.draw.rect(screen, PANEL_ALT, rect, border_radius=10)
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


def draw_battle(screen: pygame.Surface, game: KadokaQuest, buttons: list[Button]) -> None:
    battle = game.battle
    if not battle:
        return
    draw_text(screen, "模擬戦（AI更新なし）" if game.simulation else "コマンドバトル", (25, 20), 32, ACCENT, True)
    draw_text(screen, "←→で選択 / Enterで決定 / 1〜4で直接実行 / Aでオート", (360, 27), 16, MUTED)
    draw_text(screen, "オート戦闘中" if game.auto_battle else "手動戦闘", (360, 50), 15, GOOD if game.auto_battle else ACCENT, True)
    draw_text(screen, "味方", (25, 70), 20, GOOD, True)
    draw_text(screen, "相手", (790, 70), 20, WARN, True)
    for index, member in enumerate(battle.allies):
        draw_combatant(screen, game, member, pygame.Rect(25, 100 + index * 115, 310, 100), True)
    for index, member in enumerate(battle.enemies):
        draw_combatant(screen, game, member, pygame.Rect(785, 100 + index * 115, 310, 100), False)
    pygame.draw.rect(screen, PANEL, pygame.Rect(355, 90, 410, 490), border_radius=10)
    draw_text(screen, f"戦闘ログ / {battle.round_number}ターン", (372, 108), 18, MUTED, True)
    for index, line in enumerate(battle.log[-16:]):
        draw_wrapped(screen, line, pygame.Rect(372, 140 + index * 26, 375, 25), 14, TEXT)
    if battle.outcome:
        pygame.draw.rect(screen, (55, 94, 122), pygame.Rect(355, 590, 410, 42), border_radius=8)
        draw_text(screen, f"結果: {battle.outcome}　Enterでフィールドへ", (375, 600), 17, GOOD, True)
    mouse = pygame.mouse.get_pos()
    for index, button in enumerate(buttons):
        button.enabled = battle.outcome is None
        button.draw(screen, mouse)
        if index == game.battle_selection and not battle.outcome:
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
                        if game.battle and game.battle.outcome:
                            game.return_to_field()
                        else:
                            game.auto_battle = False
                            game.status = "戦闘中です。Aでオート戦闘を切り替えられます。"
                    else:
                        running = False
                elif game.mode == "field":
                    if event.key in {pygame.K_LEFT, pygame.K_a}:
                        game.move(-1, 0)
                    elif event.key in {pygame.K_RIGHT, pygame.K_d}:
                        game.move(1, 0)
                    elif event.key in {pygame.K_UP, pygame.K_w}:
                        game.move(0, -1)
                    elif event.key in {pygame.K_DOWN, pygame.K_s}:
                        game.move(0, 1)
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
                    if game.battle and game.battle.outcome and event.key in {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE}:
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
        game.update_auto_battle()
        screen.fill(BG)
        if game.mode == "field":
            draw_text(screen, "kadoka quest", (20, 18), 34, ACCENT, True)
            draw_field(screen, game)
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

