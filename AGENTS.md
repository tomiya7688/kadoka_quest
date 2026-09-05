# Kadoka Quest Codex cheat sheet

Read this file first. Open `README.md` or `docs/FORMATS.md` only when the task needs user-facing details or full JSON examples.

## Project and commands

- Canonical checkout: `C:\Users\tomiy\games\kadokaquest`
- Stack: Python 3.10+, `pygame-ce`, UTF-8 JSON. Package code is under `src/kadoka_quest/`.
- Install: `py -m venv .venv`, then `.venv\Scripts\python.exe -m pip install -e .`
- Run launcher: `.venv\Scripts\python.exe launcher.py` or `run_game.bat`
- Full tests: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
- Headless UI: set `SDL_VIDEODRIVER=dummy`, `SDL_AUDIODRIVER=dummy`, and use an isolated `KADOKA_SAVE_DIR`.
- Before reporting completion: run the full tests and `I:\program_files\ide\Git\cmd\git.exe diff --check`.

## Architecture

- `application/app_command.py`, `command_bus.py`: pygame-independent semantic command contract and one-target router. Runtime screens communicate by `target/action/payload`, never pygame events or surfaces.
- `application/runtime_orchestrator.py`: owns the active screen mode, the shared command bus, all runtime command-app registrations, and plain field-effect routing across apps.
- `src/kadoka_quest/apps/game.py`: input and orchestration for field, encounters and saves; battle drawing is not allowed here.
- `apps/battle_session.py`: pygame-free battle lifecycle state machine for command selection, paced log playback, focused actor, auto timing, simulation identity, finalization, and fixed-mob battle identity.
- `apps/password_session.py`: pygame-free bounded virtual-keyboard state for allowed characters, input length, prompt, validation, and reset; monster acquisition stays outside it.
- `apps/manager_process_service.py`: owns external manager launch command, duplicate prevention, process handle, and one-shot close detection; save reload stays in game orchestration.
- `apps/field_command_app.py`, `battle_command_app.py`, `password_command_app.py`, `manager_command_app.py`: independent pygame-free command boundaries. The pygame loop translates input to commands and may read state for rendering, but must not invoke screen actions directly.
- `apps/field_event_app.py`: pygame-free field interaction state machine. It translates NPC, transition, church, spring, manager, and pickup interactions into one plain-data effect.
- `apps/map_editor.py`, `block_editor.py`, `monster_editor.py`, `manage.py`: direct editors; no export format.
- `apps/data_creator.py`: developer-facing individual generator UI; keep generation logic outside the pygame layer.
- `core/battle.py`: combat calculation coordinator. It receives `BattleDataLoader`, `BattleInference`, and `BattleLearning`; do not move their responsibilities back into the engine.
- `core/combatant.py`: runtime combat state only. `core/battle_inference.py` selects actions without mutation; `core/battle_learning.py` mutates sparse AI learning. `core/ai.py` is their backward-compatible public facade plus default AI creation.
- `core/battle_context.py`: engine-independent fixed battle-context tags; do not store combinatorial board states.
- `core/grid_movement.py`: pygame-independent visual interpolation between integer grid positions.
- `core/field_engine.py`: pygame/file-I/O-independent field rules. Inputs and results stay plain dict/list/int/string/bool values for GDScript/Lua parity.
- `core/fixed_mob_controller.py`: pygame/file-I/O-independent fixed-mob runtime state, dialogue decks, occupancy, facing pauses, and timed movement.
- `core/hidden_enemy_controller.py`: pygame/file-I/O-independent hidden-enemy population, spawn filtering, vision, occupancy, and chase/wander timing.
- `core/player_field_controller.py`: pygame/file-I/O-independent player grid position, facing, held-key repeat state, and visual interpolation.
- `data/repository.py`: species, blocks, maps, equipment and skills.
- `data/battle_data.py`: the only battle-time loader for combatants, species definitions, skills, stats, resistances and equipment.
- `data/field_data.py`: the only runtime field map/block loader and entry-position clamp.
- `data/field_progress.py`: field-only persistence for position, revival, inventory pickup, flags, and fixed-mob despawn state.
- `data/map_presets.py`: map-schema presets saved outside the playable map catalog.
- `data/species_creator.py`: validates and creates complete four-JSON species scaffolds plus five dependency-free 64x64 PNG placeholders.
- `data/monsters.py`, `developer_monster_creator.py`, `parties.py`, `savedata.py`, `state.py`: save folders, developer outputs, and individual data.
- `ui/pixel_editor.py`: the one shared pixel editor for monster art and block art. It owns the mutable session palette; editor apps only supply controls and layout.
- `ui/pixel_operations.py`: shared pygame-surface processing for outline-bounded flood fill, RGB-distance color reduction, and nearest-neighbour image fitting; no screen/event responsibilities.
- `ui/field_renderer.py`: pygame-only field rendering; it must not decide collisions, events or encounters.
- `ui/battle_renderer.py`: pygame-only battle rendering; it reads session state but cannot run rounds, infer actions, learn, or load battle data.
- `ui/character_image_provider.py`: the only runtime character-PNG loader. It resolves portrait/directional paths, crops field transparency, nearest-neighbour scales, and caches surfaces; game orchestration only delegates.
- `ui/runtime_input_adapter.py`: pygame-only keyboard adapter. It converts quit/key down/key up plus current mode into plain command requests; it never executes game actions.
- `ui/runtime_mouse_adapter.py`: pygame-only mouse adapter. It converts password-key and battle-button hit tests into plain command requests; it never executes callbacks or game actions.
- `data/`: mod-friendly source of truth. `assets/`: PNG files. `savedata/<name>/`: player-owned state.

