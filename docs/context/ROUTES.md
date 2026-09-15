# Context routes

Use this file when you only need the smallest first-hop route for an assigned Issue. Use `docs/CODEMAP.md` when you also need the preferred tests and contract/specification for that area. The Issue remains the source of truth for scope and acceptance.

| Task area | Read first | Expand only when needed |
|---|---|---|
| Battle rules / skills / status | `src/kadoka_quest/core/battle.py`, `core/combatant.py`, matching tests | `data/battle_data.py`, `core/battle_inference.py`, `core/battle_learning.py`, `docs/FORMATS.md` |
| Battle UI / lifecycle | `apps/battle_session.py`, `ui/battle_renderer.py` | `apps/battle_command_app.py`, `application/runtime_orchestrator.py` |
| Field movement / encounters | matching controller in `core/`, `apps/game.py` only for orchestration | `data/field_data.py`, `data/field_progress.py`, `ui/field_renderer.py` |
| Field events / NPCs | `apps/field_event_app.py`, target `data/maps/<id>/map.json` | `application/runtime_orchestrator.py`, `docs/FORMATS.md` |
| Player input | `ui/runtime_input_adapter.py` or `ui/runtime_mouse_adapter.py` | matching `apps/*_command_app.py` |
| Ranch / party management | `apps/ranch_manager.py`, `data/state.py`, `data/parties.py` | `data/monsters.py`, matching tests |
| Simulation facility | `apps/simulation_manager.py`, `apps/simulation_roster_service.py` | `apps/simulation_facility_hooks.py`, battle/session files |
| Save data | `data/savedata.py`, `data/state.py`, `paths.py` | launcher/game caller and matching tests |
| Species / battle data | `data/repository.py`, target `data/species/<id>/` | `data/battle_data.py`, `docs/FORMATS.md` |
| Map / block / monster editors | matching `apps/*_editor.py` | `ui/pixel_editor.py`, `ui/pixel_operations.py`, related data module |
| Developer environment / build | `developer/workflow.py`, `developer/build_core.py` | `developer/distribution_smoke.py`, `.github/workflows/windows-distribution.yml` |
| Player / Developer launcher split | `apps/launcher_config.py`, root `launcher.py` / `developer_launcher.py` | distribution boundary tests |
| Architecture / responsibility split | `docs/CODING_RULES.md`, affected module | `docs/*責務分離機能説明書.md`, compact class diagram |
| Context / tooling | `docs/context/WORKFLOW.md`, `tools/README.md` | only the specific `tools/<name>/script/` implementation |
| CI / project integrity | relevant `.github/workflows/*.yml` | `developer/project_validator.py`, `tools/project-integrity/` when present |

Paths under `apps/`, `core/`, `data/`, `developer/`, and `ui/` are relative to `src/kadoka_quest/` unless a full repository path is shown.

## Data routes

- Blocks: `data/blocks/<id>.json`
- Maps: `data/maps/<id>/map.json` plus optional `data/maps/<id>/events/*.json`
- Species: `data/species/<id>/{species,stats,skills,plus}.json`
- Equipment / skills: repository catalogs under `data/`
- Player state: `savedata/<name>/`; tests must use isolated temporary save roots
- External individuals: `imports/acquire/` and `imports/simulation/`

## Stop rule

Stop reading when Goal / Required / Acceptance are clear and the files required to change and validate them are known. If an exact class/function is still unclear, generate/read `docs/generated/REPO_MAP.md`; do not open unrelated source files merely to browse.
