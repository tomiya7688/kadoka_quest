# Kadoka Quest CODEMAP

Meaning-based index for implementation work. Start here when the Issue identifies a feature area but not the exact symbol. Read the listed implementation and preferred tests first; open specifications only when the task changes or depends on the documented contract.

| Area | Primary implementation | Preferred tests | Contract / notes |
|---|---|---|---|
| Battle rules / skills / status | `src/kadoka_quest/core/battle.py`, `core/combatant.py`, `data/battle_data.py` | `tests/test_battle_*.py`, focused cases in `tests/test_core.py` | `docs/FORMATS.md` for skill/species data |
| Individual battle AI | `core/ai.py`, `core/battle_inference.py`, `core/battle_learning.py`, `core/battle_context.py` | focused AI/battle cases in `tests/test_core.py` | learning data stays sparse and per individual |
| Field movement / encounters | `core/field_engine.py`, `core/player_field_controller.py`, `core/fixed_mob_controller.py`, `core/hidden_enemy_controller.py` | field/controller cases in `tests/test_core.py` | `apps/game.py` is orchestration only |
| Field events / map progress | `apps/field_event_app.py`, `data/field_data.py`, `data/field_progress.py` | event/map cases in `tests/test_core.py` | `docs/FORMATS.md`, target `data/maps/<id>/` |
| Runtime command routing | `application/app_command.py`, `application/command_bus.py`, `application/runtime_orchestrator.py`, `apps/*_command_app.py` | command/orchestrator cases in `tests/test_core.py` | `docs/コマンド駆動アプリ基盤機能説明書.md` |
| Ranch / party management | `apps/ranch_manager.py`, `apps/field_party_session.py`, `apps/field_party_service.py`, `data/parties.py`, `data/monsters.py` | party/manager cases in `tests/test_core.py` | normal owned monsters only |
| Simulation facility | `apps/simulation_manager.py`, `apps/simulation_roster_service.py`, `apps/simulation_facility_hooks.py` | `tests/test_simulation_facility.py` | `docs/模擬戦会館機能説明書.md` |
| Save data / paths | `data/savedata.py`, `data/state.py`, `paths.py` | `tests/test_save_name_validation.py`, `tests/test_distribution_savedata.py` | never use real user saves in tests |
| Species / catalogs | `data/repository.py`, `data/species_creator.py`, `data/species/<id>/` | repository/species cases in `tests/test_core.py` | `docs/FORMATS.md` |
| Field / battle UI | `ui/field_renderer.py`, `ui/battle_renderer.py`, `ui/character_image_provider.py` | renderer/smoke cases in `tests/test_core.py`, `tests/test_app_smoke.py` | UI reads state; it does not decide rules |
| Input adapters | `ui/runtime_input_adapter.py`, `ui/runtime_mouse_adapter.py` | adapter cases in `tests/test_core.py` | output plain semantic commands |
| Map / block / monster editors | matching `apps/*_editor.py`, `ui/pixel_editor.py`, `ui/pixel_operations.py` | editor/data cases in `tests/test_core.py` | direct editor-to-runtime formats |
| Player / Developer launcher split | `apps/launcher_config.py`, root `launcher.py`, `developer_launcher.py` | `tests/test_launcher_split.py`, `tests/test_player_distribution_boundary.py` | Player must not expose Developer tools |
| Developer build / distribution | `developer/build_core.py`, `developer/workflow.py`, `developer/distribution_smoke.py` | `tests/test_developer_workflow.py`, `tests/test_distribution_*.py` | `.github/workflows/windows-distribution.yml` |
| Context / repo tooling | `docs/context/`, `tools/<tool-name>/script/` | `tests/test_context_tools.py`, `tests/test_context_router.py` | `tools/README.md` |

## Symbol-level lookup

When the primary file is still ambiguous, regenerate or read `docs/generated/REPO_MAP.md`:

```text
python tools/code-docs/script/generate_repo_map.py
```

The generated map contains file paths plus public top-level class/function signatures only. It deliberately omits implementation bodies, call graphs, private helpers, and prose specifications.

## Test routing

Prefer the focused test named in the table. Expand to `tests/test_core.py`, the relevant subsystem, or the full suite when shared/core/public contracts change. `tools/affected-tests/script/affected_tests.py` can suggest likely focused tests from a Git diff.

## Source of truth

This file is a routing index, not a specification. The assigned Issue defines acceptance; code/tests define runtime behavior; `docs/FORMATS.md` defines data contracts when relevant; canonical JSON under `data/` defines bundled game data.
