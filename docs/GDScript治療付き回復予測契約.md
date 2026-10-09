# GDScriptの治療付きHP回復予測契約

## 具体例と目的

例えば、術者のMPが10、対象のHPが99/100、状態が「解除不可の拘束・毒・眠り」の順である場合に、`spirit_recover`の結果を予測します。回復率3%から回復上限量は3、最大HPまでの実回復量は1、消費後MPは6です。治療成功率3%に対して判定値0.02を渡すと、拘束を飛ばして毒一つを除いた新しい一覧を返します。満HPでもMP消費と治療を予測します。

この契約は、Python版`BattleEngine._take_action`の回復分岐をGDScriptへ移すための純粋な予測単位です。HP回復は`heal_skill_contract`、候補選択と治療判定は`status_cure_contract`へ委譲し、同じ計算を二重実装しません。定義検証は既存回復契約の`validate_definition`を使い、不正なネスト値を検証前に深くコピーしません。この共用入口も治療キーそのものは拒否したままです。結果の取得は実際のMP消費・HP更新・状態除去を意味しません。AI、対象選択、Sessionの実行予約や戦闘画面は担当しません。

入口は`gdscript/engine/cure_heal_skill_contract.gd`です。開発者はGodot内で、次の定義と要求を`Contract.quote_heal(definition, request)`へ渡してください。本書の`Contract`は`preload("res://engine/cure_heal_skill_contract.gd")`で取得するスクリプト名です。

```json
{
  "definition": {
    "id": "spirit_recover", "display_name": "きあいでなおす",
    "kind": "heal", "heal_ratio": 0.03, "mp_cost": 4,
    "status_cure_chance": 0.03
  },
  "request": {
    "current_mp": 10, "target_hp": 99, "target_max_hp": 100,
    "status_effects": [
      {"id": "lock", "removable": false},
      {"id": "poison", "display_name": "毒"},
      "sleep"
    ],
    "roll": 0.02
  }
}
```

この例の結果は`ok: true`、`scope: "cure_heal_skill_quote"`、`heal_amount: 3`、`healed: 1`、`remaining_hp: 100`、`remaining_mp: 6`、`cured: true`、`cured_name: "毒"`です。`candidate_index: 1`で、`remaining_status_effects`には拘束と眠りが順に残ります。定義・要求・状態の拡張情報は原本を変えず、返却値を編集しても原本へ伝播しません。

## 定義の対応範囲

開発者は一覧から選ぶ場合、`Contract.prepare(document, skill_id)`へ`schema_version: 1`と`skills`配列のある一覧を渡してください。指定IDが一つだけ存在し、下記の定義検証を通れば、独立した正規化済み`skill`を返します。IDの欠落・重複・不正一覧は拒否します。

| 定義キー | 条件と扱い |
| --- | --- |
| `id / display_name` | 必須の空でない文字列です。IDのattack/defendは予約済みなので拒否します。 |
| `description` | 省略可能な文字列です。 |
| `kind` | healだけを許可します。 |
| `mp_cost` | 必須です。有限数値または整数文字列を0方向へ切り捨て、結果が正の整数なら許可します。 |
| `heal_ratio` | 有限数値または数値文字列です。省略時は0.15、負値/0も最低回復量1の計算へ進めます。 |
| `status_cure_chance` | 必須の有限数値または数値文字列です。判定時に0〜1へ制限します。 |

bool・null・非有限値・絶対値が`9007199254740991`を超える数値は拒否します。未知キーはfalse・0・空でも無視しません。通常HP回復のsmall_heal/healyは治療確率がないためこの入口では拒否し、既存[HP回復予測契約](GDScript回復スキル予測契約.md)を使います。その既存入口が治療付きspirit_recoverを拒否する境界も維持します。

## 要求と予測手順

要求の許可キーは`current_mp / target_hp / target_max_hp / status_effects / roll`だけです。開発者は術者の現在MPと指定対象の現在/最大HPを渡してください。資源は非負の整数数値に限定し、最大HPは正、現在HPは最大HP以下とします。整数相当のfloatは許可し、文字列・bool・小数部分・非有限値・精度上限超過は拒否します。

