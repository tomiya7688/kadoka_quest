# JSON formats

## プロジェクト設定

`data/project.json` はゲームデータ全体で使用できるID集合を定義します。

- `validation.stat_ids`: 能力ID
- `validation.skill_kinds`: スキル種別
- `validation.equipment_categories`: 装備カテゴリ
- `validation.element_ids`: 属性・耐性名
- `validation.resistance_values`: 耐性段階

MODデータ検証はこの設定を参照するため、別ゲームへ流用する場合はプログラムを変更せずプロジェクト設定側で有効な名前を追加できます。定義にない名前は起動時の検証一覧へ表示されますが、ゲーム起動自体は停止しません。

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

「出現テーブル」内の「マップ全体 / AI」タブで `pop_rate` とマップ直下の `field_ai_weights` を編集できます。継承を明示すると `null` を保存し、未編集の旧マップの省略キーは保持します。詳しくは [マップポップ率AI編集機能説明書.md](マップポップ率AI編集機能説明書.md) を参照してください。

マップエディタの「出現テーブル」で種族・重み・Lvを行単位で編集し、保存前に出現設定を検証します。追加JSON項目は保持します。操作・参考比率の定義は [野生出現テーブル編集機能説明書.md](野生出現テーブル編集機能説明書.md) を参照してください。

野生ポップ設定の契約は [野生ポップ設定データ契約機能説明書.md](野生ポップ設定データ契約機能説明書.md) にまとめています。マップ直下の `pop_rate` は0〜100の百分率（省略時100）。`spawns[].weight` は非負の有限数値による相対重み（省略時1）で、空でない出現表には正の重みが1つ以上必要です。`min_level` / `max_level` はそれぞれ省略時1です。真偽値・数値文字列は数値として扱いません。

#153以降、生成候補1枠ごとに `pop_rate` を判定し、0%では野生個体を生成しません。失敗枠の再試行はせず、種族weightは小数も含め相対比率として扱います。通常域のLvは生成時に抽選し、実行時だけの `spawn.rolled_level` に保持して戦闘へ渡します。メタル域は遭遇時のパーティ連動Lvを優先します。原本JSONや仲間セーブの形式は変更しません。詳細は [野生ポップ抽選機能説明書.md](野生ポップ抽選機能説明書.md)。

マップ直下・出現項目の `field_ai_weights` は省略または `null` で継承します。明示された不正な表はDataValidatorでエラーにします。以下のフォールバックはゲーム実行時の既存の保護動作であり、編集データが検証を通ることを意味しません。

複数chase個体の経路予約・直近経路の混雑履歴・迂回中の短期目標記憶は実行時のみの情報で、出現JSON・セーブJSONに追加項目は不要です。初回視認と通常AI重みは維持します。動作の範囲と制限は [追跡経路分散機能説明書.md](追跡経路分散機能説明書.md) を参照してください。

野生個体の移動AI抽選用に、種族 `species.json`・マップ直下・`spawns[]` の各項目で任意の `field_ai_weights` を指定できます。例: `{"random": 70, "chase": 25, "idle": 5}`。優先順は出現項目 → マップ → 種族 → 既定70/25/5。省略キーは0、合計100不要の相対重みで、非負の有限数値を使います。空・合計0・負数・非数値・真偽値・非有限値・未知キーを含む表は次へフォールバックします。実行時は各個体の `ai` に抽選結果を保持し、仲間の戦闘AIとは独立です。randomは通常周期で徘徊、idleは静止、chaseのみ視認条件内で加速追跡します。詳細は [野生個体AI割当機能説明書.md](野生個体AI割当機能説明書.md) と [野生個体AI移動機能説明書.md](野生個体AI移動機能説明書.md)。

`data/maps/<id>/map.json`

マップ直下の任意キー `encounter_context` は野生戦の出現コンテキストです。省略時は `normal`、メタル域では `metal_area` を指定します。地名や種族IDからは推測しません。戦闘開始時に渡し、仲間の個体JSONには保存しません。未知のコンテキストには、その種族で対応する逃走率が定義されていない限り逃走を適用しません。

種族定義 `data/species/<id>/species.json` の任意キー `flee_rates` はコンテキストごとのターン逃走確率です。メタルスライムは `{"normal": 0.15, "metal_area": 0.60}`。値は0〜1の数値とし、省略時は0（逃走なし）。範囲外や数値化できない値は逃走なしとして扱います。味方・模擬戦には適用しません。詳しくは [敵の地域別逃走機能説明書.md](敵の地域別逃走機能説明書.md) を参照してください。

`tiles` は高さ行・幅列のブロックID配列です。`spawns` が空なら敵は何も湧きません。各出現項目の `min_level` と `max_level` は1〜100の整数で、最小値は最大値以下にします。出現表から作られた野生モンスターは `enemy_walkable` なブロックを歩き、種族のフィールドスプライトで表示します。主人公の正面への接近など既存の遭遇条件で戦闘になり、同じマスへは重なりません。実行時の向き `direction` は出現時 `front`、移動時に更新します。保存形式は変更せず、詳細は [野生モンスター可視化機能説明書.md](野生モンスター可視化機能説明書.md) を参照してください。

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

### 道具・スキル使用イベント

`events` の `type: "use_requirement"` は、指定地点（`radius` のマンハッタン距離内）で特定の道具またはスキルを使用した場合だけ発動します。`effect.kind` は `message` または `gain_item` です。任意コードは記述できません。

```json
{
  "id": "sealed_spring",
  "x": 12,
  "y": 8,
  "type": "use_requirement",
  "radius": 1,
  "required": {"kind": "item", "id": "spring_key"},
  "text": "泉の封印がほどけた。",
  "effect": {"kind": "gain_item", "item": "clear_water", "status": "水を手に入れた。"}
}
```

