# 0.ver.mdについて

0.は編集しないこと
バージョンアップ時にはここを更新すること

書き方
```markdown
    # 1. サンプル
        helloworldを出力する機能を追加
        変更したファイル
            start.py
            開発予定.md
            仕様書.md
        追加したファイル
            hello.py

```

# 40. AGENTS段階的読込ルーター

`AGENTS.md` にContext Budget原則を明記し、最初にIssueとCODEMAPの該当1行だけを読む運用へ固定した。CODEMAPが戦闘、フィールド、エディタ、データなど領域ごとの次の資料を案内し、全体仕様の常読を防ぐ。

更新したファイル

- `AGENTS.md`
- `docs/ver.md`
- `tests/test_project_metadata.py`

# 39. リモート変更要約ツール

作業開始時にリモート変更を圧縮して確認する `tools/remote-context/script/sync_remote_context.py` を追加した。fetch後にコミット、変更ファイル、統計、境界付き差分を表示し、マージ判断のための再探索を減らす。

追加したファイル

- `tools/remote-context/script/sync_remote_context.py`

更新したファイル

- `docs/CODEMAP.md`
- `scripts/run_python.bat`
- `docs/ver.md`

# 38. 1作業単位のワークフロー

`docs/ワークフロー/ワークフロー.md` を、1つのIssueまたは独立作業を完了するまでの手順へ整理した。開始時にリモート変更を取得・確認・安全に取り込み、未コミット変更を保護してから実装する流れを明記している。

更新したファイル

- `docs/ワークフロー/ワークフロー.md`
- `docs/ver.md`

# 37. タスク別CODEMAP

実装タスクから主実装・関連テスト・仕様書・境界を一度に引ける `docs/CODEMAP.md` を追加した。詳細仕様を複製せず、ファイル移動時に索引だけを更新できる軽量な一覧にしている。

追加したファイル

- `docs/CODEMAP.md`

更新したファイル

- `AGENTS.md`
- `docs/ver.md`

# 36. 実装Issueの自己完結テンプレート

GitHub Issue Forms に、Codexへ渡す実装タスク用の短いテンプレートを追加した。目的・対象・変更しない範囲・受け入れ条件・検証を必須にし、既存挙動・データ契約・移植境界などは必要な場合だけ記入する。

追加したファイル

- `.github/ISSUE_TEMPLATE/implementation.yml`

更新したファイル

- `docs/Codexコンテキスト運用.md`
- `docs/ver.md`

# 35. Codexコンテキスト削減

毎回読み込む `AGENTS.md` を不変の作業規則・アーキテクチャ境界・主要データ契約だけに圧縮し、詳細仕様を必要時だけ読む運用へ変更した。

変更したファイル

- `AGENTS.md`
- `docs/ver.md`

追加したファイル

- `docs/Codexコンテキスト運用.md`

# 34. 戦闘中のAI判断ログ

AIがスキルを選んだ直後に、現在の戦術と選択スキルに実際に影響した習熟・状況別学習を戦闘ログへ表示するようにした。説明生成は選択処理と分離され、AIの選択・学習・保存内容を変更しない。

変更したファイル

- `docs/ver.md`
- `src/kadoka_quest/core/battle.py`

追加したファイル

- `docs/戦闘AI判断ログ機能説明書.md`
- `src/kadoka_quest/core/battle_decision_explanation.py`
- `tests/test_battle_decision_explanation.py`

# 33. 個体AIの可視化

個体・パーティ管理画面に、AIプロファイル、行動指針、学習済みスキル傾向、状況別の学習傾向を表示するようにした。表示用の集計は保存データを変更せず、絶対値の大きい傾向から最大3件を示す。

変更したファイル

- `docs/ver.md`
- `src/kadoka_quest/apps/manage.py`

追加したファイル

- `src/kadoka_quest/apps/ai_inspector.py`
- `tests/test_ai_inspector.py`

# 32. ヘッドレスゲーム評価

