# REPO_MAP (generated)

Do not edit. Regenerate: `python tools/code-docs/script/generate_repo_map.py`.
Read the matching CODEMAP row first, then search this index for its file/class.
Paths are relative to the source directory (default: src/).
Public top-level classes/functions and direct public methods, including __init__, only.
Defaults are abbreviated as ...; source files remain authoritative.
Bodies, docstrings, private helpers, nested definitions and call graphs are omitted.

## kadoka_engine/chase_traffic.py

```text
class ChaseTraffic
  __init__(self, field: FieldEngine) -> None
  clear(self) -> None
  begin(self, now: int, owners: set[int]) -> None
  release(self, owner: int) -> None
  record(self, owner: int, position: tuple[int, int]) -> None
  plan(self, owner: int, start: tuple[int, int], target: tuple[int, int], occupied: set[tuple[int, int]], fixed: set[tuple[int, int]], interval: int) -> tuple[int, int]
```

## kadoka_engine/data_validator.py

```text
class DataValidator
  __init__(self, data_root: Path) -> None
  validate(self) -> list[dict[str, str]]
```

## kadoka_engine/field_ai.py

```text
is_valid_field_ai_weights(source: object) -> bool
choose_field_ai(rng: random.Random, *sources: object) -> str
```

## kadoka_engine/field_engine.py

```text
class FieldEngine
  __init__(self, map_data: dict, blocks: dict[str, dict]) -> None
  set_world(self, map_data: dict, blocks: dict[str, dict]) -> None
  direction_for_step(dx: int, dy: int, current: str=...) -> str
  resolve_player_move(self, x: int, y: int, dx: int, dy: int, direction: str, visible_characters: list[dict], hidden_characters: list[dict]) -> dict
  front_position(self, x: int, y: int, direction: str) -> tuple[int, int]
  step_transition_at(self, x: int, y: int) -> dict | None
  nearby_event(self, x: int, y: int) -> dict | None
  tile_allows(self, x: int, y: int, rule: str) -> bool
  has_clear_axis_path(self, start: tuple[int, int], target: tuple[int, int], rule: str) -> bool
```

## kadoka_engine/fixed_mob_controller.py

```text
class FixedMobController
  __init__(self, field: FieldEngine, rng: random.Random, movement_duration_ms: int=...) -> None
  reset(self, map_data: dict, blocks: dict[str, dict], despawned: set[str], player_position: tuple[int, int], now: int, species_name: Callable[[str], str]) -> None
  find_at(self, x: int, y: int) -> dict | None
  nearby(self, front_position: tuple[int, int]) -> dict | None
  next_dialogue(self, npc: dict) -> str
  remove(self, npc: dict) -> bool
  front_position(npc: dict) -> tuple[int, int]
  faces_player(self, npc: dict, player_position: tuple[int, int]) -> bool
  move(self, npc: dict, player_position: tuple[int, int], now: int) -> bool
  move_all(self, player_position: tuple[int, int], now: int) -> bool
  update(self, player_position: tuple[int, int], now: int) -> bool
```

## kadoka_engine/grid_movement.py

```text
class GridMovement
  __init__(self, x: float, y: float, duration_ms: int=...) -> None
  snap(self, x: float, y: float) -> None
  move_to(self, x: float, y: float, now_ms: int) -> None
  position(self, now_ms: int) -> tuple[float, float]
```

## kadoka_engine/hidden_enemy_controller.py

```text
class HiddenEnemyController
  __init__(self, field: FieldEngine, rng: random.Random, chase_interval_ms: int=..., wander_interval_ms: int=..., vision_range: int=...) -> None
  set_world(self, map_data: dict, blocks: dict[str, dict]) -> None
  spawn_options(self, flags: dict) -> list[dict]
  reset(self, player_position: tuple[int, int], flags: dict, now: int, species_ai_weights: dict | None=...) -> None
  find_at(self, position: tuple[int, int]) -> dict | None
  remove(self, monster: dict) -> bool
  sees_player(self, monster: dict, player_position: tuple[int, int]) -> bool
  move(self, monster: dict, player_position: tuple[int, int], visible_positions: set[tuple[int, int]], traffic: ChaseTraffic | None=...) -> bool
  move_all(self, player_position: tuple[int, int], visible_positions: set[tuple[int, int]]) -> bool
  update(self, player_position: tuple[int, int], visible_positions: set[tuple[int, int]], now: int) -> bool
```

## kadoka_engine/player_field_controller.py

```text
class PlayerFieldController
  __init__(self, x: int, y: int, movement_duration_ms: int=..., repeat_delay_ms: int=..., repeat_interval_ms: int=...) -> None
  snap(self, x: int, y: int) -> None
  attempt_move(self, field: FieldEngine, dx: int, dy: int, visible_characters: list[dict], hidden_characters: list[dict], now: int) -> dict
  begin_hold(self, direction: str, now: int) -> tuple[int, int] | None
  stop_hold(self, direction: str) -> bool
  clear_hold(self) -> None
  repeated_vector(self, now: int) -> tuple[int, int] | None
```

## kadoka_engine/spawn_controls.py

```text
parse_map_spawn_controls(rate: str, weights: dict[str, str] | None) -> dict
map_ai_ratios(weights: dict) -> list[float] | None
prepare_spawn_document(document: dict, species_ids: set[str], entry_draft: dict | None=..., controls_draft: dict | None=...) -> dict
```

## kadoka_engine/spawn_settings.py

```text
validate_map_spawns(map_data: dict, species_ids: set[str] | None=...) -> list[dict[str, str]]
normalize_map_spawns(map_data: dict, species_ids: set[str] | None=...) -> dict
```

## kadoka_engine/spawn_table.py

```text
prepare_spawn_entry(spawns: list[dict], index: int, species_id: str, weight_text: str, minimum_text: str, maximum_text: str, species_ids: set[str]) -> dict
spawn_weight_ratios(spawns: list[dict]) -> list[float] | None
```

## kadoka_engine/wild_spawn.py

```text
relative_spawn_weights(options: list[dict]) -> list[float] | None
pop_allowed(rng: random.Random, rate: object) -> bool
draw_wild_spawn(rng: random.Random, options: list[dict], weights: list[float] | None, rate: object=...) -> dict | None
```