マップエディタでは `U` キーで使用イベント編集を開き、「マップ上へ新規配置」からブロックと重ねて配置できます。

イベントの主な `type` は `message / transition / church / reacquire_ghosts` です。イベントは地形ブロックとは別レイヤーなので、同じ座標へ重ねて配置できます。ゲーム中はイベント地点自体を色や印で描画せず、下にある地形ブロックの見た目をそのまま表示します。マップエディターでは編集時だけ種類別のオーバーレイを表示します。`"activation": "step"` は触れたとき、`"activation": "interact"` は隣または同じマスから調べたときに移動します。`church` の `revive` は全滅時の復活地点です。`ball_slime` は初期獲得専用のため、出現表へ設定しません。

`block_color_overrides` はそのマップ内だけでブロックの表示色を変更します。ブロック本体の移動・出現ルールは変えません。

### メタルエリアの動的Lv

マップ直下で `"encounter_context": "metal_area"` を指定すると、野生戦生成時に現在の戦闘参加パーティ（先頭4体）から敵Lv範囲を計算します。通常種族は実Lv、`kadoka / maru` は `max(1, Lv - 10)` を使い、換算Lvの2位±3、上位差20以上または1体編成なら1位±5。範囲を1〜100へ丸め、その両端を含む整数から抽選します。

この地域では出現項目の `min_level / max_level` より動的範囲を優先します。エディタの固定Lv欄やJSON検証用には引き続き有効な値を残してください。通常・未設定・未知のコンテキストでは従来の固定範囲を使用します。出現表や所有個体は書き換えず、模擬戦の持込個体には適用しません。詳細は [メタルエリア動的レベル機能説明書.md](メタルエリア動的レベル機能説明書.md) を参照。

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

GDScript #222も既存の配置/移動パラメータをそのまま読みます。[移動契約](GDScript固定モブ移動契約.md)を参照してください。モブの実行中座標・次回時刻・移動回数・補間・乱数状態は保存せず、再入場で配置を再生成します。既存 `despawned_fixed_mobs` を参照しますが、新しい消滅フラグはまだ生成しません。保存地点は実際の占有で検証し、読込時の初期モブとの重複はモブ側の再配置で防ぎます。消滅イベントは未移植です。
GDScript #223の[会話契約](GDScript固定モブ会話契約.md)も同じdialogue配列を読みます。文字列カードの空白を除き一巡/再抽選します。欠損・非配列・非文字列カード・有効カードなしは理由付き拒否で、Pythonの型変換/「……」fallbackを流用しません。カードの重複定義は保持します。残りカード/前回台詞は個体ごとの実行時状態であり、map.jsonや個体/AI/stateにキーを追加しません。

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

フィールドで選択中のパーティ枠と、F8で次に読むプリセットの巡回位置は `FieldPartySession` が実行中だけ保持します。これらはUIカーソルであり `state.json` へ新しいキーを追加しません。パーティ本体は従来どおり `state.json.current_party` と `savedata/<name>/parties/*.json`、個体AIは各個体の `ai.json` が正式データです。

`FieldPartyService` はF7のプリセット保存、F8の順次読込、選択個体の作戦変更とAIリセットを既存の `PartyStore / StateStore / MonsterStore` へ調停します。サービス独自のファイルやキーは作らず、プリセット名 `フィールド編成_YYYYMMDD_HHMMSS`、最大4枠、欠損IDを空き枠として扱う規則も維持します。

`MonsterImportService` は `imports/acquire` を再走査して未所有IDの個体フォルダを現在セーブへ取得し、`imports/simulation` から模擬戦相手を読み込みます。どちらも既存の `monster.json / ai.json` を使います。模擬戦用個体は現在セーブへコピーせず、生成する `BattleEngine` は常に `learning_enabled=false` です。

### フィールドアクター内部の責務境界

固定モブの実行時状態、会話デッキ、向き、占有、移動周期は `FixedMobController`、画面に出ない野生敵の出現候補、個体配置、視認、追跡・徘徊周期は `HiddenEnemyController` が担当します。どちらも既存の `map.json` とブロック定義を入力に使い、追加の保存JSONは作りません。非復活固定モブの永続化は従来どおり `state.json.despawned_fixed_mobs` です。

主人公の整数座標、向き、長押し再入力、表示補間は `PlayerFieldController`、NPCとイベントから実行効果への変換は `FieldEventApplication`、マップ・ブロック読込と入口座標の範囲補正は `FieldDataLoader`、現在地・復活地点・拾得品・進行フラグ・固定モブ消滅の保存は `FieldProgressStore` が担当します。これらも既存JSONをそのまま読み書きし、新しい保存形式は追加しません。

## Species folder

`species.json` の任意キー `experience_reward` は撃破時の専用経験値係数です。メタルスライムの初期値は `{"base": 300, "per_level": 35, "squared_divisor": 10}` で、`base + Lv * per_level + floor(Lv * Lv / squared_divisor)` を計算します。`base` と `per_level` は0以上の整数、`squared_divisor` は1以上の整数です。文字列の式は実行しません。未指定・欠落・不正値の場合は通常敵の計算へ戻ります。

通常敵は従来どおりLv×3と、通常敵を1体以上倒した戦闘ごとに基礎点8。専用式の敵だけなら基礎点8は加えません。混成時は通常敵分（基礎点は1回）と専用式分を合計します。生存・逃走個体は除外し、味方の `experience_curve` やレベルアップ必要量とは独立です。詳細は [種族別撃破経験値機能説明書.md](種族別撃破経験値機能説明書.md) を参照してください。

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

## Balance report

