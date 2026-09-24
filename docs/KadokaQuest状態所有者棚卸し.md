# KadokaQuestの状態・責務棚卸し（Issue #137）

## 範囲と結論

Issue #36の分割作業に先立つ現状確認。`src/kadoka_quest/apps/game.py` の `KadokaQuest` を対象とする。ゲーム規則、JSON形式、UI、実装の移動・削除はこのIssueでは変更しない。

棚卸し時点の27個のpropertyはすべて他オブジェクトへの互換viewであり、独立した状態コピーではない。以下はIssue #137時点の記録。「候補」は当時の移行方針であり、実施済みの差分は次節に記載する。

パスは特記以外 `src/kadoka_quest/` 相対。エンジン側は `src/kadoka_engine/`。公開シンボルの探索には [REPO_MAP](generated/REPO_MAP.md) を使い、実装を正とする。

## #138で実施した状態所有者の移行

- `apps/progress_session.py` の `ProgressSession.state` が読込中の進行データを所有する。再読込は辞書の置換であり、既存の `state_provider` は毎回この正本を参照する。保存形式・Storeの責務は変えない。
- `apps/field_session.py` の `FieldSession` がエンジン・主人公・固定モブ・見えない敵のControllerを所有する。マップとブロックはエンジンの参照を返すだけで、Sessionに別コピーを持たない。
- `enter_map()` はマップ参照の更新と主人公の座標・補間リセットを行う。ロードは `FieldDataLoader`、続く保存→見えない敵再配置→固定モブ再配置の順序は従来どおり `KadokaQuest.change_map()` が仲介する。
- `replace_field()` はControllerのエンジン参照も更新する。画像・通知・キー入力・保存処理はFieldSessionへ入れない。Sessionはpygame・ファイルI/Oに依存しない。

新たに `state / map_data / blocks / field / player_field / fixed_mobs / hidden_enemies` の7個を互換propertyにした。`KadokaQuest` に同名の独立した状態は残さず、従来の取得・代入は所有者へ渡す。既存27個と合わせて34個。戦闘状態は既に `BattleSession` が所有しているため移し直さない。呼出側の直接参照化と互換削除は #139 / #140で行う。

検証は `tests/test_session_ownership.py`。オブジェクトの同一性、マップ切替と保存・再配置、管理画面を閉じた後のパーティ再読込、既存戦闘Serviceが新しい所持品を保存することを確認する。個別テストで見つかった `application` の循環importは `RuntimeOrchestrator` の遅延公開で修正し、`tests/test_command_imports.py` で各コマンドの単独importと既存公開APIを別プロセスで検証する。

## 状態の正本と寿命

| 状態 / 現在の参照 | 現在の正本 | 移行先候補・保持する境界 |
| --- | --- | --- |
| `repository / monsters / states / parties / rng` | 各データサービス・乱数生成器 | `KadokaQuest` が依存を組み立てる。保存データそのものとサービス参照を区別する。 |
| `state`（進行フラグ・現在パーティ・保存座標等） | 読込中は `KadokaQuest.state`、永続化は `StateStore` | アプリセッションによる一元所有を候補とする。`FieldProgressStore` と `FieldPartyService` は引数を操作するだけで正本を持たない。 |
| `map_data / blocks / field` | `KadokaQuest` のロード済み定義と `FieldEngine` の参照 | フィールドセッション候補へ、ロード・マップ切替を一単位として移す。各Controllerに別の可変マップをコピーしない。 |
| `player_field` | `PlayerFieldController` の座標・向き・補間・長押し・次回tick | 所有者を維持。保存座標はチェックポイントであり、補間中の表示座標とは別。 |
| `fixed_mobs / hidden_enemies` | `FixedMobController` / `HiddenEnemyController` | 個体配置・移動・会話等の実行状態を維持。フィールドセッションは参照とライフサイクルの調整だけを持つ。 |
| `field_events / runtime` | `FieldEventApplication.last_effect` / `RuntimeOrchestrator.mode` 等 | 効果解決とコマンド配送・遷移検証を維持。画面側にゲーム規則を増やさない。 |
| `battle_session` | `BattleSession` の戦闘参照・演出・選択・時刻・終了状態 | 所有者を維持。HP/MPやターン規則は `BattleEngine`、恒久個体の保存は `MonsterStore`。 |
| `password_session` | `PasswordSession` の入力・メッセージ・開閉状態 | 所有者を維持。成功後の仲間獲得と進行保存は別の処理責務。 |
| `field_party_session / field_party_service` | 前者の選択位置・プリセットカーソル | サービスは保存・個体取得を仲介。現在パーティID列の正本は `state` のまま二重化しない。 |
| `character_images / manager_tool` | `CharacterImageProvider.cache` / `ManagerProcessService.process` | キャッシュはUI、外部管理画面のプロセス寿命はサービスに維持。 |
| `monster_import_service` | 個体取込の処理依存 | 通常獲得と旧模擬戦APIを区別。現行受付は `SimulationRosterService` を使う。 |
| `status` | `KadokaQuest` の共通表示メッセージ | 当面維持。必要なら単一の通知状態へ移す。各Sessionへ同じ文字列の可変コピーを配らない。 |
| `held_move_key` | `KadokaQuest` の旧pygameキー状態 | 入力境界への移行候補。通常の意味コマンドの方向保持は `PlayerFieldController` に残す。 |
| 模擬戦hookの動的属性 | `_simulation_facility_process / _simulation_facility_roster`、クラスの導入済みフラグ | `apps/simulation_facility_hooks.py` の遅延生成を明示的な組立へ移す候補。起動経路ごとのhook導入を確認してから変更する。 |