## kadoka_quest/application/app_command.py

```text
is_plain_data(value: Any) -> bool
class AppCommand
```

## kadoka_quest/application/command_bus.py

```text
class CommandBus
  __init__(self) -> None
  register(self, target: str, handler: Callable[[AppCommand], Any]) -> None
  dispatch(self, command: AppCommand) -> Any
```

## kadoka_quest/application/runtime_orchestrator.py

```text
class RuntimeOrchestrator
  __init__(self, session: Any) -> None
  transition_to(self, mode: str) -> str
  dispatch(self, target: str, action: str, **payload: Any) -> Any
  apply_field_effect(self, effect: dict) -> Any
```

## kadoka_quest/apps/ai_inspector.py

```text
class AiInspector
  summarize(ai: dict[str, Any], limit: int=...) -> dict[str, Any]
```

## kadoka_quest/apps/battle_command_app.py

```text
class BattleCommandApplication
  __init__(self, session: Any) -> None
  handle(self, command: AppCommand) -> Any
```

## kadoka_quest/apps/battle_flow_dependencies.py

```text
class BattleFlowDependencies
```

## kadoka_quest/apps/battle_flow_service.py

```text
class BattleFlowService
  __init__(self, dependencies: BattleFlowDependencies) -> None
  session(self)
  execute(self, command: str, now: int) -> None
  update_playback(self, now: int) -> bool
  selected_command(self) -> str
  move_selection(self, amount: int) -> int
  set_selection(self, index: int) -> int
  stop_auto(self) -> None
  toggle_auto(self, now: int) -> str | None
  update_auto(self, now: int, *, battle_mode: bool) -> None
```

## kadoka_quest/apps/battle_progression_service.py

```text
class BattleProgressionService
  __init__(self, dependencies: BattleFlowDependencies) -> None
  scout(self) -> None
  use_item(self) -> None
  finalize_if_needed(self) -> None
  award_experience(self) -> None
```

## kadoka_quest/apps/battle_session.py

```text
class BattleSession
  __init__(self, initial_log_delay_ms: int=..., action_log_delay_ms: int=..., short_log_delay_ms: int=..., next_round_delay_ms: int=...) -> None
  begin(self, battle: Any, now: int, *, simulation: bool=..., fixed_mob_id: str | None=...) -> None
  clear(self) -> dict[str, Any]
  reset_presentation(self) -> None
  start_playback(self, log_start: int, now: int) -> bool
  log_delay(self, line: str) -> int
  update_playback(self, now: int) -> dict[str, bool]
  move_selection(self, amount: int) -> int
  set_selection(self, index: int) -> int
  selected_command(self) -> str
  toggle_auto(self, now: int) -> bool | None
  stop_auto(self) -> None
  auto_command_due(self, now: int, *, battle_mode: bool) -> bool
  mark_finalized(self) -> bool
```

## kadoka_quest/apps/block_editor.py

```text
class BlockEditor
  __init__(self) -> None
  refresh(self) -> None
  load(self, block: dict) -> None
  new(self) -> None
  payload(self) -> dict
  save(self) -> None
  open_visual_editor(self) -> None
  save_visual(self) -> None
  set_canvas_size(self, size: int) -> None
  add_palette_color(self) -> None
  remove_palette_color(self) -> None
  import_visual_image(self) -> None
  merge_visual_colors(self) -> None
  reduce_visual_palette(self, max_colors: int) -> None
  scroll_list(self, amount: int) -> None
draw_visual_editor(screen: pygame.Surface, editor: BlockEditor) -> None
main() -> None
```

## kadoka_quest/apps/data_creator.py

```text
class DataCreatorApp
  __init__(self, repository: GameRepository | None=..., creator: DeveloperMonsterCreator | None=...) -> None
  fields(self) -> list[TextField]
  selected_species_id(self) -> str
  selected_target(self) -> str
  select_species(self, index: int) -> None
  cycle_target(self) -> None
  preview(self) -> dict | None
  create_monster(self) -> bool
main() -> None
```

## kadoka_quest/apps/data_validator.py

```text
main() -> None
```

## kadoka_quest/apps/developer_launcher.py

```text
main() -> None
```

## kadoka_quest/apps/field_command_app.py

```text
class FieldCommandApplication
  __init__(self, session: Any) -> None
  handle(self, command: AppCommand) -> Any
```

## kadoka_quest/apps/field_event_app.py

```text
class FieldEventApplication
  __init__(self) -> None
  resolve_step(self, event: dict | None) -> dict
  resolve_interaction(self, npc: dict | None, event: dict | None, player_direction: str, dialogue: str | None=...) -> dict
  resolve_use(self, events: list[dict], player_position: tuple[int, int], requirement_kind: str, requirement_id: str) -> dict
```

## kadoka_quest/apps/field_party_service.py

```text
class FieldPartyService
  __init__(self, session: FieldPartySession, parties: PartyStore, monsters: MonsterStore, states: StateStore, now: Callable[[], datetime] | None=...) -> None
  select(self, index: int) -> bool
  save_preset(self, state: dict) -> str
  load_next_preset(self, state: dict) -> str
  cycle_tactic(self, party: Sequence[MonsterRecord]) -> str | None
  reset_selected_ai(self, party: Sequence[MonsterRecord]) -> str | None
```

## kadoka_quest/apps/field_party_session.py

```text
class FieldPartySession
  __init__(self, party_slot_count: int=...) -> None
  select(self, index: int) -> int
  selected(self, party: Sequence[T]) -> T | None
  next_preset(self, presets: Sequence[T]) -> T | None
```

## kadoka_quest/apps/field_session.py

```text
class FieldSession
  replace_field(self, field: FieldEngine) -> None
  map_data(self) -> dict
  blocks(self) -> dict[str, dict]
  set_world(self, map_data: dict, blocks: dict[str, dict]) -> None
  enter_map(self, map_data: dict, x: int, y: int) -> None
```

## kadoka_quest/apps/game.py