未訪問マップを優先する幅優先のフィールド探索計画、意味コマンド経由の自動操作、戦闘・暗号画面・到達不能・停止理由を残すJSON評価ログを追加した。既定の評価セーブはレポート横の隔離フォルダで、通常セーブを変更しない。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/launcher.py`

追加したファイル

- `game_evaluator.py`
- `docs/ゲーム評価機能説明書.md`
- `src/kadoka_quest/devtools/evaluation_log.py`
- `src/kadoka_quest/devtools/field_explorer.py`
- `src/kadoka_quest/devtools/game_evaluator.py`
- `tests/test_game_evaluator.py`

# 31. バランス調整ツール

同レベルの種族ペアをAI学習なしで再現可能に大量模擬戦させ、対戦履歴、勝率、順位、Lv100能力値を基準にした能力値・耐性の改善候補をJSON出力するCLIを追加した。分析結果は助言専用で、ゲームデータを自動変更しない。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/ver.md`
- `docs/評価/評価者からのフィードバック.md`
- `src/kadoka_quest/apps/launcher.py`

追加したファイル

- `balance_analyzer.py`
- `docs/バランス調整ツール機能説明書.md`
- `src/kadoka_quest/devtools/__init__.py`
- `src/kadoka_quest/devtools/balance_analyzer.py`
- `tests/test_balance_analyzer.py`

# 30. マップ出現モンスターレベル範囲

マップエディタに種族ごとの出現最小Lv・最大Lvを編集する画面を追加。未登録種族は重み10で追加し、既存出現項目は範囲だけを更新する。出現Lvは1〜100かつ最小値以下最大値のJSON契約として、データ検証も追加した。ボールスライムは初期獲得専用のため、出現設定とデータ検証の両方で拒否する。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/ver.md`
- `docs/評価/評価者からのフィードバック.md`
- `src/kadoka_engine/data_validator.py`
- `src/kadoka_quest/apps/map_editor.py`
- `tests/test_data_validator.py`

追加したファイル

- `docs/出現モンスターレベル範囲機能説明書.md`
- `tests/test_map_spawn_ranges.py`

# 1. マッププリセット

マップエディターへ、現在のマップをプリセットとして保存する機能、現在のマップへ適用する機能、プリセットから新規マップを作成する機能を追加。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/map_editor.py`
- `src/kadoka_quest/data/repository.py`
- `tests/test_core.py`

追加したファイル

- `docs/マッププリセット機能説明書.md`
- `src/kadoka_quest/data/map_presets.py`

# 2. データクリエイター

種族、レベル、個体名、任意の個体IDを指定して、既存形式のモンスター個体を生成する開発ツールを追加。現在のセーブ、獲得用、模擬戦用の3種類の生成先に対応。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/launcher.py`
- `src/kadoka_quest/data/monsters.py`
- `tests/test_app_smoke.py`
- `tests/test_core.py`

追加したファイル

- `data_creator.py`
- `docs/データクリエイター機能説明書.md`
- `src/kadoka_quest/apps/data_creator.py`
- `src/kadoka_quest/data/developer_monster_creator.py`

# 3. 状況をもとにした学習

個体AIへ、自分のHP、味方の損耗、MP、人数差、敵の残HP、敵とのレベル差を使う軽量な状況別学習を追加。模擬戦の学習禁止とAIリセットの進行保持は維持。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/core/ai.py`
- `src/kadoka_quest/core/battle.py`
- `tests/test_core.py`

追加したファイル

- `docs/状況学習機能説明書.md`
- `src/kadoka_quest/core/battle_context.py`

# 4. 移動の滑らかさ

マス単位の入力・当たり判定・イベント・セーブを維持したまま、主人公と固定モブの表示位置およびカメラ追従を短時間補間する機能を追加。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/移動補間機能説明書.md`
- `src/kadoka_quest/core/grid_movement.py`

# 5. 移植可能な処理・画面・データ境界

フィールドの通行、方向、キャラクター衝突、イベント検索、視線判定をpygame非依存の処理層へ移動。フィールド描画をUI層へ分離し、GDScript／Lua移植時に使う通常データだけの入出力契約を仕様化。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/移植境界機能説明書.md`
- `src/kadoka_quest/core/field_engine.py`
- `src/kadoka_quest/ui/field_renderer.py`

# 6. モンスター種族の新規作成

モンスターエディターの種族一覧先頭へ「＋ 新規作成」を追加。レベル1～100、習得スキル、＋1～＋10を含む4 JSONと、戦闘・前後左右の64×64 PNG 5枚を一括生成する。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/monster_editor.py`
- `tests/test_core.py`

追加したファイル

- `docs/モンスター種族新規作成機能説明書.md`
- `src/kadoka_quest/data/species_creator.py`

# 7. ドットエディターの編集可能パレット

モンスターとブロックで共有するドットエディターへ、`#RRGGBB` によるペン色の追加、重複色の選択、選択色の削除を追加。最大16色とし、透明色および最後の不透明色は削除できないようにした。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/block_editor.py`
- `src/kadoka_quest/apps/monster_editor.py`
- `src/kadoka_quest/ui/pixel_editor.py`
- `tests/test_core.py`

