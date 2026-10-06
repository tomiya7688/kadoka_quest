# {
#   責務: [game: ゲームの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import random
from uuid import uuid4

import pygame

from kadoka_quest.application.runtime_orchestrator import RuntimeOrchestrator
from kadoka_quest.apps.battle_session import BattleSession
from kadoka_quest.apps.field_event_app import FieldEventApplication
from kadoka_quest.apps.field_party_service import FieldPartyService
from kadoka_quest.apps.field_party_session import FieldPartySession
from kadoka_quest.apps.field_session import FieldSession
from kadoka_quest.apps.manager_process_service import ManagerProcessService
from kadoka_quest.apps.monster_import_service import MonsterImportService
from kadoka_quest.apps.password_session import PasswordSession
from kadoka_quest.apps.progress_session import ProgressSession
from kadoka_quest.core.ai import default_ai
from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.core.battle_rewards import battle_experience
from kadoka_quest.core.spawn_levels import wild_encounter_level
from kadoka_engine.wild_spawn import draw_wild_spawn, relative_spawn_weights
from kadoka_engine.field_engine import FieldEngine
from kadoka_engine.fixed_mob_controller import FixedMobController
from kadoka_engine.grid_movement import GridMovement
from kadoka_engine.hidden_enemy_controller import HiddenEnemyController
from kadoka_quest.core.monster import MonsterRecord
from kadoka_engine.player_field_controller import PlayerFieldController
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
from kadoka_quest.ui.runtime_input_adapter import RuntimeInputAdapter
from kadoka_quest.ui.runtime_mouse_adapter import RuntimeMouseAdapter


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
# {
#   責務: [KadokaQuest: kadoka・questの状態と振る舞いを担当する]
#   フィールド: [
#     repository: データ取得先
#     monsters: モンスター一覧
#     states: states
#     progress_session: 進行状態・セッション
#     parties: parties
#     rng: 乱数供給元
#     field_data: フィールド・データ
#     field_progress: フィールド・進行状態
#     field_session: フィールド・セッション
#     field_events: フィールド・イベント一覧
#     runtime: 実行時
#     battle_session: 戦闘・セッション
#     password_session: 暗号・セッション
#     character_images: キャラクター・画像一覧
#     manager_tool: manager・tool
#     monster_import_service: モンスター・import・service
#     field_party_session: フィールド・パーティ・セッション
#     field_party_service: フィールド・パーティ・service
#     status: 状態異常
#     held_move_key: 長押し・move・キー
#     held_move_direction: 長押し・move・direction
#     mode: mode
#     state: 状態
#   ]
# }
class KadokaQuest:
    # {
    #   責務: [__init__: kadoka・questが利用する初期状態と依存を設定する]
    #   処理: [1: kadoka・questが利用する初期状態と依存を設定する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     repository: データ取得先（GameRepository | None）
    #     monsters: モンスター一覧（MonsterStore | None）
    #     states: states（StateStore | None）
    #     parties: parties（PartyStore | None）
    #     rng: 乱数供給元（random.Random | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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
        self.progress_session = ProgressSession(self.states.load())
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
        field = FieldEngine(initial_world["map"], self.field_data.blocks())
        fixed_mobs = FixedMobController(field, self.rng, FIXED_MOB_MOVE_DURATION_MS)
        hidden_enemies = HiddenEnemyController(
            field,
            self.rng,
            HIDDEN_CHASE_MOVE_INTERVAL_MS,
            HIDDEN_WANDER_MOVE_INTERVAL_MS,
            HIDDEN_VISION_RANGE,
        )
        player = PlayerFieldController(
            initial_world["x"],
            initial_world["y"],
            PLAYER_MOVE_DURATION_MS,
            MOVE_REPEAT_DELAY_MS,
            MOVE_REPEAT_INTERVAL_MS,
        )
        self.field_session = FieldSession(field, player, fixed_mobs, hidden_enemies)
        self.field_events = FieldEventApplication()
        self.runtime = RuntimeOrchestrator(self)
        self.battle_session = BattleSession()
        self.password_session = PasswordSession(PASSWORD, KANA_KEYS)
        self.character_images = CharacterImageProvider(self.repository, ASSET_ROOT)
        self.manager_tool = ManagerProcessService(PROJECT_ROOT / "manage.py")
        self.monster_import_service = MonsterImportService(self.monsters, self.repository, IMPORT_ROOT)
        self.field_party_session = FieldPartySession()
        self.field_party_service = FieldPartyService(self.field_party_session, self.parties, self.monsters, self.states)
        self.status = "矢印/WASDで移動（長押し対応）。野生モンスターが正面に来ると戦闘になります。"
        self.held_move_key: int | None = None
        self.reset_hidden_monsters()
        self.reset_home_npcs()

    # {
    #   責務: [state: kadoka・questの状態を求める]
    #   処理: [1: kadoka・questの状態を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.progress・session.state（dict）]
    # }
    @property
    def state(self) -> dict:
        return self.progress_session.state

    # {
    #   責務: [state: kadoka・questの状態へ設定値を反映する]
    #   処理: [1: kadoka・questの状態へ設定値を反映する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（dict）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @state.setter
    def state(self, value: dict) -> None:
        self.progress_session.state = value

    # {
    #   責務: [map_data: kadoka・questのマップ・データを求める]
    #   処理: [1: kadoka・questのマップ・データを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.field・session.map・データ（dict）]
    # }
    @property
    def map_data(self) -> dict:
        return self.field_session.map_data

    # {
    #   責務: [map_data: kadoka・questのマップ・データへ設定値を反映する]
    #   処理: [1: kadoka・questのマップ・データへ設定値を反映する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（dict）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @map_data.setter
    def map_data(self, value: dict) -> None:
        self.field_session.set_world(value, self.blocks)

    # {
    #   責務: [blocks: kadoka・questのブロック定義を求める]
    #   処理: [1: kadoka・questのブロック定義を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.field・session.blocks（dict[str, dict]）]
    # }
    @property
    def blocks(self) -> dict[str, dict]:
        return self.field_session.blocks

    # {
    #   責務: [blocks: kadoka・questのブロック定義へ設定値を反映する]
    #   処理: [1: kadoka・questのブロック定義へ設定値を反映する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（dict[str, dict]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @blocks.setter
    def blocks(self, value: dict[str, dict]) -> None:
        self.field_session.set_world(self.map_data, value)

    # {
    #   責務: [field: kadoka・questのフィールドを求める]
    #   処理: [1: kadoka・questのフィールドを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.field・session.field（FieldEngine）]
    # }
    @property
    def field(self) -> FieldEngine:
        return self.field_session.field

    # {
    #   責務: [field: kadoka・questのフィールドへ設定値を反映する]
    #   処理: [1: kadoka・questのフィールドへ設定値を反映する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（FieldEngine）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @field.setter
    def field(self, value: FieldEngine) -> None:
        self.field_session.replace_field(value)

    # {
    #   責務: [player_field: kadoka・questの主人公・フィールドを求める]
    #   処理: [1: kadoka・questの主人公・フィールドを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.field・session.player（PlayerFieldController）]
    # }
    @property
    def player_field(self) -> PlayerFieldController:
        return self.field_session.player

    # {
    #   責務: [player_field: kadoka・questの主人公・フィールドへ設定値を反映する]
    #   処理: [1: kadoka・questの主人公・フィールドへ設定値を反映する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（PlayerFieldController）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @player_field.setter
    def player_field(self, value: PlayerFieldController) -> None:
        self.field_session.player = value

    # {
    #   責務: [fixed_mobs: kadoka・questのfixed・モブ一覧を求める]
    #   処理: [1: kadoka・questのfixed・モブ一覧を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.field・session.fixed・モブ一覧（FixedMobController）]
    # }
    @property
    def fixed_mobs(self) -> FixedMobController:
        return self.field_session.fixed_mobs

    # {
    #   責務: [fixed_mobs: kadoka・questのfixed・モブ一覧へ設定値を反映する]
    #   処理: [1: kadoka・questのfixed・モブ一覧へ設定値を反映する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（FixedMobController）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @fixed_mobs.setter
    def fixed_mobs(self, value: FixedMobController) -> None:
        self.field_session.fixed_mobs = value

    # {
    #   責務: [hidden_enemies: kadoka・questの非表示・敵を求める]
    #   処理: [1: kadoka・questの非表示・敵を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.field・session.hidden・敵（HiddenEnemyController）]
    # }
    @property
    def hidden_enemies(self) -> HiddenEnemyController:
        return self.field_session.hidden_enemies

    # {
    #   責務: [hidden_enemies: kadoka・questの非表示・敵へ設定値を反映する]
    #   処理: [1: kadoka・questの非表示・敵へ設定値を反映する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（HiddenEnemyController）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @hidden_enemies.setter
    def hidden_enemies(self, value: HiddenEnemyController) -> None:
        self.field_session.hidden_enemies = value

    # {
    #   責務: [home_npcs: Compatibility view of fixed-mob runtime state.]
    #   処理: [1: Compatibility view of fixed-mob runtime state.]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.fixed・mobs.npcs（list[dict]）]
    # }
    @property
    def home_npcs(self) -> list[dict]:
        """Compatibility view of fixed-mob runtime state."""
        return self.fixed_mobs.npcs

    # {
    #   責務: [home_npcs: kadoka・questのhome・npcsへ設定値を反映する]
    #   処理: [1: kadoka・questのhome・npcsへ設定値を反映する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（list[dict]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @home_npcs.setter
    def home_npcs(self, value: list[dict]) -> None:
        self.fixed_mobs.npcs = value

    # {
    #   責務: [hidden_monsters: Compatibility view of invisible-enemy runtime state.]
    #   処理: [1: Compatibility view of invisible-enemy runtime state.]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.hidden・enemies.monsters（list[dict]）]
    # }
    @property
    def hidden_monsters(self) -> list[dict]:
        """Compatibility view of invisible-enemy runtime state."""
        return self.hidden_enemies.monsters

    # {
    #   責務: [hidden_monsters: kadoka・questの非表示・モンスター一覧へ設定値を反映する]
    #   処理: [1: kadoka・questの非表示・モンスター一覧へ設定値を反映する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（list[dict]）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @hidden_monsters.setter
    def hidden_monsters(self, value: list[dict]) -> None:
        self.hidden_enemies.monsters = value

    # {
    #   責務: [player_x: kadoka・questの主人公・X座標を求める]
    #   処理: [1: kadoka・questの主人公・X座標を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.player・field.x（int）]
    # }
    @property
    def player_x(self) -> int:
        return self.player_field.x

    # {
    #   責務: [player_x: kadoka・questの主人公・X座標へ設定値を反映する]
    #   処理: [1: kadoka・questの主人公・X座標へ設定値を反映する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @player_x.setter
    def player_x(self, value: int) -> None:
        self.player_field.x = int(value)

    # {
    #   責務: [player_y: kadoka・questの主人公・Y座標を求める]
    #   処理: [1: kadoka・questの主人公・Y座標を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.player・field.y（int）]
    # }
    @property
    def player_y(self) -> int:
        return self.player_field.y

    # {
    #   責務: [player_y: kadoka・questの主人公・Y座標へ設定値を反映する]
    #   処理: [1: kadoka・questの主人公・Y座標へ設定値を反映する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @player_y.setter
    def player_y(self, value: int) -> None:
        self.player_field.y = int(value)

    # {
    #   責務: [player_direction: kadoka・questの主人公・directionを求める]
    #   処理: [1: kadoka・questの主人公・directionを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.player・field.direction（str）]
    # }
    @property
    def player_direction(self) -> str:
        return self.player_field.direction

    # {
    #   責務: [player_direction: kadoka・questの主人公・directionへ設定値を反映する]
    #   処理: [1: kadoka・questの主人公・directionへ設定値を反映する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（str）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @player_direction.setter
    def player_direction(self, value: str) -> None:
        self.player_field.direction = str(value)

    # {
    #   責務: [player_movement: kadoka・questの主人公・移動を求める]
    #   処理: [1: kadoka・questの主人公・移動を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.player・field.visual（GridMovement）]
    # }
    @property
    def player_movement(self) -> GridMovement:
        return self.player_field.visual

    # {
    #   責務: [held_move_direction: kadoka・questの長押し・move・directionを求める]
    #   処理: [1: kadoka・questの長押し・move・directionを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.player・field.held・direction（str | None）]
    # }
    @property
    def held_move_direction(self) -> str | None:
        return self.player_field.held_direction

    # {
    #   責務: [held_move_direction: kadoka・questの長押し・move・directionへ設定値を反映する]
    #   処理: [1: kadoka・questの長押し・move・directionへ設定値を反映する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（str | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @held_move_direction.setter
    def held_move_direction(self, value: str | None) -> None:
        self.player_field.held_direction = value

    # {
    #   責務: [next_move_tick: move・tickを次の値を求める]
    #   処理: [1: move・tickを次の値を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.player・field.next・move・tick（int）]
    # }
    @property
    def next_move_tick(self) -> int:
        return self.player_field.next_move_tick

    # {
    #   責務: [next_move_tick: kadoka・questのnext・move・tickへ設定値を反映する]
    #   処理: [1: kadoka・questのnext・move・tickへ設定値を反映する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @next_move_tick.setter
    def next_move_tick(self, value: int) -> None:
        self.player_field.next_move_tick = int(value)

    # {
    #   責務: [mode: kadoka・questのmodeを求める]
    #   処理: [1: kadoka・questのmodeを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.runtime.mode（str）]
    # }
    @property
    def mode(self) -> str:
        return self.runtime.mode

    # {
    #   責務: [mode: kadoka・questのmodeへ設定値を反映する]
    #   処理: [1: kadoka・questのmodeへ設定値を反映する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（str）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @mode.setter
    def mode(self, value: str) -> None:
        self.runtime.transition_to(value)

    # {
    #   責務: [battle: kadoka・questの戦闘を求める]
    #   処理: [1: kadoka・questの戦闘を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.battle・session.battle（BattleEngine | None）]
    # }
    @property
    def battle(self) -> BattleEngine | None:
        return self.battle_session.battle

    # {
    #   責務: [battle: kadoka・questの戦闘へ設定値を反映する]
    #   処理: [1: kadoka・questの戦闘へ設定値を反映する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（BattleEngine | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @battle.setter
    def battle(self, value: BattleEngine | None) -> None:
        self.battle_session.battle = value

    # {
    #   責務: [battle_selection: kadoka・questの戦闘・選択状態を求める]
    #   処理: [1: kadoka・questの戦闘・選択状態を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.battle・session.selection（int）]
    # }
    @property
    def battle_selection(self) -> int:
        return self.battle_session.selection

    # {
    #   責務: [battle_selection: kadoka・questの戦闘・選択状態へ設定値を反映する]
    #   処理: [1: kadoka・questの戦闘・選択状態へ設定値を反映する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @battle_selection.setter
    def battle_selection(self, value: int) -> None:
        self.battle_session.selection = int(value)

    # {
    #   責務: [last_auto_tick: kadoka・questのlast・自動・tickを求める]
    #   処理: [1: kadoka・questのlast・自動・tickを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.battle・session.last・自動・tick（int）]
    # }
    @property
    def last_auto_tick(self) -> int:
        return self.battle_session.last_auto_tick

    # {
    #   責務: [last_auto_tick: kadoka・questのlast・自動・tickへ設定値を反映する]
    #   処理: [1: kadoka・questのlast・自動・tickへ設定値を反映する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @last_auto_tick.setter
    def last_auto_tick(self, value: int) -> None:
        self.battle_session.last_auto_tick = int(value)

    # {
    #   責務: [battle_playback: kadoka・questの戦闘・playbackを求める]
    #   処理: [1: kadoka・questの戦闘・playbackを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.battle・session.playback（bool）]
    # }
    @property
    def battle_playback(self) -> bool:
        return self.battle_session.playback

    # {
    #   責務: [battle_playback: kadoka・questの戦闘・playbackへ設定値を反映する]
    #   処理: [1: kadoka・questの戦闘・playbackへ設定値を反映する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（bool）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @battle_playback.setter
    def battle_playback(self, value: bool) -> None:
        self.battle_session.playback = bool(value)

    # {
    #   責務: [battle_visible_log_count: kadoka・questの戦闘・visible・ログ・countを求める]
    #   処理: [1: kadoka・questの戦闘・visible・ログ・countを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.battle・session.visible・ログ・count（int）]
    # }
    @property
    def battle_visible_log_count(self) -> int:
        return self.battle_session.visible_log_count

    # {
    #   責務: [battle_visible_log_count: kadoka・questの戦闘・visible・ログ・countへ設定値を反映する]
    #   処理: [1: kadoka・questの戦闘・visible・ログ・countへ設定値を反映する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @battle_visible_log_count.setter
    def battle_visible_log_count(self, value: int) -> None:
        self.battle_session.visible_log_count = int(value)

    # {
    #   責務: [battle_next_log_tick: kadoka・questの戦闘・next・ログ・tickを求める]
    #   処理: [1: kadoka・questの戦闘・next・ログ・tickを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.battle・session.next・ログ・tick（int）]
    # }
    @property
    def battle_next_log_tick(self) -> int:
        return self.battle_session.next_log_tick

    # {
    #   責務: [battle_next_log_tick: kadoka・questの戦闘・next・ログ・tickへ設定値を反映する]
    #   処理: [1: kadoka・questの戦闘・next・ログ・tickへ設定値を反映する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @battle_next_log_tick.setter
    def battle_next_log_tick(self, value: int) -> None:
        self.battle_session.next_log_tick = int(value)

    # {
    #   責務: [battle_focus_id: kadoka・questの戦闘・focus・識別子を求める]
    #   処理: [1: kadoka・questの戦闘・focus・識別子を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.battle・session.focus・識別子（str | None）]
    # }
    @property
    def battle_focus_id(self) -> str | None:
        return self.battle_session.focus_id

    # {
    #   責務: [battle_focus_id: kadoka・questの戦闘・focus・識別子へ設定値を反映する]
    #   処理: [1: kadoka・questの戦闘・focus・識別子へ設定値を反映する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（str | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @battle_focus_id.setter
    def battle_focus_id(self, value: str | None) -> None:
        self.battle_session.focus_id = value

    # {
    #   責務: [simulation: kadoka・questのsimulationを求める]
    #   処理: [1: kadoka・questのsimulationを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.battle・session.simulation（bool）]
    # }
    @property
    def simulation(self) -> bool:
        return self.battle_session.simulation

    # {
    #   責務: [simulation: kadoka・questのsimulationへ設定値を反映する]
    #   処理: [1: kadoka・questのsimulationへ設定値を反映する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（bool）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @simulation.setter
    def simulation(self, value: bool) -> None:
        self.battle_session.simulation = bool(value)

    # {
    #   責務: [password_input: kadoka・questの暗号・入力を求める]
    #   処理: [1: kadoka・questの暗号・入力を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: self.password・session.input・文字列（str）]
    # }
    @property
    def password_input(self) -> str:
        return self.password_session.input_text

    # {
    #   責務: [password_input: kadoka・questの暗号・入力へ設定値を反映する]
    #   処理: [1: kadoka・questの暗号・入力へ設定値を反映する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     value: 値（str）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    @password_input.setter
    def password_input(self, value: str) -> None:
        self.password_session.input_text = str(value)

    # {
    #   責務: [party: kadoka・questのパーティを求める]
    #   処理: [1: kadoka・questのパーティを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: kadoka・questのパーティを求めるための結果（list[MonsterRecord]）]
    # }
    def party(self) -> list[MonsterRecord]:
        return StateStore.party_records(self.state, self.monsters)

    # {
    #   責務: [save_position: 座標を保存する]
    #   処理: [1: 座標を保存する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def save_position(self) -> None:
        self.field_progress.save_position(
            self.state,
            str(self.map_data["id"]),
            self.player_x,
            self.player_y,
        )

    # {
    #   責務: [change_map: マップを切り替える]
    #   処理: [1: マップを切り替える]
    #   引数: [
    #     self: 処理対象インスタンス
    #     map_id: マップ・識別子（str）
    #     x: X座標（int）
    #     y: Y座標（int）
    #     message: message（str | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def change_map(self, map_id: str, x: int, y: int, message: str | None = None) -> None:
        loaded = self.field_data.load_map(map_id, x, y)
        self.field_session.enter_map(loaded["map"], loaded["x"], loaded["y"])
        self.save_position()
        self.reset_hidden_monsters()
        self.reset_home_npcs()
        self.status = message or f"{self.map_data['display_name']}へ入りました。"

    # {
    #   責務: [move: kadoka・questを移動する]
    #   処理: [1: kadoka・questを移動する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     dx: 横方向の移動量（int）
    #     dy: 縦方向の移動量（int）
    #     now: 現在時刻（int | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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

    # {
    #   責務: [character_at: kadoka・questのキャラクター・atを求める]
    #   処理: [1: kadoka・questのキャラクター・atを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     x: X座標（int）
    #     y: Y座標（int）
    #     include_hidden: include・非表示（bool）
    #     include_home: include・home（bool）
    #   ]
    #   戻り値: [result: kadoka・questのキャラクター・atを求めるための結果（dict | None）]
    # }
    def character_at(self, x: int, y: int, *, include_hidden: bool = True, include_home: bool = True) -> dict | None:
        if include_home:
            found = next((npc for npc in self.home_npcs if (int(npc["x"]), int(npc["y"])) == (int(x), int(y))), None)
            if found:
                return found
        if include_hidden:
            return next((monster for monster in self.hidden_monsters if (int(monster["x"]), int(monster["y"])) == (int(x), int(y))), None)
        return None

    # {
    #   責務: [player_front_position: kadoka・questの主人公・front・座標を求める]
    #   処理: [1: kadoka・questの主人公・front・座標を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: kadoka・questの主人公・front・座標を求めるための結果（tuple[int, int]）]
    # }
    def player_front_position(self) -> tuple[int, int]:
        self.field.set_world(self.map_data, self.blocks)
        return self.field.front_position(self.player_x, self.player_y, self.player_direction)

    # {
    #   責務: [start_held_move: 長押し・moveを開始する]
    #   処理: [1: 長押し・moveを開始する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     key: キー（int）
    #     now: 現在時刻（int）
    #   ]
    #   戻り値: [result: 長押し・moveを開始するための結果（bool）]
    # }
    def start_held_move(self, key: int, now: int) -> bool:
        direction = MOVE_KEY_DIRECTIONS.get(key)
        if direction is None:
            return False
        self.held_move_key = key
        return self.start_held_direction(direction, now)

    # {
    #   責務: [start_held_direction: 長押し・directionを開始する]
    #   処理: [1: 長押し・directionを開始する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     direction: direction（str）
    #     now: 現在時刻（int）
    #   ]
    #   戻り値: [result: 長押し・directionを開始するための結果（bool）]
    # }
    def start_held_direction(self, direction: str, now: int) -> bool:
        if self.mode != "field":
            return False
        vector = self.player_field.begin_hold(direction, now)
        if vector is None:
            return False
        self.move(*vector, now=now)
        return True

    # {
    #   責務: [stop_held_move: 長押し・moveを停止する]
    #   処理: [1: 長押し・moveを停止する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     key: キー（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def stop_held_move(self, key: int) -> None:
        if key == self.held_move_key:
            self.held_move_key = None
            self.held_move_direction = None

    # {
    #   責務: [stop_held_direction: 長押し・directionを停止する]
    #   処理: [1: 長押し・directionを停止する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     direction: direction（str）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def stop_held_direction(self, direction: str) -> None:
        if self.player_field.stop_hold(direction):
            self.held_move_key = None

    # {
    #   責務: [update_held_move: 長押し・moveを更新する]
    #   処理: [1: 長押し・moveを更新する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     now: 現在時刻（int）
    #   ]
    #   戻り値: [result: 長押し・moveを更新するための結果（bool）]
    # }
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

    # {
    #   責務: [handle_step_event: step・イベントを入力を処理する]
    #   処理: [1: step・イベントを入力を処理する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: step・イベントを入力を処理するための結果（bool）]
    # }
    def handle_step_event(self) -> bool:
        self.field.set_world(self.map_data, self.blocks)
        event = self.field.step_transition_at(self.player_x, self.player_y)
        effect = self.field_events.resolve_step(event)
        if effect["kind"] != "transition":
            return False
        self.runtime.apply_field_effect(effect)
        return True

    # {
    #   責務: [nearby_event: イベントを近くの対象を探す]
    #   処理: [1: イベントを近くの対象を探す]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: イベントを近くの対象を探すための結果（dict | None）]
    # }
    def nearby_event(self) -> dict | None:
        self.field.set_world(self.map_data, self.blocks)
        return self.field.nearby_event(self.player_x, self.player_y)

    # {
    #   責務: [interact: kadoka・questのinteractを求める]
    #   処理: [1: kadoka・questのinteractを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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

    # {
    #   責務: [use_field_requirement: Apply an item or skill use to a nearby declarative field event.]
    #   処理: [1: Apply an item or skill use to a nearby declarative field event.]
    #   引数: [
    #     self: 処理対象インスタンス
    #     requirement_kind: requirement・種別（str）
    #     requirement_id: requirement・識別子（str）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def use_field_requirement(self, requirement_kind: str, requirement_id: str) -> None:
        """Apply an item or skill use to a nearby declarative field event.

        Item and skill menus call this semantic boundary; the field screen
        itself does not need to know event-specific gameplay rules.
        """
        effect = self.field_events.resolve_use(
            list(self.map_data.get("events", [])),
            (self.player_x, self.player_y),
            requirement_kind,
            requirement_id,
        )
        self.runtime.apply_field_effect(effect)

    # {
    #   責務: [reacquire_ghosts: kadoka・questのreacquire・ghostsを求める]
    #   処理: [1: kadoka・questのreacquire・ghostsを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def reacquire_ghosts(self) -> None:
        added = []
        for species_id in ("maru", "kadoka"):
            if not any(record.species_id == species_id for record in self.monsters.list_records()):
                record = self.monsters.create(species_id, level=1, source="ghost_home_password")
                added.append(record.name)
        self.field_progress.set_flag(self.state, "ghost_entrance_open", True)
        self.status = "へいわなすみか。" + (f" 牧場に {'・'.join(added)} が増えました。" if added else " 2匹とも既にいます。")

    # {
    #   責務: [open_password_input: 暗号・入力を開く]
    #   処理: [1: 暗号・入力を開く]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def open_password_input(self) -> None:
        self.password_session.open()
        self.mode = "password"

    # {
    #   責務: [append_password: 暗号を末尾へ追加する]
    #   処理: [1: 暗号を末尾へ追加する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     character: キャラクター（str）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def append_password(self, character: str) -> None:
        self.password_session.append(character)

    # {
    #   責務: [backspace_password: kadoka・questのbackspace・暗号を求める]
    #   処理: [1: kadoka・questのbackspace・暗号を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def backspace_password(self) -> None:
        self.password_session.backspace()

    # {
    #   責務: [submit_password: 暗号を確定する]
    #   処理: [1: 暗号を確定する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 暗号を確定するための結果（bool）]
    # }
    def submit_password(self) -> bool:
        if not self.password_session.submit():
            return False
        self.mode = "field"
        self.reacquire_ghosts()
        return True

    # {
    #   責務: [cancel_password: kadoka・questのcancel・暗号を求める]
    #   処理: [1: kadoka・questのcancel・暗号を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def cancel_password(self) -> None:
        self.password_session.cancel()
        self.mode = "field"
        self.status = "水の湧き場から離れました。"

    # {
    #   責務: [reset_home_npcs: home・npcsの初期状態へ戻す]
    #   処理: [1: home・npcsの初期状態へ戻す]
    #   引数: [
    #     self: 処理対象インスタンス
    #     now: 現在時刻（int | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def reset_home_npcs(self, now: int | None = None) -> None:
        now = pygame.time.get_ticks() if now is None else int(now)

        # {
        #   責務: [species_name: kadoka・questの種族・名前を求める]
        #   処理: [1: kadoka・questの種族・名前を求める]
        #   引数: [species_id: 種族・識別子（str）]
        #   戻り値: [result: kadoka・questの種族・名前を求めるための結果（str）]
        # }
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

    # {
    #   責務: [nearby_home_npc: home・npcを近くの対象を探す]
    #   処理: [1: home・npcを近くの対象を探す]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: home・npcを近くの対象を探すための結果（dict | None）]
    # }
    def nearby_home_npc(self) -> dict | None:
        return self.fixed_mobs.nearby(self.player_front_position())

    # {
    #   責務: [next_npc_dialogue: npc・会話を次の値を求める]
    #   処理: [1: npc・会話を次の値を求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     npc: npc（dict）
    #   ]
    #   戻り値: [result: npc・会話を次の値を求めるための結果（str）]
    # }
    def next_npc_dialogue(self, npc: dict) -> str:
        return self.fixed_mobs.next_dialogue(npc)

    # {
    #   責務: [despawn_fixed_mob: kadoka・questのdespawn・fixed・モブを求める]
    #   処理: [1: kadoka・questのdespawn・fixed・モブを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     npc: npc（dict）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def despawn_fixed_mob(self, npc: dict) -> None:
        self.fixed_mobs.remove(npc)
        if not npc.get("respawn_on_map_enter", True):
            key = f"{self.map_data['id']}:{npc['id']}"
            self.field_progress.mark_despawned(self.state, key)

    # {
    #   責務: [despawn_fixed_mob_by_id: kadoka・questのdespawn・fixed・モブ・by・識別子を求める]
    #   処理: [1: kadoka・questのdespawn・fixed・モブ・by・識別子を求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     npc_id: npc・識別子（str）
    #   ]
    #   戻り値: [result: kadoka・questのdespawn・fixed・モブ・by・識別子を求めるための結果（bool）]
    # }
    def despawn_fixed_mob_by_id(self, npc_id: str) -> bool:
        npc = next((item for item in self.home_npcs if str(item.get("id")) == str(npc_id)), None)
        if npc is None:
            return False
        self.despawn_fixed_mob(npc)
        return True

    # {
    #   責務: [register_church: 教会を登録する]
    #   処理: [1: 教会を登録する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     revive: 復活（dict）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def register_church(self, revive: dict) -> None:
        self.field_progress.register_church(self.state, revive)

    # {
    #   責務: [gain_field_item: フィールド・アイテムを取得する]
    #   処理: [1: フィールド・アイテムを取得する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     item_id: アイテム・識別子（str）
    #   ]
    #   戻り値: [result: フィールド・アイテムを取得するための結果（int）]
    # }
    def gain_field_item(self, item_id: str) -> int:
        return self.field_progress.add_item(self.state, item_id)

    # {
    #   責務: [npc_front_position: kadoka・questのnpc・front・座標を求める]
    #   処理: [1: kadoka・questのnpc・front・座標を求める]
    #   引数: [npc: npc（dict）]
    #   戻り値: [result: kadoka・questのnpc・front・座標を求めるための結果（tuple[int, int]）]
    # }
    @staticmethod
    def npc_front_position(npc: dict) -> tuple[int, int]:
        return FixedMobController.front_position(npc)

    # {
    #   責務: [npc_faces_player: kadoka・questのnpc・faces・主人公を求める]
    #   処理: [1: kadoka・questのnpc・faces・主人公を求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     npc: npc（dict）
    #   ]
    #   戻り値: [result: kadoka・questのnpc・faces・主人公を求めるための結果（bool）]
    # }
    def npc_faces_player(self, npc: dict) -> bool:
        return self.fixed_mobs.faces_player(npc, (self.player_x, self.player_y))

    # {
    #   責務: [move_home_npcs: home・npcsを移動する]
    #   処理: [1: home・npcsを移動する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def move_home_npcs(self) -> None:
        if self.mode != "field" or not self.home_npcs:
            return
        self.fixed_mobs.move_all(
            (self.player_x, self.player_y),
            pygame.time.get_ticks(),
        )

    # {
    #   責務: [move_home_npc: home・npcを移動する]
    #   処理: [1: home・npcを移動する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     npc: npc（dict）
    #     now: 現在時刻（int | None）
    #   ]
    #   戻り値: [result: home・npcを移動するための結果（bool）]
    # }
    def move_home_npc(self, npc: dict, now: int | None = None) -> bool:
        now = pygame.time.get_ticks() if now is None else int(now)
        return self.fixed_mobs.move(npc, (self.player_x, self.player_y), now)

    # {
    #   責務: [character_image: kadoka・questのキャラクター・画像を求める]
    #   処理: [1: kadoka・questのキャラクター・画像を求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     species_id: 種族・識別子（str）
    #     kind: 種別（str）
    #     size: 大きさ（tuple[int, int]）
    #   ]
    #   戻り値: [result: kadoka・questのキャラクター・画像を求めるための結果（pygame.Surface | None）]
    # }
    def character_image(self, species_id: str, kind: str, size: tuple[int, int]) -> pygame.Surface | None:
        return self.character_images.get(species_id, kind, size)

    # {
    #   責務: [field_pickup: kadoka・questのフィールド・pickupを求める]
    #   処理: [1: kadoka・questのフィールド・pickupを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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

    # {
    #   責務: [spawn_options: kadoka・questの出現・optionsを求める]
    #   処理: [1: kadoka・questの出現・optionsを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: kadoka・questの出現・optionsを求めるための結果（list[dict]）]
    # }
    def spawn_options(self) -> list[dict]:
        self.hidden_enemies.set_world(self.map_data, self.blocks)
        return self.hidden_enemies.spawn_options(self.state.get("flags", {}))

    # {
    #   責務: [reset_hidden_monsters: 非表示・モンスター一覧の初期状態へ戻す]
    #   処理: [1: 非表示・モンスター一覧の初期状態へ戻す]
    #   引数: [
    #     self: 処理対象インスタンス
    #     now: 現在時刻（int | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def reset_hidden_monsters(self, now: int | None = None) -> None:
        now = pygame.time.get_ticks() if now is None else int(now)
        self.hidden_enemies.set_world(self.map_data, self.blocks)
        self.hidden_enemies.reset(
            (self.player_x, self.player_y),
            self.state.get("flags", {}),
            now,
            species_ai_weights=self.field_data.species_ai_weights(self.map_data),
        )

    # {
    #   責務: [move_hidden_monsters: 非表示・モンスター一覧を移動する]
    #   処理: [1: 非表示・モンスター一覧を移動する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def move_hidden_monsters(self) -> None:
        if self.mode != "field":
            return
        self.hidden_enemies.move_all(
            (self.player_x, self.player_y),
            {(int(npc["x"]), int(npc["y"])) for npc in self.home_npcs},
        )
        self.check_hidden_collision()

    # {
    #   責務: [monster_sees_player: kadoka・questのモンスター・sees・主人公を求める]
    #   処理: [1: kadoka・questのモンスター・sees・主人公を求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     monster: モンスター（dict）
    #   ]
    #   戻り値: [result: kadoka・questのモンスター・sees・主人公を求めるための結果（bool）]
    # }
    def monster_sees_player(self, monster: dict) -> bool:
        return self.hidden_enemies.sees_player(monster, (self.player_x, self.player_y))

    # {
    #   責務: [move_hidden_monster: 非表示・モンスターを移動する]
    #   処理: [1: 非表示・モンスターを移動する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     monster: モンスター（dict）
    #   ]
    #   戻り値: [result: 非表示・モンスターを移動するための結果（bool）]
    # }
    def move_hidden_monster(self, monster: dict) -> bool:
        return self.hidden_enemies.move(
            monster,
            (self.player_x, self.player_y),
            {(int(npc["x"]), int(npc["y"])) for npc in self.home_npcs},
        )

    # {
    #   責務: [update_field_mobs: フィールド・モブ一覧を更新する]
    #   処理: [1: フィールド・モブ一覧を更新する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     now: 現在時刻（int）
    #   ]
    #   戻り値: [result: フィールド・モブ一覧を更新するための結果（bool）]
    # }
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

    # {
    #   責務: [check_hidden_collision: 非表示・collisionを検査する]
    #   処理: [1: 非表示・collisionを検査する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: 非表示・collisionを検査するための結果（bool）]
    # }
    def check_hidden_collision(self) -> bool:
        if self.mode != "field":
            return False
        monster = self.hidden_enemies.find_at(self.player_front_position())
        if monster is None:
            return False
        return self.start_wild_battle(monster["spawn"], monster)

    # {
    #   責務: [make_wild: wildを構築する]
    #   処理: [1: wildを構築する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     spawn: 出現（dict）
    #   ]
    #   戻り値: [result: wildを構築するための結果（MonsterRecord）]
    # }
    def make_wild(self, spawn: dict) -> MonsterRecord:
        species_id = str(spawn["species_id"])
        bundle = self.repository.get_species(species_id)
        context = str(self.field_session.map_data.get("encounter_context", "normal"))
        party = self.party() if context == "metal_area" else []
        level = wild_encounter_level(spawn, party, context, self.rng)
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

    # {
    #   責務: [start_wild_battle: wild・戦闘を開始する]
    #   処理: [1: wild・戦闘を開始する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     spawn: 出現（dict | None）
    #     hidden_monster: 非表示・モンスター（dict | None）
    #     fixed_mob_id: fixed・モブ・識別子（str | None）
    #   ]
    #   戻り値: [result: wild・戦闘を開始するための結果（bool）]
    # }
    def start_wild_battle(
        self,
        spawn: dict | None = None,
        hidden_monster: dict | None = None,
        *,
        fixed_mob_id: str | None = None,
    ) -> bool:
        if self.mode != "field" or self.battle_session.battle is not None:
            return False
        options = self.spawn_options()
        if (not spawn and not options) or not self.party():
            return False
        if spawn is None:
            spawn = draw_wild_spawn(
                self.rng, options, relative_spawn_weights(options),
                self.field_session.map_data.get("pop_rate", 100),
            )
            if spawn is None:
                return False
        enemies = [self.make_wild(spawn)]
        battle = BattleEngine(
            self.repository, self.party(), enemies, self.rng, learning_enabled=True,
            encounter_context=str(self.field_session.map_data.get("encounter_context", "normal")),
        )
        self.battle_session.begin(
            battle,
            pygame.time.get_ticks(),
            fixed_mob_id=fixed_mob_id,
        )
        if hidden_monster is not None:
            self.hidden_enemies.remove(hidden_monster)
        self.mode = "battle"
        self.status = f"{', '.join(record.name for record in enemies)} が現れた。"
        return True

    # {
    #   責務: [start_simulation: simulationを開始する]
    #   処理: [1: simulationを開始する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def start_simulation(self) -> None:
        battle, self.status = self.monster_import_service.create_simulation(self.party(), self.rng)
        if battle is None:
            return
        self.battle_session.begin(battle, pygame.time.get_ticks(), simulation=True)
        self.mode = "battle"

    # {
    #   責務: [handle_battle_command: 戦闘・コマンドを入力を処理する]
    #   処理: [1: 戦闘・コマンドを入力を処理する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     command: コマンド（str）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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

    # {
    #   責務: [reset_battle_presentation: 戦闘・presentationの初期状態へ戻す]
    #   処理: [1: 戦闘・presentationの初期状態へ戻す]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def reset_battle_presentation(self) -> None:
        self.battle_session.reset_presentation()

    # {
    #   責務: [start_battle_playback: 戦闘・playbackを開始する]
    #   処理: [1: 戦闘・playbackを開始する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     log_start: ログ・start（int）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def start_battle_playback(self, log_start: int) -> None:
        self.battle_session.start_playback(log_start, pygame.time.get_ticks())

    # {
    #   責務: [battle_log_delay: kadoka・questの戦闘・ログ・delayを求める]
    #   処理: [1: kadoka・questの戦闘・ログ・delayを求める]
    #   引数: [
    #     self: 処理対象インスタンス
    #     line: line（str）
    #   ]
    #   戻り値: [result: kadoka・questの戦闘・ログ・delayを求めるための結果（int）]
    # }
    def battle_log_delay(self, line: str) -> int:
        return self.battle_session.log_delay(line)

    # {
    #   責務: [update_battle_playback: 戦闘・playbackを更新する]
    #   処理: [1: 戦闘・playbackを更新する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     now: 現在時刻（int | None）
    #   ]
    #   戻り値: [result: 戦闘・playbackを更新するための結果（bool）]
    # }
    def update_battle_playback(self, now: int | None = None) -> bool:
        now = pygame.time.get_ticks() if now is None else int(now)
        result = self.battle_session.update_playback(now)
        if result["completed"]:
            self.finalize_battle_if_needed()
        return result["changed"]

    # {
    #   責務: [selected_battle_command: kadoka・questの選択中・戦闘・コマンドを求める]
    #   処理: [1: kadoka・questの選択中・戦闘・コマンドを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: kadoka・questの選択中・戦闘・コマンドを求めるための結果（str）]
    # }
    def selected_battle_command(self) -> str:
        return self.battle_session.selected_command()

    # {
    #   責務: [toggle_auto_battle: 自動・戦闘を切り替える]
    #   処理: [1: 自動・戦闘を切り替える]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def toggle_auto_battle(self) -> None:
        enabled = self.battle_session.toggle_auto(pygame.time.get_ticks())
        if enabled is None:
            return
        self.status = "オート戦闘を開始しました。" if enabled else "オート戦闘を停止しました。"

    # {
    #   責務: [update_auto_battle: 自動・戦闘を更新する]
    #   処理: [1: 自動・戦闘を更新する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     now: 現在時刻（int | None）
    #   ]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def update_auto_battle(self, now: int | None = None) -> None:
        now = pygame.time.get_ticks() if now is None else int(now)
        if not self.battle_session.auto_command_due(now, battle_mode=self.mode == "battle"):
            return
        self.handle_battle_command("fight")
        if self.battle and self.battle.outcome:
            self.battle_session.stop_auto()

    # {
    #   責務: [finalize_battle_if_needed: kadoka・questのfinalize・戦闘・if・neededを求める]
    #   処理: [1: kadoka・questのfinalize・戦闘・if・neededを求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def finalize_battle_if_needed(self) -> None:
        if not self.battle_session.mark_finalized():
            return
        assert self.battle is not None
        self.battle.mark_battle_complete()
        if self.battle.learning_enabled:
            self.monsters.save_all_ai(member.record for member in self.battle.allies)
            if self.battle.outcome == "victory":
                self.award_experience()

    # {
    #   責務: [award_experience: kadoka・questのaward・経験値を求める]
    #   処理: [1: kadoka・questのaward・経験値を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def award_experience(self) -> None:
        if not self.battle or self.battle.outcome != "victory" or not self.battle.learning_enabled:
            return
        gained = battle_experience(self.battle.enemies)
        if gained <= 0:
            return
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

    # {
    #   責務: [return_to_field: to・フィールドを返す]
    #   処理: [1: to・フィールドを返す]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
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

    # {
    #   責務: [revive_at_church: kadoka・questの復活・at・教会を求める]
    #   処理: [1: kadoka・questの復活・at・教会を求める]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def revive_at_church(self) -> None:
        revive = self.field_progress.revive_point(self.state)
        self.change_map(str(revive["map_id"]), int(revive["x"]), int(revive["y"]), f"全滅しました。{revive.get('name', '教会')}から復活しました。")

    # {
    #   責務: [scan_acquire: acquireを再走査する]
    #   処理: [1: acquireを再走査する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def scan_acquire(self) -> None:
        self.status = self.monster_import_service.scan_acquire()

    # {
    #   責務: [open_manager: managerを開く]
    #   処理: [1: managerを開く]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def open_manager(self) -> None:
        if self.manager_tool.open() == "already_running":
            self.status = "牧場台帳は既に開いています。"
            return
        self.status = "牧場台帳を開きました。個体管理とパーティ編成ができます。"

    # {
    #   責務: [refresh_manager_if_closed: manager・if・closedを更新内容を読み直す]
    #   処理: [1: manager・if・closedを更新内容を読み直す]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def refresh_manager_if_closed(self) -> None:
        if not self.manager_tool.consume_closed():
            return
        self.state = self.states.load()
        self.status = "牧場台帳の変更をゲームへ反映しました。"

    # {
    #   責務: [save_preset: プリセットを保存する]
    #   処理: [1: プリセットを保存する]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def save_preset(self) -> None:
        self.status = self.field_party_service.save_preset(self.state)

    # {
    #   責務: [load_next_preset: next・プリセットを読み込む]
    #   処理: [1: next・プリセットを読み込む]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def load_next_preset(self) -> None:
        self.status = self.field_party_service.load_next_preset(self.state)

    # {
    #   責務: [cycle_tactic: tacticを順に切り替える]
    #   処理: [1: tacticを順に切り替える]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def cycle_tactic(self) -> None:
        message = self.field_party_service.cycle_tactic(self.party())
        if message is not None:
            self.status = message

    # {
    #   責務: [reset_selected_ai: 選択中・AIの初期状態へ戻す]
    #   処理: [1: 選択中・AIの初期状態へ戻す]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def reset_selected_ai(self) -> None:
        message = self.field_party_service.reset_selected_ai(self.party())
        if message is not None:
            self.status = message

    # {
    #   責務: [select_party: パーティを選択する]
    #   処理: [1: パーティを選択する]
    #   引数: [
    #     self: 処理対象インスタンス
    #     index: 位置番号（int）
    #   ]
    #   戻り値: [result: パーティを選択するための結果（bool）]
    # }
    def select_party(self, index: int) -> bool:
        return self.field_party_service.select(index)