```text
class KadokaQuest
  __init__(self, repository: GameRepository | None=..., monsters: MonsterStore | None=..., states: StateStore | None=..., parties: PartyStore | None=..., rng: random.Random | None=...) -> None
  state(self) -> dict
  state(self, value: dict) -> None
  map_data(self) -> dict
  map_data(self, value: dict) -> None
  blocks(self) -> dict[str, dict]
  blocks(self, value: dict[str, dict]) -> None
  field(self) -> FieldEngine
  field(self, value: FieldEngine) -> None
  player_field(self) -> PlayerFieldController
  player_field(self, value: PlayerFieldController) -> None
  fixed_mobs(self) -> FixedMobController
  fixed_mobs(self, value: FixedMobController) -> None
  hidden_enemies(self) -> HiddenEnemyController
  hidden_enemies(self, value: HiddenEnemyController) -> None
  home_npcs(self) -> list[dict]
  home_npcs(self, value: list[dict]) -> None
  hidden_monsters(self) -> list[dict]
  hidden_monsters(self, value: list[dict]) -> None
  player_x(self) -> int
  player_x(self, value: int) -> None
  player_y(self) -> int
  player_y(self, value: int) -> None
  player_direction(self) -> str
  player_direction(self, value: str) -> None
  player_movement(self) -> GridMovement
  held_move_direction(self) -> str | None
  held_move_direction(self, value: str | None) -> None
  next_move_tick(self) -> int
  next_move_tick(self, value: int) -> None
  mode(self) -> str
  mode(self, value: str) -> None
  battle(self) -> BattleEngine | None
  battle(self, value: BattleEngine | None) -> None
  battle_selection(self) -> int
  battle_selection(self, value: int) -> None
  last_auto_tick(self) -> int
  last_auto_tick(self, value: int) -> None
  battle_playback(self) -> bool
  battle_playback(self, value: bool) -> None
  battle_visible_log_count(self) -> int
  battle_visible_log_count(self, value: int) -> None
  battle_next_log_tick(self) -> int
  battle_next_log_tick(self, value: int) -> None
  battle_focus_id(self) -> str | None
  battle_focus_id(self, value: str | None) -> None
  simulation(self) -> bool
  simulation(self, value: bool) -> None
  password_input(self) -> str
  password_input(self, value: str) -> None
  party(self) -> list[MonsterRecord]
  save_position(self) -> None
  change_map(self, map_id: str, x: int, y: int, message: str | None=...) -> None
  move(self, dx: int, dy: int, now: int | None=...) -> None
  character_at(self, x: int, y: int, *, include_hidden: bool=..., include_home: bool=...) -> dict | None
  player_front_position(self) -> tuple[int, int]
  start_held_move(self, key: int, now: int) -> bool
  start_held_direction(self, direction: str, now: int) -> bool
  stop_held_move(self, key: int) -> None
  stop_held_direction(self, direction: str) -> None
  update_held_move(self, now: int) -> bool
  handle_step_event(self) -> bool
  nearby_event(self) -> dict | None
  interact(self) -> None
  use_field_requirement(self, requirement_kind: str, requirement_id: str) -> None
  reacquire_ghosts(self) -> None
  open_password_input(self) -> None
  append_password(self, character: str) -> None
  backspace_password(self) -> None
  submit_password(self) -> bool
  cancel_password(self) -> None
  reset_home_npcs(self, now: int | None=...) -> None
  nearby_home_npc(self) -> dict | None
  next_npc_dialogue(self, npc: dict) -> str
  despawn_fixed_mob(self, npc: dict) -> None
  despawn_fixed_mob_by_id(self, npc_id: str) -> bool
  register_church(self, revive: dict) -> None
  gain_field_item(self, item_id: str) -> int
  npc_front_position(npc: dict) -> tuple[int, int]
  npc_faces_player(self, npc: dict) -> bool
  move_home_npcs(self) -> None
  move_home_npc(self, npc: dict, now: int | None=...) -> bool
  character_image(self, species_id: str, kind: str, size: tuple[int, int]) -> pygame.Surface | None
  field_pickup(self) -> None
  spawn_options(self) -> list[dict]
  reset_hidden_monsters(self, now: int | None=...) -> None
  move_hidden_monsters(self) -> None
  monster_sees_player(self, monster: dict) -> bool
  move_hidden_monster(self, monster: dict) -> bool
  update_field_mobs(self, now: int) -> bool
  check_hidden_collision(self) -> bool
  make_wild(self, spawn: dict) -> MonsterRecord
  start_wild_battle(self, spawn: dict | None=..., hidden_monster: dict | None=..., *, fixed_mob_id: str | None=...) -> bool
  start_simulation(self) -> None
  handle_battle_command(self, command: str) -> None
  reset_battle_presentation(self) -> None
  start_battle_playback(self, log_start: int) -> None
  battle_log_delay(self, line: str) -> int
  update_battle_playback(self, now: int | None=...) -> bool
  selected_battle_command(self) -> str
  toggle_auto_battle(self) -> None
  update_auto_battle(self, now: int | None=...) -> None
  finalize_battle_if_needed(self) -> None
  award_experience(self) -> None
  return_to_field(self) -> None
  revive_at_church(self) -> None
  scan_acquire(self) -> None
  open_manager(self) -> None
  refresh_manager_if_closed(self) -> None
  save_preset(self) -> None
  load_next_preset(self) -> None
  cycle_tactic(self) -> None
  reset_selected_ai(self) -> None
  select_party(self, index: int) -> bool
password_controls() -> tuple[list[tuple[str, pygame.Rect]], pygame.Rect, pygame.Rect, pygame.Rect]
draw_password(screen: pygame.Surface, session: PasswordSession) -> None
main() -> None
```

## kadoka_quest/apps/launcher.py

```text
main() -> None
```

## kadoka_quest/apps/legacy_battle_command_adapter.py

```text
class LegacyBattleCommandAdapter
  __init__(self, session: Any) -> None
  handle(self, command: AppCommand) -> Any
```

## kadoka_quest/apps/manage.py

```text
class Manager
  __init__(self) -> None
  refresh(self) -> None
  selected_record(self)
  create(self) -> None
  add_party(self) -> None
  remove_party(self) -> None
  reset_ai(self) -> None
  cycle_tactic(self) -> None
  save_preset(self) -> None
  update_preset(self) -> None
  load_preset(self) -> None
  acquire(self) -> None
  simulation(self) -> None
main() -> None
```