追加したファイル

- `docs/ドットエディターパレット機能説明書.md`

# 8. ドットエディターの画像編集基本機能

共通ドットエディターへ、輪郭内の連続領域を塗るバケツ、しきい値指定の近似色統合、縦横比維持・最近傍縮小・中央配置による画像読込を追加。モンスターとブロックの両画面で利用でき、各操作をCtrl+Zで戻せるようにした。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/block_editor.py`
- `src/kadoka_quest/apps/monster_editor.py`
- `src/kadoka_quest/ui/pixel_editor.py`
- `tests/test_core.py`

追加したファイル

- `docs/ドットエディター画像編集機能説明書.md`
- `src/kadoka_quest/ui/pixel_operations.py`

# 9. コマンド駆動アプリ基盤 第1段階

pygame入力ループからフィールド・戦闘・暗号入力処理への直接呼出しを廃止し、`target / action / payload` の共通コマンドへ変換して対象アプリへ配送する基盤を追加。移動方向もキーコードではなく意味名で渡し、各コマンドアプリをpygame非依存にした。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `src/kadoka_quest/application/__init__.py`
- `src/kadoka_quest/application/app_command.py`
- `src/kadoka_quest/application/command_bus.py`
- `src/kadoka_quest/apps/field_command_app.py`
- `src/kadoka_quest/apps/battle_command_app.py`
- `src/kadoka_quest/apps/password_command_app.py`

# 10. 戦闘責務分離 第2段階

戦闘画面描画、計算、AI学習、AI推論、データ読込を独立モジュールへ分離。BattleEngineは各責務を注入可能にし、通常戦だけが学習する契約と既存の公開関数・カタログ属性を維持した。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/game.py`
- `src/kadoka_quest/core/ai.py`
- `src/kadoka_quest/core/battle.py`
- `tests/test_core.py`

追加したファイル

- `docs/戦闘責務分離機能説明書.md`
- `src/kadoka_quest/core/battle_inference.py`
- `src/kadoka_quest/core/battle_learning.py`
- `src/kadoka_quest/core/combatant.py`
- `src/kadoka_quest/data/battle_data.py`
- `src/kadoka_quest/ui/battle_renderer.py`

# 11. フィールドアクター責務分離 第3段階

固定モブの実行時状態・会話・占有・移動と、非表示エンカウント敵の出現・視認・追跡・徘徊を、pygameおよび保存I/Oに依存しない2つの状態機械へ分離。ゲーム本体の既存公開メソッドとリスト属性は互換窓口として維持した。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/フィールドアクター責務分離機能説明書.md`
- `src/kadoka_quest/core/fixed_mob_controller.py`
- `src/kadoka_quest/core/hidden_enemy_controller.py`

# 12. フィールドセッション責務分離 第4段階

主人公の整数座標・向き・長押し移動・表示補間、NPC/イベントの効果解釈、現在地・復活地点・拾得品・進行状態の保存、マップ/ブロック読込と入口座標補正を4つの独立責務へ分離。既存のゲーム本体属性とメソッドは互換窓口として維持した。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/フィールドアクター責務分離機能説明書.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/フィールドセッション責務分離機能説明書.md`
- `src/kadoka_quest/apps/field_event_app.py`
- `src/kadoka_quest/core/player_field_controller.py`
- `src/kadoka_quest/data/field_data.py`
- `src/kadoka_quest/data/field_progress.py`

# 13. 実行時オーケストレーター 第5段階