管理画面を閉じると `refresh_manager_if_closed()` は `self.state` を読込結果へ置換する。`BattleFlowDependencies.state_provider` の遅延参照を維持し、移行前の辞書をサービスへ固定して保存しない。マップ切替でも `FieldEngine` とControllerの参照更新、座標補間のリセット、モブ初期配置を一緒に検証する。

## 互換property 27個

方針: **維持**は仲介APIとして残す。**移行**は利用側を所有者へ移した後に削除を検討する。**候補**はリポジトリ内の属性利用を確認できなかったもの。外部MODの利用がない証明ではなく、直ちに削除しない。同名の他クラス属性やソース文字列を調べるテストは利用者に数えない。

| property | 現在の正本 | 主な利用側・注意点 | 方針 |
| --- | --- | --- | --- |
| `home_npcs` | `fixed_mobs.npcs` | フィールド描画、ゲーム内処理、coreテスト | 移行 |
| `hidden_monsters` | `hidden_enemies.monsters` | ゲーム内処理、coreテスト | 移行 |
| `selected_party` | `field_party_session.selected_index` | フィールド描画。setterの `select()` を維持 | 移行 |
| `preset_index` | `field_party_session.preset_cursor` | setterの非負整数化に注意 | 候補 |
| `player_x` | `player_field.x` | フィールド描画、評価ツール、ゲーム内処理、テスト | 移行 |
| `player_y` | `player_field.y` | 同上。表示補間の座標と混同しない | 移行 |
| `player_direction` | `player_field.direction` | フィールド描画、ゲーム内処理、テスト | 移行 |
| `player_movement` | `player_field.visual` | フィールド描画、テスト。読取専用view | 移行 |
| `held_move_direction` | `player_field.held_direction` | 旧長押し停止処理 | 移行 |
| `next_move_tick` | `player_field.next_move_tick` | coreテスト。setterで整数化 | 移行 |
| `mode` | `runtime.mode` | コマンド、hook、メインループ、評価ツール。setterは `transition_to()` で検証 | 維持 |
| `battle` | `battle_session.battle` | 描画、メインループ、戦闘開始、評価ツール、テスト | 移行 |
| `battle_finalized` | `battle_session.finalized` | 終了判定はSession/Service側で一度だけ行う | 候補 |
| `battle_selection` | `battle_session.selection` | 戦闘描画、テスト | 移行 |
| `auto_battle` | `battle_session.auto` | 戦闘描画、旧処理 | 移行 |
| `last_auto_tick` | `battle_session.last_auto_tick` | coreテスト | 移行 |
| `battle_playback` | `battle_session.playback` | 戦闘描画、メインループ、旧処理、テスト | 移行 |
| `battle_visible_log_count` | `battle_session.visible_log_count` | 戦闘描画、テスト | 移行 |
| `battle_next_log_tick` | `battle_session.next_log_tick` | coreテスト | 移行 |
| `battle_action_line` | `battle_session.action_line` | 戦闘描画 | 移行 |
| `battle_focus_id` | `battle_session.focus_id` | 戦闘描画、テスト | 移行 |
| `simulation` | `battle_session.simulation` | 戦闘描画、旧処理、テスト | 移行 |
| `fixed_mob_battle_id` | `battle_session.fixed_mob_id` | 帰還処理は `clear()` の結果辞書を使う | 候補 |
| `password_input` | `password_session.input_text` | 同モジュールの暗号描画、テスト | 移行 |
| `password_message` | `password_session.message` | 同モジュールの暗号描画 | 移行 |
| `image_cache` | `character_images.cache` | 読取専用view | 候補 |
| `manager_process` | `manager_tool.process` | 管理プロセス操作はサービス側 | 候補 |

