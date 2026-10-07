# GDScript単体魔法スキルの予測契約

## 背景と目的

GDScript版は、Python版の戦闘計算を小さな実装単位で移植します。この契約は、正のMPを消費する単体魔法の定義と属性耐性を検証し、使用した場合のHPとMPを予測します。予測処理は入力を変更せず、実際の行動権取得・MP支払い・HP更新・AI選択・画面表示・保存を行いません。

開発者は、[移行実装単位](ワークフロー/GDScript移行実装単位.md)で進捗を確認してください。物理スキルは別の[物理予測契約](GDScript物理スキル予測契約.md)と[物理行動契約](GDScript物理スキル行動契約.md)に従います。

## 実装と対応範囲

`gdscript/engine/magic_skill_contract.gd`は、スキルの定義検証とMP不足判定を行います。`gdscript/engine/magic_numbers.gd`は、魔力・威力・耐性からHPの変化を計算します。通常ダメージの最終整数化とHP下限は、既存の`attack_numbers.gd.finish_damage`を共用します。各処理はファイル・Session・乱数源・AI・UIに依存しません。

この単位は正規スキル`weaken`（ちからぬき）と同じ形式のMOD魔法に対応します。自傷付きの`metal_burst`、吸MPの`possess`、ランダム魔法の`dice_magic`は対応しません。状態異常、全体攻撃、回避、反撃、味方保護等も対象外です。未対応の定義キーや要求キーがある場合、値がfalse・0・空でも拒否します。

### 定義を選択するAPI

開発者は`Contract.prepare(document, skill_id)`へ、`schema_version: 1`と`skills`配列を持つ一覧、および選択するIDを渡してください。処理は選択したIDだけを検証し、欠落または重複を拒否します。成功時の`skill`は原本と独立した辞書です。

定義に使用できるキーは`id / display_name / description / kind / power / element / mp_cost`です。`kind`は`magic`に限定します。IDと表示名は空でない文字列、説明は省略可能な文字列です。通常攻撃ID`attack`と防御ID`defend`は拒否します。

`power`省略時の威力は1.0、`element`省略時の属性は`physical`です。属性名は空でない文字列とし、MOD固有の名前も使えます。`mp_cost`はPythonの`int`と同じく0方向へ切り捨てた後に正である必要があります。有限数値と数値文字列は既存の数値変換規則で検証し、bool・非有限値・整数精度上限超過は拒否します。

### 結果を予測するAPI

開発者は`Contract.quote_damage(definition, request)`へ、対応する魔法定義と次の要求を渡してください。`prepare`を省略して直接定義を渡しても、同じ定義検証を行います。

| 要求キー | 意味と条件 |
| --- | --- |
| `magic` | 行動者の魔力です。Python互換の整数変換を行います。 |
| `current_mp` | 行動者の現在MPです。非負の整数値とし、文字列や小数部分のある値は拒否します。 |
| `target_hp` | 対象の現在HPです。整数値とし、0以上かつ最大HP以下に限定します。 |
| `target_max_hp` | 対象の最大HPです。正の整数値に限定します。吸収回復の上限に使います。 |
| `variance` | 呼出元が用意する0.92〜1.08の揺らぎです。予測処理は乱数を生成しません。 |
| `target_resistances` | 属性名をキー、耐性名を値とする辞書です。省略時は空辞書とし、使用する属性の欠落は等倍として扱います。使用しない属性の値は検証しません。 |
| `fixed_bonus_damage` | 装備による固定追加ダメージの数値投影です。省略時は0とし、Python互換の整数変換を行います。装備JSON自体は受け取りません。 |
| `guard` | 対象の防御倍率です。省略時は1.0とし、有限数値として検証しますが魔法の軽減には使いません。 |

現在HP・最大HPにも文字列と小数部分のある値は使用できません。数値入力と計算結果は、JSONとの受け渡しで整数を正確に表せる`±9007199254740991`以内に限定します。有限な入力同士の計算でも、その精度範囲を超えた場合は拒否します。