`balance_analyzer.py` が出力する `reports/balance_report.json` は保存データやゲーム定義ではなく、再現用の開発レポートです。`matchups[].history` には個別戦闘のseed・勝者・ターン数、`rankings` には勝敗集計と順位、`recommendations` にはLv100基準の能力値・耐性候補を入れます。提案は自動反映されません。

## Game evaluation report

`game_evaluator.py` が出力する `reports/game_evaluation.json` は自動探索の開発ログです。`visited_maps`、`attempted_events`、時系列の `entries` を持ち、各entryは `map_entered / move / event_attempted / battle_started / battle_finished / password_cancelled / blocked / stalled` のいずれかです。プレイヤーセーブへ混ぜず、既定では出力先に隣接する `evaluator_save/` を使います。

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

### GDScriptフィールド試作の保存

GDScript版は同じフォルダ形式を、既定で `user://savedata/<save_name>/` に保存します。Python版の正規セーブへ自動接続せず、`active.json` も使用しません。保存rootは `KADOKA_GDSCRIPT_SAVE_ROOT` の絶対パス、名前は `KADOKA_GDSCRIPT_SAVE_NAME`（既定 `default`）で指定します。GUIでのスロット管理は未移植です。

`state.json.player.direction` は任意で `front / back / left / right` のいずれかです。GDScript版は保存時に追加し、旧形式で欠けていれば `front` として復元します。Python側の位置読込は追加キーを無視できます。既存stateの位置以外のキーは引き継ぎ、個体/AI/items/parties/metaの既存ファイルは変更しません。stateのJSON再出力はbyte単位の維持ではなく、Godotの数値精度外のMOD値の完全往復は保証しません。

初回保存は主人公・ボールスライムをLv1/＋選択なし/装備なしで生成し、既存の `monster.json / ai.json` 形式と `source: starter` を使います。`current_party` は主人公→ボールスライムの個体IDです。AI初期値はPythonの `default_ai` と同じで、AI判断/学習/リセットはまだ実行しません。保存失敗後に初期個体が公開済みなら再利用しますが、既存stateへ仲間を自動追加したり既存AIをリセットしたりはしません。

F6の一覧は全保有個体と先頭4パーティ枠を表示します。個体フォルダとJSON内のIDの一致、1〜100の整数Lv、種族の存在、JSON/schemaを確認し、読込できない個体を警告します。元ファイルと欠損パーティIDは一覧表示だけでは変更しません。同じ種族JSONから補正前の基礎能力値/Lv習得スキルと、＋/装備補正後の能力値/追加スキルを別に再構築します。

基礎値は `stats.json.levels[str(Lv)]` の6項目を整数化して読むだけです。純粋な契約ではPythonと同様に能力値の参照Lvを1〜100へ制限し、スキルは入力Lvの整数値以下の習得項目を、宣言順/重複除去で返します（実個体は1〜100を別途検証）。schema省略は1、learnset省略は空、習得項目のlevel省略は1。有限数値/ASCII整数文字列はPythonのint相当で扱い、bool/不正型/欠損行・項目/未対応schema/安全なJSON整数精度を超える絶対値は拒否します。成長式はPythonのデータ生成時にLv表へ展開されるため、runtimeの新形式や欠損行の自動補間は追加しません。未知キーと原本は書き換えません。

種族の能力値/スキルだけが読込不可でも、個体/AIの有効な原本とパーティIDは保持し、一覧で基礎値の読込不可と注意を表示します。1回の一覧走査内では同種族の表を共用し、次の再走査で読み直します。計算結果は実行時のplainデータで、個体JSONへ保存しません。

＋/装備の再構築は次のPython正本の計算規則を使います。個体の選択内容の編集や妥当な選択への修復は行いません。

- `plus_choices` の選択IDを重複除去し、`plus.json.stages/options` の宣言順で選択済み効果を適用します。入力配列の順序ではありません。同じIDの定義が複数あれば、各定義の効果を順に適用します。計算時には選択数、1段階1択、`max_stage`、`requires_any` を検証/補正しません（選択UIの制約とは別です）。
- `stat_add` は `int(value)` 相当（省略0）、`stat_multiplier` は有限倍率（省略1）で各適用時に偶数丸めを行います。ちょうど `.5` は隣の偶数に寄せ、負数も同様です。Lv習得スキルに、選択済み `kind: skill` の `skill_id` を定義順で追加し、全体を重複除去します。
- `equipment_id` の省略/null/空文字は装備なし。不明IDは効果なしと理由を返し、元IDを残します。カタログ内の重複IDはPythonの辞書化と同様、最後の定義を使用します。許可は装備側の `allowed_species_ids` だけで判定し、省略/空リストは全種族不可。独立した拒否リストや種族側の装備カテゴリでは判定しません。
- 許可された装備の `stat_multipliers` を＋補正の後に適用し、倍率ごとに偶数丸めを行います。全補正の最後に6能力値を最低1へ制限します。装備不可は無補正として理由を返し、保存されたIDを削除しません。
- 不明な＋選択ID、未知の対象能力値、未対応の＋効果は能力値/スキルに反映せず注意を返します。構造/schema、選択済み効果の数値/スキルID、使用する装備の許可リスト/倍率が不正なら補正結果を失敗にし、基礎値を完成値として代用しません。有限数値/ASCII数値文字列を扱い、bool/非有限値/安全なJSON整数精度を超える演算は拒否します。使用しない数値効果まで全カタログの完全検証を行うわけではありません。

実行時の `record.progression` は従来の `stats / skill_ids / scope: level_base` を補正前として保持し、`modifiers` に `ok / stats / skill_ids / scope: stats_with_modifiers / warnings / equipment_status / equipment` を追加します。`equipment_status` は元ID、適用可否、`none / unknown_id / not_allowed / applied` の理由です。不正時は理由付き失敗で補正値を持ちません。注意は一覧へ表示するだけで、未知IDを保存し直したり初期個体生成を妨げたりしません。読込不可の補正定義は一覧全体にも警告しますが、有効な個体/AI/partyは保持します。同種族plusと全装備の原本は走査内で共用し、再走査で外部更新を反映します。

