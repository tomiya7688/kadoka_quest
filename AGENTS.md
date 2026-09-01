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

- `src/kadoka_quest/apps/game.py`: input and orchestration for field, encounters, saves and battle presentation.
- `apps/map_editor.py`, `block_editor.py`, `monster_editor.py`, `manage.py`: direct editors; no export format.
- `apps/data_creator.py`: developer-facing individual generator UI; keep generation logic outside the pygame layer.
- `core/battle.py`, `core/monster.py`, `core/ai.py`: combat calculations and individual AI learning.
- `core/battle_context.py`: engine-independent fixed battle-context tags; do not store combinatorial board states.
- `core/grid_movement.py`: pygame-independent visual interpolation between integer grid positions.
- `core/field_engine.py`: pygame/file-I/O-independent field rules. Inputs and results stay plain dict/list/int/string/bool values for GDScript/Lua parity.
- `data/repository.py`: species, blocks, maps, equipment and skills.
- `data/map_presets.py`: map-schema presets saved outside the playable map catalog.
- `data/species_creator.py`: validates and creates complete four-JSON species scaffolds plus five dependency-free 64x64 PNG placeholders.
- `data/monsters.py`, `developer_monster_creator.py`, `parties.py`, `savedata.py`, `state.py`: save folders, developer outputs, and individual data.
- `ui/pixel_editor.py`: the one shared pixel editor for monster art and block art. It owns the mutable session palette; editor apps only supply controls and layout.
- `ui/pixel_operations.py`: shared pygame-surface processing for outline-bounded flood fill, RGB-distance color reduction, and nearest-neighbour image fitting; no screen/event responsibilities.
- `ui/field_renderer.py`: pygame-only field rendering; it must not decide collisions, events or encounters.
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
