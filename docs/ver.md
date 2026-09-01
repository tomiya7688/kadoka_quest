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