保持する装備定義中の `skill_modifiers / fixed_bonus_damage / resistance_steps` 等の戦闘効果と、＋の耐性/特性は今回の能力値/スキルID再構築では適用しません。装備/＋の編集UI、戦闘、AI判断/学習は別の移植単位です。個体/AI/種族/装備のJSONと不明キーは書き換えません。

#221の[通常攻撃数値契約](GDScript通常攻撃数値契約.md)は、#220の補正後能力値と許可装備をplain入力として使用します。通常攻撃の `skill_modifiers.attack.power_multiplier / fixed_bonus_damage` をダメージ計算へ反映しますが、再構築stats自体や保存形式は変更しません。#230でSessionへ通常攻撃だけ接続し、個体/AI/stateの保存書込は行いません。戦闘Scene、耐性/全スキル/AIは未移植です。

#227の[戦闘個体状態契約](GDScript戦闘個体状態契約.md)のplain snapshotは `identity:{id,species_id,name} / stats:{6能力値} / hp / mp / fled / alive` です。新規戦闘でHP/MPを最大値から始め、HP0を再初期化しません。実行時専用でmonster.json/ai.json/state.json/itemsへキーを追加せず、未知の保有hp/mpを読んで現在値にしません。入力/スナップショットは独立コピー、数値は有限の非負整数値（最大HP>0、MP0可、2^53−1以下）。解決済み戦闘チームは0〜4体で5体以上を拒否し、所有数/プリセット数は無制限のままです。生存対象/ターン・AI・勝敗保存/実敗北復活は別の接続段階です。

#228の[行動順契約](GDScript行動順契約.md)は同snapshotを実行時だけ読み、対象を `side:allies/enemies / id` の2キーで識別します。明示shuffleは開始時生存者全員の順列のみ許可し、stable速度順のplain initial/orderを返します。最新状態のcan_act/stop/reasonは行動直前の条件で、勝敗保存や攻撃成功ではありません。未対応のsnapshot/identity/stats追加キーは拒否しますが、保有JSONの未知キーは削除しません。新しいファイル/保存schema/キーを導入せず、AI/個体/party/items/data/assetsは変更しません。

#229の[戦闘Session](GDScript戦闘Session契約.md)はfresh snapshotからStateを一度だけ所有し、plain `phase / round / cursor / order / pending / teams / scope` を返します。pendingは `{ticket:{round,slot,actor:{side,id}},stage:offered/claimed}`、取得だけではcan_execute=false、claim成功で一度だけtrueです。finishはclaimedのみ消費し、古いticket/二重操作を拒否。HP/MP/fledを次ラウンドまで保持します。実行時だけの契約で保存JSON/schemaは増やさず、stoppedは勝敗/報酬/復活成功ではありません。

#230の[通常攻撃行動](GDScript通常攻撃行動契約.md)は厳密な `{ticket,target,skill_id:attack,critical_roll,variance}` を受けます。正規attack定義と許可装備の独立コピーを使い、検証→単一claim→現在HP適用→finishを同期実行します。不正/未対応/重複はclaim前に拒否、死亡/敵なし取消はexecuted=false、成功はnumbers/sessionを返します。requestからの装備/guard上書き、防御/他スキルを拒否。全て実行時だけで保存形式は変更しません。

#251の[基本防御行動](GDScript基本防御行動契約.md)は別APIで厳密な{ticket,skill_id:defend}だけを受けます。target/guard等の上書きは拒否。正規defendの有限MP0/既定倍率0.5を検証し、Session所有guardだけを更新します。effects()はscope:basic_guard_onlyとteams:{allies:{id:倍率},enemies:{id:倍率}}の独立コピー、資源snapshotは従来6キー。通常/会心の物理攻撃は対象の現在guardを使い、正規終端で全guard1、HP/MP/fledは保持。保存JSON/schemaは変更しません。

未起票の[MP付き物理行動](GDScript物理スキル行動契約.md)はresolve_physical_skill({ticket,target,skill_id,critical_roll,variance})だけを受けます。開始時の再構築結果に独立したskill_idsを加えますが、資源snapshotの6キーは変更しません。選択IDの許可装備補正と最新MPを使い、単一claim→実MP消費→HP→finishを行います。未習得・不足・不正・未対応効果は不消費です。保存JSON/schemaは変更せず、AI/Sceneは未接続です。

#224の[暗号入力契約](GDScript暗号入力契約.md)は既存 `password_spring` を使い、入力/案内/誤答/activeを純粋な実行時Sessionだけに持ちます。7文字/かな許可/完全一致の結果はplain `password_matched / password_cancelled`。入力/誤答/取消は保存せず、一致の取得・保存は#225の[独立applicationサービス](GDScriptおばけ取得契約.md)へ接続します。新しいJSON/schema/フラグは追加しません。

不足するmaru/kadokaの個体だけをLv1/経験0/＋なし/装備null/source:ghost_home_password/種族由来の初期AIで追加し、state.flags.ghost_entrance_openをtrueにします。既存個体/AI/items/parties/metaと、stateの保存済み位置/方向/current_party/復活地点/他フラグ/未知キーは保持します。フラグtrueならstateを不要に再出力せず、不足個体だけを追加します。初回プロフィール作成は従来のF5で行い、未保存/破損なら取得を拒否します。

