# Kadoka Quest: Codex quick context

Read this file first. Load only the linked document required for the task; do not load the complete roadmap, feedback, or format reference by default.

## Context Budget

Start with this file, the selected Issue, and one matching `docs/CODEMAP.md` row. Do not read README, FORMATS, every feature document, or unrelated source files until that row and Issue show a concrete need. CODEMAP routes battle/AI, field/fixed mobs, monster, map/block, editor, runtime command, save/data, and UI/input work to the next files. For architecture, responsibility splitting, new modules/classes, or dependency-direction changes, additionally read `docs/CODING_RULES.md`.

## Work order

1. Run `python tools/remote-context/script/sync_remote_context.py` to fetch and compactly inspect remote changes. Read the full diff only if its output is insufficient.
2. Check GitHub Issues and their priority first. Then check only relevant feedback and roadmap entries.
3. Work on a branch; preserve unrelated dirty and untracked files.
4. Test, update the relevant document and `docs/ver.md`, then commit only task files.
5. Never push, open a PR, close an Issue, or alter player saves without explicit permission.

If the Issue service is unavailable, report that fact and use the last verified priority rather than inventing one.

## Commands

- Canonical checkout: `C:\Users\tomiy\games\kadokaquest`
- Python: `venv_3135` (3.13.5); use `scripts\run_python.bat`.
- Full test: `scripts\run_python.bat -m unittest discover -s tests -v`
- Headless test: set dummy SDL drivers and an isolated `KADOKA_SAVE_DIR`.
- Always finish with a syntax check and `git diff --check`.
- Project tools belong under `tools/<tool-name>/script/`; do not add new root or top-level `scripts/` tools.

## Boundaries

- `kadoka_engine` is reusable, pygame-free, and must never import `kadoka_quest`.
- `apps/` owns pygame-free application actions. Runtime screens communicate only via `AppCommand(target, action, payload)`.
- `apps/game.py` orchestrates input and modes; battle drawing belongs to `ui/battle_renderer.py`.
- `ui/` draws or adapts pygame input only; it must not decide gameplay rules.
- One class has one responsibility and lives in its own module.

## Data contracts

- Source-of-truth JSON is directly edited and directly read by the game: no export format.
- Maps: `data/maps/<id>/map.json`; separate `tiles`, `spawns`, `fixed_mobs`, `events` layers.
- Species: `data/species/<id>/{species,stats,skills,plus}.json`; all levels 1–100.
- Equipment owns `allowed_species_ids`; species do not.
- Saves: `savedata/<name>/{state.json,items/items.json,monsters/<id>/{monster,ai}.json,parties/*.json}`.
- Monster portrait/front/right/left/back PNG canvases are exact 64×64 and use nearest-neighbour scaling.
- Update `docs/FORMATS.md` whenever a JSON key changes.

## Gameplay invariants

- Start at `starting_town`; defeat revives at registered church.
- Hidden enemies encounter only when they reach the player-facing tile; `ball_slime` never wild-spawns.
- Signs, rocks, and fixed characters block movement; characters cannot overlap.
- Normal battles learn individual AI; simulations use `learning_enabled=False`; AI reset preserves identity, level, and plus choices.

## Load on demand

- Task-to-file index: `docs/CODEMAP.md`
- JSON details: `docs/FORMATS.md`
- Current plans: `docs/開発予定.md`
- Evaluator feedback: `docs/評価/評価者からのフィードバック.md`
- Version history: `docs/ver.md`
- Feature-specific documents: `docs/*機能説明書.md`

Keep this file compact. Put feature details in a feature document, not here.
