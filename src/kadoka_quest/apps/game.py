from __future__ import annotations

import random
from pathlib import Path

import pygame

from kadoka_quest.application.runtime_orchestrator import RuntimeOrchestrator
from kadoka_quest.apps.battle_session import BattleSession
from kadoka_quest.apps.field_party_service import FieldPartyService
from kadoka_quest.apps.field_party_session import FieldPartySession
from kadoka_quest.apps.manager_process_service import ManagerProcessService
from kadoka_quest.apps.monster_import_service import MonsterImportService
from kadoka_quest.apps.password_session import PasswordSession
from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.core.fixed_mob_controller import FixedMobController
from kadoka_quest.core.hidden_enemy_controller import HiddenEnemyController
from kadoka_quest.core.player_field_controller import PlayerFieldController
from kadoka_quest.data.battle_data import BattleDataLoader
from kadoka_quest.data.field_data import FieldDataLoader
from kadoka_quest.data.field_progress import FieldProgressStore
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.parties import PartyStore
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.data.state import StateStore
from kadoka_quest.paths import IMPORT_ROOT, PROJECT_ROOT, SAVE_ROOT
from kadoka_quest.ui.battle_renderer import BattleRenderer
from kadoka_quest.ui.character_image_provider import CharacterImageProvider
from kadoka_quest.ui.common import ACCENT, BG, PANEL_ALT, Button, draw_text, draw_wrapped
from kadoka_quest.ui.field_renderer import draw_field
from kadoka_quest.ui.runtime_input_adapter import RuntimeInputAdapter
from kadoka_quest.ui.runtime_mouse_adapter import RuntimeMouseAdapter

SCREEN_WIDTH = 1120
SCREEN_HEIGHT = 768
PASSWORD = "へいわ"
KANA_KEYS = "へいわな"
MOVE_DIRECTIONS = {
    pygame.K_LEFT: "left",
    pygame.K_RIGHT: "right",
    pygame.K_UP: "back",
    pygame.K_DOWN: "front",
}


