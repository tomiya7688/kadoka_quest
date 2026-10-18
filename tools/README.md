# Project tooling

治療付き回復の実適用性能はcheck_gdscript_status_cure.py --cure-actionで確認します。開発者はリポジトリルートでKADOKA_GODOT_EXECUTABLEにGodotを設定し、指定Pythonから実行してください。標準20000回・7サンプル・2000回事前実行で、八行動ごとの新規構築を含む一行動中央値3000us以内と、全行動の実HP1回復/MP6消費/毒解除・固定八体の最終資源/状態・原本保持が成功条件です。総行動数は八の倍数が必要です。AI・描画・I/O・実セーブは計測しません。[実治療契約](../docs/GDScript治療付き回復行動契約.md)を確認してください。

治療付き回復の準備済み定義選択は、リポジトリルートでKADOKA_GODOT_EXECUTABLEを指定して`python tools/performance-check/script/check_gdscript_status_cure.py --cure-context`を実行してください。八体/千件の準備済み索引からの選択だけを標準20000回・7サンプル・2000回事前実行で測り、中央値3000us以内・正常定義・参加数/索引数・入力/準備保持を確認します。初期状態検証/索引構築・起動/I/O・実更新・Session・描画・AIは計測しません。Godot未指定は終了コード2の未検証です。入力・境界・再試行方法は[準備契約](../docs/GDScript治療付き回復準備契約.md)を参照してください。

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

状態付きSession開始の性能はcheck_gdscript_status_cure.py --session-statusで測ります。開発者は環境変数KADOKA_GODOT_EXECUTABLEにGodotを設定し、リポジトリルートで指定Pythonから実行してください。各反復で八体を新規開始し、個別/全体状態と数値snapshotを読み取ります。標準20000回・7サンプル・2000回事前実行で中央値3ms以内と、固定参加者/初期状態の実結果・原本保持が成功条件です。従来カーソルとは別の開始ライフサイクルで、治療行動・AI・描画・I/O・実セーブは含みません。詳細は[状態保持契約](../docs/GDScript戦闘Session状態保持契約.md)を参照してください。

The GDScript normal-attack guard measures one next/validate/claim/actual-HP/finish action in an eight-actor session (same counts, median <= 3ms), amortizing a round plan every eight actions. HP persists; content preparation and state initialization are outside timing. It does not select AI actions, render a battle, measure eight complete actions together or touch saves. Missing Godot exits 2 as Unverified.

The basic-defend guard cycles four explicit defend actions then four actual guarded attacks in an eight-actor Session. It measures one stage (standard counts; median <= 3ms), amortizing plan and terminal guard clearing every eight stages. It also checks actual HP loss and final guard=1 without resetting resources. This is not AI, a complete skills runtime, rendering, I/O, export or all eight actions timed as one. Nonstandard total counts must end on an eight-stage boundary to verify terminal clearing.

Reusable patterns in `code-docs` and `task-workflow` were adapted from `tomiya7688/AI_game_player`.

`affected-tests`, `import-map`, and the bounded exploration/validation workflow were adapted from the MIT-licensed `tomiya7688/ai-context-reducer` principles. They are kept local to this repository so Kadoka Quest does not depend on that repository at runtime or during development.

The UPD checker is a development/CI dependency fetched from the MIT-licensed `tomiya7688/upd-commander-base-design` repository. No UPD checker package is added to Kadoka Quest runtime dependencies.

Project-specific OCR, screen capture, Windows input, GUI automation, or unrelated project behavior is intentionally not imported into Kadoka Quest.

状態一件の非破壊付与予測はcheck_gdscript_status_cure.py --status-applyで測ります。開発者は環境変数KADOKA_GODOT_EXECUTABLEへ使えるGodotを設定し、リポジトリルートで指定Pythonから実行してください。四件の状態に対するネスト付き出血の成功予測を標準20000回・7サンプル・2000回事前実行で測り、一予測中央値3000us以内・確率0.5・五件の結果一覧・固定原本保持を成功条件とします。拒否や重複だけの高速結果は通過しません。実状態/Session更新・保存・AI・描画・I/Oは測りません。Godot未指定は終了コード2の未検証です。入力と失敗対応は[付与予測契約](../docs/GDScript状態付与予測契約.md)を確認してください。

