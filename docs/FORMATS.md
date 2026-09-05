# JSON formats

すべてUTF-8、JSONオブジェクトをルートに持ちます。`schema_version` は現在 `1` です。未知の追加キーは基本的に無視するため、MOD側でメタデータを加えられます。

JSONにはpygameの `Rect`、`Surface`、キーコードなどの実装固有値を保存しません。ゲーム処理層との受け渡しは辞書、配列、数値、文字列、真偽値だけを使います。GDScript／Luaへの移植境界は [移植境界機能説明書](移植境界機能説明書.md) を参照してください。

## Block

`data/blocks/<id>.json`

```json
{
  "schema_version": 1,
  "id": "grass",
  "display_name": "草地",
  "player_walkable": true,
  "enemy_spawnable": true,
  "enemy_walkable": true,
  "appearance": {"type": "color", "value": "#4E9F3D"}
}
```

`appearance.type` は `color` または `path`。`path` の値は `assets/` からの相対パスです。内蔵ドットエディターで新規作成した画像は既定で `assets/appearance/blocks/<id>.png`（64×64）へ保存されます。

## Map

`data/maps/<id>/map.json`

`tiles` は高さ行・幅列のブロックID配列です。`spawns` が空なら敵は何も湧きません。出現表から作られた野生モンスターは画面には描かれず、`enemy_walkable` なブロックを裏で歩きます。プレイヤーと同じマスへ来たときに戦闘になります。

```json
{
  "id": "greenwood",
  "width": 48,
  "height": 32,
  "start": {"x": 6, "y": 5},
  "block_color_overrides": {"safe": "#101B3A"},
  "tiles": [["grass"]],
  "spawns": [
    {"species_id": "slime", "weight": 50, "min_level": 2, "max_level": 5}
  ],
  "events": [
    {"id": "sign", "x": 8, "y": 6, "type": "message", "text": "..."},
    {
      "id": "to_next_map", "x": 47, "y": 6, "type": "transition",
      "activation": "step",
      "target": {"map_id": "next_map", "x": 1, "y": 6}
    }
  ]
}
```

イベントの主な `type` は `message / transition / church / reacquire_ghosts` です。イベントは地形ブロックとは別レイヤーなので、同じ座標へ重ねて配置できます。ゲーム中はイベント地点自体を色や印で描画せず、下にある地形ブロックの見た目をそのまま表示します。マップエディターでは編集時だけ種類別のオーバーレイを表示します。`"activation": "step"` は触れたとき、`"activation": "interact"` は隣または同じマスから調べたときに移動します。`church` の `revive` は全滅時の復活地点です。`ball_slime` は初期獲得専用のため、出現表へ設定しません。

`block_color_overrides` はそのマップ内だけでブロックの表示色を変更します。ブロック本体の移動・出現ルールは変えません。

### Map preset

`data/map_presets/<preset_id>.json`

マッププリセットは通常マップと同じJSON構造です。マップエディターから現在のマップをプリセットとして保存し、選択したプリセットを既存マップへ適用するか、新しいマップとして作成できます。

- 現在マップへ適用: 現在の `id` と `display_name` を維持し、それ以外のマップ内容を読み込む
- 新規マップ作成: プリセットの `id` と `display_name` を入力値へ置き換えて `data/maps/<id>/map.json` に保存する
- 適用後の既存マップは未保存状態になるため、通常の保存操作で確定する

詳しい処理は [マッププリセット機能説明書.md](マッププリセット機能説明書.md) を参照してください。

### Fixed mobs

村人・ボス・固定配置モンスターはマップ直下の `fixed_mobs` に置きます。マップへ入るたび、設定された初期座標から生成されます。