# {
#   責務: [password_controls: ゲームの暗号・controlsを求める]
#   処理: [1: ゲームの暗号・controlsを求める]
#   引数: []
#   戻り値: [result: ゲームの暗号・controlsを求めるための結果（tuple[list[tuple[str, pygame.Rect]], pygame.Rect, pygame.Rect, pygame.Rect]）]
# }
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


# {
#   責務: [draw_password: 暗号を描画する]
#   処理: [1: 暗号を描画する]
#   引数: [
#     screen: 描画先（pygame.Surface）
#     session: セッション（PasswordSession）
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def draw_password(screen: pygame.Surface, session: PasswordSession) -> None:
    draw_text(screen, "水の湧き場", (455, 34), 36, (100, 210, 255), True)
    draw_text(screen, "7文字のあいことば", (457, 84), 21, MUTED, True)
    slot_x = 306
    for index in range(7):
        rect = pygame.Rect(slot_x + index * 74, 135, 62, 70)
        pygame.draw.rect(screen, PANEL_ALT, rect, border_radius=8)
        pygame.draw.rect(screen, ACCENT if index == len(session.input_text) and index < 7 else MUTED, rect, 2, border_radius=8)
        if index < len(session.input_text):
            draw_text(screen, session.input_text[index], (rect.x + 14, rect.y + 14), 31, TEXT, True)
    keys, erase, decide, cancel = password_controls()
    mouse = pygame.mouse.get_pos()
    for label, rect in keys:
        pygame.draw.rect(screen, (60, 102, 132) if rect.collidepoint(mouse) else PANEL_ALT, rect, border_radius=7)
        draw_text(screen, label, (rect.x + 26, rect.y + 11), 23, TEXT, True)
    for label, rect, color in (("けす", erase, WARN), ("決定", decide, GOOD), ("やめる", cancel, MUTED)):
        pygame.draw.rect(screen, color if rect.collidepoint(mouse) else PANEL_ALT, rect, border_radius=8)
        draw_text(screen, label, (rect.x + 29, rect.y + 13), 20, TEXT, True)
    if session.message:
        draw_text(screen, session.message, (390, 645), 18, WARN if "違" in session.message else MUTED, True)