暗号画面を開いた時点のdigest、所有再走査、取得定義の事前検証、既存Dataの個体2ファイル公開/atomic state置換と保存後照合を使います。複数個体とstateの全件トランザクションではなく、部分失敗はcreated/flag_saved/partial/stage/errorで明示し、公開済み個体と以前のstateを削除しません。次の入力で最新所有から不足分だけ再試行します。並行writerの完全排他は保証しません。

#226の[教会登録契約](GDScript教会登録契約.md)は既存church/reviveから、map_id/x/y/name・対象マップ/通行可否を確認し、state.revive_pointだけを辞書コピーで置き換えます。地点の未知キーは引き継ぎ、既存の保存位置/方向/current_party/flags/他キーと個体/AI/items/parties/metaは保持します。同一地点ならstateのbyteも保持。未保存は先にF5を案内し、初期保存を作りません。digest/リンク/置換失敗・保存後照合は既存Dataを使い、HP回復/実敗北復活/自動移動は行いません。旧schema/方向の省略はそのまま保持し、登録以外の欠損キーを挿入しません。

一覧のE/編成ボタンから現在パーティを明示的に編集できます。保存時は `current_party` だけを4枠の個体ID/null配列に更新します。重複ID・未読込個体は保存せず、既存の問題枠はユーザーが外す必要があります。不正型・5枠以上は開く時点で拒否し、自動切捨てしません。空編成も許可し、所有個体は削除しません。変更なし・キャンセルではstateのbyteも維持します。編集中の外部更新をdigestで検出し、置換失敗時も以前のstateと下書きを保持します。個体/AI/items/プリセットと位置は変更しません。牧場の `open_manager` は同じ一覧へ接続し、調べる/閉じるだけでは保存せず、JSON形式も追加しません。

編成のP/プリセットボタンは、同じ `parties/*.json` 形式で新規保存・一覧・下書きへの読込を行います。schemaは1（省略時も1）、非空の文字列name、4枠までのID/null配列membersを検証し、短い配列はnullで4枠へ補います。新規保存時は選択個体を再検証し、同名なら `_2` 等の別ファイルを作り、既存ファイルを更新/削除しません。表示名は日本語可、生成するファイル名は安全なASCII名です。ファイル数に上限は設けません。

プリセット読込はstateを書かず、保存ボタンを押すまで下書きだけです。消失/読込不可の個体は空き枠と注意に変換しますが、原本のmembersや未知キーは変更しません。既知個体の重複、不正型・枠溢れ、破損JSON/未対応schemaは拒否して元の下書きを残します。旧Python実装の切捨てに合わせず、5枠以上は拒否します。一覧後の外部変更は読込時に再検証します。個体/AI/items/metaとstateはプリセット操作だけでは変更せず、明示保存した新規プリセットは編成キャンセルでも削除しません。

位置のない/不正な既存state、未対応schema、復元できないマップや座標は上書きしません。既存セーブの移行はコピーで試してください。操作・失敗時の扱いは [GDScript README](../gdscript/README.md) を参照してください。

## Import

- `imports/acquire/`: 再走査で所有フォルダへコピー。同じ個体IDは上書きしない
- `imports/simulation/`: コピーせず読み取り、模擬戦だけで使用。AI更新なし

### GDScriptのSession初期状態保持（実行時だけ）

[Session状態保持契約](GDScript戦闘Session状態保持契約.md)のstart_with_statusesは、満数値資源と全参加者に一致する明示initial_statusesを全成功時だけ保持します。statuses()はscope=battle_status_onlyとside/id別teamsの状態配列、status(key)はokとstatus_effectsだけのsnapshotを返す独立読取です。従来Session開始・数値snapshot六キー・保存JSON/schemaは変更しません。Applicationの専用開始からも設定でき、Session.apply_status_cureは現在取得済み票一回の治療だけを公開します。AI・画面・保存は未接続です。

### GDScriptの治療付きHP回復行動（実行時だけ）

[治療付き回復行動契約](GDScript治療付き回復行動契約.md)のApplication.resolve_cure_heal_skillは、現在のticket・同陣営target・治療付きskill_idと任意rollだけを受けます。候補があれば確率0/1でも0以上1未満の有限rollが必要です。専用開始で構築した行動だけが最新資源/状態を確認し、単一claim→MP消費→上限付きHP回復→最新一覧一件治療→finishを実行します。未知キー・定義/装備不正・不足は取得前に拒否し、取消/重複は追加更新しません。

結果scopeはexplicit_cure_heal_skill_onlyで、独立ticket/target・統合予測numbers・実spent_mp/healed・実治療cure・数値sessionと別のstatusesを返します。現在取得済み票による二回治療は不成立/候補なしでも拒否します。従来開始は状態未設定で、通常resolve_heal_skillの治療付き定義拒否は維持します。数値七/六キー・正規data/assets・保存JSON/schemaは変更しません。

### GDScriptの治療付きHP回復準備（実行時だけ）

[治療付き回復準備契約](GDScript治療付き回復準備契約.md)は既存回復の開始資源/習得/許可装備を共用検証し、initial_statusesのallies/enemies別ID集合を全参加者と一致させます。状態なしも[]で明示し、欠落/余分なID・不正状態を部分成功なしで拒否します。同じIDでも陣営を分離します。成功結果のsnapshots/context/initial_statusesは入力と独立した編集可能な通常データであり、Sessionの状態所有者や不変の内部状態ではありません。

専用selectは準備済みの習得/許可装備/ID索引から一意な治療付き定義を返します。通常HP回復入口の治療拒否は維持し、未知効果や補正はfalse/0/空でも無視しません。準備自体はHP/MP・状態・行動予約を更新せず、数値snapshot六キーと正規data/assets・保存JSON/schemaは変更しません。成功データからのSession保持と実治療は上記専用開始/行動へ委譲します。純粋準備自体は更新せず、AI・画面は未接続です。

