# CODEMAP

実装タスクでは、最初にこの表の該当行だけを読む。詳細な仕様をここへ複写せず、リンク先を更新して索引を保つ。

| タスク種別 | 主実装 | 関連テスト | 仕様書・データ | 境界 |
| --- | --- | --- | --- | --- |
| 戦闘 / AI | `core/battle.py`, `core/{ai,battle_inference,battle_learning,battle_context}.py`, `apps/{battle_session,battle_command_app,ai_inspector}.py` | `test_core.py`, `test_ai_inspector.py`, `test_battle_decision_explanation.py` | `docs/戦闘責務分離機能説明書.md`, `docs/状況学習機能説明書.md`, `docs/個体AI可視化機能説明書.md` | 戦闘規則・推論・学習は分離し、描画はUIへ渡す。 |
| フィールド | `kadoka_engine/field_engine.py`, `apps/{game,field_command_app,field_event_app}.py`, `data/{field_data,field_progress}.py` | `test_core.py`, `test_field_use_events.py` | `docs/フィールドエンジン分離第2段階機能説明書.md`, `docs/FORMATS.md` | `kadoka_engine` はpygame・リポジトリ非依存。 |
| fixed mob / 野生敵 | `kadoka_engine/{fixed_mob_controller,hidden_enemy_controller,player_field_controller}.py` | `test_core.py` | `docs/フィールドアクター責務分離機能説明書.md`, `docs/FORMATS.md` | 個体の移動・会話状態はコントローラーが所有する。 |
| モンスター / 個体 / パーティ | `core/monster.py`, `data/{monsters,parties,species_creator,developer_monster_creator}.py`, `apps/{monster_editor,field_party_service,field_party_session,monster_import_service}.py` | `test_core.py` | `docs/モンスター種族新規作成機能説明書.md`, `docs/外部個体取込責務分離機能説明書.md`, `docs/FORMATS.md` | 種族定義と個体保存を混在させない。 |
| map / block | `data/{repository,map_presets}.py`, `apps/{map_editor,block_editor}.py` | `test_core.py`, `test_map_spawn_ranges.py`, `test_field_use_events.py` | `docs/マッププリセット機能説明書.md`, `docs/出現モンスターレベル範囲機能説明書.md`, `docs/FORMATS.md` | マップJSONは直接編集・直接読込する。 |
| editor / ドット絵 | `ui/{pixel_editor,pixel_operations}.py`, `apps/{monster_editor,block_editor,map_editor}.py` | `test_core.py`, `test_pixel_editor_canvas.py` | `docs/ドットエディター画像編集機能説明書.md`, `docs/可変キャンバス機能説明書.md` | 共通ピクセルエディタに対象データだけを渡す。 |
| runtime command | `application/{app_command,command_bus,runtime_orchestrator}.py`, `apps/*_command_app.py` | `test_core.py` | `docs/コマンド駆動アプリ基盤機能説明書.md`, `docs/実行時オーケストレーター機能説明書.md` | 画面間通信はJSON互換の `AppCommand` のみ。 |
| save / data | `data/{savedata,state,jsonio,battle_data,data_validator}.py` | `test_core.py`, `test_data_validator.py` | `docs/FORMATS.md`, `docs/MODデータ一括検証機能説明書.md` | 保存は個体フォルダ単位。JSONキー変更時はFORMATSを更新。 |
| UI / input | `ui/{battle_renderer,field_renderer,character_image_provider,runtime_input_adapter,runtime_mouse_adapter}.py`, `apps/game.py` | `test_core.py`, `test_app_smoke.py` | `docs/実行時入力アダプター責務分離機能説明書.md`, `docs/実行時マウスアダプター責務分離機能説明書.md` | UIは描画・入力変換だけでゲーム規則を決めない。 |
| 開発補助 | `scripts/remote_change_summary.py` | `test_remote_change_summary.py` | `docs/リモート変更要約ツール機能説明書.md` | Git履歴を読むだけで、マージや保存データ変更は行わない。 |

## 更新ルール

- 新領域を追加したら、対応する主実装・最小の関連テスト・仕様書・境界を1行で追加する。
- ファイルを移動したら、この表の参照先だけを更新する。説明書本文を複製しない。
- 1行で収まらない領域は、専用の機能説明書を作り、この表からそこへリンクする。
