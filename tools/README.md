# Project tooling

Development and maintenance tools live under `tools/<tool-name>/`.

Each tool keeps executable scripts under `tools/<tool-name>/script/`. Tool-specific support files should stay inside that tool directory. Do not add new project tooling directly to the repository root or top-level `scripts/`.

Current tools:
- `remote-context`: fetches and summarizes remote changes for Chat/Codex workflows.
- `affected-tests`: maps changed files to likely focused tests and signals when broader validation is safer.
- `import-map`: emits a compact JSON index of Python files and imports for dependency-routing questions.
- `character-sprites`: builds bundled character sprites from source sheets.
- `sample-data`: regenerates bundled sample JSON data.
- `code-docs`: AST-based code-derived documentation. `script/generate_class_diagram.py` generates or checks Mermaid class diagrams without reading implementation bodies into agent context. CI tracks the compact application-layer diagram under `docs/generated/application_class_diagram.mmd`.
- `project-integrity`: checks machine-enforceable architecture rules such as the pygame/file-I/O-free `core/` boundary and required project entry paths, with concise failure output.
- `upd-commander`: runs the pinned Python checker from `tomiya7688/upd-commander-base-design`. UPD errors are blocking; warnings and attentions remain visible migration guidance. `script/check.py --advisory` is available only for temporary investigation.
- `performance-check`: runs short runtime-routing microbenchmarks for `AppCommand`, plain payload validation, `CommandBus` dispatch, and command creation+dispatch. It is development/CI-only and is never imported by Player runtime.
- `task-workflow`: small task-selection helpers. `script/start_task.bat` returns only the oldest open Issue at the highest available priority (`critical -> high -> medium -> low`) instead of scanning the full Issue list.

UPD checker setup and execution:

```text
python -m pip install -r tools/upd-commander/requirements.txt
python tools/upd-commander/script/check.py
python tools/upd-commander/script/check.py --advisory
```

Runtime performance check:

```text
python tools/performance-check/script/check_runtime_performance.py
```

The performance thresholds intentionally allow normal CI variance and fail only large routing-overhead regressions. Do not tighten them to chase small benchmark differences on hosted runners.

Reusable patterns in `code-docs` and `task-workflow` were adapted from `tomiya7688/AI_game_player`.

`affected-tests`, `import-map`, and the bounded exploration/validation workflow were adapted from the MIT-licensed `tomiya7688/ai-context-reducer` principles. They are kept local to this repository so Kadoka Quest does not depend on that repository at runtime or during development.

The UPD checker itself is installed only for development/CI from the MIT-licensed `tomiya7688/upd-commander-base-design` repository at the commit pinned in `tools/upd-commander/requirements.txt`. No UPD checker package is added to Kadoka Quest runtime dependencies.

Project-specific OCR, screen capture, Windows input, GUI automation, or unrelated project behavior is intentionally not imported into Kadoka Quest.