## Data contracts

- Blocks: `data/blocks/<id>.json`; keep player walkability, enemy spawning and enemy walkability independent.
- Maps: `data/maps/<id>/map.json`; `tiles`, hidden-enemy `spawns`, visible `fixed_mobs`, and `events` are separate layers.
- Map presets: `data/map_presets/<id>.json`; use the same JSON shape as maps. Applying keeps the target map identity; creating replaces it with a new identity.
- Species: `data/species/<id>/{species,stats,skills,plus}.json`; stats contain every level 1-100.
- Monster editor species list begins with `+ new`; creation must reject duplicate IDs and generate all four JSON files plus portrait/front/right/left/back PNGs.
- Equipment owns `allowed_species_ids`; species do not own equipment-category permissions.
- All portraits and front/right/left/back source images use exact 64x64 PNG canvases and nearest-neighbour scaling.
- Pixel-editor palettes are session UI state, accept `#RRGGBB`, hold at most 16 colors, and are not serialized into species/block JSON or PNG metadata.
- Image import never enlarges a source, preserves aspect ratio, centres it on the target canvas, uses nearest-neighbour scaling, then applies the selected 0-255 color tolerance. Import, fill, and color reduction each create one undo step.
- Save layout: `savedata/<name>/{state.json,items/items.json,monsters/<id>/{monster,ai}.json,parties/*.json}`.
- Developer monster outputs use the same individual format and may target the active save, `imports/acquire`, or `imports/simulation`; never overwrite an existing individual ID.
- Normal battles may learn individual AI; simulation battles must use `learning_enabled=False`. AI reset must not reset identity, level or plus choices.
- Context learning stores sparse per-tag skill preferences for exactly six current tags: self HP, ally damage, MP, numbers, target HP, and level threat.

## Fixed mobs

`map.json.fixed_mobs[]` is for villagers, bosses and visible placed monsters. Core keys:

- identity/placement: `id`, `species_id`, `name`, `x`, `y`, `direction`, `enabled`, `level`
- movement: `ai` = `idle|random|chase`, `move_interval_ms` >= 100, `move_chance` = 0..100
- interaction: `interaction` = `talk|battle`; battle uses `level`
- talk: `dialogue` is a deck, normally 3-5 strings; exhaust the deck before repeating
- disappearance: `despawn_after_interaction`, `respawn_on_map_enter`

Fixed mobs spawn at their initial point whenever the map loads, cannot share a tile, and do not move while the player is directly in front of them. Permanent disappearance is saved in `state.json.despawned_fixed_mobs`.

## Gameplay invariants already requested

- Start in `starting_town`; its ranch opens monster/party management. World order continues through `greenwood`, `fresh_forest`, `rokuta_village`, and `ghost_home`.
- Defeat revives at the registered church. Signs, rocks and fixed characters are blocking.
- Wild enemies are invisible field actors; encounter when one reaches the tile directly in front of the player. Ball slime is starter-only and never spawns as an enemy.
- Ghost-home password is entered at the water spring. `へいわなすみか` recruits Maru and Kadoka.
- Maru and Kadoka remain visible regardless of ownership; Maru moves more often. They cannot overlap the player or each other.
- Combat uses party AI rather than per-monster manual commands, supports keyboard and auto battle, and reveals actions at a readable pace.
- Guard reduces physical damage only.
- Field collisions, events, encounters, and saves always use integer grid coordinates. Only visible player/fixed-mob positions and camera tracking are interpolated.

## Editing and Git rules

- Preserve plain JSON and direct editor-to-runtime formats. Update `docs/FORMATS.md` when adding keys.
- Preserve unrelated dirty-worktree changes. In particular, do not restore/delete BAT files unless the task asks for it.
- Do not modify user save data during tests; use a temporary `KADOKA_SAVE_DIR`.
- The user prefers terminal Git. Do not push unless explicitly asked; verify the remote result before saying an upload completed.
- Remote: `https://github.com/tomiya7688/kadoka_quest.git`, branch `main`.
- Keep command payloads plain (`str/int/float/bool/list/dict/None`) so applications can later move to processes or another engine. Add commands at an application boundary instead of importing pygame into command apps.