画面モード、共通コマンドバス、実行時アプリ登録、フィールド効果から別アプリへの配送を `RuntimeOrchestrator` へ集約。管理画面にも独立コマンド境界を追加し、固定モブ実体などの実行時オブジェクトをコマンドpayloadへ含めない契約に変更した。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/フィールドセッション責務分離機能説明書.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/application/__init__.py`
- `src/kadoka_quest/apps/battle_command_app.py`
- `src/kadoka_quest/apps/field_command_app.py`
- `src/kadoka_quest/apps/field_event_app.py`
- `src/kadoka_quest/apps/game.py`
- `src/kadoka_quest/apps/password_command_app.py`
- `tests/test_core.py`

追加したファイル

- `docs/実行時オーケストレーター機能説明書.md`
- `src/kadoka_quest/application/runtime_orchestrator.py`
- `src/kadoka_quest/apps/manager_command_app.py`

# 14. 戦闘セッション責務分離 第6段階

戦闘の開始・終了、コマンド選択、時間差ログ演出、行動中個体、オート戦闘時刻、通常戦・模擬戦、固定モブ戦の識別をpygame非依存の `BattleSession` へ集約。戦闘計算、AI推論・学習、保存、描画との境界および既存公開属性を維持した。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/実行時オーケストレーター機能説明書.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/battle_command_app.py`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/戦闘セッション責務分離機能説明書.md`
- `src/kadoka_quest/apps/battle_session.py`

# 15. 暗号入力セッション責務分離 第7段階

水の湧き場の仮想キーボードについて、許可文字、7文字上限、入力文字列、案内・誤答メッセージ、正解判定、取消状態をpygame非依存の `PasswordSession` へ集約。正解後のまる・かどか獲得と進行保存はゲーム進行側に維持した。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/実行時オーケストレーター機能説明書.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/暗号入力セッション責務分離機能説明書.md`
- `src/kadoka_quest/apps/password_session.py`

# 16. キャラクター画像取得責務分離 第8段階

種族定義からの戦闘立ち絵・前後左右フィールド画像のパス解決、RGBA PNG読込、フィールド透明余白の切詰め、縦横比を維持した最近傍拡大、取得失敗を含むSurfaceキャッシュを `CharacterImageProvider` へ集約した。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/実行時オーケストレーター機能説明書.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/キャラクター画像取得責務分離機能説明書.md`
- `src/kadoka_quest/ui/character_image_provider.py`

# 17. 管理ツールプロセス責務分離 第9段階

牧場管理ツールのPythonプロセス生成、二重起動防止、実行中判定、終了通知の一度だけの消費を `ManagerProcessService` へ集約。ゲーム側は意味結果の表示と終了後のセーブ再読込だけを担当するようにした。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/実行時オーケストレーター機能説明書.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/管理ツールプロセス責務分離機能説明書.md`
- `src/kadoka_quest/apps/manager_process_service.py`

# 18. 実行時入力アダプター責務分離 第10段階

pygameの終了・キーダウン・キーアップを、画面モードと戦闘状態に応じたプレーンな意味コマンド要求へ変換する `RuntimeInputAdapter` を追加。メインループからフィールド・戦闘・暗号入力のキー分岐を除去した。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/実行時オーケストレーター機能説明書.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/実行時入力アダプター責務分離機能説明書.md`
- `src/kadoka_quest/ui/runtime_input_adapter.py`

# 19. 実行時マウスアダプター責務分離 第11段階

- パスワード画面の仮想キーボード、消去、決定、取消の当たり判定を `RuntimeMouseAdapter` へ分離
- 戦闘画面の戦う、スカウト、道具、逃げるの当たり判定を同じアダプターへ分離
- 左クリックだけを意味コマンド要求へ変換し、右クリック、戦闘終了後、演出中は操作要求を生成しない
- `Button` は描画用として維持し、ゲームループからコールバック実行と画面固有 `collidepoint` を除去
- 保存JSONの形式変更なし

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/実行時オーケストレーター機能説明書.md`
- `docs/実行時入力アダプター責務分離機能説明書.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/実行時マウスアダプター責務分離機能説明書.md`
- `src/kadoka_quest/ui/runtime_mouse_adapter.py`

# 20. フィールドパーティ選択状態責務分離 第12段階

- `FieldPartySession` を追加し、フィールドで選択中のパーティ枠と次のプリセット巡回位置を分離
- 選択枠を0～3に制限し、現在のパーティ人数に合わせて従来どおり循環補正
- `FieldCommandApplication` の `party.select` はゲーム属性へ直接代入せず公開操作を呼ぶ
- `game.py` の既存 `selected_party / preset_index` APIは互換プロパティとして維持
- パーティ、プリセット、個体AIの保存JSON形式は変更なし

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/ver.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/実行時オーケストレーター機能説明書.md`
- `src/kadoka_quest/apps/field_command_app.py`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/フィールドパーティ選択状態責務分離機能説明書.md`
- `src/kadoka_quest/apps/field_party_session.py`

# 21. フィールドパーティ永続操作責務分離 第13段階

