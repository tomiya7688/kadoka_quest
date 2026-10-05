# CODEMAP

実装タスクでは、最初にこの表の該当行だけを読む。詳細な仕様をここへ複写せず、リンク先を更新して索引を保つ。

`core/`, `apps/`, `data/`, `ui/`, `application/`, `developer/` は `src/kadoka_quest/` からの相対パス。`kadoka_engine/` は `src/`、`test_*.py` は `tests/` からの相対パス。波括弧は列挙の省略表記。
変更箇所の行にある関連テストを最初に実行する。共通契約を変更した場合はサブシステムまたは全体へ広げる。追加探索が必要な場合だけ `docs/context/ROUTES.md` を参照する。

| タスク種別 | 主実装 | 関連テスト | 仕様書・データ | 境界 |
| --- | --- | --- | --- | --- |
| ゲーム状態 / 責務移行 | `apps/{game,progress_session,field_session,battle_session,field_party_session,password_session}.py` | `test_session_ownership.py`, `test_core.py`, `test_battle_flow_service.py`, `test_simulation_facility.py` | `docs/KadokaQuest状態所有者棚卸し.md` | 正本・互換view・保存時点のコピーを区別し、所有者→呼出側→互換削除の順に移す。 |
| 戦闘 / AI | `core/battle.py`, `core/{ai,battle_inference,battle_learning,battle_context}.py`, `apps/{battle_session,battle_command_app,ai_inspector}.py` | `test_core.py`, `test_ai_inspector.py`, `test_battle_decision_explanation.py` | `docs/戦闘責務分離機能説明書.md`, `docs/状況学習機能説明書.md`, `docs/個体AI可視化機能説明書.md` | 戦闘規則・推論・学習は分離し、描画はUIへ渡す。 |
| AI学習傾向サマリ / 管理画面 | `core/ai_tendencies.py`, `apps/{ai_inspector,ranch_manager,manage}.py`, `ui/ai_tendency_panel.py` | `test_ai_tendencies.py`, `test_ai_inspector.py`, `test_ai_tendency_ui.py` | `docs/AI学習傾向サマリ機能説明書.md`, `docs/個体AI可視化機能説明書.md` | 既存学習値から5指標を純粋計算。両管理画面でゲージ表示しF5/フォーカス復帰で再読込。 |
| フィールド | `kadoka_engine/field_engine.py`, `apps/{game,field_command_app,field_event_app}.py`, `data/{field_data,field_progress}.py` | `test_core.py`, `test_field_use_events.py` | `docs/フィールドエンジン分離第2段階機能説明書.md`, `docs/FORMATS.md` | `kadoka_engine` はpygame・リポジトリ非依存。 |
| fixed mob / 野生敵 | `kadoka_engine/{fixed_mob_controller,hidden_enemy_controller,player_field_controller}.py` | `test_core.py` | `docs/フィールドアクター責務分離機能説明書.md`, `docs/FORMATS.md` | 個体の移動・会話状態はコントローラーが所有する。 |
| モンスター / 個体 / パーティ | `core/monster.py`, `data/{monsters,parties,species_creator,developer_monster_creator}.py`, `apps/{ranch_manager,monster_editor,field_party_service,field_party_session,monster_import_service}.py` | `test_core.py`, `test_player_distribution_boundary.py` | `docs/モンスター種族新規作成機能説明書.md`, `docs/外部個体取込責務分離機能説明書.md`, `docs/FORMATS.md` | 種族定義と個体保存を混在させない。 |
| 模擬戦施設 | `apps/{simulation_manager,simulation_roster_service,simulation_facility_hooks}.py` | `test_simulation_facility.py`, `test_field_command_legacy_cleanup.py` | `docs/模擬戦会館機能説明書.md` | 現行Player導線。旧 `simulation_facility_service.py` は受付の実装ではない。 |
| 戦闘進行 / コマンド | `apps/{battle_flow_service,battle_flow_dependencies,battle_progression_service,battle_command_app,legacy_battle_command_adapter}.py` | `test_battle_flow_service.py`, `test_legacy_battle_command_adapter.py` | `docs/戦闘セッション責務分離機能説明書.md` | 入力ルーティング・進行・永続化の変更箇所を分けて辿る。 |
| map / block | `data/{repository,map_presets}.py`, `apps/{map_editor,block_editor}.py` | `test_core.py`, `test_map_spawn_ranges.py`, `test_metal_spawn_tables.py`, `test_field_use_events.py` | `docs/マッププリセット機能説明書.md`, `docs/出現モンスターレベル範囲機能説明書.md`, `docs/FORMATS.md` | マップJSONは直接編集・直接読込する。 |
| 野生ポップ設定の契約 | `kadoka_engine/{spawn_settings,data_validator,field_ai}.py` | `test_spawn_settings.py`, `test_data_validator.py` | `docs/野生ポップ設定データ契約機能説明書.md`, `docs/FORMATS.md` | 形式・既定値・検証。実行時抽選はwild_spawn。 |
| 出現テーブル編集UI | `apps/map_editor.py`, `ui/spawn_table_dialog.py`, `kadoka_engine/spawn_table.py` | `test_spawn_table_editor.py`, `test_map_spawn_ranges.py` | `docs/野生出現テーブル編集機能説明書.md` | 候補行の編集・比率表示・保存前検証。 |
| マップのポップ率/AI編集 | `ui/map_spawn_form.py`, `kadoka_engine/spawn_controls.py`, `apps/map_editor.py` | `test_map_spawn_controls.py`, `test_spawn_table_editor.py` | `docs/マップポップ率AI編集機能説明書.md`, `docs/FORMATS.md` | 両タブをコピー上で検証して保存。 |
| 野生ポップ抽選 | `kadoka_engine/{wild_spawn,hidden_enemy_controller}.py`, `core/spawn_levels.py`, `apps/game.py` | `test_wild_spawn_runtime.py`, `test_field_ai_assignment.py`, `test_spawn_levels.py` | `docs/野生ポップ抽選機能説明書.md` | 枠ごとのポップ率→種族→Lv→AI。通常Lv保持、メタル域は遭遇時再計算。 |
| editor / ドット絵 | `ui/{pixel_editor,pixel_operations}.py`, `apps/{monster_editor,block_editor,map_editor}.py` | `test_core.py`, `test_pixel_editor_canvas.py` | `docs/ドットエディター画像編集機能説明書.md`, `docs/可変キャンバス機能説明書.md` | 共通ピクセルエディタに対象データだけを渡す。 |
| runtime command | `application/{__init__,app_command,command_bus,runtime_orchestrator}.py`, `apps/*_command_app.py` | `test_command_imports.py`, `test_core.py` | `docs/コマンド駆動アプリ基盤機能説明書.md`, `docs/実行時オーケストレーター機能説明書.md` | 画面間通信はJSON互換の `AppCommand` のみ。 |
| save / data | `data/{savedata,state,jsonio,battle_data,data_validator}.py` | `test_core.py`, `test_data_validator.py` | `docs/FORMATS.md`, `docs/MODデータ一括検証機能説明書.md` | 保存は個体フォルダ単位。JSONキー変更時はFORMATSを更新。 |
| UI / input | `ui/{battle_renderer,field_renderer,character_image_provider,runtime_input_adapter,runtime_mouse_adapter}.py`, `apps/game.py` | `test_session_renderers.py`, `test_core.py`, `test_app_smoke.py` | `docs/実行時入力アダプター責務分離機能説明書.md`, `docs/実行時マウスアダプター責務分離機能説明書.md`, `docs/KadokaQuest状態所有者棚卸し.md` | 描画はSessionと画像Providerを受け取り、ゲーム全体・repositoryを参照しない。 |
| Developer / 配布 | `developer/{workflow,build_core,distribution_smoke}.py`, `apps/developer_launcher.py` | `test_developer_workflow.py`, `test_distribution_process.py`, `test_distribution_paths.py` | `docs/Developer環境説明書.md` | PlayerとDeveloperの起動・ビルドを分離する。 |
| 開発補助 / コンテキスト | `tools/remote-context/script/sync_remote_context.py`, `tools/affected-tests/script/affected_tests.py`, `tools/import-map/script/python_import_map.py` | `test_remote_context.py`, `test_context_tools.py`, `test_context_router.py` | `tools/README.md`, `docs/context/WORKFLOW.md` | 要約は探索の案内。実装とIssueを正とする。 |
| Issue優先度 / 作業選択 | `tools/task-workflow/script/start_task.bat` | `test_task_priority.py`, `test_context_router.py` | `docs/ワークフロー/{ワークフロー,Issue優先度方針,GDScript移行実装単位}.md`, `tools/README.md` | P0は緊急専用、P1内はgdscript優先。候補のみ返し、依存/ローカル実装済み判断は本文とコードへ戻る。 |
| CI / 整合性 | `tools/project-integrity/script/check_project_rules.py`, `developer/project_validator.py`, `.github/workflows/python-app.yml` | `test_project_integrity.py`, `test_data_validator.py` | `docs/CODING_RULES.md` | 機械検証の規則を仕様本文へ複写しない。 |
| E2E期待動作 / 未対応一覧 | `tools/e2e-catalog/script/check_e2e_catalog.py`, `tests/e2e/{harness,runtime_driver,launcher_driver,render_observation}.py` | `test_e2e_catalog.py`, `tests/e2e/{test_harness,test_field_journeys}.py` | `docs/testing/E2E_EXPECTATIONS.md`, `tests/e2e/README.md` | #201は一時セーブ・RNG/clock固定、#202は本番launcher/field/event/save/load（P01～P12）。次は #203/#204。参照チェックは実行成功の代替ではない。 |

