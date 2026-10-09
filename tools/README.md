# Project tooling

Development and maintenance tools live under `tools/<tool-name>/`.

Each tool keeps executable scripts under `tools/<tool-name>/script/`. Tool-specific support files should stay inside that tool directory. Do not add new project tooling directly to the repository root or top-level `scripts/`.

Current tools:

- `comment-check`: `python tools/comment-check/script/check_comments.py` checks declaration-comment coverage and signature agreement for all tracked Python/GDScript, batch entry/subroutines and executable CI workflow headers. It uses static source inspection, never imports Player code, and is read-only. See [COMMENT_RULES](../docs/COMMENT_RULES.md); tests: `tests/test_comment_contract.py`. It is a narrow project guard, not an upstream parser fork or prose correctness guarantee.

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
python tools/performance-check/script/check_gdscript_fixed_mobs.py
python tools/performance-check/script/check_gdscript_combatant.py
python tools/performance-check/script/check_gdscript_battle_session.py
python tools/performance-check/script/check_gdscript_normal_attack.py
python tools/performance-check/script/check_gdscript_basic_defend.py
python tools/performance-check/script/check_gdscript_physical_skill.py
python tools/performance-check/script/check_gdscript_physical_action.py
python tools/performance-check/script/check_gdscript_magic_skill.py
python tools/performance-check/script/check_gdscript_magic_action.py
python tools/performance-check/script/check_gdscript_magic_action.py --self-damage
python tools/performance-check/script/check_gdscript_magic_action.py --drain-mp
python tools/performance-check/script/check_gdscript_magic_action.py --heal
python tools/performance-check/script/check_gdscript_self_damage_magic.py
python tools/performance-check/script/check_gdscript_drain_mp_skill.py
python tools/performance-check/script/check_gdscript_heal_skill.py
python tools/performance-check/script/check_gdscript_status_cure.py
python tools/performance-check/script/check_gdscript_status_cure.py --cure-heal
python tools/performance-check/script/check_gdscript_status_cure.py --status-state
```

戦闘状態一覧の保持/更新性能はcheck_gdscript_status_cure.py --status-stateで測ります。開発者はリポジトリルートでKADOKA_GODOT_EXECUTABLEへ使えるGodotを指定して実行してください。各反復で新しい四件状態の開始→非破壊予測→読取→毒一件の実治療→読取を実行します。標準20000回・7サンプル・2000回事前実行で、中央値3000us以内・開始/予測後四件・実治療後三件・原本保持を照合します。Session・起動/I/O・保存・描画・AIは測りません。Godot未指定は終了コード2の未検証です。入力と拒否対応は[戦闘状態一覧契約](../docs/GDScript戦闘状態一覧契約.md)を確認してください。

状態異常一つの治療予測性能はcheck_gdscript_status_cure.pyで測ります。開発者はKADOKA_GODOT_EXECUTABLEを設定して実行してください。解除不可2件を飛ばした毒一件の治療予測を標準20000回・7サンプル・2000回事前実行で測り、中央値3000us以内・毒だけの除去・元一覧保持を確認します。起動/読込・実治療・描画・AIは測りません。Godot未指定は終了コード2の未検証です。入力と失敗対応は[状態治療予測契約](../docs/GDScript状態治療予測契約.md)を確認してください。

治療付きHP回復の予測性能はcheck_gdscript_status_cure.py --cure-healで測ります。開発者はリポジトリルートで、環境変数KADOKA_GODOT_EXECUTABLEに使えるGodotの実行ファイルを設定して実行してください。HP990/1000・MP10から回復上限30/実回復10・残HP1000/MP6と毒一件の解除・入力保持を照合します。20000回・7サンプル・2000回事前実行で一回中央値3000us以内を確認し、治療単体は区分なしで再測定できます。実Session治療・描画・AIは測らず、具体的な入力と拒否は[治療付き回復予測契約](../docs/GDScript治療付き回復予測契約.md)を確認してください。

単体HP回復の実適用性能はcheck_gdscript_magic_action.py --healで測ります。開発者はKADOKA_GODOT_EXECUTABLEを設定して実行してください。専用8体の次行動取得から実MP消費・実HP回復・予約完了までを標準20000回・7サンプル・2000回事前実行で測り、中央値3000us以内と8体の累積HP/MPを確認します。全反復で回復する専用MOD率1e-9を使い、満HPでのMP消費・正規回復率は回帰テストへ分けます。実セーブ・描画・AIは測りません。入力と失敗対応は[回復スキル行動契約](../docs/GDScript回復スキル行動契約.md)を確認してください。

単体HP回復の純粋予測性能はcheck_gdscript_heal_skill.pyで測ります。開発者はKADOKA_GODOT_EXECUTABLEを設定して実行してください。標準20000回・7サンプル・2000回の事前実行で予測1回を測り、中央値3000us以内、回復上限量220・実回復100・残HP1000/MP4と元入力の保持を確認します。起動・読込・実資源更新・描画・AIは測りません。Godot未指定は終了コード2の未検証です。入力と失敗対応は[回復スキル予測契約](../docs/GDScript回復スキル予測契約.md)を確認してください。

吸MP付き魔法の純粋予測性能はcheck_gdscript_drain_mp_skill.pyで測ります。開発者はKADOKA_GODOT_EXECUTABLEを設定して実行してください。標準20000回・7サンプル・2000回の事前実行で予測1回を測り、中央値3000us以内、敵HP975・術者MP19・敵MP66、敵MP喪失/術者MP回復がともに14と元入力の保持を確認します。起動・読込・実資源更新・描画・AIは測りません。Godot未指定は終了コード2の未検証です。入力と失敗対応は[吸MPスキル予測契約](../docs/GDScript吸MPスキル予測契約.md)を確認してください。

吸MP魔法の実適用性能はcheck_gdscript_magic_action.py --drain-mpで測ります。開発者はKADOKA_GODOT_EXECUTABLEを設定して実行してください。専用8体の1行動を標準20000回・7サンプル・2000回の事前実行で測り、中央値3000us以内、各行動の実MP移転・8体の累積資源・HP変化を確認します。専用係数0.7を使い、無効/吸収ではMPを奪いません。初回の満タン回復で味方2体が各2MPを回復できないため、累積MP純減は総行動数×消費MP5に4を加えた量です。総反復数が8未満または8の倍数でない設定は拒否します。実セーブ・描画・AIの性能は測りません。入力と失敗対応は[吸MPスキル行動契約](../docs/GDScript吸MPスキル行動契約.md)を確認してください。

自傷魔法の実適用性能はcheck_gdscript_magic_action.py --self-damageで測ります。開発者はKADOKA_GODOT_EXECUTABLEを設定して実行してください。専用8体の1行動を標準20000回・7サンプル・2000回の事前実行で測り、中央値3000us以内と累積MP消費・敵HP効果・術者HP代償を確認します。全員の生存を維持する専用MOD率1e-9を使い、正規率0.1とHP1下限は回帰テストへ分けます。実セーブ・描画・AIの性能は測りません。入力・資源・失敗対応は[自傷魔法行動契約](../docs/GDScript自傷魔法行動契約.md)を確認してください。

自傷付き魔法の純粋予測は、通常魔法と同じ20000回・7サンプル・2000回の事前実行で測ります。開発者はGodotを指定し、check_gdscript_self_damage_magic.pyを実行してください。時間上限3000usに加え、敵HP・術者HP代償・残MPの期待値と元入力の保持を確認します。実資源更新や描画は測りません。Godot未指定は終了コード2の未検証です。入力と失敗時の確認方法は[自傷魔法予測契約](../docs/GDScript自傷魔法予測契約.md)を参照してください。

The performance thresholds intentionally allow normal CI variance and fail only large runtime regressions. Grow this tool with the project: when field updates, battle resolution, data transformations, or other runtime paths become performance-sensitive, add representative benchmark cases here rather than introducing runtime profiling overhead into the game.

単体魔法の性能検査は、実Godotの純粋予測1回を20000回・7サンプル・2000回の事前実行で測定します。中央値3000us以内、期待したHP/MP予測、入力不変のすべてを確認します。実MP消費・描画・ファイル読込は計測しません。開発者は`KADOKA_GODOT_EXECUTABLE`を指定して上記の`check_gdscript_magic_skill.py`を実行してください。Godot未指定時は終了コード2の未検証です。対応範囲と失敗対応は[魔法予測契約](../docs/GDScript魔法スキル予測契約.md)を確認してください。

単体魔法行動の性能検査は、8体Sessionの次行動取得から検証・claim・実MP/HP適用・finishまでを1行動ずつ測ります。標準20000回・7サンプル・2000回warmup、中央値3000us以内と累積MP消費・通常/無効/吸収/強耐性のHP変化を確認します。8行動ごとのラウンド準備を含めますが、起動・読込・初期再構築・描画・AI・保存は計測しません。開発者はGodotを指定してcheck_gdscript_magic_action.pyを実行してください。Godot未指定は終了コード2の未検証、診断・資源不一致・時間超過は失敗です。[魔法行動契約](../docs/GDScript魔法スキル行動契約.md)で入力と失敗条件を確認してください。
The GDScript fixed-mob guard requires `KADOKA_GODOT_EXECUTABLE` and measures real headless Godot update + snapshot for 24 actors (20,000 iterations / 7 samples / 2,000 warmup; median <= 2ms). It uses private fixtures and does not measure drawing, I/O, window FPS, or exported builds. Missing Godot is Unverified with exit 2, never a successful substitute.
It also measures dialogue selection + plain effect generation for the last of 24 actors with five cards (median <= 100us), including repeated deck refills. This is not timing of keyboard delivery or text rendering.
The GDScript combatant guard measures eight battle-only resource states (init + damage + MP + flee + snapshot + living) in real headless Godot: 20,000 iterations / 7 samples / 2,000 warmup, median <= 1ms. It does not execute a battle round, AI or scene, and never changes save/content files. Missing Godot exits 2 as Unverified. These tools remain outside Player runtime imports.
It also measures base-speed round planning plus one latest-resource eligibility check for eight combatants (same standard counts, median <= 2ms). It does not time eight actions, attack/AI resolution, an executed round, rendering or I/O.
The GDScript battle-session guard measures one next/claim/zero-resource/finish stage in an eight-actor session (same counts, median <= 2ms), amortizing one new round plan every eight stages. State initialization is outside timing. This is not eight resolved actions, a real battle round, AI, rendering, I/O or export.

The GDScript normal-attack guard measures one next/validate/claim/actual-HP/finish action in an eight-actor session (same counts, median <= 3ms), amortizing a round plan every eight actions. HP persists; content preparation and state initialization are outside timing. It does not select AI actions, render a battle, measure eight complete actions together or touch saves. Missing Godot exits 2 as Unverified.

The basic-defend guard cycles four explicit defend actions then four actual guarded attacks in an eight-actor Session. It measures one stage (standard counts; median <= 3ms), amortizing plan and terminal guard clearing every eight stages. It also checks actual HP loss and final guard=1 without resetting resources. This is not AI, a complete skills runtime, rendering, I/O, export or all eight actions timed as one. Nonstandard total counts must end on an eight-stage boundary to verify terminal clearing.

Reusable patterns in `code-docs` and `task-workflow` were adapted from `tomiya7688/AI_game_player`.

`affected-tests`, `import-map`, and the bounded exploration/validation workflow were adapted from the MIT-licensed `tomiya7688/ai-context-reducer` principles. They are kept local to this repository so Kadoka Quest does not depend on that repository at runtime or during development.

The UPD checker is a development/CI dependency fetched from the MIT-licensed `tomiya7688/upd-commander-base-design` repository. No UPD checker package is added to Kadoka Quest runtime dependencies.

Project-specific OCR, screen capture, Windows input, GUI automation, or unrelated project behavior is intentionally not imported into Kadoka Quest.
