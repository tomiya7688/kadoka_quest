# Kadoka Quest agent router

Read this file, the [developer rules index](docs/開発者向け/README.md), and the assigned Issue first. Read all three mandatory rules linked by that index. Do not read the whole repository up front.
Use [Issue priority policy](docs/ワークフロー/Issue優先度方針.md): P0 is emergency-only; normal priority starts at P1.
During active migration, prefer gdscript P1 units; read [migration units](docs/ワークフロー/GDScript移行実装単位.md) to skip locally implemented work.

## Context Budget

1. Extract **Goal / Required / Acceptance** from the Issue.
2. Read the matching row in `docs/CODEMAP.md` for implementation, focused tests, and specification. Use `docs/context/ROUTES.md` only for additional routing when needed.
3. Run `python tools/remote-context/script/sync_remote_context.py` at task start and before every commit/push.
4. Search or use compact indexes before opening additional full files.
5. Stop exploring once the required change, constraints, and validation are clear.

`README.md`, `docs/FORMATS.md`, generated diagrams, and broad architecture docs are not default reading. Open them only when the route or task requires them. Generated/index files are navigation aids, never source-of-truth replacements.

## Co-development

The user, Codex, Claude Code, Copilot, and ChatGPT work concurrently; follow [the task workflow](docs/ワークフロー/ワークフロー.md). Skip units already in an active remote branch or open PR. Branch from latest `origin/main` with an author prefix (`codex/`, `claude/`, `copilot/`, `kadoka/`). `CLAUDE.md`, `.github/copilot-instructions.md`, and the `kadoka-task` skill only route here.

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
- Follow [coding/review standards](docs/開発者向け/コーディング規約.md), [responsibility boundaries](docs/開発者向け/CODING_RULES.md), and [declaration comments](docs/開発者向け/COMMENT_RULES.md). Their canonical text is separated from game specifications under `docs/開発者向け/`.
- Read optional local instructions through `docs/開発者向け/ローカル専用/README.md` when present; local overrides still control mandatory local reading. Never publish ignored local rule text. Clean clones do not require local-only files.
- Validate all tracked declaration comments with `python tools/comment-check/script/check_comments.py`; stage only the current task's new files before this check.

Machine-checkable boundaries belong in tests/CI rather than duplicated prose. Run `python tools/project-integrity/script/check_project_rules.py` when that tool exists on the working branch.

For architecture/responsibility changes, follow the latest-UPD installation and blocking-error rules in [responsibility boundaries](docs/開発者向け/CODING_RULES.md#upd-commander-checker). Report checker-side improvements upstream instead of creating a private fork, subject to public-write authorization.

For routing/layer or runtime-hot-path changes, run and extend the [runtime performance guard](docs/開発者向け/CODING_RULES.md#実行速度の保護). Keep development checkers out of Player runtime; any necessary performance exception must remain local, rule-specific, and justified.

## Routing

Use `docs/context/ROUTES.md` to choose the next files for battle, field, UI, ranch, simulation, save data, editors, build, architecture, context tooling, and CI tasks.

For context-efficient implementation workflow details, read `docs/context/WORKFLOW.md` only when the task concerns process/tooling or the route calls for it.

Useful compact helpers:

- remote changes and active branches: `tools/remote-context/script/sync_remote_context.py`
- likely tests: `tools/affected-tests/script/affected_tests.py`
- dependency ambiguity: `tools/import-map/script/python_import_map.py`
- compact class diagram: `tools/code-docs/script/generate_class_diagram.py`
- symbol signatures: search `docs/generated/REPO_MAP.md` after selecting a CODEMAP row; regenerate with `python tools/code-docs/script/generate_repo_map.py`.

## Completion and Git

- Preserve unrelated changes; do not mix unrelated refactors into the current task.
- Do not modify real user saves during tests.
- Run focused tests first, then the full required suite before reporting completion.
- Run `git diff --check` for local Git work.
- Report materially relevant untested areas as **Unverified** instead of continuing open-ended exploration.
- Use a feature branch/PR for repository changes. Do not merge a PR unless the user explicitly asks.