class KadokaQuest:
    def __init__(self, *, rng: random.Random | None = None) -> None:
        self.repository = GameRepository()
        self.rng = rng or random.Random()
        self.states = StateStore(SAVE_ROOT / "state.json")
        self.monsters = MonsterStore(SAVE_ROOT / "monsters", self.repository)
        self.parties = PartyStore(SAVE_ROOT / "parties", self.monsters)
        self.field_data = FieldDataLoader(self.repository)
        self.field_progress = FieldProgressStore(self.states)
        self.manager_tool = ManagerProcessService(PROJECT_ROOT / "manage.py")
        self.field_party_session = FieldPartySession()
        self.field_party_service = FieldPartyService(
            self.field_party_session,
            self.parties,
            self.monsters,
            self.states,
        )
        self.monster_import_service = MonsterImportService(
            self.monsters,
            self.repository,
            IMPORT_ROOT,
            BattleEngine,
        )
        self.password_session = PasswordSession(PASSWORD, KANA_KEYS)
        self.runtime = RuntimeOrchestrator(self)
        self.battle_session = BattleSession()
        self.status = ""
        self.map_id = "starting_town"
        self.player_x = 0
        self.player_y = 0
        self.player_direction = "front"
        self.state: dict = {}
        self.map_data: dict = {}
        self.blocks: dict[str, dict] = {}
        self.player_field: PlayerFieldController | None = None
        self.hidden_enemy_controller: HiddenEnemyController | None = None
        self.fixed_mob_controller: FixedMobController | None = None
        self.visible_characters: list[dict] = []
        self.hidden_characters: list[dict] = []
        self._load_initial_state()

    @property
    def mode(self) -> str:
        return self.runtime.mode

    @mode.setter
    def mode(self, value: str) -> None:
        self.runtime.mode = value

    @property
    def battle(self) -> BattleEngine | None:
        return self.battle_session.battle

    @battle.setter
    def battle(self, value: BattleEngine | None) -> None:
        self.battle_session.battle = value

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
    def selected_party(self) -> int:
        return self.field_party_session.selected_index

    @selected_party.setter
    def selected_party(self, value: int) -> None:
        self.field_party_session.selected_index = int(value)

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

    def _load_initial_state(self) -> None:
        self.state = self.states.load()
        self.map_id = str(self.state.get("map_id", "starting_town"))
        self.player_x = int(self.state.get("x", 0))
        self.player_y = int(self.state.get("y", 0))
        self.player_direction = str(self.state.get("direction", "front"))
        self._load_map_runtime()

    def _load_map_runtime(self) -> None:
        loaded = self.field_data.load_map(self.map_id)
        self.map_data = loaded["map"]
        self.blocks = loaded["blocks"]
        self.player_field = PlayerFieldController(self.map_data, self.blocks)
        self.hidden_enemy_controller = HiddenEnemyController(self.map_data, self.blocks, self.rng)
        self.fixed_mob_controller = FixedMobController(self.map_data, self.blocks, self.rng)
        self._refresh_characters()

    def _refresh_characters(self) -> None:
        if self.hidden_enemy_controller is None or self.fixed_mob_controller is None:
            self.visible_characters = []
            self.hidden_characters = []
            return
        self.hidden_characters = self.hidden_enemy_controller.characters()
        self.visible_characters = self.fixed_mob_controller.characters()

    def party(self):
        return self.parties.current(self.state.get("current_party", []))

    def select_party(self, index: int) -> bool:
        return self.field_party_service.select(index)

    def start_held_direction(self, direction: str, now: int) -> bool:
        if self.player_field is None:
            return False
        return self.player_field.start_held_direction(direction, now)

    def stop_held_direction(self, direction: str | None = None) -> None:
        if self.player_field is not None:
            self.player_field.stop_held_direction(direction)

    def open_manager(self) -> None:
        if self.manager_tool.open() == "already_running":
            self.status = "牧場管理は既に開いています。"
            return
        self.status = "牧場管理を開きました。"

    def refresh_manager_if_closed(self) -> None:
        if not self.manager_tool.consume_closed():
            return
        self.state = self.states.load()
        self.status = "牧場管理の変更を反映しました。"

    def scan_acquire(self) -> None:
        self.status = self.monster_import_service.scan_acquire()

    def start_simulation(self) -> None:
        battle, message = self.monster_import_service.create_simulation(self.party(), self.rng)
        self.status = message
        if battle is None:
            return
        self.battle_session.begin(battle, pygame.time.get_ticks(), simulation=True)
        self.mode = "battle"

    def save_party_preset(self) -> None:
        self.status = self.field_party_service.save_preset(self.state)

    def load_next_party_preset(self) -> None:
        self.status = self.field_party_service.load_next_preset(self.state)

    def cycle_tactic(self) -> None:
        message = self.field_party_service.cycle_tactic(self.party())
        if message:
            self.status = message

    def reset_selected_ai(self) -> None:
        message = self.field_party_service.reset_selected_ai(self.party())
        if message:
            self.status = message

    def append_password(self, character: str) -> None:
        self.password_session.append(character)

    def backspace_password(self) -> None:
        self.password_session.backspace()

    def submit_password(self) -> None:
        if self.password_session.submit():
            self.mode = self.runtime.previous_mode
            self.status = "合言葉を確認しました。"

    def cancel_password(self) -> None:
        self.password_session.cancel()
        self.mode = self.runtime.previous_mode

    def open_password_input(self) -> None:
        self.password_session.open()
        self.runtime.transition_to("password")

    def register_church(self, event: dict) -> None:
        church_id = str(event.get("id", "church"))
        map_id = str(self.map_id)
        self.field_progress.register_church(church_id, map_id, int(event["x"]), int(event["y"]))
        self.status = str(event.get("text", "教会を登録した。"))

    def gain_field_item(self, item_id: str, amount: int = 1) -> None:
        inventory = self.state.setdefault("inventory", {})
        inventory[item_id] = int(inventory.get(item_id, 0)) + int(amount)
        self.states.save(self.state)

    def change_map(self, map_id: str, x: int, y: int, status: str = "") -> None:
        self.map_id = str(map_id)
        self.player_x = int(x)
        self.player_y = int(y)
        self.state["map_id"] = self.map_id
        self.state["x"] = self.player_x
        self.state["y"] = self.player_y
        self.states.save(self.state)
        self._load_map_runtime()
        self.status = status

    def despawn_fixed_mob_by_id(self, mob_id: str) -> None:
        if self.fixed_mob_controller is None:
            return
        self.fixed_mob_controller.despawn(mob_id)
        self._refresh_characters()

    def start_wild_battle(self, spawn: dict, *, fixed_mob_id: str = "") -> None:
        party = self.party()
        if not party:
            self.status = "パーティが空です。"
            return
        loader = BattleDataLoader(self.repository)
        enemy = loader.enemy_from_spawn(spawn, self.rng)
        battle = BattleEngine(self.repository, party, [enemy], self.rng)
        self.battle_session.begin(
            battle,
            pygame.time.get_ticks(),
            fixed_mob_id=fixed_mob_id or None,
        )
        self.mode = "battle"
        self.status = "戦闘開始。"

    def handle_battle_command(self, command: str) -> None:
        if not self.battle or self.battle.outcome or self.battle_playback:
            return
        log_start = len(self.battle.log)
        if command == "fight":
            self.battle.run_round()
        elif command == "scout":
            success, target, _ = self.battle.try_scout()
            if success and target is not None:
                acquired = self.monsters.create(
                    target.species_id,
                    level=target.level,
                    source="scout",
                )
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
        else:
            raise ValueError(f"戦闘コマンド {command} は未対応です。")
        self.start_battle_playback(log_start)
        if not self.battle_playback:
            self.finalize_battle_if_needed()

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

    def update_auto_battle(self, now: int) -> None:
        if not self.battle_session.auto_command_due(now, battle_mode=self.mode == "battle"):
            return
        self.handle_battle_command("fight")
        if self.battle and self.battle.outcome:
            self.stop_auto_battle()

    def start_battle_playback(self, log_start: int) -> None:
        self.battle_session.start_playback(log_start, pygame.time.get_ticks())

    def update_battle_playback(self, now: int) -> bool:
        result = self.battle_session.update_playback(now)
        if result["completed"]:
            self.finalize_battle_if_needed()
        return bool(result["changed"])

    def finalize_battle_if_needed(self) -> None:
        if not self.battle_session.mark_finalized():
            return
        assert self.battle is not None
        self.battle.mark_battle_complete()
        if not self.battle.learning_enabled:
            return
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
        context = self.battle_session.clear()
        if context["outcome"] == "defeat" and not context["simulation"]:
            church = self.field_progress.church_or_default()
            self.change_map(
                str(church["map_id"]),
                int(church["x"]),
                int(church["y"]),
                "全滅した。教会へ戻った。",
            )
        else:
            self.mode = "field"
            self.status = "フィールドへ戻った。"
        fixed_mob_id = context.get("fixed_mob_id")
        if context["outcome"] == "victory" and fixed_mob_id:
            self.despawn_fixed_mob_by_id(str(fixed_mob_id))

    def interact(self) -> None:
        if self.player_field is None:
            return
        target_x, target_y = self.player_field.front_position(
            self.player_x,
            self.player_y,
            self.player_direction,
        )
        npc = next(
            (
                character
                for character in [*self.visible_characters, *self.hidden_characters]
                if int(character["x"]) == target_x and int(character["y"]) == target_y
            ),
            None,
        )
        event = self.player_field.nearby_event(target_x, target_y)
        effect = self.runtime.field_events.resolve_interaction(
            npc,
            event,
            self.player_direction,
            self.status,
        )
        self.runtime.apply_field_effect(effect)

    def pickup(self) -> None:
        if self.player_field is None:
            return
        event = self.player_field.nearby_event(self.player_x, self.player_y)
        if event is None or event.get("type") != "pickup":
            self.status = "ここには拾えるものがない。"
            return
        item_id = str(event.get("item_id", "orange"))
        amount = int(event.get("amount", 1))
        self.gain_field_item(item_id, amount)
        self.status = str(event.get("text", f"{item_id}を拾った。"))

    def update_field(self, now: int) -> None:
        if self.player_field is None:
            return
        move_result = self.player_field.update(
            now,
            self.player_x,
            self.player_y,
            self.player_direction,
            self.visible_characters,
            self.hidden_characters,
        )
        if move_result:
            self.player_x = int(move_result["x"])
            self.player_y = int(move_result["y"])
            self.player_direction = str(move_result["direction"])
            self.state["x"] = self.player_x
            self.state["y"] = self.player_y
            self.state["direction"] = self.player_direction
            self.states.save(self.state)
            transition = self.player_field.step_transition_at(self.player_x, self.player_y)
            if transition is not None:
                self.runtime.apply_field_effect(
                    {
                        "kind": "transition",
                        "status": str(transition.get("text", "")),
                        "target": dict(transition["target"]),
                    }
                )
                return
        if self.hidden_enemy_controller is not None:
            encounter = self.hidden_enemy_controller.update(
                now,
                self.player_x,
                self.player_y,
                self.hidden_characters,
            )
            if encounter is not None:
                self.runtime.dispatch("battle", "start.wild", spawn=encounter, fixed_mob_id="")
                return
            self.hidden_characters = self.hidden_enemy_controller.characters()
        if self.fixed_mob_controller is not None:
            encounter = self.fixed_mob_controller.update(
                now,
                self.player_x,
                self.player_y,
                self.visible_characters,
            )
            if encounter is not None:
                self.runtime.dispatch(
                    "battle",
                    "start.wild",
                    spawn=dict(encounter["spawn"]),
                    fixed_mob_id=str(encounter["mob_id"]),
                )
                return
            self.visible_characters = self.fixed_mob_controller.characters()


