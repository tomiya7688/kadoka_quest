# Project tooling

Development and maintenance tools live under `tools/<tool-name>/`.

Each tool keeps executable scripts under `tools/<tool-name>/script/`. Tool-specific support files should stay inside that tool directory. Do not add new project tooling directly to the repository root or top-level `scripts/`.

Current tools:
- `remote-context`: fetches and summarizes remote changes for Chat/Codex workflows.
- `character-sprites`: builds bundled character sprites from source sheets.
- `sample-data`: regenerates bundled sample JSON data.
- `code-docs`: AST-based code-derived documentation. `script/generate_class_diagram.py` generates or checks `docs/generated/class_diagram.mmd` without reading implementation bodies into agent context.
- `task-workflow`: small task-selection helpers. `script/start_task.bat` returns only the oldest open Issue at the highest available priority (`critical -> high -> medium -> low`) instead of scanning the full Issue list.

Reusable patterns in `code-docs` and `task-workflow` were adapted from `tomiya7688/AI_game_player`. Project-specific OCR, screen capture, Windows input, and GUI automation code is intentionally not imported into Kadoka Quest.
