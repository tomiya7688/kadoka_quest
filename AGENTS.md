# Kadoka Quest agent router

Read this file and the assigned Issue first. Do not read the whole repository up front.

## Context budget

1. Extract **Goal / Required / Acceptance** from the Issue.
2. Read the matching row in `docs/context/ROUTES.md` and only its first-hop files.
3. Run `python tools/remote-context/script/sync_remote_context.py` when local work may be behind remote Chat/Codex changes.
4. Search or use compact indexes before opening additional full files.
5. Stop exploring once the required change, constraints, and validation are clear.

`README.md`, `docs/FORMATS.md`, generated diagrams, and broad architecture docs are not default reading. Open them only when the route or task requires them. Generated/index files are navigation aids, never source-of-truth replacements.

## Project basics

- Python 3.10+, `pygame-ce`, UTF-8 JSON.
- Package code: `src/kadoka_quest/`.
- Mod/game data source of truth: `data/`.
- Image assets: `assets/`.
- Player-owned runtime data: save/UserData roots; tests must use isolated temporary save roots.
- Project tools belong under `tools/<tool-name>/`; executable scripts belong under `tools/<tool-name>/script/`.

Common commands:

```text
py -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\python.exe launcher.py
.venv\Scripts\python.exe -m pytest
```

For headless UI tests set `SDL_VIDEODRIVER=dummy`, `SDL_AUDIODRIVER=dummy`, and use an isolated `KADOKA_SAVE_DIR`.

## Hard boundaries

- `core/` is gameplay/domain logic and must stay free of pygame and file I/O.
- `application/` owns plain semantic command routing. Command payloads remain JSON-like plain data.
- `apps/` coordinates sessions/services and screen flow; do not move substantial new domain logic into `apps/game.py`.
- `data/` owns persistence and canonical data loading.
- `ui/` owns pygame rendering/input adaptation; renderers do not decide gameplay outcomes.
- Player and Developer entry points stay separated. Developer tooling must not leak into the Player launcher/build.
- Preserve direct JSON/editor-to-runtime formats. When a data contract changes, update `docs/FORMATS.md`.
- Follow `docs/CODING_RULES.md` for architecture/responsibility changes.

Machine-checkable boundaries belong in tests/CI rather than duplicated prose. Run `python tools/project-integrity/script/check_project_rules.py` when that tool exists on the working branch.

For architecture/responsibility changes, install and run the latest UPD checker from `tomiya7688/upd-commander-base-design`:

```text
python -m pip install --no-cache-dir --upgrade --force-reinstall -r tools/upd-commander/requirements.txt
python tools/upd-commander/script/check.py
```

UPD errors are blocking. Warnings and attentions are migration guidance and remain non-blocking. `--advisory` may be used only for temporary investigation, not as a completion substitute.

When UPD checker usage reveals a checker-side improvement, missing rule, false positive, reporting problem, or CI integration need, create an Issue in `tomiya7688/upd-commander-base-design` instead of implementing a private Kadoka-only fork.

When adding or changing routing/Commander/Messenger/Service layers or another runtime hot path, run and extend the Kadoka Quest performance checker as needed:

```text
python tools/performance-check/script/check_runtime_performance.py
```

The performance checker is a Kadoka Quest local development tool. Grow its benchmark coverage alongside the game (for example field update, battle resolution, or data conversion) when those paths become performance-sensitive. Do not add checker or benchmark imports to Player runtime code. Performance-motivated UPD exceptions must be local, rule-specific, and include a reason.

## Routing

Use `docs/context/ROUTES.md` to choose the next files for battle, field, UI, ranch, simulation, save data, editors, build, architecture, context tooling, and CI tasks.

For context-efficient implementation workflow details, read `docs/context/WORKFLOW.md` only when the task concerns process/tooling or the route calls for it.

Useful compact helpers:

- remote changes: `tools/remote-context/script/sync_remote_context.py`
- likely tests: `tools/affected-tests/script/affected_tests.py`
- dependency ambiguity: `tools/import-map/script/python_import_map.py`
- compact class diagram: `tools/code-docs/script/generate_class_diagram.py`

## Completion and Git

- Preserve unrelated changes; do not mix unrelated refactors into the current task.
- Do not modify real user saves during tests.
- Run focused tests first, then the full required suite before reporting completion.
- Run `git diff --check` for local Git work.
- Report materially relevant untested areas as **Unverified** instead of continuing open-ended exploration.
- Use a feature branch/PR for repository changes. Do not merge a PR unless the user explicitly asks.
