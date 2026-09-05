from __future__ import annotations

from datetime import datetime
import random
from uuid import uuid4

import pygame

from kadoka_quest.application.runtime_orchestrator import RuntimeOrchestrator
from kadoka_quest.apps.battle_session import BattleSession
from kadoka_quest.apps.field_event_app import FieldEventApplication
from kadoka_quest.apps.manager_process_service import ManagerProcessService
from kadoka_quest.apps.password_session import PasswordSession
from kadoka_quest.core.ai import TACTICS, default_ai
from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.core.field_engine import FieldEngine
from kadoka_quest.core.fixed_mob_controller import FixedMobController
from kadoka_quest.core.grid_movement import GridMovement
from kadoka_quest.core.hidden_enemy_controller import HiddenEnemyController
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.core.player_field_controller import PlayerFieldController
from kadoka_quest.data.field_data import FieldDataLoader
from kadoka_quest.data.field_progress import FieldProgressStore
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.parties import PartyStore
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.data.state import StateStore
from kadoka_quest.paths import ASSET_ROOT, IMPORT_ROOT, PROJECT_ROOT
from kadoka_quest.ui.battle_renderer import BattleRenderer
from kadoka_quest.ui.character_image_provider import CharacterImageProvider
from kadoka_quest.ui.common import ACCENT, BG, GOOD, MUTED, PANEL, PANEL_ALT, TEXT, WARN, Button, draw_text, draw_wrapped, init_pygame, smoke_frames
from kadoka_quest.ui.field_renderer import FIELD_RECT, TILE, draw_field