### GDScriptの戦闘状態一覧保持・一件治療（実行時だけ）

[戦闘状態一覧契約](GDScript戦闘状態一覧契約.md)のcombatant_status_stateは、明示した順序付き状態配列を一度だけ検証・独立保持します。snapshotはstatus_effectsだけの独立コピー、未開始は空辞書です。既存combatant_state/Sessionの数値snapshot六キーと保存JSON/schemaは変更しません。

状態所有者のquote_cure/cureはcure_chanceと任意rollだけを受け、共用治療契約の確率・候補順序・判定値規則を使います。予測では一覧を変更せず、実治療では最新一覧の最初の候補一件だけを除きます。不成立/拒否は一覧を保持し、外部一覧や古い予測の持ち込みは拒否します。予測scopeはstatus_cure_quote、実治療scopeはcombatant_status_cureで、残存一覧は独立コピーです。Sessionは専用開始の保持/読取と現在取得済み票一回の治療を公開し、上記専用行動がHP/MPと治療を統合します。状態付与/継続効果・保存・AI・画面は未接続です。

### GDScriptの治療付きHP回復予測（実行時だけ）

[治療付き回復予測契約](GDScript治療付き回復予測契約.md)は、kind:healと必須status_cure_chanceのあるspirit_recover/互換MOD定義へ、current_mp・target_hp・target_max_hp・status_effectsと任意rollだけを渡して使います。既存HP回復と一件治療の純粋契約へ委譲し、MP不足は治療一覧/判定値の検証前に拒否します。候補があれば確率0/1でも明示判定値が必要です。満HPでも消費MPと治療を予測し、不正ではHPだけの部分成功を返しません。

成功結果のscopeはcure_heal_skill_quoteで、heal_amount・healed・remaining_hp・mp_cost・remaining_mpと一件治療のcured/cured_name・candidate_index・roll_required・cure_chance・独立したremaining_status_effectsを返します。未知定義/要求はfalse・0・空でも拒否し、原本・保存JSON/schema・Session/snapshotは変更しません。HP0の数値予測は復活許可を意味しません。通常HP回復入口は治療付き定義を拒否したままで、純粋統合予測は上記専用行動へ接続しました。AI・画面は未接続です。

### GDScriptの状態異常一つの治療予測（実行時だけ）

[状態治療予測契約](GDScript状態治療予測契約.md)のquote_cureは、status_effects・cure_chanceと任意のrollだけを受けます。状態一覧は文字列/辞書の順序を保持し、解除不可の辞書を飛ばした最初の候補一件だけを予測で除きます。候補があれば確率0でも判定値が必要で、候補なしは判定不要です。0〜1に制限した確率より判定値が小さい場合だけ成立し、等値は不成立です。

成功結果のscopeはstatus_cure_quoteで、cured・cured_name・candidate_index・roll_required・cure_chanceと独立したremaining_status_effectsを返します。認識する状態キーは文字列id/display_nameとboolのremovableです。未知IDとJSON互換の拡張キーは情報として保持し、継続効果を実装済みとしません。未知要求・不正型・非有限/精度超過・深さ32超過や必要判定値の欠落は拒否します。原本・保存JSON/schema・Session/snapshotは変更せず、既存HP回復APIの治療付き定義拒否も維持します。Session実治療は専用行動から状態所有者へ委譲します。AI・画面は未接続です。

### GDScriptの単体HP回復予測（実行時だけ）

[回復スキル予測契約](GDScript回復スキル予測契約.md)は、kind:healのsmall_heal/healyと互換MOD定義に、current_mp・target_hp・target_max_hpだけを渡して使います。結果はscope:heal_skill_quoteとし、最大HPで制限する前のheal_amount・実回復量の予測healed・remaining_hp・mp_cost・remaining_mpを返します。満HPではhealedが0でもMP消費を予測します。治療付きspirit_recover・未知効果/要求・MP不足・不正資源や精度超過は拒否します。対象HP0の数値予測は復活許可を意味しません。原本・実資源・Session・保存JSON/schemaは変更せず、AI・戦闘画面は未接続です。

### GDScriptの単体HP回復行動（実行時だけ）

[回復スキル行動契約](GDScript回復スキル行動契約.md)のresolve_heal_skillは、厳密な{ticket,target,skill_id}だけを受けます。targetは本人を含む同陣営の生存個体で、敵・欠落・死亡・逃走対象を拒否します。最新予約・習得・許可装備とSessionの現在MP/対象HPを検証し、単一claim→MP消費→最大HPまでの実HP回復→finishを実行します。満HPでもMPを払い、guard・耐性・魔力・攻撃用装備補正は回復量に使いません。

回復行動の結果はscope:explicit_heal_skill_onlyとし、予測numbersと別に実消費spent_mp・実回復healed・独立sessionを返します。要求側の回復率や資源の上書き・治療付きspirit_recover・未知効果/装備補正を拒否し、不正・不足では予約と資源を保持します。snapshotの6キー、正規data/assets・個体/AI/items/partyの保存JSON/schemaは変更しません。治療・AI・戦闘画面は未接続です。

### GDScriptの単体魔法行動（実行時だけ）

[単体魔法行動契約](GDScript魔法スキル行動契約.md)の開始情報には、既存snapshot・skill_ids・equipmentと別に、種族と許可装備から再構築したresistances辞書があります。snapshotのidentity・stats・hp・mp・fled・aliveという6キーと、保存JSON/schemaは変更しません。