個体の一件実付与の性能はcheck_gdscript_status_cure.py --status-apply-stateで測ります。開発者は環境変数KADOKA_GODOT_EXECUTABLEへ使えるGodotを設定し、リポジトリルートで指定Pythonから実行してください。各反復で四件の新規開始・付与準備・予測/読取・出血一件追加/読取・判定値なしの同ID再付与/読取を行います。標準20000回・7サンプル・2000回事前実行で一サイクル中央値3000us以内と、固定原本/初期四件/予測非変更/更新後五件/重複後五件を照合します。構築/準備/読取は含め、I/O・Session・描画・AI・保存は測りません。Godot未指定は終了コード2の未検証です。入力と拒否対応は[状態一覧契約](../docs/GDScript戦闘状態一覧契約.md#最新一覧への一件付与)を確認してください。

参加者状態集合の対象一体付与はcheck_gdscript_status_cure.py --roster-status-applyで測ります。開発者は環境変数KADOKA_GODOT_EXECUTABLEへ使えるGodotを設定し、リポジトリルートで指定Pythonから実行してください。各反復で同IDの両陣営各四体を開始し、enemies/member_2だけへの準備/予測/読取/出血一件追加/同ID重複/個別全体読取を測ります。標準20000回・7サンプル・2000回事前実行で一サイクル中央値3000us以内、対象一体三件→四件・他七体三件保持・固定原本と全実結果一致を照合します。構築/保持/読取は含み、I/O・Session予約/攻撃・AI・描画・保存は測りません。Godot未指定は終了コード2の未検証です。入力と拒否対応は[参加者状態付与契約](../docs/GDScript参加者状態付与契約.md)を確認してください。

取得済み予約の状態付与はcheck_gdscript_status_cure.py --session-status-applyで測ります。開発者は環境変数KADOKA_GODOT_EXECUTABLEへ使えるGodotを指定し、リポジトリルートで指定Pythonから実行してください。八行動ごとの新規八体構築/初回順序込みで、予約提示/取得・敵一体への実付与・同予約の別対象への再判定拒否・個別/全体読取・完了を測ります。標準20000回・7サンプル・2000回事前実行で、一判定中央値3000us以内と全反復確認数/最終八体四状態/数値不変/固定原本を照合します。iterationsとwarmupは八の倍数が必要です。起動/I/O・MP消費・攻撃計算・耐性再構築・AI・描画・保存は測りません。Godot未指定は終了コード2の未検証です。入力と拒否対応は[予約付き付与契約](../docs/GDScript予約付き状態付与契約.md)を確認してください。

付与付き物理の純粋予測はcheck_gdscript_status_physical.pyで測ります。開発者はKADOKA_GODOT_EXECUTABLEへ使えるGodotを指定し、リポジトリルートで指定Pythonから実行してください。共用起動/診断へ委譲し、標準20000回・7サンプル・2000回事前実行で、一予測中央値3000us以内と固定原本・79ダメージ/残HP921/MP97/出血一件成功を照合します。致死/重複/拒否だけの高速結果は通過しません。起動/I/O・一覧prepare・実更新/予約・能力/耐性再構築・AI・描画・保存は測りません。Godot未指定は終了コード2の未検証です。条件と拒否対応は[専用予測契約](../docs/GDScript状態付与付き物理予測契約.md)を確認してください。


付与付き物理の準備済み索引からの選択はcheck_gdscript_status_physical.py --contextで測ります。開発者はKADOKA_GODOT_EXECUTABLEへ使えるGodotを指定し、リポジトリルートで指定Pythonから実行してください。標準20000回・7サンプル・2000回事前実行で一選択中央値3000us以内、固定八体/千定義・付与定義・装備倍率2/加算3・初期状態/耐性・数値六キーと原本保持を照合します。準備/索引構築・I/O・実HPMP/状態更新・予約・AI・描画・保存は測りません。拒否だけの高速結果は通過せず、Godot未指定は終了コード2の未検証です。入出力と未接続範囲は[実行準備契約](../docs/GDScript状態付与付き物理準備契約.md)を確認してください。


付与付き物理の最新予約/資源/状態の非消費検査はcheck_gdscript_status_physical.py --preflightで測ります。開発者はKADOKA_GODOT_EXECUTABLEへ使えるGodotを指定し、リポジトリルートで指定Pythonから実行してください。標準20000回・7サンプル・2000回事前実行で一検査中央値3000us以内と、固定八体/千定義・成功選択/最新状態・満資源/提示予約の保持を照合します。高速拒否だけでは通過しません。準備/索引作成・起動/I/O・実行/能力補正・AI・描画・保存は測りません。Godot未指定は終了コード2の未検証です。入出力/拒否/未接続範囲は[開始/検査契約](../docs/GDScript状態付与付き物理検査契約.md)を確認してください。

状態能力値補正の性能検査は、四状態・重複出血・一時速度倍率1.5を含む固定入力から防御45・速度55を予測し、入力保持も照合します。開発者はKADOKA_GODOT_EXECUTABLEへ使えるGodotを指定し、リポジトリルートで指定Pythonから `tools/performance-check/script/check_gdscript_status_stats.py` を実行してください。状態能力値補正の標準計測は20000回・7サンプル・2000回事前実行で、一予測中央値3000us以内が合格条件です。状態能力値補正の計測には、起動/I/O・戦闘行動・AI・描画・保存を含めません。専用CLIはGodot未指定時に終了コード2を返し、未検証として扱います。開発者は入力と拒否対応を[状態能力値補正契約](../docs/GDScript状態能力値補正契約.md)で確認してください。

状態付与付き物理の実行性能は `tools/performance-check/script/check_gdscript_status_physical_action.py` で検査します。開発者は使えるGodotをKADOKA_GODOT_EXECUTABLEへ指定し、リポジトリルートで指定Pythonから実行してください。専用検査は八体/千定義・八行動ごとの新規構築込みで、実MP消費・ダメージ・出血・予約完了/再送拒否を測ります。固定入力/最終資源/状態と確認件数を照合し、標準20000回・7サンプル・2000回事前実行で一行動中央値3000us以内を要求します。起動/I/O・AI・描画・保存は測りません。Godot未指定は終了コード2の未検証です。開発者はAPIと内部失敗時の制限を[専用行動契約](../docs/GDScript状態付与付き物理行動契約.md)で確認してください。
