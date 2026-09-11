# Implementation workflow

Use the smallest context that can complete the assigned task.

1. If no Issue is explicitly assigned, run `tools/task-workflow/script/start_task.bat` and use the single Issue it returns.
2. Run `python tools/remote-context/script/sync_remote_context.py` before implementation to fetch and summarize remote changes.
3. Read the selected Issue and only its Read scope / related CODEMAP entries.
4. Expand to additional source, tests, or full diffs only when the compact context is insufficient.
5. Keep development utilities under `tools/<tool-name>/script/`.
6. For architecture inspection, prefer generated/compact artifacts before repository-wide reading. Generate the class diagram with `python tools/code-docs/script/generate_class_diagram.py`; verify it with `--check` when it is tracked/generated in the current workflow.
7. Run the relevant focused tests first, then the required full completion checks before reporting completion.

Do not start by scanning every Issue, document, generated artifact, or source file.