## 処理の責務と残す仲介

| 現在の処理群 | 移行・維持する所有者と制約 |
| --- | --- |
| `__init__` とモジュールの `main` | 依存の組立、pygameループ、入力・描画の接続を維持。Sessionにpygameイベントを渡さない。 |
| `party`、パーティ選択・プリセット・作戦・AIリセット | `FieldPartyService / FieldPartySession` を正規経路とする。個体保存はStoreへ。 |
| `move / change_map / save_position`、長押し、衝突、前方マス、踏んだイベント | フィールドセッション候補で寿命を調整。移動計算は既存Controller、永続化は `FieldProgressStore`。 |
| `interact / use_field_requirement`、暗号開閉 | `FieldEventApplication` のplain effectを仲介。会話中の停止・調べる/触れる条件を保つ。 |
| `reacquire_ghosts / field_pickup` | 獲得・進行処理サービスへの移行候補。種族条件、乱数、重複獲得防止、進行保存をUIから分離する。 |
| `make_wild / start_wild_battle` | 遭遇生成処理への移行候補。乱数・個体ID生成を保ち、戦闘開始と画面切替は仲介する。 |
| 戦闘コマンド、演出、オート、終了確定、経験値 | 正規経路は `BattleCommandApplication -> BattleFlowService / BattleProgressionService / BattleSession`。旧 `handle_battle_command / award_experience / finalize_battle_if_needed` 等には処理が残るため、単なる転送メソッドとして削除しない。 |
| `return_to_field / revive_at_church` | `BattleSession.clear()` の結果から、教会復活・固定モブ消滅・フィールド再開を仲介。複数領域の境界処理は無理に戦闘Sessionへ移さない。 |
| 固定モブの初期配置・会話・消滅、見えない敵の生成・追跡・遭遇 | 既存Controllerを維持し、進行フラグだけStoreと調整。 |
| `character_image`、暗号画面描画 | 画像は `CharacterImageProvider`。モジュール関数 `draw_password / password_controls` はUI側へ移す候補（クラスのメソッドではない）。 |
| `open_manager / refresh_manager_if_closed` | プロセス寿命は `ManagerProcessService`、閉じた後の状態再読込はセッション間の仲介。 |
| 旧 `start_simulation` と現行受付hook | 旧 `MonsterImportService` 経路と現行 `SimulationRosterService` 経路を区別。模擬戦のAI・報酬非保存を維持。 |

現状の `BattleRenderer.draw()` の引数は `KadokaQuest` であり、引数名が `session` でも `BattleSession` の直接参照ではない。画像取得・repositoryへの参照もあるため、戦闘Sessionだけを渡す変更では足りない。描画に必要な読み取り状態と画像取得依存を明示して渡す。フィールド描画と評価ツールも同様に、必要な境界だけを移す。

## 後続Issueの実行順と検証

1. **#138 状態所有者の移行**: まず未分離のフィールド寿命・進行状態の単位を選ぶ。Controllerの状態はコピーせず集約し、互換viewを残す。状態再読込・マップ切替・モブ再配置が同じ正本を見ることを検証する。
2. **#139 呼出側の移行**: 描画、コマンド、評価ツール、旧直接呼出テストを所有者へ移す。旧戦闘ロジックは正規Serviceへの委譲と挙動比較を先に行う。依存循環を作らず、経過時刻は外から渡す。
3. **#140 互換窓口の整理**: 公開利用箇所を再検索し、候補5個を含め、移行できた窓口だけ削除する。外部利用の互換方針を決めてから削除する。`mode` の遷移検証を迂回しない。

優先テスト: `tests/test_core.py`、`tests/test_battle_flow_service.py`、`tests/test_legacy_battle_command_adapter.py`、`tests/test_simulation_facility.py`、`tests/test_field_use_events.py`、`tests/test_game_evaluator.py`。起動経路は `tests/test_app_smoke.py` も確認する。実装変更時はAGENTSの整合性・UPD・性能・全体テストの条件に従う。

この棚卸しの受入確認は、実コードとの設計照合と、全propertyが表に一度ずつ載ることの確認。後続実装の完了や外部MOD互換を保証するものではない。