- `FieldPartyService` を追加し、プリセット保存・順次読込・作戦変更・AIリセットをゲーム本体から分離
- 既存の `FieldPartySession` と `PartyStore / StateStore / MonsterStore` を依存注入して調停
- パーティなし・プリセットなしの場合は従来どおり状態を変更しない
- 時刻供給を差し替え可能にし、プリセット名生成を決定的にテスト
- 保存JSONの場所、キー、最大4枠、無制限プリセット規則は変更なし

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/ver.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/実行時オーケストレーター機能説明書.md`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/フィールドパーティ永続操作責務分離機能説明書.md`
- `src/kadoka_quest/apps/field_party_service.py`

# 22. 外部個体取込責務分離 第14段階

- `MonsterImportService` を追加し、取得用フォルダ再走査と模擬戦用フォルダ読込をゲーム本体から分離
- 模擬戦の `BattleEngine` を必ず `learning_enabled=False` で生成
- 外部個体なし・不正個体では戦闘を開始せず従来の案内を返す
- ゲーム本体はサービス結果を受け、戦闘セッション開始と画面遷移だけを担当
- `monster.json / ai.json`、取得先、模擬戦非コピー規則は変更なし
- Iドライブ上のPythonを使用せず、CドライブのPython 3.13.5とpygame-ce 2.5.8で検証

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/ver.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/実行時オーケストレーター機能説明書.md`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/外部個体取込責務分離機能説明書.md`
- `src/kadoka_quest/apps/monster_import_service.py`

# 23. Python 3.13.5並行実行環境

- CドライブのPython 3.13.5からプロジェクト内に `venv_3135` を作成
- `scripts/run_python.bat` は `venv_3135` を優先し、存在しない場合だけ既存 `.venv` を使用
- 3.13.5使用時はpygame同梱DLLとWindows基本ディレクトリを優先し、利用不能なドライブ上のDLLを参照しない
- Python版の選択を起動スクリプトに限定し、ゲーム本体・公開JSON・pygame非依存コアは変更なし
- `pyproject.toml` の対応範囲 `Python >= 3.10` を維持
- 仮想環境本体は `.gitignore` 対象とし、ソース管理へ含めない

変更したファイル

- `.gitignore`
- `AGENTS.md`
- `README.md`
- `docs/ver.md`
- `run_game.bat`

追加したファイル

- `docs/Python3135並行環境機能説明書.md`
- `scripts/run_python.bat`
- `tests/test_environment_contract.py`

# 24. ドットエディタ連続描画

- 高速ドラッグ時に前回の論理ドットから現在の論理ドットまで整数直線で補間
- モンスターエディタとブロックエディタの共通 `PixelArtEditor` へ一度だけ実装
- 左ドラッグの着色と右ドラッグの透明化の両方へ適用
- キャンバス外へ出た場合は線分を切り、再進入時の意図しない長い線を防止
- 1回のドラッグを引き続き1回のUndo履歴として管理
- 中央ボタンでペン入力が始まらないよう入力条件を明確化

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/ver.md`
- `docs/開発予定.md`
- `src/kadoka_quest/apps/block_editor.py`
- `src/kadoka_quest/apps/monster_editor.py`
- `src/kadoka_quest/ui/pixel_editor.py`
- `tests/test_core.py`

追加したファイル

- `docs/ドットエディタ連続描画機能説明書.md`

# 25. MODデータ一括検証

- 起動を停止せず全問題を収集するpygame非依存 `DataValidator` を追加
- JSON構文、ブロック、マップ、種族、Lv別能力、スキル、＋分岐、装備、耐性を一括検査
- 検証語彙を `data/project.json` へ切り出し、ゲーム固有名を検証処理から分離
- ランチャー起動時に問題件数を表示
- 問題コード・JSONパス・説明を表示するスクロール対応の検証画面を追加
- ブロック・マップ・モンスターエディタの保存直後にも全体検証を実行
- 問題が存在してもゲーム・エディタの起動は継続可能
- 正常な同梱データで問題0件を確認

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/ver.md`
- `docs/評価/評価者からのフィードバック.md`
- `docs/開発予定.md`
- `src/kadoka_quest/apps/launcher.py`
- `src/kadoka_quest/apps/block_editor.py`
- `src/kadoka_quest/apps/map_editor.py`
- `src/kadoka_quest/apps/monster_editor.py`
- `tests/test_app_smoke.py`

追加したファイル