resolve_magic_skillは厳密な{ticket,target,skill_id,variance}だけを受けます。最新予約・習得・敵対象・現在MP/HPを検証し、一回分のclaim→実MP支払い→ダメージまたは最大HPで止まる吸収回復→finishを行います。会心値・耐性・威力・MPの要求側上書きは拒否します。無効・満タン吸収でもMPを消費し、基本ぼうぎょは魔法を軽減しません。不正・未対応・不足は予約と資源を保持し、死亡/逃走/敵なし取消は資源を消費しません。AI・戦闘画面・全スキルは未接続です。

### GDScriptの吸MP魔法予測（実行時だけ）

[吸MPスキル予測契約](GDScript吸MPスキル予測契約.md)はkind:drain_mpと任意のmp_power（省略時0.12）を持つ既存形式の定義を使います。通常魔法の要求に非負整数のactor_max_mp/target_mpを加え、MP消費後の敵MP喪失と術者最大MPまでの回復を別々に予測します。結果はscope:drain_mp_skill_quote、mp_after_payment・drained_mp・recovered_mp・remaining_target_mp・吸収後remaining_mp等です。敵HP0でもMP吸収を予測し、無効/吸収耐性ではMP吸収しません。予測APIは実HP/MP・Session・保存JSON/schemaを変更しません。Session実適用は次の専用入口へ接続し、AI・画面は未接続です。未知効果/要求はfalse・0・空でも拒否します。

### GDScriptの吸MP魔法行動（実行時だけ）

[吸MPスキル行動契約](GDScript吸MPスキル行動契約.md)のresolve_drain_mp_skillは、厳密な{ticket,target,skill_id,variance}だけを受けます。術者の最大MP・敵の現在MPは最新Sessionから取得し、要求側のMP・係数・喪失量・回復量の上書きを拒否します。吸MP行動は最新予約・習得・許可装備・敵対象・資源を検証し、単一claim→実MP消費→敵HP効果→敵MP喪失→術者MP回復→finishを行います。吸MP行動は敵撃破後もMPを奪い、術者の最大MPで回復を制限します。無効/吸収耐性ではMPを奪わず、不正・不足・取消・重複では追加消費しません。

吸MP行動の結果はscope:explicit_drain_mp_magic_onlyとし、予測numbersと別に実消費spent_mp・敵の実喪失drained_mp・術者の実回復recovered_mpを返します。数値資源APIのrestore_mpは非負整数を検証し、空きMPで制限した実回復量を返します。restore_mpはHP・fled・予約・段階を変えず、死亡/逃走個体への数値MP回復も復活・逃走解除を意味しません。snapshotの6キー・正規data/assets・個体/AI/items/partyの保存JSON/schemaは変更しません。通常/自傷の魔法入口は吸MPを拒否し、AI・戦闘画面は未接続です。

### GDScriptの自傷魔法予測（実行時だけ）

[自傷魔法予測契約](GDScript自傷魔法予測契約.md)は、既存スキルのself_damage_ratioと通常魔法の数値要求にactor_hp/actor_max_hpを加えて使います。対象への魔法効果の後に、最大HP基準の代償と術者HP1の下限を予測します。結果はscope:self_damage_magic_quoteとし、self_damage（計算上の代償）・self_dealt（実減少）・remaining_actor_hp等を返します。予測APIは原本・実HP/MP・Sessionを変更しません。実適用は次の専用入口へ接続し、通常魔法の入口は自傷を拒否します。

### GDScriptの自傷魔法行動（実行時だけ）

[自傷魔法行動契約](GDScript自傷魔法行動契約.md)のresolve_self_damage_magic_skillは、厳密な{ticket,target,skill_id,variance}だけを受けます。術者の現在HP・最大HPはSessionから取得し、要求側での上書きを拒否します。最新予約と習得・許可装備・敵対象・資源を検証し、単一claim→実MP消費→敵効果→術者のself_dealt適用→finishを行います。無効・吸収・最後の敵の撃破でも代償が発生し、HP1を残します。不正・不足・取消・重複で追加消費しません。結果のscopeはexplicit_self_damage_magic_onlyです。snapshotの6キー、正規data/assets、個体/AI/items/partyの保存JSON/schemaは変更しません。AI・戦闘画面は未接続です。

### GDScriptの状態一件の付与予測（保存形式変更なし）

[状態付与予測契約](GDScript状態付与予測契約.md)のquote_applicationはeffect/status_effectsと任意resistance_level/rollを受け、重複防止・状態耐性倍率・明示判定から一件付与後の独立resulting_status_effectsを返します。prepare_applicationはrollを受けず、成功率と判定要否を返します。新規IDの前後空白だけを正規化し、成立時の候補からchanceを除き、display_name/removableの省略値を補います。付与予測は未知MOD IDとJSON互換拡張情報を保持しますが、拡張効果を実行しません。

付与予測のscopeはstatus_apply_quoteです。IDなし・重複・確率0以下・無効耐性ではroll不要、正の確率では1でもroll必須です。付与予測は指定済み不正roll・未知要求を拒否します。現在一覧の形式検査は治療と共用し、原本・実状態・数値snapshot・保存JSON/schemaは変更しません。状態所有者/参加者集合/取得済みSession予約への実更新は専用入口へ接続しました。付与付き攻撃行動・継続効果・AI・画面は未接続です。

### GDScriptの個体状態所有者による一件付与（保存形式変更なし）