## 敵の表示・逃走・報酬・出現Lv

| タスク種別 | 主実装 | 関連テスト | 仕様書 | 境界 |
| --- | --- | --- | --- | --- |
| 地域別逃走 | `core/{battle,combatant}.py`, `data/battle_data.py`, `apps/{game,battle_progression_service}.py` | `test_enemy_flee.py` | `docs/敵の地域別逃走機能説明書.md` | 地域は戦闘開始時に渡す。個体JSONへ保存しない。 |
| 撃破経験値 | `core/battle_rewards.py`, `data/battle_data.py`, `apps/{game,battle_progression_service}.py` | `test_battle_rewards.py`, `test_enemy_flee.py` | `docs/種族別撃破経験値機能説明書.md`, `docs/FORMATS.md` | 種族係数と味方の成長を分離。計算は共通関数、保存はStore。 |
| メタル域の動的Lv | `core/spawn_levels.py`, `apps/game.py` の `make_wild` | `test_spawn_levels.py`, `test_map_spawn_ranges.py` | `docs/メタルエリア動的レベル機能説明書.md` | 遭遇時の先頭4体で計算し、通常域・所有個体を書き換えない。 |
| 野生敵表示 | `ui/field_renderer.py`, `kadoka_engine/hidden_enemy_controller.py` | `test_wild_enemy_rendering.py`, `test_session_renderers.py` | `docs/野生モンスター可視化機能説明書.md` | 描画は既存個体の位置と向きだけを読む。 |