## kadoka_quest/apps/manager_command_app.py

```text
class ManagerCommandApplication
  __init__(self, session: Any) -> None
  handle(self, command: AppCommand) -> Any
```

## kadoka_quest/apps/manager_process_service.py

```text
class ManagerProcessService
  __init__(self, script_path: Path, *, python_executable: str | None=..., launcher: Callable[..., Any]=..., frozen: bool | None=..., frozen_argument: str=...) -> None
  open(self) -> str
  is_running(self) -> bool
  consume_closed(self) -> bool
```

## kadoka_quest/apps/map_editor.py

```text
hex_color(value: str) -> tuple[int, int, int]
class MapEditor
  __init__(self, repository: GameRepository | None=..., preset_store: MapPresetStore | None=...) -> None
  save(self) -> None
  preset_fields(self) -> list[TextField]
  refresh_preset_catalog(self) -> None
  open_preset_dialog(self) -> None
  select_preset(self, index: int) -> None
  save_current_as_preset(self) -> bool
  apply_selected_preset(self) -> bool
  create_map_from_selected_preset(self) -> bool
  fixed_mobs(self) -> list[dict]
  current_fixed_mob(self) -> dict | None
  fixed_mob_fields(self) -> list[TextField]
  open_fixed_mob_dialog(self) -> None
  select_fixed_mob(self, index: int) -> None
  select_fixed_mob_brush(self) -> None
  begin_fixed_mob_placement(self) -> None
  add_fixed_mob_at(self, x: int, y: int, *, open_editor: bool=...) -> bool
  cycle_fixed_mob_ai(self) -> None
  cycle_fixed_mob_interaction(self) -> None
  toggle_fixed_mob_option(self, key: str) -> None
  apply_fixed_mob(self) -> bool
  delete_fixed_mob(self) -> None
  selected_species_id(self) -> str
  current_spawn(self) -> dict | None
  spawn_fields(self) -> list[TextField]
  select_species(self, index: int) -> None
  select_spawn(self, index: int) -> None
  new_spawn(self) -> None
  load_spawn_fields(self) -> None
  spawn_draft_changed(self) -> bool
  open_spawn_dialog(self) -> None
  apply_map_spawn_settings(self) -> bool
  add_spawn(self) -> bool
  apply_spawn_range(self) -> bool
  remove_spawn(self) -> None
  move_camera(self, dx: int, dy: int) -> None
  select_map(self, index: int) -> bool
  new_map_fields(self) -> list[TextField]
  open_new_map_dialog(self) -> None
  create_new_map(self) -> bool
  grid_position(self, position: tuple[int, int]) -> tuple[int, int] | None
  paint(self, position: tuple[int, int]) -> bool
  pick_block(self, position: tuple[int, int]) -> bool
  transitions(self) -> list[dict]
  use_events(self) -> list[dict]
  current_use_event(self) -> dict | None
  use_event_fields(self) -> list[TextField]
  open_use_event_dialog(self) -> None
  select_use_event(self, index: int) -> None
  select_use_event_brush(self) -> None
  add_use_event_at(self, x: int, y: int, *, open_editor: bool=...) -> bool
  apply_use_event(self) -> bool
  delete_use_event(self) -> None
  current_transition(self) -> dict | None
  transition_fields(self) -> list[TextField]
  open_transition_dialog(self) -> None
  select_transition(self, index: int) -> None
  begin_transition_placement(self) -> None
  select_block_brush(self, block_id: str) -> None
  select_transition_brush(self, activation: str) -> None
  add_transition_at(self, x: int, y: int, activation: str | None=..., *, open_editor: bool=...) -> bool
  set_transition_activation(self, activation: str) -> None
  set_transition_target(self, map_id: str) -> None
  apply_transition(self) -> bool
  delete_transition(self) -> None
main() -> None
```

## kadoka_quest/apps/monster_editor.py

```text
class MonsterEditor
  __init__(self, repository: GameRepository | None=..., asset_root: Path=...) -> None
  species_id(self) -> str
  creating_new(self) -> bool
  load_selected(self) -> None
  load_new_draft(self) -> None
  store_level_fields(self) -> None
  load_level_fields(self) -> None
  change_level(self, amount: int) -> None
  cycle_ai(self) -> None
  cycle_skill(self, amount: int) -> None
  select_available_skill(self, index: int) -> None
  remove_skill(self) -> None
  select_species(self, index: int) -> None
  scroll_list(self, amount: int) -> None
  add_skill(self) -> None
  save(self) -> None
  save_visuals(self) -> None
  add_palette_color(self) -> None
  remove_palette_color(self) -> None
  import_visual_image(self) -> None
  merge_visual_colors(self) -> None
  reduce_visual_palette(self, max_colors: int) -> None
draw_checker(screen: pygame.Surface, rect: pygame.Rect, cell: int=...) -> None
draw_visual_editor(screen: pygame.Surface, editor: MonsterEditor) -> None
draw_skill_editor(screen: pygame.Surface, editor: MonsterEditor, available_scroll: ScrollBar, learned_scroll: ScrollBar) -> None
main() -> None
```

## kadoka_quest/apps/monster_import_service.py

```text
class MonsterImportService
  __init__(self, monsters: MonsterStore, repository: GameRepository, import_root: Path, battle_factory: Callable[..., BattleEngine]=...) -> None
  scan_acquire(self) -> str
  create_simulation(self, allies: Sequence[MonsterRecord], rng: random.Random) -> tuple[BattleEngine | None, str]
```

## kadoka_quest/apps/password_command_app.py

```text
class PasswordCommandApplication
  __init__(self, session: Any) -> None
  handle(self, command: AppCommand) -> Any
```

## kadoka_quest/apps/password_session.py

```text
class PasswordSession
  __init__(self, secret: str, allowed_characters: Iterable[str], *, prompt: str=..., failure_message: str=...) -> None
  open(self) -> None
  append(self, character: str) -> bool
  backspace(self) -> bool
  submit(self) -> bool
  cancel(self) -> None
```