```json
{
  "fixed_mobs": [
    {
      "id": "village_resident_1",
      "species_id": "hero",
      "name": "村人",
      "x": 12,
      "y": 8,
      "direction": "front",
      "enabled": true,
      "level": 1,
      "ai": "random",
      "interaction": "talk",
      "move_interval_ms": 900,
      "move_chance": 40,
      "despawn_after_interaction": false,
      "respawn_on_map_enter": true,
      "dialogue": ["こんにちは。", "今日はいい天気ですね。", "森へ行くなら気をつけて。"]
    }
  ]
}
```

- `ai`: `idle`（立ち止まる）、`random`（ランダム移動）、`chase`（プレイヤーへ向かう）
- `interaction`: `talk` は会話、`battle` は設定レベルの固定戦闘を開始する。村人とボスを同じ形式で配置できる
- `level`: `interaction: battle` で出現する敵のレベル（1～100）
- `move_interval_ms`: 移動判定を行う間隔。小さいほど移動速度が速い
- `move_chance`: 移動判定ごとに実際に1マス動く確率（0～100）
- `dialogue`: 会話デッキ。全台詞を一巡するまで同じ台詞を繰り返さない
- `despawn_after_interaction`: 会話直後、または固定戦闘に勝利したあとマップ上から消える
- `respawn_on_map_enter`: 消えたあとマップへ入り直すと復活する。`false` の場合はセーブデータの `despawned_fixed_mobs` に記録される
- `enabled`: `false` にするとデータを残したまま出現を停止する

固定モブはプレイヤーと同じマスへ移動しません。プレイヤーが正面にいる間も移動しないため、そのまま話しかけられます。

## 実行時アプリ間コマンド

実行時コマンドは保存JSONではなく、アプリ間の一時的なメッセージです。形式は `target`、`action`、`payload` の3要素で、payloadには文字列・数値・真偽値・リスト・辞書・null相当だけを渡します。pygameのイベント、キーコード、`Rect`、`Surface` は渡しません。

```json
{
  "target": "field",
  "action": "move.start",
  "payload": {"direction": "left", "now": 1200}
}
```

`target` は現在 `field`、`battle`、`password`、`manager` の4種類です。不明な対象や各アプリが対応しないactionはエラーにして黙って無視しません。画面モードと配送先登録は `RuntimeOrchestrator` が一元管理します。

フィールドイベントが別アプリを必要とするときは、まず `FieldEventApplication` がプレーン辞書の効果を返し、`RuntimeOrchestrator` が対応するコマンドへ変換します。固定モブ実体や `GridMovement` などの実行時オブジェクトはpayloadへ入れず、`npc_id`、座標、移動先、出現定義だけを渡します。

### 戦闘内部の責務境界

戦闘計算は `BattleEngine`、戦闘用データ読込は `BattleDataLoader`、行動選択は `BattleInference`、学習更新は `BattleLearning`、画面描画は `BattleRenderer` が担当します。これらの間で保存用の派生JSONは作らず、従来の種族JSONと個体AI JSONをそのまま使います。`learning_enabled: false` の模擬戦は、注入された学習処理を一度も呼びません。

戦闘の開始・終了、選択中コマンド、ログの表示位置、行動中個体、オート戦闘の待機時刻、模擬戦かどうか、固定モブIDはpygame非依存の `BattleSession` が担当します。これは実行中だけの状態であり、JSONへ保存するキーは追加しません。戦闘終了時は結果・模擬戦フラグ・固定モブIDだけをプレーン辞書としてゲーム進行へ返します。

暗号入力画面の入力文字列、許可文字、最大長、案内・誤答メッセージ、入力中状態はpygame非依存の `PasswordSession` が担当します。これも実行中だけの状態でありJSONへ保存しません。正解した事実だけをゲーム進行側が受け取り、従来どおりまる・かどかの個体フォルダと進行フラグを保存します。

実行時のキャラクター画像は `CharacterImageProvider` だけが種族定義の `portrait_path / field_sprites / field_sprite_path` を解決します。戦闘用 `portrait` はPNG全体、フィールド用は透明余白を切り詰めてから、指定枠へ縦横比を維持して最近傍拡大します。元PNGやJSONは変更せず、変換後Surfaceは種族ID・用途・表示幅・表示高さをキーにメモリ内だけでキャッシュします。