処理は定義と許可要求キーを検証し、HP回復契約へ資源を渡します。MP不足なら治療一覧・判定値の検証前に`insufficient_mp`を返します。資源を満たす場合、回復上限量を`max(1, int(対象最大HP × heal_ratio))`で求め、最大HPまでの空き量で実回復を制限します。満HPでも積を検証し、積の精度超過を拒否します。魔力・装備倍率・耐性・基本ぼうぎょは回復量に使いません。

続いて治療契約へ状態一覧、定義の治療確率、明示判定値を渡します。`status_effects`は必須です。文字列/辞書の順序を保持し、最初の解除可能な候補一件だけを判定します。辞書の`removable`省略と文字列は解除可能です。状態キーの型、未知ID、JSON互換の拡張情報、深さ上限と表示名の規則は[状態治療予測契約](GDScript状態治療予測契約.md)と同じです。

`roll`は省略またはnullなら未指定です。候補があれば確率0/1でも、0以上1未満の有限数値を必ず渡してください。候補なしでは判定値を要求しませんが、指定済みの不正値は拒否します。`roll < 制限後の治療確率`なら一件を除き、等値では治りません。処理は乱数を生成/消費しません。

両計算が成功した場合だけ統合結果を返します。状態や判定値が不正なら、HPだけの部分成功は返しません。対象HP0の数値予測は復活許可を意味せず、実行側が死亡対象を回復対象に選べることも保証しません。

## 結果と拒否への対応

| 成功結果 | 意味 |
| --- | --- |
| `ok / scope / skill_id` | true、固定区分cure_heal_skill_quote、使った定義IDです。 |
| `heal_amount / healed / remaining_hp` | 最大HP制限前の回復上限量、実回復量の予測、回復後HPの予測です。 |
| `mp_cost / remaining_mp` | 消費MP、消費後MPの予測です。 |
| `candidate_index / roll_required` | 候補の位置と判定値の要否です。候補なしは-1/falseです。 |
| `cure_chance / cured / cured_name` | 制限後の確率、治療成立、治療名です。不成立時の名前はnullです。 |
| `remaining_status_effects` | 成立なら一件を除き、不成立なら全件を保持した独立コピーです。 |

拒否結果は`ok: false / reason`だけです。未知定義キーは`unsupported_cure_heal_skill`、未知要求キーは`unsupported_cure_heal_request`です。必須治療確率の欠落/不正は`invalid_cure_chance`、状態不正は`invalid_status_effects`、判定値不正は`invalid_cure_roll`、必要判定値の欠落は`missing_cure_roll`です。回復定義・資源・MP不足・回復積の拒否理由は既存HP回復契約から返します。開発者は該当入力を確認し、原本や保存JSONを自動補修しないでください。

## 開発者の実行方法と完了確認

開発者はリポジトリルートで、使えるGodotとPythonの実行ファイルを指定して次の検証を実行してください。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotの実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_cure_heal_skill.py tests/test_gdscript_status_cure.py tests/test_battle_status_cure.py tests/test_gdscript_heal_skill.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_cure.py --cure-heal
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_cure.py
```

テストは行動選択だけを固定した学習なしのPython正本で実回復分岐を呼び、HP/MP・一件治療・乱数要否を実Godotと比較します。返却値の編集後も原本と再実行結果が変わらないこと、専用ダミーの個体/AI/items/party/stateと要求ファイルのbyte不変も確認します。正規data/assetsと利用者セーブは書き換えません。

`--cure-heal`の標準性能検査は、HP990/1000・MP10の対象に回復上限30/実回復10と、解除不可2件の後の毒一件治療を予測します。20000回・7サンプル・2000回事前実行で、一回中央値3000us以内・残HP1000/MP6・毒だけの解除・入力保持がすべて一致した場合だけ成功します。区分を省略したコマンドは既存治療単体経路の性能を測ります。起動・I/O・描画・実更新・AIの時間は含めません。

Godot未指定によるテストスキップと性能終了コード2は未検証です。開発者はGodotを指定して再実行してください。解析/実行診断・期待値不一致・時間超過は失敗です。Session実治療・状態付与/継続効果・AI・戦闘画面・実GUI・配布export・リモートCIはこの単位の検証対象ではありません。保存JSON/schemaと既存Sessionのsnapshotは変更しません。

[コードの入口](CODEMAP.md) / [移行実装単位](ワークフロー/GDScript移行実装単位.md) / [GDScript開発案内](../gdscript/README.md)