## kadoka_quest/apps/progress_session.py

```text
class ProgressSession
```

## kadoka_quest/apps/ranch_manager.py

```text
class RanchManager
  __init__(self) -> None
  refresh(self) -> None
  selected_record(self)
  add_party(self) -> None
  remove_party(self) -> None
  reset_ai(self) -> None
  cycle_tactic(self) -> None
  save_preset(self) -> None
  update_preset(self) -> None
  load_preset(self) -> None
main() -> None
```

## kadoka_quest/apps/simulation_facility_hooks.py

```text
open_simulation_manager(session) -> None
refresh_simulation_if_closed(session) -> None
install_simulation_facility_hooks(game_class) -> None
```

## kadoka_quest/apps/simulation_facility_service.py

```text
class SimulationFacilityService
  __init__(self, repository: GameRepository, simulation_root: Path, battle_factory: Callable[..., BattleEngine]=...) -> None
  list_individuals(self) -> list[MonsterRecord]
  create_individual(self, species_id: str, level: int=..., name: str | None=...) -> MonsterRecord
  delete_individual(self, monster_id: str) -> bool
  opponent_ids(self) -> list[str]
  set_opponents(self, monster_ids: Sequence[str]) -> list[MonsterRecord]
  clear_opponents(self) -> None
  opponents(self) -> list[MonsterRecord]
  create_battle(self, allies: Sequence[MonsterRecord], rng: random.Random) -> tuple[BattleEngine | None, str]
```

## kadoka_quest/apps/simulation_manager.py

```text
class SimulationManager
  __init__(self) -> None
  refresh(self) -> None
  selected_record(self)
  selected_species_id(self) -> str
  cycle_species(self, amount: int) -> None
  change_level(self, amount: int) -> None
  create_opponent(self) -> None
  import_external(self) -> None
  delete_selected(self) -> None
  toggle_selected(self) -> None
  request_battle(self) -> bool
main() -> None
```

## kadoka_quest/apps/simulation_roster_service.py

```text
class SimulationRosterService
  __init__(self, root: Path, repository: GameRepository, import_root: Path) -> None
  list_records(self) -> list[MonsterRecord]
  create(self, species_id: str, *, level: int=..., name: str | None=..., monster_id: str | None=...) -> MonsterRecord
  delete(self, monster_id: str) -> None
  import_external(self) -> tuple[int, int]
  request_battle(self, monster_ids: Iterable[str]) -> None
  consume_battle_request(self) -> list[MonsterRecord]
```

## kadoka_quest/core/ai.py

```text
default_ai(profile: str=..., tactic: str=...) -> dict[str, Any]
choose_skill(ai: dict[str, Any], skills: Iterable[dict[str, Any]], hp_ratio: float, ally_missing_hp_ratio: float, mp_ratio: float, rng: random.Random, context_tags: Iterable[str]=...) -> dict[str, Any] | None
learn_from_action(ai: dict[str, Any], skill_id: str, reward: float, context_tags: Iterable[str]=...) -> None
```

## kadoka_quest/core/battle.py

```text
class BattleEngine
  __init__(self, repository: GameRepository, allies: list[MonsterRecord], enemies: list[MonsterRecord], rng: random.Random | None=..., learning_enabled: bool=..., data_loader: BattleDataLoader | None=..., inference: BattleInference | None=..., learning: BattleLearning | None=..., encounter_context: str | None=...) -> None
  run_round(self) -> list[str]
  try_scout(self, multiplier: float=..., fixed_bonus: float=...) -> tuple[bool, MonsterRecord | None, float]
  use_party_item(self) -> None
  try_run(self) -> bool
  mark_battle_complete(self) -> None
```

## kadoka_quest/core/battle_context.py

```text
describe_battle_context(hp_ratio: float, ally_missing_hp_ratio: float, mp_ratio: float, living_allies: int, living_enemies: int, lowest_enemy_hp_ratio: float, actor_level: int, highest_enemy_level: int) -> tuple[str, ...]
```

## kadoka_quest/core/battle_decision_explanation.py

```text
class BattleDecisionExplanation
  describe(ai: dict[str, Any], skill: dict[str, Any], context_tags: Iterable[str]) -> str
```

## kadoka_quest/core/battle_inference.py

```text
class BattleInference
  choose(self, ai: dict[str, Any], skills: Iterable[dict[str, Any]], hp_ratio: float, ally_missing_hp_ratio: float, mp_ratio: float, rng: random.Random, context_tags: Iterable[str]=...) -> dict[str, Any] | None
```

## kadoka_quest/core/battle_learning.py

```text
class BattleLearning
  learn(self, ai: dict[str, Any], skill_id: str, reward: float, context_tags: Iterable[str]=...) -> None
```

## kadoka_quest/core/battle_rewards.py

```text
custom_defeat_experience(level: int, rule: Any) -> int | None
battle_experience(enemies: Iterable[Combatant]) -> int
```

## kadoka_quest/core/combatant.py

```text
class Combatant
  alive(self) -> bool
  name(self) -> str
  speed(self) -> int
  defense(self) -> int
```

## kadoka_quest/core/monster.py

```text
class MonsterRecord
  monster_id(self) -> str
  species_id(self) -> str
  name(self) -> str
  level(self) -> int
  plus_choices(self) -> list[str]
  equipment_id(self) -> str | None
equipment_allows_species(equipment: dict[str, Any], species_id: str) -> bool
calculate_stats(repository: GameRepository, record: MonsterRecord) -> dict[str, int]
available_skill_ids(repository: GameRepository, record: MonsterRecord) -> list[str]
```

## kadoka_quest/core/spawn_levels.py

```text
metal_area_level_range(party: Sequence[MonsterRecord]) -> tuple[int, int]
spawn_level_range(spawn: dict[str, Any], party: Sequence[MonsterRecord], encounter_context: str=...) -> tuple[int, int]
wild_encounter_level(spawn: dict[str, Any], party: Sequence[MonsterRecord], encounter_context: str, rng: random.Random) -> int
```

## kadoka_quest/core/status_effects.py