SCREEN_SIZE = (1120, 740)
PASSWORD = "へいわなすみか"
KANA_KEYS = tuple("あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん")
MOVE_KEY_DIRECTIONS = {
    pygame.K_LEFT: "left",
    pygame.K_a: "left",
    pygame.K_RIGHT: "right",
    pygame.K_d: "right",
    pygame.K_UP: "back",
    pygame.K_w: "back",
    pygame.K_DOWN: "front",
    pygame.K_s: "front",
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
        self.field_data = FieldDataLoader(self.repository)
        self.field_progress = FieldProgressStore(self.states)
        saved_player = self.state.get("player", {})
        initial_world = self.field_data.load_map(
            str(self.state.get("map_id", "starting_town")),
            saved_player.get("x"),
            saved_player.get("y"),
        )
        self.map_data = initial_world["map"]
        self.blocks = self.field_data.blocks()
        self.field = FieldEngine(self.map_data, self.blocks)
        self.fixed_mobs = FixedMobController(self.field, self.rng, FIXED_MOB_MOVE_DURATION_MS)
        self.hidden_enemies = HiddenEnemyController(
            self.field,
            self.rng,
            HIDDEN_CHASE_MOVE_INTERVAL_MS,
            HIDDEN_WANDER_MOVE_INTERVAL_MS,
            HIDDEN_VISION_RANGE,
        )
        self.hidden_enemies.set_world(self.map_data, self.blocks)
        self.player_field = PlayerFieldController(
            initial_world["x"],
            initial_world["y"],
            PLAYER_MOVE_DURATION_MS,
            MOVE_REPEAT_DELAY_MS,
            MOVE_REPEAT_INTERVAL_MS,
        )
        self.field_events = FieldEventApplication()
        self.runtime = RuntimeOrchestrator(self)
        self.battle_session = BattleSession()
        self.password_session = PasswordSession(PASSWORD, KANA_KEYS)
        self.character_images = CharacterImageProvider(self.repository, ASSET_ROOT)
        self.manager_tool = ManagerProcessService(PROJECT_ROOT / "manage.py")
        self.status = "矢印/WASDで移動（長押し対応）。見えない野生モンスターも裏で歩いています。"
        self.selected_party = 0
        self.preset_index = 0
        self.held_move_key: int | None = None
        self.reset_hidden_monsters()
        self.reset_home_npcs()

    @property
    def home_npcs(self) -> list[dict]:
        """Compatibility view of fixed-mob runtime state."""
        return self.fixed_mobs.npcs

    @home_npcs.setter
    def home_npcs(self, value: list[dict]) -> None:
        self.fixed_mobs.npcs = value

    @property
    def hidden_monsters(self) -> list[dict]:
        """Compatibility view of invisible-enemy runtime state."""
        return self.hidden_enemies.monsters

    @hidden_monsters.setter
    def hidden_monsters(self, value: list[dict]) -> None:
        self.hidden_enemies.monsters = value

    @property
    def player_x(self) -> int:
        return self.player_field.x

    @player_x.setter
    def player_x(self, value: int) -> None:
        self.player_field.x = int(value)

    @property
    def player_y(self) -> int:
        return self.player_field.y

    @player_y.setter
    def player_y(self, value: int) -> None:
        self.player_field.y = int(value)

    @property
    def player_direction(self) -> str:
        return self.player_field.direction

    @player_direction.setter
    def player_direction(self, value: str) -> None:
        self.player_field.direction = str(value)

    @property
    def player_movement(self) -> GridMovement:
        return self.player_field.visual

    @property
    def held_move_direction(self) -> str | None:
        return self.player_field.held_direction

    @held_move_direction.setter
    def held_move_direction(self, value: str | None) -> None:
        self.player_field.held_direction = value

    @property
    def next_move_tick(self) -> int:
        return self.player_field.next_move_tick

    @next_move_tick.setter
    def next_move_tick(self, value: int) -> None:
        self.player_field.next_move_tick = int(value)

    @property
    def mode(self) -> str:
        return self.runtime.mode

    @mode.setter
    def mode(self, value: str) -> None:
        self.runtime.transition_to(value)

    @property
    def battle(self) -> BattleEngine | None:
        return self.battle_session.battle

    @battle.setter
    def battle(self, value: BattleEngine | None) -> None:
        self.battle_session.battle = value

    @property
    def battle_finalized(self) -> bool:
        return self.battle_session.finalized

    @battle_finalized.setter
    def battle_finalized(self, value: bool) -> None:
        self.battle_session.finalized = bool(value)

    @property
    def battle_selection(self) -> int:
        return self.battle_session.selection

    @battle_selection.setter
    def battle_selection(self, value: int) -> None:
        self.battle_session.selection = int(value)

    @property
    def auto_battle(self) -> bool:
        return self.battle_session.auto

    @auto_battle.setter
    def auto_battle(self, value: bool) -> None:
        self.battle_session.auto = bool(value)

    @property
    def last_auto_tick(self) -> int:
        return self.battle_session.last_auto_tick

    @last_auto_tick.setter
    def last_auto_tick(self, value: int) -> None:
        self.battle_session.last_auto_tick = int(value)

    @property
    def battle_playback(self) -> bool:
        return self.battle_session.playback

    @battle_playback.setter
    def battle_playback(self, value: bool) -> None:
        self.battle_session.playback = bool(value)

    @property
    def battle_visible_log_count(self) -> int:
        return self.battle_session.visible_log_count

    @battle_visible_log_count.setter
    def battle_visible_log_count(self, value: int) -> None:
        self.battle_session.visible_log_count = int(value)

    @property
    def battle_next_log_tick(self) -> int:
        return self.battle_session.next_log_tick

    @battle_next_log_tick.setter
    def battle_next_log_tick(self, value: int) -> None:
        self.battle_session.next_log_tick = int(value)

    @property
    def battle_action_line(self) -> str:
        return self.battle_session.action_line

    @battle_action_line.setter
    def battle_action_line(self, value: str) -> None:
        self.battle_session.action_line = str(value)

    @property
    def battle_focus_id(self) -> str | None:
        return self.battle_session.focus_id

    @battle_focus_id.setter
    def battle_focus_id(self, value: str | None) -> None:
        self.battle_session.focus_id = value

    @property
    def simulation(self) -> bool:
        return self.battle_session.simulation

    @simulation.setter
    def simulation(self, value: bool) -> None:
        self.battle_session.simulation = bool(value)

    @property
    def fixed_mob_battle_id(self) -> str | None:
        return self.battle_session.fixed_mob_id

    @fixed_mob_battle_id.setter
    def fixed_mob_battle_id(self, value: str | None) -> None:
        self.battle_session.fixed_mob_id = value

    @property
    def password_input(self) -> str:
        return self.password_session.input_text

    @password_input.setter
    def password_input(self, value: str) -> None:
        self.password_session.input_text = str(value)

    @property
    def password_message(self) -> str:
        return self.password_session.message

    @password_message.setter
    def password_message(self, value: str) -> None:
        self.password_session.message = str(value)

    @property
    def image_cache(self) -> dict[tuple[str, str, int, int], pygame.Surface | None]:
        return self.character_images.cache

    @property
    def manager_process(self) -> object | None:
        return self.manager_tool.process

    @manager_process.setter
    def manager_process(self, value: object | None) -> None:
        self.manager_tool.process = value

    def party(self) -> list[MonsterRecord]:
        return StateStore.party_records(self.state, self.monsters)

    def save_position(self) -> None:
        self.field_progress.save_position(
            self.state,
            str(self.map_data["id"]),
            self.player_x,
            self.player_y,
        )

    def change_map(self, map_id: str, x: int, y: int, message: str | None = None) -> None:
        loaded = self.field_data.load_map(map_id, x, y)
        self.map_data = loaded["map"]
        self.field.set_world(self.map_data, self.blocks)
        self.hidden_enemies.set_world(self.map_data, self.blocks)
        self.player_field.snap(loaded["x"], loaded["y"])
        self.save_position()
        self.reset_hidden_monsters()
        self.reset_home_npcs()
        self.status = message or f"{self.map_data['display_name']}へ入りました。"

    def move(self, dx: int, dy: int, now: int | None = None) -> None:
        now = pygame.time.get_ticks() if now is None else int(now)
        self.field.set_world(self.map_data, self.blocks)
        result = self.player_field.attempt_move(
            self.field,
            dx,
            dy,
            self.home_npcs,
            self.hidden_monsters,
            now,
        )
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
        direction = MOVE_KEY_DIRECTIONS.get(key)
        if direction is None:
            return False
        self.held_move_key = key
        return self.start_held_direction(direction, now)

    def start_held_direction(self, direction: str, now: int) -> bool:
        if self.mode != "field":
            return False
        vector = self.player_field.begin_hold(direction, now)
        if vector is None:
            return False
        self.move(*vector, now=now)
        return True

    def stop_held_move(self, key: int) -> None:
        if key == self.held_move_key:
            self.held_move_key = None
            self.held_move_direction = None

    def stop_held_direction(self, direction: str) -> None:
        if self.player_field.stop_hold(direction):
            self.held_move_key = None

    def update_held_move(self, now: int) -> bool:
        if self.mode != "field":
            self.held_move_key = None
            self.player_field.clear_hold()
            return False
        vector = self.player_field.repeated_vector(now)
        if vector is None:
            return False
        self.move(*vector, now=now)
        return True

    def handle_step_event(self) -> bool:
        self.field.set_world(self.map_data, self.blocks)
        event = self.field.step_transition_at(self.player_x, self.player_y)
        effect = self.field_events.resolve_step(event)
        if effect["kind"] != "transition":
            return False
        self.runtime.apply_field_effect(effect)
        return True

    def nearby_event(self) -> dict | None:
        self.field.set_world(self.map_data, self.blocks)
        return self.field.nearby_event(self.player_x, self.player_y)

    def interact(self) -> None:
        npc = self.nearby_home_npc()
        event = None if npc is not None else self.nearby_event()
        dialogue = self.next_npc_dialogue(npc) if npc is not None else None
        effect = self.field_events.resolve_interaction(
            npc,
            event,
            self.player_direction,
            dialogue,
        )
        self.runtime.apply_field_effect(effect)

    def reacquire_ghosts(self) -> None:
        added = []
        for species_id in ("maru", "kadoka"):
            if not any(record.species_id == species_id for record in self.monsters.list_records()):
                record = self.monsters.create(species_id, level=1, source="ghost_home_password")
                added.append(record.name)
        self.field_progress.set_flag(self.state, "ghost_entrance_open", True)
        self.status = "へいわなすみか。" + (f" 牧場に {'・'.join(added)} が増えました。" if added else " 2匹とも既にいます。")

    def open_password_input(self) -> None:
        self.password_session.open()
        self.mode = "password"

    def append_password(self, character: str) -> None:
        self.password_session.append(character)

    def backspace_password(self) -> None:
        self.password_session.backspace()

    def submit_password(self) -> bool:
        if not self.password_session.submit():
            return False
        self.mode = "field"
        self.reacquire_ghosts()
        return True

    def cancel_password(self) -> None:
        self.password_session.cancel()
        self.mode = "field"
        self.status = "水の湧き場から離れました。"

    def reset_home_npcs(self, now: int | None = None) -> None:
        now = pygame.time.get_ticks() if now is None else int(now)

        def species_name(species_id: str) -> str:
            definition = self.repository.get_species(species_id).definition
            return str(definition.get("display_name", species_id))

        self.fixed_mobs.reset(
            self.map_data,
            self.blocks,
            set(self.state.get("despawned_fixed_mobs", [])),
            (self.player_x, self.player_y),
            now,
            species_name,
        )

    def nearby_home_npc(self) -> dict | None:
        return self.fixed_mobs.nearby(self.player_front_position())

    def next_npc_dialogue(self, npc: dict) -> str:
        return self.fixed_mobs.next_dialogue(npc)

    def despawn_fixed_mob(self, npc: dict) -> None:
        self.fixed_mobs.remove(npc)
        if not npc.get("respawn_on_map_enter", True):
            key = f"{self.map_data['id']}:{npc['id']}"
            self.field_progress.mark_despawned(self.state, key)

    def despawn_fixed_mob_by_id(self, npc_id: str) -> bool:
        npc = next((item for item in self.home_npcs if str(item.get("id")) == str(npc_id)), None)
        if npc is None:
            return False
        self.despawn_fixed_mob(npc)
        return True

    def register_church(self, revive: dict) -> None:
        self.field_progress.register_church(self.state, revive)

    def gain_field_item(self, item_id: str) -> int:
        return self.field_progress.add_item(self.state, item_id)

    @staticmethod
    def npc_front_position(npc: dict) -> tuple[int, int]:
        return FixedMobController.front_position(npc)

    def npc_faces_player(self, npc: dict) -> bool:
        return self.fixed_mobs.faces_player(npc, (self.player_x, self.player_y))

    def move_home_npcs(self) -> None:
        if self.mode != "field" or not self.home_npcs:
            return
        self.fixed_mobs.move_all(
            (self.player_x, self.player_y),
            pygame.time.get_ticks(),
        )

    def move_home_npc(self, npc: dict, now: int | None = None) -> bool:
        now = pygame.time.get_ticks() if now is None else int(now)
        return self.fixed_mobs.move(npc, (self.player_x, self.player_y), now)

    def character_image(self, species_id: str, kind: str, size: tuple[int, int]) -> pygame.Surface | None:
        return self.character_images.get(species_id, kind, size)

    def field_pickup(self) -> None:
        picker = next((record for record in self.party() if record.species_id in {"maru", "kadoka"}), None)
        if not picker:
            self.status = "まるかかどかをパーティに入れると『ものを拾う』を使えます。"
            return
        if picker.species_id == "maru":
            item = self.rng.choice(["小石", "曲がった釘", "空き瓶", "変な布", "木の枝"])
        else:
            roll = self.rng.random()
            item = "柿" if roll < 0.05 else "みかん" if roll < 0.8 else "小石"
        self.field_progress.add_item(self.state, item)
        self.status = f"{picker.name}が{item}を拾ってきました。"

    def spawn_options(self) -> list[dict]:
        self.hidden_enemies.set_world(self.map_data, self.blocks)
        return self.hidden_enemies.spawn_options(self.state.get("flags", {}))

    def reset_hidden_monsters(self, now: int | None = None) -> None:
        now = pygame.time.get_ticks() if now is None else int(now)
        self.hidden_enemies.set_world(self.map_data, self.blocks)
        self.hidden_enemies.reset(
            (self.player_x, self.player_y),
            self.state.get("flags", {}),
            now,
        )

    def move_hidden_monsters(self) -> None:
        if self.mode != "field":
            return
        self.hidden_enemies.move_all(
            (self.player_x, self.player_y),
            {(int(npc["x"]), int(npc["y"])) for npc in self.home_npcs},
        )
        self.check_hidden_collision()

    def monster_sees_player(self, monster: dict) -> bool:
        return self.hidden_enemies.sees_player(monster, (self.player_x, self.player_y))

    def move_hidden_monster(self, monster: dict) -> bool:
        return self.hidden_enemies.move(
            monster,
            (self.player_x, self.player_y),
            {(int(npc["x"]), int(npc["y"])) for npc in self.home_npcs},
        )

    def update_field_mobs(self, now: int) -> bool:
        if self.mode != "field":
            return False
        moved = self.fixed_mobs.update((self.player_x, self.player_y), int(now))
        visible_positions = {(int(npc["x"]), int(npc["y"])) for npc in self.home_npcs}
        moved = self.hidden_enemies.update(
            (self.player_x, self.player_y),
            visible_positions,
            int(now),
        ) or moved
        return self.check_hidden_collision() or moved

    def check_hidden_collision(self) -> bool:
        monster = self.hidden_enemies.find_at(self.player_front_position())
        if monster is None:
            return False
        self.start_wild_battle(monster["spawn"], monster)
        return True

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

    def start_wild_battle(
        self,
        spawn: dict | None = None,
        hidden_monster: dict | None = None,
        *,
        fixed_mob_id: str | None = None,
    ) -> None:
        options = self.spawn_options()
        if (not spawn and not options) or not self.party():
            return
        if spawn is None:
            spawn = self.rng.choices(options, weights=[int(item.get("weight", 1)) for item in options])[0]
        enemies = [self.make_wild(spawn)]
        if hidden_monster is not None:
            self.hidden_enemies.remove(hidden_monster)
        battle = BattleEngine(self.repository, self.party(), enemies, self.rng, learning_enabled=True)
        self.battle_session.begin(
            battle,
            pygame.time.get_ticks(),
            fixed_mob_id=fixed_mob_id,
        )
        self.mode = "battle"
        self.status = f"{', '.join(record.name for record in enemies)} が現れた。"

    def start_simulation(self) -> None:
        imported = self.monsters.discover_external(IMPORT_ROOT / "simulation")
        if not imported:
            self.status = "imports/simulation に個体フォルダを置いてください。"
            return
        try:
            battle = BattleEngine(self.repository, self.party(), imported, self.rng, learning_enabled=False)
        except (OSError, ValueError, KeyError) as exc:
            self.status = f"模擬戦個体を読めません: {exc}"
            return
        self.battle_session.begin(battle, pygame.time.get_ticks(), simulation=True)
        self.mode = "battle"
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
        self.battle_session.reset_presentation()

    def start_battle_playback(self, log_start: int) -> None:
        self.battle_session.start_playback(log_start, pygame.time.get_ticks())

    def battle_log_delay(self, line: str) -> int:
        return self.battle_session.log_delay(line)

    def update_battle_playback(self, now: int | None = None) -> bool:
        now = pygame.time.get_ticks() if now is None else int(now)
        result = self.battle_session.update_playback(now)
        if result["completed"]:
            self.finalize_battle_if_needed()
        return result["changed"]

    def selected_battle_command(self) -> str:
        return self.battle_session.selected_command()

    def move_battle_selection(self, amount: int) -> int:
        return self.battle_session.move_selection(amount)

    def set_battle_selection(self, index: int) -> int:
        return self.battle_session.set_selection(index)

    def stop_auto_battle(self) -> None:
        self.battle_session.stop_auto()

    def toggle_auto_battle(self) -> None:
        enabled = self.battle_session.toggle_auto(pygame.time.get_ticks())
        if enabled is None:
            return
        self.status = "オート戦闘を開始しました。" if enabled else "オート戦闘を停止しました。"

    def update_auto_battle(self, now: int | None = None) -> None:
        now = pygame.time.get_ticks() if now is None else int(now)
        if not self.battle_session.auto_command_due(now, battle_mode=self.mode == "battle"):
            return
        self.handle_battle_command("fight")
        if self.battle and self.battle.outcome:
            self.battle_session.stop_auto()

    def finalize_battle_if_needed(self) -> None:
        if not self.battle_session.mark_finalized():
            return
        assert self.battle is not None
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
        result = self.battle_session.clear()
        outcome = result["outcome"]
        was_simulation = bool(result["simulation"])
        fixed_mob_battle_id = result["fixed_mob_id"]
        self.mode = "field"
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
        revive = self.field_progress.revive_point(self.state)
        self.change_map(str(revive["map_id"]), int(revive["x"]), int(revive["y"]), f"全滅しました。{revive.get('name', '教会')}から復活しました。")

    def scan_acquire(self) -> None:
        added, skipped = self.monsters.acquire_from_scan(IMPORT_ROOT / "acquire")
        self.status = f"個体再走査：{added}体を獲得、{skipped}件をスキップ。"

    def open_manager(self) -> None:
        if self.manager_tool.open() == "already_running":
            self.status = "牧場台帳は既に開いています。"
            return
        self.status = "牧場台帳を開きました。個体管理とパーティ編成ができます。"

    def refresh_manager_if_closed(self) -> None:
        if not self.manager_tool.consume_closed():
            return
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
    battle_renderer = BattleRenderer()

    def dispatch(target: str, action: str, **payload) -> object:
        return game.runtime.dispatch(target, action, **payload)

    running = True
    smoke = smoke_frames()
    frames = 0
    battle_buttons = [
        Button(pygame.Rect(355, 650, 95, 48), "戦う", lambda: dispatch("battle", "execute", command="fight")),
        Button(pygame.Rect(460, 650, 95, 48), "スカウト", lambda: dispatch("battle", "execute", command="scout")),
        Button(pygame.Rect(565, 650, 95, 48), "道具", lambda: dispatch("battle", "execute", command="item")),
        Button(pygame.Rect(670, 650, 95, 48), "逃げる", lambda: dispatch("battle", "execute", command="run")),
    ]

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if game.mode == "password":
                        dispatch("password", "cancel")
                    elif game.mode == "battle":
                        if game.battle and game.battle.outcome and not game.battle_playback:
                            dispatch("battle", "return")
                        else:
                            dispatch("battle", "cancel")
                    else:
                        running = False
                elif game.mode == "field":
                    if event.key in MOVE_KEY_DIRECTIONS:
                        if not getattr(event, "repeat", False):
                            dispatch(
                                "field",
                                "move.start",
                                direction=MOVE_KEY_DIRECTIONS[event.key],
                                now=pygame.time.get_ticks(),
                            )
                    elif event.key == pygame.K_SPACE:
                        dispatch("field", "interact")
                    elif event.key == pygame.K_l:
                        dispatch("field", "pickup")
                    elif pygame.K_1 <= event.key <= pygame.K_4:
                        dispatch("field", "party.select", index=event.key - pygame.K_1)
                    elif event.key == pygame.K_t:
                        dispatch("field", "tactic.cycle")
                    elif event.key == pygame.K_r:
                        dispatch("field", "ai.reset")
                    elif event.key == pygame.K_F5:
                        dispatch("field", "acquire.scan")
                    elif event.key == pygame.K_F6:
                        dispatch("field", "simulation.start")
                    elif event.key == pygame.K_F7:
                        dispatch("field", "party.save_preset")
                    elif event.key == pygame.K_F8:
                        dispatch("field", "party.load_next_preset")
                elif game.mode == "battle":
                    if game.battle and game.battle.outcome and not game.battle_playback and event.key in {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE}:
                        dispatch("battle", "return")
                    elif event.key == pygame.K_a:
                        dispatch("battle", "auto.toggle")
                    elif event.key in {pygame.K_LEFT, pygame.K_UP}:
                        dispatch("battle", "selection.move", amount=-1)
                    elif event.key in {pygame.K_RIGHT, pygame.K_DOWN}:
                        dispatch("battle", "selection.move", amount=1)
                    elif event.key in {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE}:
                        dispatch("battle", "execute.selected")
                    elif pygame.K_1 <= event.key <= pygame.K_4:
                        dispatch("battle", "selection.set", index=event.key - pygame.K_1)
                        dispatch("battle", "execute.selected")
                elif game.mode == "password":
                    if event.key == pygame.K_BACKSPACE:
                        dispatch("password", "backspace")
                    elif event.key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
                        dispatch("password", "submit")
                    elif event.unicode:
                        dispatch("password", "append", character=event.unicode)
            if event.type == pygame.KEYUP and event.key in MOVE_KEY_DIRECTIONS:
                dispatch("field", "move.stop", direction=MOVE_KEY_DIRECTIONS[event.key])
            if game.mode == "password" and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                keys, erase, decide, cancel = password_controls()
                for character, rect in keys:
                    if rect.collidepoint(event.pos):
                        dispatch("password", "append", character=character)
                        break
                if erase.collidepoint(event.pos):
                    dispatch("password", "backspace")
                elif decide.collidepoint(event.pos):
                    dispatch("password", "submit")
                elif cancel.collidepoint(event.pos):
                    dispatch("password", "cancel")
            elif game.mode == "battle":
                for button in battle_buttons:
                    button.handle(event)

        dispatch("manager", "refresh")
        now = pygame.time.get_ticks()
        if game.mode == "field":
            dispatch("field", "tick", now=now)
        elif game.mode == "battle":
            dispatch("battle", "tick", now=now)
        screen.fill(BG)
        if game.mode == "field":
            draw_text(screen, "kadoka quest", (20, 18), 34, ACCENT, True)
            draw_field(screen, game, now)
        elif game.mode == "battle":
            battle_renderer.draw(screen, game, battle_buttons)
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