# {
#   責務: [main: ゲームのエントリ処理を実行する]
#   処理: [1: ゲームのエントリ処理を実行する]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def main() -> None:
    screen = init_pygame("kadoka quest", SCREEN_SIZE)
    clock = pygame.time.Clock()
    game = KadokaQuest()
    battle_renderer = BattleRenderer(game.character_images)
    input_adapter = RuntimeInputAdapter(MOVE_KEY_DIRECTIONS)

    # {
    #   責務: [dispatch: ゲームを配送する]
    #   処理: [1: ゲームを配送する]
    #   引数: [
    #     target: 対象（str）
    #     action: action（str）
    #     payload: 要求データ
    #   ]
    #   戻り値: [result: ゲームを配送するための結果（object）]
    # }
    def dispatch(target: str, action: str, **payload) -> object:
        return game.runtime.dispatch(target, action, **payload)

    running = True
    smoke = smoke_frames()
    frames = 0
    battle_buttons = [
        Button(pygame.Rect(355, 650, 95, 48), "戦う", lambda: None),
        Button(pygame.Rect(460, 650, 95, 48), "スカウト", lambda: None),
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
            battle = game.battle_session.battle
            battle_finished = bool(battle and battle.outcome)
            for request in input_adapter.translate(
                event,
                game.mode,
                pygame.time.get_ticks(),
                battle_finished=battle_finished,
                battle_playback=game.battle_session.playback,
            ):
                if request["kind"] == "quit":
                    running = False
                else:
                    dispatch(str(request["target"]), str(request["action"]), **dict(request["payload"]))
            battle = game.battle_session.battle
            battle_enabled = bool(battle and not battle.outcome and not game.battle_session.playback)
            for request in mouse_adapter.translate(event, game.mode, battle_enabled=battle_enabled):
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
            draw_field(screen, game.field_session, game.character_images, game.party(), game.field_party_session.selected_index, now)
        elif game.mode == "battle":
            battle_renderer.draw(screen, game.battle_session, battle_buttons)
        else:
            draw_password(screen, game.password_session)
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