- `data/project.json`
- `data_validator.py`
- `docs/MODデータ一括検証機能説明書.md`
- `docs/評価/過去のフィードバック.md`
- `src/kadoka_quest/apps/data_validator.py`
- `src/kadoka_quest/data/data_validator.py`
- `tests/test_data_validator.py`

# 26. エンジン分離 第1段階

- 再利用可能コード用の `kadoka_engine` パッケージを新設
- MODデータ検証本体を `kadoka_engine.data_validator` へ移動
- 汎用検証側から `kadoka_quest.paths` と固定データルートへの依存を除去
- ゲーム・各エディタがデータルートを明示して汎用エンジンを利用
- 旧 `kadoka_quest.data.data_validator` は既定パス付き互換アダプターとして維持
- `kadoka_engine` からKadoka Quest本体・pygameへの逆依存を禁止する自動テストを追加
- 3層分離全体は未完了のため、評価者フィードバックは継続項目として保持

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/MODデータ一括検証機能説明書.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/block_editor.py`
- `src/kadoka_quest/apps/data_validator.py`
- `src/kadoka_quest/apps/launcher.py`
- `src/kadoka_quest/apps/map_editor.py`
- `src/kadoka_quest/apps/monster_editor.py`
- `src/kadoka_quest/data/data_validator.py`
- `tests/test_data_validator.py`

追加したファイル

- `docs/エンジン分離第1段階機能説明書.md`
- `src/kadoka_engine/__init__.py`
- `src/kadoka_engine/data_validator.py`
- `tests/test_engine_boundaries.py`

# 27. フィールドエンジン分離 第2段階

- フィールド規則、座標補間、固定モブ、見えない敵、主人公移動の5責務を `kadoka_engine` へ移動
- エンジン内部の相互参照を `kadoka_engine` 内で完結
- ゲーム本体とフィールド描画が新しいエンジンAPIを直接利用
- 旧 `kadoka_quest.core` の5モジュールは同じクラスを再公開する互換窓口として維持
- `kadoka_engine` のKadoka Quest・pygame逆依存禁止テストを継続
- 旧importと新importのクラス同一性を自動テスト
- 3層分離全体は未完了のため、評価者フィードバックは継続項目として保持

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/ver.md`
- `docs/エンジン分離第1段階機能説明書.md`
- `src/kadoka_engine/__init__.py`
- `src/kadoka_quest/apps/game.py`
- `src/kadoka_quest/core/field_engine.py`
- `src/kadoka_quest/core/fixed_mob_controller.py`
- `src/kadoka_quest/core/grid_movement.py`
- `src/kadoka_quest/core/hidden_enemy_controller.py`
- `src/kadoka_quest/core/player_field_controller.py`
- `src/kadoka_quest/ui/field_renderer.py`
- `tests/test_engine_boundaries.py`

追加したファイル

- `docs/フィールドエンジン分離第2段階機能説明書.md`
- `src/kadoka_engine/field_engine.py`
- `src/kadoka_engine/fixed_mob_controller.py`
- `src/kadoka_engine/grid_movement.py`
- `src/kadoka_engine/hidden_enemy_controller.py`
- `src/kadoka_engine/player_field_controller.py`

# 28. 公開ライセンス・セキュリティ整備

- プロジェクト本体のコード、JSONデータ、通常アセットにMIT Licenseを明記
- まる・かどかの画像、キャラクターデザイン、派生ドット絵だけをObake Character License v1.1の例外として明記
- パッケージメタデータにもMITを設定
- 実プロジェクトのバージョンと非公開連絡先を示すSECURITYポリシーを追加
- ライセンス表記とセキュリティポリシーを検査するテストを追加

変更したファイル

- `README.md`
- `docs/ver.md`
- `pyproject.toml`

追加したファイル

- `LICENSE`
- `LICENSES/Obake-Character-License-v1.1.md`
- `SECURITY.md`
- `tests/test_project_metadata.py`

# 29. ブロック用可変キャンバス

- 共有ドットエディタに1 / 2 / 4 / 8 / 16 / 32 / 64 / 128の正方形キャンバスを追加
- ブロックエディタから保存前にキャンバスサイズを選択可能化
- 変更は最近傍法による1回のUndoとして扱い、PNGの実寸を保存・再読込
- モンスターの64×64画像契約は維持

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/block_editor.py`
- `src/kadoka_quest/ui/pixel_editor.py`

追加したファイル

- `docs/可変キャンバス機能説明書.md`
- `tests/test_pixel_editor_canvas.py`