| 野生個体AI割当 | `kadoka_engine/{field_ai,hidden_enemy_controller}.py`, `data/field_data.py`, `apps/game.py` | `test_field_ai_assignment.py`, `test_metal_spawn_tables.py` | `docs/野生個体AI割当機能説明書.md`, `docs/FORMATS.md` | 種族/マップ重みはDataから注入し、出現時に個体へ保持。 |
| 野生個体AI移動 | `kadoka_engine/hidden_enemy_controller.py` | `test_field_ai_movement.py`, `test_core.py`, `test_wild_enemy_rendering.py` | `docs/野生個体AI移動機能説明書.md` | randomは徘徊、idleは静止、chaseだけ視認時に加速追跡。占有と時間を管理。 |

| 追跡経路分散 | `kadoka_engine/{chase_traffic,hidden_enemy_controller}.py` | `test_chase_traffic.py`, `test_field_ai_movement.py` | `docs/追跡経路分散機能説明書.md` | 次3マスの予約、期限付き混雑履歴、範囲限定探索。実際の占有は厳守。 |

| 野生接触 / 戦闘復帰 | `apps/game.py`, `apps/{battle_session,battle_flow_service,battle_progression_service}.py` | `test_wild_encounter_flow.py`, `test_spawn_levels.py`, `test_core.py` | `docs/野生接触戦闘フロー機能説明書.md` | 開始成功後に接触個体を消費。種族/レベル範囲と終了結果を検証。 |

