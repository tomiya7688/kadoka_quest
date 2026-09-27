# CODEMAP

実装タスクでは、最初にこの表の該当行だけを読む。詳細な仕様をここへ複写せず、リンク先を更新して索引を保つ。

`core/`, `apps/`, `data/`, `ui/`, `application/`, `developer/` は `src/kadoka_quest/` からの相対パス。`kadoka_engine/` は `src/`、`test_*.py` は `tests/` からの相対パス。波括弧は列挙の省略表記。
変更箇所の行にある関連テストを最初に実行する。共通契約を変更した場合はサブシステムまたは全体へ広げる。追加探索が必要な場合だけ `docs/context/ROUTES.md` を参照する。

| タスク種別 | 主実装 | 関連テスト | 仕様書・データ | 境界 |
| --- | --- | --- | --- | --- |
| ゲーム状態 / 責務移行 | `apps/{game,progress_session,field_session,battle_session,field_party_session,password_session}.py` | `test_session_ownership.py`, `test_core.py`, `test_battle_flow_service.py`, `test_simulation_facility.py` | `docs/KadokaQuest状態所有者棚卸し.md` | 正本・互換view・保存時点のコピーを区別し、所有者→呼出側→互換削除の順に移す。 |
| 戦闘 / AI | `core/battle.py`, `core/{ai,battle_inference,battle_learning,battle_context}.py`, `apps/{battle_session,battle_command_app,ai_inspector}.py` | `test_core.py`, `test_ai_inspector.py`, `test_battle_decision_explanation.py` | `docs/戦闘責務分離機能説明書.md`, `docs/状況学習機能説明書.md`, `docs/個体AI可視化機能説明書.md` | 戦闘規則・推論・学習は分離し、描画はUIへ渡す。 |
| フィールド | `kadoka_engine/field_engine.py`, `apps/{game,field_command_app,field_event_app}.py`, `data/{field_data,field_progress}.py` | `test_core.py`, `test_field_use_events.py` | `docs/フィールドエンジン分離第2段階機能説明書.md`, `docs/FORMATS.md` | `kadoka_engine` はpygame・リポジトリ非依存。 |
| fixed mob / 野生敵 | `kadoka_engine/{fixed_mob_controller,hidden_enemy_controller,player_field_controller}.py` | `test_core.py` | `docs/フィールドアクター責務分離機能説明書.md`, `docs/FORMATS.md` | 個体の移動・会話状態はコントローラーが所有する。 |
| モンスター / 個体 / パーティ | `core/monster.py`, `data/{monsters,parties,species_creator,developer_monster_creator}.py`, `apps/{ranch_manager,monster_editor,field_party_service,field_party_session,monster_import_service}.py` | `test_core.py`, `test_player_distribution_boundary.py` | `docs/モンスター種族新規作成機能説明書.md`, `docs/外部個体取込責務分離機能説明書.md`, `docs/FORMATS.md` | 種族定義と個体保存を混在させない。 |
| 模擬戦施設 | `apps/{simulation_manager,simulation_roster_service,simulation_facility_hooks}.py` | `test_simulation_facility.py`, `test_field_command_legacy_cleanup.py` | `docs/模擬戦会館機能説明書.md` | 現行Player導線。旧 `simulation_facility_service.py` は受付の実装ではない。 |
| 戦闘進行 / コマンド | `apps/{battle_flow_service,battle_flow_dependencies,battle_progression_service,battle_command_app,legacy_battle_command_adapter}.py` | `test_battle_flow_service.py`, `test_legacy_battle_command_adapter.py` | `docs/戦闘セッション責務分離機能説明書.md` | 入力ルーティング・進行・永続化の変更箇所を分けて辿る。 |
| map / block | `data/{repository,map_presets}.py`, `apps/{map_editor,block_editor}.py` | `test_core.py`, `test_map_spawn_ranges.py`, `test_metal_spawn_tables.py`, `test_field_use_events.py` | `docs/マッププリセット機能説明書.md`, `docs/出現モンスターレベル範囲機能説明書.md`, `docs/FORMATS.md` | マップJSONは直接編集・直接読込する。 |
| editor / ドット絵 | `ui/{pixel_editor,pixel_operations}.py`, `apps/{monster_editor,block_editor,map_editor}.py` | `test_core.py`, `test_pixel_editor_canvas.py` | `docs/ドットエディター画像編集機能説明書.md`, `docs/可変キャンバス機能説明書.md` | 共通ピクセルエディタに対象データだけを渡す。 |
| runtime command | `application/{__init__,app_command,command_bus,runtime_orchestrator}.py`, `apps/*_command_app.py` | `test_command_imports.py`, `test_core.py` | `docs/コマンド駆動アプリ基盤機能説明書.md`, `docs/実行時オーケストレーター機能説明書.md` | 画面間通信はJSON互換の `AppCommand` のみ。 |
| save / data | `data/{savedata,state,jsonio,battle_data,data_validator}.py` | `test_core.py`, `test_data_validator.py` | `docs/FORMATS.md`, `docs/MODデータ一括検証機能説明書.md` | 保存は個体フォルダ単位。JSONキー変更時はFORMATSを更新。 |
| UI / input | `ui/{battle_renderer,field_renderer,character_image_provider,runtime_input_adapter,runtime_mouse_adapter}.py`, `apps/game.py` | `test_session_renderers.py`, `test_core.py`, `test_app_smoke.py` | `docs/実行時入力アダプター責務分離機能説明書.md`, `docs/実行時マウスアダプター責務分離機能説明書.md`, `docs/KadokaQuest状態所有者棚卸し.md` | 描画はSessionと画像Providerを受け取り、ゲーム全体・repositoryを参照しない。 |
| Developer / 配布 | `developer/{workflow,build_core,distribution_smoke}.py`, `apps/developer_launcher.py` | `test_developer_workflow.py`, `test_distribution_process.py`, `test_distribution_paths.py` | `docs/Developer環境説明書.md` | PlayerとDeveloperの起動・ビルドを分離する。 |
| 開発補助 / コンテキスト | `tools/remote-context/script/sync_remote_context.py`, `tools/affected-tests/script/affected_tests.py`, `tools/import-map/script/python_import_map.py` | `test_remote_context.py`, `test_context_tools.py`, `test_context_router.py` | `tools/README.md`, `docs/context/WORKFLOW.md` | 要約は探索の案内。実装とIssueを正とする。 |
| CI / 整合性 | `tools/project-integrity/script/check_project_rules.py`, `developer/project_validator.py`, `.github/workflows/python-app.yml` | `test_project_integrity.py`, `test_data_validator.py` | `docs/CODING_RULES.md` | 機械検証の規則を仕様本文へ複写しない。 |

