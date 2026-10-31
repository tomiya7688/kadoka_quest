# Implementation workflow

Use the smallest context that can complete the assigned task. Accuracy comes before context reduction.

Read the [developer rules index](../開発者向け/README.md) and its mandatory coding, responsibility, and comment rules before implementation. Keep their text in the linked canonical documents rather than copying it into AGENTS or game specifications.

## Start and stop conditions

1. If no Issue is explicitly assigned, run `tools/task-workflow/script/start_task.bat` and use the single Issue it returns.
   Follow the [Issue priority policy](../ワークフロー/Issue優先度方針.md): P0 is reserved for emergencies; normal work uses P1 through P4. Check dependencies before implementing the returned candidate.
   During active GDScript migration, prefer gdscript-tagged P1 units and consult [migration units](../ワークフロー/GDScript移行実装単位.md) before repeating locally implemented work.
2. Extract the task's **Goal / Required / Acceptance** from the Issue before broad exploration.
3. Run `python tools/remote-context/script/sync_remote_context.py` before implementation to fetch and summarize remote changes.
4. Read the selected Issue and only its Read scope / related routing information.
5. Search or use an index first; read full files second. Expand to additional source, tests, docs, or full diffs only when required evidence is missing.
6. Once Goal / Required / Acceptance and the working set are sufficient to implement safely, stop exploring.

Do not start by scanning every Issue, document, generated artifact, source file, log, or history. Generated/index artifacts are navigation aids, not substitutes for source-of-truth files.

## Source of truth

- Requested change and acceptance: the assigned Issue.
- Game/runtime behavior: implementation and matching tests.
- Mod/game data: canonical JSON under `data/`.
- Data-format contracts: `docs/FORMATS.md` when the task changes those contracts.
- Generated diagrams/indexes: navigation only; return to source/tests when details matter.

Do not mix unrelated refactors into the current task.

## Routing helpers

- Remote changes: `python tools/remote-context/script/sync_remote_context.py`
- Likely affected tests: `python tools/affected-tests/script/affected_tests.py --base origin/main...HEAD`
- Python dependency ambiguity only: `python tools/import-map/script/python_import_map.py`
- Architecture overview: `python tools/code-docs/script/generate_class_diagram.py`
- Machine-checkable architecture rules: `python tools/project-integrity/script/check_project_rules.py`
- Tracked application diagram freshness: `python tools/code-docs/script/generate_class_diagram.py --source src/kadoka_quest/application --output docs/generated/application_class_diagram.mmd --check`

Use these compact outputs to narrow the working set. Do not load their complete output when the target files are already known.

## Validation

1. Run the smallest relevant focused tests first. Use `affected-tests` as a candidate selector, not as proof that no other tests can be affected.
2. If it reports `fallback: broader`, or shared/core/public contracts changed, expand validation to the subsystem or full suite.
3. Machine-checkable architecture rules and tracked generated-doc freshness are enforced by the `project-integrity` CI job; do not duplicate those rules as task-specific prose unless an exception needs human judgment.
4. After implementing, run `python tools/format/script/format_changed.py` to format the Python and GDScript files you added, then run the required full completion checks before reporting completion. Before pushing, run `python tools/local-ci/script/run_local_ci.py` with `KADOKA_GODOT_EXECUTABLE` set: it runs the same commands as the `Python quality` CI workflow, including the Godot job, and fails when any Godot test is skipped. Exit code 3 means some jobs were not run; report them as **Unverified**.
5. Report any materially relevant area not checked as **Unverified** instead of continuing open-ended exploration merely for reassurance.

Keep development utilities under `tools/<tool-name>/script/`; tool-specific config/support files stay inside that tool directory.

## User-visible expectations

For user-observable changes, update the matching Given / When / Then row in
`docs/testing/E2E_EXPECTATIONS.md`, including persistence/reload expectations.
Use its stable scenario ID in the corresponding source E2E. If the harness or
scenario is not implemented, leave the row `missing` with a reason; do not relabel
unit/integration/smoke evidence as E2E coverage. Run
`python tools/e2e-catalog/script/check_e2e_catalog.py` after catalog/test-reference
changes. It checks references only; executing E2E is separate. CI/quality command
integration remains Issue #205 after the harness and scenarios exist.