[戦闘状態一覧契約](GDScript戦闘状態一覧契約.md#最新一覧への一件付与)のprepare_applicationはeffectと任意resistance_levelだけを受け、最新一覧で判定値の要否を返します。quote_application/applyは任意rollも受け、外部一覧/古い予測の持ち込みを拒否します。実付与applyはscope:combatant_status_applyで一件追加後の独立resulting_status_effectsを返し、成立した新規候補だけを別コピーして所有一覧へ追加します。同IDは重ねず、予測/不成立/拒否で状態を変更しません。治療後は同IDを再付与できます。

個体状態所有者の付与は数値snapshot六キーと保存JSON/schemaを変更しません。個体状態所有者はHP/MP・生死・逃走・行動予約・スキル条件・耐性再構築を持たず、Session予約の付与接続は専用入口で扱います。付与付き行動・継続効果・保存・AI・画面は未接続です。

### GDScriptの参加者状態集合への一件付与（保存形式変更なし）

[参加者状態付与契約](GDScript参加者状態付与契約.md)のbattle_status_stateはprepare_application/quote_application/applyへkeyとrequestを受けます。keyはallies/enemiesのsideと個体idだけで、同IDも陣営別に索引で対象を選びます。初期化・形式・存在を確認した後、状態集合は個体の最新一覧による準備/予測/一件追加へ委譲し、他の参加者を変更しません。外部一覧/古い予測は拒否し、返却値は所有状態と独立です。

状態集合の付与結果は個体のstatus_apply_quoteまたはcombatant_status_applyを維持し、全体snapshotはteamsとscope:battle_status_only、個別readはokとstatus_effects一キーのsnapshotです。数値Session七キー/個体六キーと保存JSON/schemaは変更しません。付与のSession予約/攻撃行動・HPMP・生死/逃走条件・耐性再構築・継続効果・保存・AI・画面は本集合の責務外です。

### GDScriptの取得済み予約による一回付与（保存形式変更なし）

[予約付き状態付与契約](GDScript予約付き状態付与契約.md)のSession.apply_status_application(ticket, target, request)は、現在取得済みの厳密round/slot/actorと最新生存を確認し、effectと任意resistance_level/rollだけを所有状態へ渡します。対象は生存する味方/敵/本人で、スキルの対象制限や消費MPを代用しません。外部一覧/古い予測/未知要求は拒否し、数値資源・防御倍率・予約段階を変更しません。

内部claimed_status_updatesは正常な付与判定を一予約一回に制限します。IDなし/重複/確率0/無効/不成立も使用済みとなり、二回目はstatus_application_already_appliedです。不正要求は使用済みにせず、入力を修正して再試行できます。既存治療と付与は各一回の独立制限です。実結果はcombatant_status_apply、数値Session七キー/個体六キー、保存JSON/schemaを維持します。付与付き攻撃行動・耐性再構築・継続効果・保存・AI・画面は未接続です。

### GDScriptの付与付き単体物理予測（保存形式変更なし）

[付与付き物理予測](GDScript状態付与付き物理予測契約.md)のprepareは対応physical定義のstatus_effect辞書を必須にし、従来物理と付与の検証を共用します。prepare_quote/quote_damageは既存物理の数値へstatus_effectsと任意status_resistance_level、結果予測だけの任意status_rollを追加します。defenseは現在状態の補正済み値で、契約は状態から能力を再構築しません。

結果はscope:status_physical_skill_preparationまたはstatus_physical_skill_quoteとphysical/status/status_eligibleです。実dealtが正で残HPも正のときだけ付与を予測し、致死/ダメージなしは確率0・roll不要で一覧を保持します。指定済み不正rollと不正/未知条件は部分成功なしで拒否します。正規スキルの付与定義はなく、独立MOD形式で検証します。従来入口の拒否、数値/保存JSON/schemaを維持し、実行/予約・能力補正・魔法/全体・AI・画面は未接続です。状態耐性の種族再構築と実行準備は専用契約へ接続しました。



### GDScriptの付与付き物理実行準備（保存形式変更なし）

[実行準備契約](GDScript状態付与付き物理準備契約.md)のprepareは、再構築済みteams/skillsと、全参加者に一致する明示initial_statusesを検証します。結果はsnapshots/context/initial_statusesで、context.membersの各side/idはskill_ids/equipment/status_resistancesを保持します。純粋準備ではstatus_resistancesの欠落を拒否し、Builderは種族定義の省略時だけ空辞書を補います。

Builderのstatus_resistancesは属性resistancesと独立し、Pythonと同じく装備の属性resistance_stepsや＋選択を状態耐性へ加えません。未知の文字列耐性名は保持して既存付与契約へ渡します。数値snapshot六キー/Session七キー、正規データと保存JSON/schemaは維持します。初期状態の検証/コピーは治療準備と共用します。

専用selectは習得済みの付与付きphysical定義と選択IDの装備補正だけを返し、通常物理入口の付与拒否を維持します。準備/選択はHPMP・状態・予約・保存を実更新せず、専用開始とSession/Applicationの非消費検査へ接続しました。実攻撃・状態能力補正・AI・画面は未接続です。


### GDScriptの付与付き物理の非消費検査（保存形式変更なし）

[開始/検査契約](GDScript状態付与付き物理検査契約.md)は初回ラウンド前のSessionと数値/初期状態が一致した場合だけ非公開contextを保持します。Application.start_with_statusesは候補Session/各行動/検査と初回ラウンドが全成功した場合だけ参照を公開し、従来startは専用検査を設定しません。

inspect_status_physical_skillの要求はticket/target/skill_idの三キーだけです。検査は最新offered・習得/定義/許可装備・敵対象・実行可能者の最新MP/対象生存を確認します。成功scope=status_physical_preflight_onlyは非消費の読取で、独立ticket/eligibility/skill/equipment・actor_resources/target_resources・actor_status/target_status・target_status_resistances/target_guardを返します。stats_scope=before_status_modifiersは状態補正前のstatsを示します。

検査は乱数/外部状態/定義の指定、未知キー、取得済み/古い予約を拒否します。行動不能者はeligibility.can_act=falseとして区別し、検査は予約取消/claim/HPMP変更/状態付与を行いません。検査結果は実行許可/最終ダメージではなく、数値/保存JSON/schemaと通常物理の付与拒否を維持します。