牧場管理ツールのプロセス起動・二重起動防止・終了検知は `ManagerProcessService` が担当します。プロセス情報は保存JSONへ含めません。管理ツール終了後にゲーム側が既存のアクティブセーブを再読込するため、個体・AI・パーティの形式と反映方法は変わりません。

pygameのキーダウン・キーアップ・終了イベントは `RuntimeInputAdapter` が、現在の画面モードと戦闘終了状態を加味してプレーン辞書のコマンド要求へ変換します。キーコードやpygameイベントをコマンドpayloadへ入れず、移動方向、選択番号、入力文字、時刻だけを渡します。この入力要求も保存JSONではありません。

パスワード画面と戦闘画面の左クリックは `RuntimeMouseAdapter` が、登録済みのpygame Rectと現在の画面モードを使ってプレーン辞書のコマンド要求へ変換します。クリック座標、pygameイベント、Rectはpayloadへ入れず、入力文字または戦闘コマンド名だけを渡します。戦闘終了後と演出中のボタン操作は要求を生成しません。この入力要求も保存JSONではありません。

### フィールドアクター内部の責務境界

固定モブの実行時状態、会話デッキ、向き、占有、移動周期は `FixedMobController`、画面に出ない野生敵の出現候補、個体配置、視認、追跡・徘徊周期は `HiddenEnemyController` が担当します。どちらも既存の `map.json` とブロック定義を入力に使い、追加の保存JSONは作りません。非復活固定モブの永続化は従来どおり `state.json.despawned_fixed_mobs` です。

主人公の整数座標、向き、長押し再入力、表示補間は `PlayerFieldController`、NPCとイベントから実行効果への変換は `FieldEventApplication`、マップ・ブロック読込と入口座標の範囲補正は `FieldDataLoader`、現在地・復活地点・拾得品・進行フラグ・固定モブ消滅の保存は `FieldProgressStore` が担当します。これらも既存JSONをそのまま読み書きし、新しい保存形式は追加しません。

## Species folder

`data/species/<species_id>/` は起動時にフォルダ単位で発見されます。

モンスターエディターの一覧先頭にある「＋ 新規作成」は、この4ファイルと `assets/characters/<species_id>/` の64×64 PNG 5枚を一括生成します。IDは半角英小文字・数字・`_`・`-`だけを使い、既存IDは上書きできません。

## ドットエディターのパレット

モンスターとブロックの見た目編集は、共通のドットエディターが持つ編集セッション内パレットを使います。色入力は `#RRGGBB` 形式、登録上限は16色です。同じ色を追加すると重複登録せずにその色を選択します。透明色と最後の不透明色は削除できません。

パレットは編集操作の補助情報であり、種族JSON、ブロックJSON、PNGメタデータには保存しません。画像の正式な保存形式は引き続きRGBA PNGで、PNG内の各ピクセル色がデータ本体です。

### 画像読込と色統合

画像読込は対象キャンバス（現在は64×64）より大きい画像だけを最近傍法で縮小します。縦横比を維持して透明キャンバス中央へ置き、小さい画像は原寸のままです。その後、指定した色差0～255をRGBユークリッド距離のしきい値として、同じアルファ値を持つ近似色を走査順の代表色へ統合します。透明ピクセルは統合しません。

これらはエディター内処理であり、JSONキーは追加しません。読込後の画像も保存時はRGBA PNGです。

- `species.json`: ID、表示、耐性、AIプロファイル、再獲得規則
- `stats.json`: `levels["1"]` から `levels["100"]` までの `attack / defense / speed / magic / hp / mp`
- `skills.json`: `learnset` の `{level, skill_id}`
- `plus.json`: `stages` 1〜10、それぞれの `options`