```text
status_effect_id(effect: dict[str, Any] | str) -> str
has_status(effects: Iterable[dict[str, Any] | str], status_id: str) -> bool
status_apply_chance(base_chance: float, resistance_level: str) -> float
status_stat_multiplier(effects: Iterable[dict[str, Any] | str], stat: str) -> float
end_turn_status_damage(effect: dict[str, Any] | str, max_hp: int) -> int
```

## kadoka_quest/data/battle_data.py

```text
class BattleDataLoader
  __init__(self, repository: GameRepository) -> None
  species_definition(self, species_id: str) -> dict[str, Any]
  build_combatant(self, record: MonsterRecord) -> Combatant
```

## kadoka_quest/data/data_validator.py

```text
class DataValidator(EngineDataValidator)
  __init__(self, data_root: Path | None=...) -> None
```

## kadoka_quest/data/developer_monster_creator.py

```text
class DeveloperMonsterCreator
  __init__(self, repository: GameRepository | None=..., output_roots: dict[str, Path] | None=...) -> None
  preview(self, species_id: str, level: int) -> dict[str, Any]
  create(self, species_id: str, level: int, name: str, target: str, monster_id: str | None=...) -> tuple[MonsterRecord, Path]
```

## kadoka_quest/data/field_data.py

```text
class FieldDataLoader
  __init__(self, repository: GameRepository) -> None
  blocks(self) -> dict[str, dict]
  species_ai_weights(self, map_data: dict) -> dict
  load_map(self, map_id: str, x: int | None=..., y: int | None=...) -> dict
```

## kadoka_quest/data/field_progress.py

```text
class FieldProgressStore
  __init__(self, states: StateStore) -> None
  save_position(self, state: dict, map_id: str, x: int, y: int) -> None
  register_church(self, state: dict, revive: dict) -> None
  add_item(self, state: dict, item_id: str, amount: int=...) -> int
  set_flag(self, state: dict, flag_id: str, value: bool) -> None
  mark_despawned(self, state: dict, key: str) -> bool
  revive_point(state: dict) -> dict
```

## kadoka_quest/data/jsonio.py

```text
read_json(path: Path) -> dict[str, Any]
write_json(path: Path, value: dict[str, Any]) -> None
```

## kadoka_quest/data/map_presets.py

```text
class MapPresetStore
  __init__(self, data_root: Path | None=...) -> None
  list_ids(self) -> list[str]
  get(self, preset_id: str) -> dict[str, Any]
  save_from_map(self, preset_id: str, display_name: str, map_data: dict[str, Any], *, overwrite: bool=...) -> dict[str, Any]
  apply_to_map(self, preset_id: str, target_map: dict[str, Any]) -> dict[str, Any]
  build_map(self, preset_id: str, map_id: str, display_name: str) -> dict[str, Any]
```

## kadoka_quest/data/monsters.py

```text
class MonsterStore
  __init__(self, root: Path | None=..., repository: GameRepository | None=...) -> None
  list_records(self) -> list[MonsterRecord]
  get(self, monster_id: str) -> MonsterRecord | None
  create(self, species_id: str, name: str | None=..., level: int=..., source: str=..., monster_id: str | None=...) -> MonsterRecord
  save(self, record: MonsterRecord) -> None
  save_ai(self, monster_id: str, ai: dict) -> None
  reset_ai(self, monster_id: str) -> MonsterRecord
  set_tactic(self, monster_id: str, tactic: str) -> None
  discover_external(root: Path) -> list[MonsterRecord]
  acquire_from_scan(self, source_root: Path) -> tuple[int, int]
  ensure_species(self, species_id: str, name: str | None=...) -> MonsterRecord
  delete(self, monster_id: str) -> None
  save_all_ai(self, records: Iterable[MonsterRecord]) -> None
```

## kadoka_quest/data/parties.py

```text
class PartyStore
  __init__(self, root: Path | None=...) -> None
  save(self, name: str, member_ids: list[str | None], overwrite: bool=...) -> Path
  list_presets(self) -> list[Path]
  update(self, path: Path, name: str, member_ids: list[str | None]) -> None
  load(self, path: Path, monsters: MonsterStore) -> list[MonsterRecord | None]
```

## kadoka_quest/data/repository.py

```text
class SpeciesBundle
  species_id(self) -> str
class GameRepository
  __init__(self, data_root: Path | None=...) -> None
  list_blocks(self) -> list[dict[str, Any]]
  get_block(self, block_id: str) -> dict[str, Any]
  save_block(self, block: dict[str, Any]) -> None
  list_maps(self) -> list[str]
  get_map(self, map_id: str) -> dict[str, Any]
  save_map(self, map_data: dict[str, Any]) -> None
  create_map(self, map_id: str, display_name: str, width: int, height: int, fill_block_id: str) -> dict[str, Any]
  create_map_from_document(self, map_data: dict[str, Any]) -> dict[str, Any]
  list_species_ids(self) -> list[str]
  get_species(self, species_id: str) -> SpeciesBundle
  save_species_definition(self, definition: dict[str, Any]) -> None
  save_species_stats(self, species_id: str, stats: dict[str, Any]) -> None
  save_species_skills(self, species_id: str, skills: dict[str, Any]) -> None
  save_species_plus(self, species_id: str, plus: dict[str, Any]) -> None
  stats_at(self, species_id: str, level: int) -> dict[str, int]
  skill_ids_at(self, species_id: str, level: int, plus_choices: list[str] | None=...) -> list[str]
  get_skills(self) -> dict[str, dict[str, Any]]
  get_equipment(self) -> dict[str, dict[str, Any]]
```

## kadoka_quest/data/savedata.py

```text
class SaveDataManager
  __init__(self, root: Path | None=...) -> None
  validate_name(self, name: str) -> str
  profile_root(self, name: str) -> Path
  list_names(self) -> list[str]
  active_name(self) -> str
  set_active(self, name: str) -> Path
  ensure_profile(self, name: str) -> Path
  create(self, name: str) -> Path
  copy_profile(self, source_name: str, new_name: str) -> Path
  import_legacy(self, source: Path, name: str=...) -> Path | None
```

## kadoka_quest/data/species_creator.py