## 敵の表示・逃走・報酬・出現Lv

| タスク種別 | 主実装 | 関連テスト | 仕様書 | 境界 |
| --- | --- | --- | --- | --- |
| 地域別逃走 | `core/{battle,combatant}.py`, `data/battle_data.py`, `apps/{game,battle_progression_service}.py` | `test_enemy_flee.py` | `docs/敵の地域別逃走機能説明書.md` | 地域は戦闘開始時に渡す。個体JSONへ保存しない。 |
| 撃破経験値 | `core/battle_rewards.py`, `data/battle_data.py`, `apps/{game,battle_progression_service}.py` | `test_battle_rewards.py`, `test_enemy_flee.py` | `docs/種族別撃破経験値機能説明書.md`, `docs/FORMATS.md` | 種族係数と味方の成長を分離。計算は共通関数、保存はStore。 |
| メタル域の動的Lv | `core/spawn_levels.py`, `apps/game.py` の `make_wild` | `test_spawn_levels.py`, `test_map_spawn_ranges.py` | `docs/メタルエリア動的レベル機能説明書.md` | 遭遇時の先頭4体で計算し、通常域・所有個体を書き換えない。 |
| 野生敵表示 | `ui/field_renderer.py`, `kadoka_engine/hidden_enemy_controller.py` | `test_wild_enemy_rendering.py`, `test_session_renderers.py` | `docs/野生モンスター可視化機能説明書.md` | 描画は既存個体の位置と向きだけを読む。 |

## 更新ルール

- シンボルを絞るときだけ `docs/generated/REPO_MAP.md` の該当ファイル名を検索する。公開APIと引数の索引であり、詳細は対象コードを読む。
- `src/` の公開クラス・関数・メソッドを変更したら `python tools/code-docs/script/generate_repo_map.py` で再生成する。CIの `--check` が更新漏れを検出する。生成文書は手修正しない。

- 新領域を追加したら、対応する主実装・最小の関連テスト・仕様書・境界を1行で追加する。
- ファイルを移動したら、この表の参照先だけを更新する。説明書本文を複製しない。
- 1行で収まらない領域は、専用の機能説明書を作り、この表からそこへリンクする。
