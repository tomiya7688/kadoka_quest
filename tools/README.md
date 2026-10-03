# Project tooling

Development and maintenance tools live under `tools/<tool-name>/`.

Each tool keeps executable scripts under `tools/<tool-name>/script/`. Tool-specific support files should stay inside that tool directory. Do not add new project tooling directly to the repository root or top-level `scripts/`.

Current tools:

REPO_MAP: `python tools/code-docs/script/generate_repo_map.py` generates
`docs/generated/REPO_MAP.md` from `src/` using only the standard library and AST;
game modules are never imported. Use `--check` for read-only freshness validation.
`--source` / `--output` accept repository-relative or absolute paths. Public
top-level classes/functions and direct public methods (plus constructors) are
included; defaults become `...`. Bodies, docstrings, private helpers and nested
definitions are omitted. Paths are sorted; timestamps and absolute paths are not
embedded. Search only the relevant file section after reading CODEMAP. Tests:
`python -m pytest tests/test_repo_map.py`.

- `remote-context`: fetches and summarizes remote changes for Chat/Codex workflows.
- `affected-tests`: maps changed files to likely focused tests and signals when broader validation is safer.
- `import-map`: emits a compact JSON index of Python files and imports for dependency-routing questions.
- `character-sprites`: builds bundled character sprites from source sheets.
- `sample-data`: regenerates bundled sample JSON data.
- `code-docs`: AST-based code-derived documentation. `script/generate_class_diagram.py` generates or checks Mermaid class diagrams without reading implementation bodies into agent context. CI tracks the compact application-layer diagram under `docs/generated/application_class_diagram.mmd`.
- `project-integrity`: checks machine-enforceable architecture rules such as the pygame/file-I/O-free `core/` boundary and required project entry paths, with concise failure output.
- `upd-commander`: installs the latest Python checker from `tomiya7688/upd-commander-base-design` `main`. UPD errors are blocking; warnings and attentions remain visible migration guidance. Checker-side improvements belong in the upstream repository rather than a Kadoka-only fork.
- `performance-check`: Kadoka Quest-owned runtime microbenchmarks. It starts with command routing overhead and should gain focused benchmarks as new performance-sensitive paths appear. It is development/CI-only and is never imported by Player runtime.
- `task-workflow`: small task-selection helpers. `script/start_task.bat` returns one open candidate (`p0 -> p1 -> p2 -> p3 -> p4`). During active migration, P1 prefers the oldest gdscript-tagged Issue before general P1; P0 is always checked first. See [Issue priority policy](../docs/ワークフロー/Issue優先度方針.md) and [migration units](../docs/ワークフロー/GDScript移行実装単位.md). Tests: `tests/test_task_priority.py` (real Windows batch with isolated fake `gh`, no GitHub writes).
- `e2e-catalog`: validates `docs/testing/E2E_EXPECTATIONS.md` and statically checks covered source E2E node references. Run `python tools/e2e-catalog/script/check_e2e_catalog.py`; use `--missing` for unresolved scenarios. It never imports game/test modules or runs tests. This is a catalog check, not proof that E2E passed. Tests: `python -m pytest tests/test_e2e_catalog.py`.

UPD checker setup and execution:

```text
python -m pip install --no-cache-dir --upgrade --force-reinstall -r tools/upd-commander/requirements.txt
python tools/upd-commander/script/check.py
python tools/upd-commander/script/check.py --advisory
```

If using the checker exposes a missing rule, false positive, output/reporting problem, or CI integration improvement, file it at `tomiya7688/upd-commander-base-design`. Do not copy or patch the checker implementation inside Kadoka Quest unless a temporary diagnostic experiment is explicitly required.

Runtime performance check:

```text
python tools/performance-check/script/check_runtime_performance.py
```

The performance thresholds intentionally allow normal CI variance and fail only large runtime regressions. Grow this tool with the project: when field updates, battle resolution, data transformations, or other runtime paths become performance-sensitive, add representative benchmark cases here rather than introducing runtime profiling overhead into the game.

Reusable patterns in `code-docs` and `task-workflow` were adapted from `tomiya7688/AI_game_player`.

`affected-tests`, `import-map`, and the bounded exploration/validation workflow were adapted from the MIT-licensed `tomiya7688/ai-context-reducer` principles. They are kept local to this repository so Kadoka Quest does not depend on that repository at runtime or during development.

The UPD checker is a development/CI dependency fetched from the MIT-licensed `tomiya7688/upd-commander-base-design` repository. No UPD checker package is added to Kadoka Quest runtime dependencies.

Project-specific OCR, screen capture, Windows input, GUI automation, or unrelated project behavior is intentionally not imported into Kadoka Quest.