```text
class SpeciesCreator
  __init__(self, repository: GameRepository, asset_root: Path) -> None
  validate_id(species_id: str) -> str
  normalize_color(value: str) -> str
  build_draft(self, species_id: str=..., display_name: str=..., color: str=...) -> tuple[dict, dict, dict, dict]
  create(self, definition: dict, stats: dict, skills: dict, plus: dict) -> str
```

## kadoka_quest/data/state.py

```text
class StateStore
  __init__(self, path: Path | None=...) -> None
  load(self) -> dict[str, Any]
  save(self, state: dict[str, Any]) -> None
  ensure_starters(self, state: dict[str, Any], monsters: MonsterStore) -> None
  party_records(state: dict[str, Any], monsters: MonsterStore) -> list
```

## kadoka_quest/developer/build_core.py

```text
class BuildTarget
executable_name(target: BuildTarget) -> str
default_targets(source_root: Path) -> dict[str, BuildTarget]
selected_targets(source_root: Path, value: str) -> list[BuildTarget]
require_pyinstaller() -> None
reset_user_data(output: Path) -> Path
copy_runtime_content(output: Path, content_root: Path) -> None
subprocess_pyinstaller(command: Sequence[str], *, cwd: Path) -> None
build_target(target: BuildTarget, *, source_root: Path, content_root: Path, dist_root: Path, build_root: Path, runner: Callable[..., None]=..., extra_args: Sequence[str]=...) -> Path
build_distributions(*, source_root: Path, content_root: Path | None=..., dist_root: Path | None=..., build_root: Path | None=..., targets: str=..., clean: bool=..., runner: Callable[..., None]=..., developer_extra_args: Sequence[str]=...) -> list[Path]
install_player_runtime_template(developer_output: Path, player_output: Path) -> Path
materialize_player_distribution(template: Path, *, content_root: Path, dist_root: Path) -> Path
```

## kadoka_quest/developer/distribution_smoke.py

```text
selected_targets(value: str) -> list[str]
executable_path(distribution: Path, name: str) -> Path
verify_static_layout(distribution: Path, name: str) -> Path
smoke_environment() -> dict[str, str]
diagnostic_text(distribution: Path) -> str
run_process(distribution: Path, executable: Path, arguments: list[str], environment: dict[str, str]) -> None
run_smoke(key: str, distribution: Path, executable: Path) -> None
smoke_distributions(dist_root: Path, *, targets: str=...) -> list[Path]
```

## kadoka_quest/developer/project_validator.py

```text
class ValidationMessage
  compact(self) -> str
class ValidationReport
  errors(self) -> tuple[ValidationMessage, ...]
  warnings(self) -> tuple[ValidationMessage, ...]
  ok(self) -> bool
  summary(self, *, detail_limit: int=...) -> str
class ProjectValidator
  __init__(self, data_root: Path | None=..., asset_root: Path | None=...) -> None
  validate(self) -> ValidationReport
```

## kadoka_quest/developer/workflow.py

```text
class WorkflowResult
class RunningTask
class DeveloperWorkflowService
  __init__(self, project_root: Path | None=..., *, executable: str | None=..., frozen: bool | None=..., launcher: Callable[..., Any]=...) -> None
  log_root(self) -> Path
  validate_project(self) -> WorkflowResult
  preview_player(self) -> WorkflowResult
  start_player_build(self) -> WorkflowResult
  start_player_smoke(self) -> WorkflowResult
  poll(self) -> WorkflowResult | None
```

## kadoka_quest/devtools/balance_analyzer.py

```text
class BalanceSettings
class BalanceAnalyzer
  __init__(self, repository: GameRepository, settings: BalanceSettings | None=...) -> None
  analyze(self, species_ids: Iterable[str] | None=...) -> dict[str, Any]
```

## kadoka_quest/devtools/evaluation_log.py

```text
class EvaluationLog
  __init__(self) -> None
  add(self, kind: str, step: int, **details: Any) -> None
  report(self, *, status: str, visited_maps: set[str], attempted_events: set[str]) -> dict[str, Any]
```

## kadoka_quest/devtools/field_explorer.py

```text
class FieldExplorer
  next_plan(self, map_data: dict[str, Any], blocks: dict[str, dict[str, Any]], player: tuple[int, int], visited_maps: set[str], attempted_events: set[str]) -> dict[str, Any] | None
```

## kadoka_quest/devtools/game_evaluator.py

```text
class GameEvaluationRunner
  __init__(self, game: Any, explorer: FieldExplorer | None=..., log: EvaluationLog | None=...) -> None
  from_default_game(cls) -> 'GameEvaluationRunner'
  run(self, max_steps: int=...) -> dict[str, Any]
```

## kadoka_quest/paths.py

```text
is_frozen() -> bool
runtime_root() -> Path
active_save_name() -> str
ensure_runtime_directories() -> None
```

## kadoka_quest/ui/battle_renderer.py

```text
class BattleRenderer
  __init__(self, images: CharacterImageProvider) -> None
  draw(self, screen: pygame.Surface, session: BattleSession, buttons: list[Button]) -> None
```

## kadoka_quest/ui/character_image_provider.py

```text
class CharacterImageProvider
  __init__(self, repository: Any, asset_root: Path) -> None
  get(self, species_id: str, kind: str, size: tuple[int, int]) -> pygame.Surface | None
  clear(self) -> None
  appearance(self, species_id: str) -> dict
```

## kadoka_quest/ui/common.py

```text
init_pygame(title: str, size: tuple[int, int]) -> pygame.Surface
font(size: int, bold: bool=...) -> pygame.font.Font
draw_text(surface: pygame.Surface, value: object, position: tuple[int, int], size: int=..., color: tuple[int, int, int]=..., bold: bool=...) -> pygame.Rect
draw_wrapped(surface: pygame.Surface, value: str, rect: pygame.Rect, size: int=..., color: tuple[int, int, int]=..., line_gap: int=...) -> int
class Button
  draw(self, surface: pygame.Surface, mouse: tuple[int, int]) -> None
  handle(self, event: pygame.event.Event) -> bool
class ScrollBar
  __init__(self, rect: pygame.Rect, orientation: str=..., total: int=..., page: int=...) -> None
  maximum(self) -> int
  configure(self, total: int, page: int) -> None
  thumb_rect(self) -> pygame.Rect
  handle(self, event: pygame.event.Event) -> bool
  draw(self, surface: pygame.Surface, mouse: tuple[int, int]) -> None
class TextField
  __init__(self, rect: pygame.Rect, value: str=..., numeric: bool=...) -> None
  draw(self, surface: pygame.Surface, label: str=...) -> None
  handle(self, event: pygame.event.Event) -> bool
handle_fields(fields: list[TextField], event: pygame.event.Event) -> bool
draw_status_bar(surface: pygame.Surface, message: str, rect: pygame.Rect, *, warning: bool=...) -> None
smoke_frames() -> int | None
```

