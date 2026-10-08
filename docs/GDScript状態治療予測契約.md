# GDScriptの状態異常一つの治療予測契約

## 具体例と目的

例えば、解除不可の「特殊拘束」の後に「毒」と「眠り」が付いている個体へ、成功率3%・判定値0.02の治療を予測します。`status_cure_contract.quote_cure`は特殊拘束を飛ばし、毒一つだけを除いた新しい一覧を返します。元の一覧は変えず、実際の個体から毒を除いたことにはなりません。

GDScript版の治療付き回復`spirit_recover`を移植するには、HP回復とは別に治療候補と成功判定が必要です。この単位は、Python版`BattleEngine._try_cure_status`の候補順序・表示名・判定を純粋計算として移植します。HP/MPの計算、スキル選択、行動権や戦闘Sessionへの実適用は行いません。既存のHP回復APIは引き続き治療付き定義を拒否します。

入口は`gdscript/engine/status_cure_contract.gd`です。本書の`Contract`は、Godot内で`preload("res://engine/status_cure_contract.gd")`により得るスクリプトの名前です。開発者は、次のような要求を`Contract.quote_cure(request)`へ渡してください。

```json
{
  "status_effects": [
    {"id": "special_lock", "display_name": "特殊拘束", "removable": false},
    {"id": "poison", "display_name": "毒"},
    "sleep"
  ],
  "cure_chance": 0.03,
  "roll": 0.02
}
```

処理は`ok: true`、`cured: true`、`cured_name: "毒"`、`candidate_index: 1`を返します。`remaining_status_effects`には特殊拘束と文字列`"sleep"`が順に残ります。ネスト付き拡張情報も原本と独立したコピーです。

## 状態一覧の対応形式

`status_effects`は順序付き配列です。各要素は文字列または辞書に限定します。文字列は常に解除可能で、治療名は文字列そのものです。辞書では次のキーを認識します。

| 辞書キー | 条件と扱い |
| --- | --- |
| `removable` | 省略時はtrueです。指定時はboolに限定し、falseなら候補から飛ばします。文字列`"false"`や数値0へ読み替えません。 |
| `display_name` | 省略可能な文字列です。空でない場合は治療名に使います。 |
| `id` | 省略可能な文字列です。表示名がない/空の場合はIDを治療名に使います。 |

辞書の表示名とIDが両方ない/空なら、治療名は「状態異常」です。空文字列の状態と空辞書もPythonの候補選択に合わせて許可します。未知のMOD ID・同IDの重複もそのまま保持し、成功しても最初の候補一件だけを除きます。

拡張キーは治療による効果を実行せず、情報として保持します。例えば`duration`やネスト付き`metadata`は失敗/残存時に内容と順序を保持します。拡張キーの保持は、その状態の付与・持続時間更新・出血ダメージ・行動不能を実装済みとする意味ではありません。

一覧全体の値は、null・bool・文字列・有限数値・配列・文字列キーの辞書に限定します。数値の絶対値上限はJSON整数交換の精度範囲`9007199254740991`です。一覧を深さ0とし、子の深さが32を超えた値・循環コンテナ・Object等の非JSON値は拒否します。`id/display_name`のnull・数値への自動変換や、`removable`の任意値の真偽変換は行いません。Pythonが型変換で扱える全入力へ互換範囲を広げる契約ではありません。

## 候補選択と明示判定の手順

開発者は、乱数を用意する必要があるか先に確認する場合、`Contract.select_candidate(effects)`へ状態一覧を渡してください。成功結果は独立した`effects`、候補の配列位置`candidate_index`、判定値を要するかの`roll_required`です。候補なしの位置は-1です。解除不可の辞書だけ、または空一覧では`roll_required: false`になります。

開発者は、その候補と確率を治療予測へ渡すとき、`quote_cure`へ`status_effects / cure_chance / roll`以外のキーを指定しないでください。未知の要求キーはfalse・0・空でも拒否します。

`cure_chance`は必須の有限数値または数値文字列です。bool・非有限値・精度上限超過は拒否します。有限の負値は0、1を超える値は1へ制限します。`roll`は0以上1未満の有限数値だけに限定し、文字列・bool・非有限値は拒否します。省略またはnullは未指定です。

候補がある場合は、確率が0/1でも`roll`が必要です。処理は`roll < 制限後の確率`の場合だけ治療を成立させ、等しい値では成立しません。後続候補への再判定は行いません。候補がない場合は判定値を要求せず、治療不成立と独立した元一覧を返します。候補なしでも指定済みの不正判定値は拒否します。

このAPIは乱数を生成/消費しません。`roll_required`はPython正本がその場合に一回の乱数を使うことを示す情報です。後続の実行側が乱数取得を担当するための契約であり、予測側へ乱数源やAIを渡さないでください。

## 結果と拒否への対応

| 成功結果キー | 意味 |
| --- | --- |
| `ok / scope` | trueと固定区分`status_cure_quote`です。 |
| `candidate_index / roll_required` | 治療候補の位置と、候補による判定値の要否です。判定不成立でも候補位置は保持します。 |
| `cure_chance` | 0〜1へ制限した成功確率です。 |
| `cured / cured_name` | 治療成立と治療名です。不成立時の治療名はnullです。 |
| `remaining_status_effects` | 治療成立なら候補一つを除いた一覧、不成立なら全件を保持した独立コピーです。 |

拒否結果は`ok: false`と`reason`です。要求形式不正は`invalid_cure_request`、未知キーは`unsupported_cure_request`、一覧形式不正は`invalid_status_effects`、確率不正は`invalid_cure_chance`、判定値不正は`invalid_cure_roll`、必要な判定値の欠落は`missing_cure_roll`です。開発者は該当入力を確認し、原本や保存JSONを自動補修しないでください。

## 開発者の実行方法と完了確認

開発者はリポジトリルートで、使えるPythonとGodotの実行ファイルを指定し、次の検証を実行してください。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotの実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_status_cure.py tests/test_battle_status_cure.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_cure.py
```

実Godotと学習なしのPython正本を比較し、候補順序・一件除去・表示名・等値判定・候補なしの乱数0回を照合します。返却値を編集して元要求と再実行結果が不変なこと、専用ダミーの個体/AI/items/party/stateと要求ファイルのbyteが不変なことも確認します。正規data/assetsと利用者セーブは書き換えません。

JSON交換で丸められる「1の直前の小数」は、Godot内で明示生成して上限未満の受理を確認します。数値交換の丸めとAPIの上限判定を混同しないでください。

性能検査は、解除不可2件の後にネスト付き毒と眠りを置き、毒一つを治療する予測を標準20000回・7サンプル・2000回事前実行で測ります。一回中央値3000us以内・期待した一件治療・元一覧保持が全部成立した場合だけ成功します。Godot起動・ファイル読込・描画・AI・Session実更新・保存の時間は含めません。

Godot未指定のテストスキップと性能終了コード2は未検証です。開発者はGodotを設定して再実行してください。解析/実行診断・期待値不一致・時間超過は失敗です。Session実治療・治療付き回復スキル予測・状態付与/持続効果・AI・戦闘画面・実GUI・配布export・リモートCIはこの単位では検証しません。保存形式/schemaと既存Sessionのsnapshotは変更しません。

[コードの入口](CODEMAP.md) / [移行実装単位](ワークフロー/GDScript移行実装単位.md) / [GDScript開発案内](../gdscript/README.md)