## GDScript移植（source試作）

| タスク種別 | 主実装 | 関連テスト | 仕様 | 境界 |
| --- | --- | --- | --- | --- |
| Godot起動 / JSON / マス移動 | `gdscript/{project.godot,engine/field_engine.gd,data/content_repository.gd,application/field_session.gd,application/field_application.gd,ui/}` | `tests/test_gdscript_bootstrap.py`, `gdscript/tests/{run_contracts,run_scene_smoke}.gd` | `gdscript/README.md`, `docs/移植境界機能説明書.md` | 正規data/assetsをread-only利用。純粋なFieldEngine入出力をPythonと比較。戦闘・AI・exportは未移植。 |
| Godotフィールド保存 / 復元 | `gdscript/{engine/field_save_contract.gd,data/json_documents.gd,data/field_save_store.gd,application/field_persistence.gd}` | `tests/test_gdscript_save.py`, `gdscript/tests/run_save_probe.gd` | `gdscript/README.md`, `docs/FORMATS.md` | F5/F9/起動復元。user://の名前付きフォルダ。既存個体/AI/items不変、破損・不正位置・置換失敗は上書き拒否。戦闘AI・スロットUIは未移植。 |
| Godot初期個体 / 所有一覧 | `gdscript/{engine/monster_record_contract.gd,data/monster_store.gd,application/owned_roster.gd,ui/roster_view.gd}` | `tests/test_gdscript_roster.py`, `gdscript/tests/run_roster_probe.gd` | `gdscript/README.md`, `docs/FORMATS.md` | 初回F5のみ初期2体/パーティ。F6は全保有/先頭4枠・縦スクロール。既存AI/JSON不変。不正個体は注意、AI判断を代替しない。 |
| Godot現在パーティ編成 | `gdscript/{engine/party_selection.gd,application/party_editor.gd,ui/party_view.gd,application/field_application.gd}` | `tests/test_gdscript_party.py`, `gdscript/tests/run_party_probe.gd` | `gdscript/README.md`, `docs/FORMATS.md` | 一覧のE/ボタン→下書き→保存/取消。4枠/重複/欠損検証、stateのpartyだけatomic更新、外部digest変更は拒否。個体/AI/items不変。 |
| Godotパーティプリセット | `gdscript/{engine/party_preset_contract.gd,data/party_preset_store.gd,application/party_presets.gd,ui/party_preset_view.gd}` | `tests/test_gdscript_presets.py`, `gdscript/tests/run_party_probe.gd` | `gdscript/README.md`, `docs/FORMATS.md` | 編成P/ボタン→無制限一覧/新規保存/下書き読込。既存JSON上書き/削除なし、欠損→null注意。読込だけでstate更新しない。更新/削除UIは未移植。 |
| Godot牧場台帳の導線 | `gdscript/application/field_application.gd`, `data/maps/{starting_town,starting_ranch}/map.json` | `tests/test_gdscript_ranch.py`, `gdscript/tests/run_party_probe.gd` | `gdscript/README.md`, `docs/ワークフロー/GDScript移行実装単位.md` | #218。open_manager→既存一覧/編成/プリセット。開くだけでは保存しない。台帳blockingとmodal入力停止。個体編集/AI変更は未移植。 |
| Godot基礎能力値 / Lv習得スキル | `gdscript/{engine/monster_progression.gd,engine/stat_numbers.gd,data/content_repository.gd,application/monster_progression.gd,application/owned_roster.gd,ui/roster_view.gd}` | `tests/test_gdscript_progression.py`, `gdscript/tests/run_progression_probe.gd` | `gdscript/README.md`, `docs/FORMATS.md` | #219。明示Lv表/順序付きlearnsetをPythonと比較。基礎契約は補正前のまま、#220が補正後を別に結合。不正表でも個体/AIは保持。成長式は生成時でruntime補完なし。 |
| Godot＋選択 / 装備制限・能力補正 | `gdscript/{engine/monster_modifiers.gd,engine/stat_numbers.gd,application/monster_reconstruction.gd,data/content_repository.gd,ui/roster_view.gd}` | `tests/test_gdscript_modifiers.py`, `gdscript/tests/run_modifiers_probe.gd` | `gdscript/README.md`, `docs/FORMATS.md` | #220。Python宣言順/重複除去/偶数丸め/装備側whitelistを比較。不明IDは理由付き保持、破損は補正結果なし。走査内I/O共用、次走査で更新。装備編集/戦闘効果は別単位。 |
| Godot通常攻撃 / 防御・会心数値 | `gdscript/engine/{attack_numbers,stat_numbers}.gd` | `tests/test_gdscript_attack_numbers.py`, `gdscript/tests/run_attack_probe.gd`, `test_core.py`のguard/critical | `docs/GDScript通常攻撃数値契約.md`, `gdscript/README.md` | #221。明示乱数/0方向切捨て/最低1、会心1/16と防御無視、guardは物理のみ。#220結果/許可装備のattack威力と固定追加。Scene/ターン/耐性/全スキル/AIは未接続。 |
| Godot固定モブ周期移動 / 占有 | `gdscript/engine/{fixed_mob_controller,field_random}.gd`, `gdscript/application/field_session.gd`, `gdscript/ui/field_view.gd` | `tests/test_gdscript_fixed_mobs.py`, `gdscript/tests/run_fixed_mobs_probe.gd` | `docs/GDScript固定モブ移動契約.md`, `gdscript/README.md` | #222。clock/RNG注入、周期/占有/初期配置/保存座標。実Godot性能ガードcheck_gdscript_fixed_mobs.py。会話は#223、野生/接触戦闘は未移植。 |
| Godot固定モブ会話 / 正面停止 | `gdscript/engine/{dialogue_deck,fixed_mob_controller}.gd`, `gdscript/application/{field_session,field_application}.gd` | `tests/test_gdscript_dialogue.py`, `gdscript/tests/run_fixed_mobs_probe.gd` | `docs/GDScript固定モブ会話契約.md` | #223。一巡/再抽選/境目の連続回避、正面対象、振り向き/停止/再開。不正デッキは理由付き。取得/戦闘/消滅は代用しない。 |
| Godot湧き場の暗号入力 | `gdscript/engine/password_session.gd`, `gdscript/ui/password_view.gd`, `gdscript/application/field_application.gd` | `tests/test_gdscript_password.py`, `gdscript/tests/run_password_probe.gd` | `docs/GDScript暗号入力契約.md` | #224。7文字/KANA/純粋状態と仮想・native UI、modal停止/再開。UIは保存しない。一致を#225へ接続。IME実入力/export未検証。 |
| Godotまる/かどか取得・保存 | `gdscript/{engine,application}/ghost_acquisition.gd`, `gdscript/engine/monster_record_contract.gd`, `gdscript/application/field_application.gd` | `tests/test_gdscript_ghost_acquisition.py`, `gdscript/tests/run_password_probe.gd` | `docs/GDScriptおばけ取得契約.md` | #225。不足だけLv1/source/初期AI、既存AI/party/位置保持、digest/再走査/部分保存と再試行。F5保存前は拒否。住処2体不変。全体原子性は主張しない。 |
| Godot教会の復活地点登録 | `gdscript/engine/revive_point_contract.gd`, `gdscript/application/{church_registration,field_application}.gd`, `gdscript/data/{content_repository,field_save_store}.gd` | `tests/test_gdscript_church.py`, `gdscript/tests/run_church_probe.gd` | `docs/GDScript教会登録契約.md` | #226。revive_pointだけを保存、通行/型/digest/リンク/置換/保存後照合。HP回復・実敗北復活は未接続。 |

## 更新ルール

- シンボルを絞るときだけ `docs/generated/REPO_MAP.md` の該当ファイル名を検索する。公開APIと引数の索引であり、詳細は対象コードを読む。
- `src/` の公開クラス・関数・メソッドを変更したら `python tools/code-docs/script/generate_repo_map.py` で再生成する。CIの `--check` が更新漏れを検出する。生成文書は手修正しない。

- 新領域を追加したら、対応する主実装・最小の関連テスト・仕様書・境界を1行で追加する。
- ファイルを移動したら、この表の参照先だけを更新する。説明書本文を複製しない。
- 1行で収まらない領域は、専用の機能説明書を作り、この表からそこへリンクする。