## kadoka_quest/ui/field_renderer.py

```text
draw_field(screen: pygame.Surface, session: FieldSession, images: CharacterImageProvider, party: Sequence[MonsterRecord], selected_index: int, now: int | None=...) -> None
```

## kadoka_quest/ui/map_spawn_form.py

```text
class MapSpawnForm
  __init__(self) -> None
  snapshot(self) -> tuple
  changed(self) -> bool
  draft(self) -> dict
  load(self, document: dict) -> None
  deactivate(self) -> None
  toggle(self) -> None
  toggle_button(self) -> Button
  handle(self, event: pygame.event.Event) -> None
  draw(self, surface: pygame.Surface, mouse: tuple[int, int]) -> None
```

## kadoka_quest/ui/pixel_editor.py

```text
class PixelTarget
class PixelArtEditor
  __init__(self, asset_root: Path, targets: Iterable[PixelTarget]=...) -> None
  zoom(self) -> float
  zoom_percent(self) -> int
  logical_size(self) -> int
  set_targets(self, targets: Iterable[PixelTarget]) -> None
  load_targets(self, targets: Iterable[PixelTarget], body_color: tuple[int, int, int]=..., selected: str | None=..., kadoka_palette_limit: int | None=...) -> None
  load_species(self, definition: dict, species_id: str) -> None
  load_block(self, relative_path: str, body_color: tuple[int, int, int]=...) -> None
  resize_canvas(self, size: int) -> bool
  select(self, slot: str) -> None
  set_tool_mode(self, mode: str) -> bool
  color_to_hex(color: tuple[int, int, int, int]) -> str
  parse_palette_color(value: str) -> tuple[int, int, int, int]
  parse_tolerance(value: str) -> int
  add_palette_color(self, value: str) -> tuple[int, int, int, int]
  remove_palette_color(self, color: tuple[int, int, int, int] | None=...) -> bool
  palette_rects(self, origin: tuple[int, int], columns: int, swatch_size: tuple[int, int], gap: tuple[int, int]=...) -> list[tuple[tuple[int, int, int, int], pygame.Rect]]
  zoom_in(self) -> bool
  zoom_out(self) -> bool
  reset_zoom(self) -> None
  image_rect(self, canvas: pygame.Rect) -> pygame.Rect
  begin_pan(self, position: tuple[int, int], canvas: pygame.Rect) -> bool
  pan_to(self, position: tuple[int, int], canvas: pygame.Rect) -> bool
  end_pan(self) -> None
  begin_stroke(self) -> bool
  end_stroke(self) -> None
  undo(self) -> bool
  import_image(self, value: str, tolerance: int=...) -> int
  merge_similar_colors(self, tolerance: int=...) -> int
  reduce_to_kadoka_colors(self, max_colors: int) -> tuple[int, int]
  visible_color_count(self) -> int
  draw_checker(surface: pygame.Surface, rect: pygame.Rect, cell: int=...) -> None
  draw_canvas(self, surface: pygame.Surface, canvas: pygame.Rect) -> None
  paint(self, position: tuple[int, int], canvas: pygame.Rect, erase: bool=...) -> bool
  fill(self, position: tuple[int, int], canvas: pygame.Rect, erase: bool=...) -> int
  save_images(self) -> None
  save_all(self, definition: dict) -> None
```

## kadoka_quest/ui/pixel_operations.py

```text
rgba(color: pygame.Color | ColorTuple) -> ColorTuple
flood_fill_copy(source: pygame.Surface, start: tuple[int, int], replacement: ColorTuple) -> tuple[pygame.Surface, int]
color_distance_squared(first: ColorTuple, second: ColorTuple) -> int
reduce_similar_colors(source: pygame.Surface, tolerance: int) -> tuple[pygame.Surface, int]
nearest_palette_color(color: ColorTuple, palette: Iterable[ColorTuple]) -> ColorTuple
opaque_color_count(source: pygame.Surface) -> int
select_kadoka_palette(source: pygame.Surface, max_colors: int) -> tuple[ColorTuple, ...]
reduce_to_kadoka_palette(source: pygame.Surface, max_colors: int=...) -> tuple[pygame.Surface, int, tuple[ColorTuple, ...]]
fit_imported_image(source: pygame.Surface, size: int=...) -> pygame.Surface
```

## kadoka_quest/ui/runtime_input_adapter.py

```text
class RuntimeInputAdapter
  __init__(self, move_directions: dict[int, str]) -> None
  translate(self, event: pygame.event.Event, mode: str, now: int, *, battle_finished: bool=..., battle_playback: bool=...) -> list[dict]
```

## kadoka_quest/ui/runtime_mouse_adapter.py

```text
class RuntimeMouseAdapter
  __init__(self, password_keys: Iterable[tuple[str, pygame.Rect]], password_actions: Mapping[str, pygame.Rect], battle_buttons: Iterable[tuple[str, pygame.Rect]]) -> None
  translate(self, event: pygame.event.Event, mode: str, *, battle_enabled: bool=..., now: int | None=...) -> list[dict]
```

## kadoka_quest/ui/spawn_table_dialog.py

```text
class SpawnTableDialog
  __init__(self, editor: MapEditor) -> None
  close(self) -> None
  new(self) -> None
  revert(self) -> None
  revert_map(self) -> None
  select_tab(self, tab: str) -> None
  handle(self, event: pygame.event.Event, mouse: tuple[int, int] | None=...) -> None
  draw(self, surface: pygame.Surface, mouse: tuple[int, int]) -> None
```
