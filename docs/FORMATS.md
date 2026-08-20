# JSON formats

すべてUTF-8、JSONオブジェクトをルートに持ちます。`schema_version` は現在 `1` です。未知の追加キーは基本的に無視するため、MOD側でメタデータを加えられます。

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

`appearance.type` は `color` または `path`。`path` の値は `assets/appearance/` からの相対パスです。

## Map

`data/maps/<id>/map.json`

`tiles` は高さ行・幅列のブロックID配列です。`spawns` が空なら敵は何も湧きません。出現表から作られた野生モンスターは画面には描かれず、`enemy_walkable` なブロックを裏で歩きます。プレイヤーと同じマスへ来たときに戦闘になります。

```json
{
  "id": "greenwood",
  "width": 48,
  "height": 32,
  "start": {"x": 6, "y": 5},
  "tiles": [["grass"]],
  "spawns": [
    {"species_id": "slime", "weight": 50, "min_level": 2, "max_level": 5}
  ],
  "events": [
    {"id": "sign", "x": 8, "y": 6, "type": "message", "text": "..."}
  ]
}
```

イベントの主な `type` は `message / transition / church / reacquire_ghosts` です。`transition` は通常そのマスへ乗ると移動し、`"activation": "interact"` を指定すると隣から調べたときだけ移動します。`church` の `revive` は全滅時の復活地点です。`ball_slime` は初期獲得専用のため、出現表へ設定しません。

## Species folder

`data/species/<species_id>/` は起動時にフォルダ単位で発見されます。

- `species.json`: ID、表示、耐性、装備可能カテゴリ、AIプロファイル、再獲得規則
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

装備枠は1つ。カテゴリは `sword / clothes / staff` です。名前が剣でも、爪や重りなど実物の形は問いません。

```json
{
  "id": "ken",
  "category": "sword",
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

## Import

- `imports/acquire/`: 再走査で所有フォルダへコピー。同じ個体IDは上書きしない
- `imports/simulation/`: コピーせず読み取り、模擬戦だけで使用。AI更新なし