＋選択の主な `kind` は次です。

- `stat_add`: 対象能力へ固定加算
- `stat_multiplier`: 対象能力へ倍率
- `skill`: スキル追加
- 将来用: `resistance_step`, `trait`

`requires_any` を置くと、前段階の選択による分岐条件を表現できます。

## Equipment

`data/equipment/equipment.json`

装備枠は1つ。装備できる種族は装備品側の `allowed_species_ids` で管理します。

```json
{
  "id": "ken",
  "category": "sword",
  "allowed_species_ids": ["slime", "ball_slime", "dice_slime", "metal_slime"],
  "stat_multipliers": {"speed": 0.8},
  "skill_modifiers": {"attack": {"power_multiplier": 1.5}}
}
```

能力補正は倍率です。`fixed_bonus_damage` のみ、メタル狩り用などの固定追加ダメージを表します。

## Individual monster

`savedata/<save_name>/monsters/<individual_id>/`

```text
monster.json
ai.json
```

`monster.json`:

```json
{
  "schema_version": 1,
  "id": "monster_123",
  "species_id": "ghost",
  "name": "おばけA",
  "level": 42,
  "experience": 0,
  "plus_choices": ["ghost_plus_1_magic"],
  "equipment_id": "wood_staff",
  "source": "scout"
}
```

能力値と習得済みスキルは種族フォルダから再構築します。`ai.json` の `action_preferences` は `-1.0`〜`1.0` に制限し、実戦経験で少しずつ変化します。`tactic` は `balanced / aggressive / careful / variety` です。

状況学習は次の任意キーを使います。古い個体にキーがない場合は空として扱います。

- `context_preferences`: `状況タグ -> スキルID -> 評価値`。各評価値は `-0.6`～`0.6`
- `context_actions`: 状況タグごとの経験行動回数

自分のHP、味方の損耗、MP、人数差、敵の残HP、敵とのレベル差から1行動あたり6タグだけを使用します。全組合せを保存しないため、学習量は軽量です。詳しくは [状況学習機能説明書.md](状況学習機能説明書.md) を参照してください。

### Developer monster creator

`data_creator.py` は種族、レベル1～100、個体名、任意の個体IDを指定し、通常個体と同じ `monster.json` と `ai.json` を生成します。

- 現在のセーブ: `savedata/<active>/monsters/<individual_id>/`
- 獲得用: `imports/acquire/<individual_id>/`
- 模擬戦用: `imports/simulation/<individual_id>/`

同じ生成先に同一個体IDがある場合は上書きしません。詳細は [データクリエイター機能説明書.md](データクリエイター機能説明書.md) を参照してください。

## Party preset

```json
{
  "schema_version": 1,
  "name": "対ボス用",
  "members": ["monster_001", "monster_002", null, "monster_004"]
}
```

個体が存在しなければ、その位置は空き枠として読みます。プリセットファイル数に制限はありません。

## Named save data

```text
savedata/<save_name>/
  meta.json
  state.json
  items/items.json
  monsters/<individual_id>/monster.json
  monsters/<individual_id>/ai.json
  parties/*.json
```

`state.json` は現在地・復活地点・現在パーティ・進行フラグを持ちます。所持品は `items/items.json` に分離します。ランチャーの「別名保存」はこのフォルダ全体を複製するため、保有モンスターと個体AIも一緒に保存されます。`savedata/active.json` は次回直接起動時に読み込むセーブ名です。

プレイヤー座標は引き続き整数のマス座標として保存します。滑らかな歩行に使う小数の表示座標や補間途中の状態はセーブせず、読込時は保存されたマスへ即時同期します。詳細は [移動補間機能説明書.md](移動補間機能説明書.md) を参照してください。

## Import

- `imports/acquire/`: 再走査で所有フォルダへコピー。同じ個体IDは上書きしない
- `imports/simulation/`: コピーせず読み取り、模擬戦だけで使用。AI更新なし