正のMP消費量が現在MPを超える場合、結果は`ok: false / reason: insufficient_mp`です。成功時の`remaining_mp`は現在MPから消費量を引いた予測値であり、無効・吸収でも同じように消費量を差し引きます。予測成功は、死亡者が行動できることやSessionの行動権取得を保証しません。

## Python正本と一致させる計算

数値の比較先は`src/kadoka_quest/core/battle.py`の`RESISTANCE_MULTIPLIER`と`BattleEngine._attack`です。反撃を無効にした単体魔法のHP計算だけを比較します。

| 選択属性の耐性名 | 倍率 | HPへの効果 |
| --- | ---: | --- |
| `normal` | 1.0 | 通常ダメージを与えます。 |
| `weak` | 1.4 | 弱点倍率のダメージを与えます。 |
| `strong` | 0.6 | 耐性倍率のダメージを与えます。 |
| `immune` | 0.0 | ダメージも回復もなく、HPを保持します。 |
| `absorb` | -0.5 | 生ダメージの絶対値に応じて回復します。 |
| 未知の文字列 | 1.0 | Python正本と同じ等倍にし、`resistance_known: false`で未知値と分かるようにします。 |

通常ダメージは`int(魔力 × 威力 × 耐性倍率)`へ整数化した装備追加値を足し、その後に揺らぎを掛けて0方向へ切り捨てます。最終ダメージは最低1、実際のHP減少量は現在HP以下になります。対象の防御力、物理攻撃倍率、会心、装備のスキル威力倍率は使いません。属性名が`physical`でも、`kind: magic`なら防御倍率による軽減はありません。

無効の場合は、装備追加値と揺らぎをHPへ適用しません。吸収の場合は、装備追加値を足さず、生ダメージの絶対値へ揺らぎを掛けた整数を最低1の回復量にします。回復後HPは最大HP以下となり、満HPの対象の実回復量は0です。負の威力もPython正本と同じ計算を行います。

成功結果には`ok / scope: magic_skill_quote / skill_id / mp_cost / remaining_mp / element / resistance_kind / resistance_multiplier / resistance_known / effect / raw_damage / damage / dealt / healed / remaining_hp / applied_guard / variance`があります。`effect`は`damage / immune / absorb`です。`raw_damage`は揺らぎ適用前の整数で、通常ダメージでは装備追加値を含みます。`damage`は通常ダメージの最低1を適用した値で、無効・吸収では0です。`dealt`は実際のHP減少量で、吸収時は実回復量を負で表します。`healed`は実回復量です。吸収時だけ、上限適用前の回復量`recovery`も返します。`applied_guard`は常に1.0です。

## 開発者の実行方法

開発者はリポジトリのルートで、使用できるGodot実行ファイルとPython環境を指定して次の検証を実行してください。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotの実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_magic_skill.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_magic_skill.py
```

専用プローブは一時要求JSONだけを読み取り、正規データや実セーブへ書き込みません。性能検査は20000回・7サンプル・2000回の事前実行で予測1回の中央値を測ります。中央値3000マイクロ秒以内、期待したHP/MP予測、入力不変のすべてが成立した場合だけ成功します。描画・ファイル読込・Godot起動・実MP消費の性能は測りません。

Godot未指定時のテストスキップや性能検査の終了コード2は未検証です。開発者はGodotを指定して再実行してください。拒否結果には`reason`があるため、開発者は不正数値・MP不足・重複・未対応キーを区別し、原本を勝手に補修せず入力を確認してください。Godotの解析・実行診断があれば、計測値が出ても検証失敗になります。

## この単位で保証しないこと

実際の魔法行動、SessionへのHP/MP適用、習得と装備許可の照合、回避・状態異常・自傷・吸MP・反撃・全体攻撃、戦闘画面、AI、勝敗と報酬、復活、実GUI、配布export、リモートCIはこの予測契約の保証対象外です。JSON保存形式と正規データは変更しません。

[コードの入口を確認する](CODEMAP.md) / [GDScript開発案内へ戻る](../gdscript/README.md)