def password_controls() -> tuple[list[tuple[str, pygame.Rect]], pygame.Rect, pygame.Rect, pygame.Rect]:
    keys = [(character, pygame.Rect(210 + index * 80, 370, 62, 54)) for index, character in enumerate(KANA_KEYS)]
    erase = pygame.Rect(210, 445, 100, 54)
    decide = pygame.Rect(330, 445, 100, 54)
    cancel = pygame.Rect(450, 445, 100, 54)
    return keys, erase, decide, cancel


def draw_password(screen: pygame.Surface, game: KadokaQuest) -> None:
    draw_text(screen, "合言葉", (360, 230), 34, ACCENT, True)
    draw_text(screen, game.password_input or "・・・・", (400, 310), 30)
    if game.password_message:
        draw_text(screen, game.password_message, (340, 520), 18)


def main(*, smoke: int | None = None) -> None:
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("kadoka quest")
    clock = pygame.time.Clock()
    game = KadokaQuest()
    battle_renderer = BattleRenderer(CharacterImageProvider())
    input_adapter = RuntimeInputAdapter(MOVE_DIRECTIONS)
    runtime = game.runtime
    running = True
    frames = 0

    def dispatch(target: str, action: str, **payload: object) -> object:
        return runtime.dispatch(target, action, **payload)

    battle_buttons = [
        Button(pygame.Rect(250, 650, 95, 48), "たたかう", lambda: None),
        Button(pygame.Rect(355, 650, 95, 48), "スカウト", lambda: None),
        Button(pygame.Rect(565, 650, 95, 48), "道具", lambda: None),
        Button(pygame.Rect(670, 650, 95, 48), "逃げる", lambda: None),
    ]
    password_keys, erase, decide, cancel = password_controls()
    mouse_adapter = RuntimeMouseAdapter(
        password_keys,
        {"backspace": erase, "submit": decide, "cancel": cancel},
        [(command, button.rect) for command, button in zip(("fight", "scout", "item", "run"), battle_buttons)],
    )

    while running:
        for event in pygame.event.get():
            event_now = pygame.time.get_ticks()
            battle_finished = bool(game.battle and game.battle.outcome)
            for request in input_adapter.translate(
                event,
                game.mode,
                event_now,
                battle_finished=battle_finished,
                battle_playback=game.battle_playback,
            ):
                if request["kind"] == "quit":
                    running = False
                else:
                    dispatch(str(request["target"]), str(request["action"]), **dict(request["payload"]))
            battle_enabled = bool(game.battle and not game.battle.outcome and not game.battle_playback)
            for request in mouse_adapter.translate(
                event,
                game.mode,
                battle_enabled=battle_enabled,
                now=event_now,
            ):
                dispatch(str(request["target"]), str(request["action"]), **dict(request["payload"]))

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
