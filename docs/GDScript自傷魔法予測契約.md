# GDScript自傷付き単体魔法の予測契約

## 背景と目的

GDScript版は、Python版の戦闘を小さな単位で移植します。自傷付きの`metal_burst`（メタルバースト）は、敵への魔法効果と術者のHP代償を持つため、追加効果のない魔法とは別の検証が必要です。この契約は、定義・敵への効果・術者の代償・残MPを予測します。予測は入力を変更せず、実際の行動権取得・資源更新・AI判断・画面表示・保存を行いません。

## 実装と定義の選択

開発者は`gdscript/engine/self_damage_magic_contract.gd`の`prepare(document, skill_id)`へ、`schema_version: 1`と`skills`配列を持つ一覧、および空でない文字列IDを渡してください。処理は指定IDの欠落・重複を拒否し、成功時に原本と独立した`skill`辞書を返します。未選択の定義は変更しません。

一覧からの一意な選択は`magic_skill_contract.select_definition`と共用します。この共用APIは一覧の形式とIDの一意性だけを検証するため、選択結果だけでは効果の対応可否を保証しません。通常魔法の`prepare`と自傷魔法の`prepare`が、それぞれの対応効果を検証します。

定義は[通常魔法の予測契約](GDScript魔法スキル予測契約.md#定義を選択するapi)の`id / display_name / description / kind / power / element / mp_cost`に、必須の`self_damage_ratio`を加えた形式です。`kind`は`magic`、整数化後の`mp_cost`は正とします。自傷率は有限数値または有限の数値文字列を使用できます。bool・欠落・null・非有限値・精度上限超過は拒否します。状態異常、全体攻撃、吸MP、ランダム攻撃等の未対応キーは、false・0・空でも拒否します。

`prepare`は自傷率の元の表現を保持します。Python正本では数値の`0`は自傷なしですが、文字列の`"0"`は真として判定され、最低1の代償が発生します。正の率だけに制限せず、有限の負の率もPythonと同じ最低1の代償になります。MODのこれらの数値を独自に補修しません。

## 数値を予測するAPI

開発者は`quote_damage(definition, request)`へ、自傷付き魔法定義と数値要求を渡してください。`prepare`を省略しても同じ定義検証を行います。要求は[通常魔法の数値要求](GDScript魔法スキル予測契約.md#結果を予測するapi)に、次の2キーを加えます。

| 追加する要求キー | 意味と条件 |
| --- | --- |
| `actor_hp` | 術者の現在HPです。正の整数値かつ最大HP以下とします。死亡者の復活は予測しません。 |
| `actor_max_hp` | 術者の最大HPです。正の整数値とし、HP代償の基準に使います。 |

術者HPは文字列・bool・小数部分のある値を拒否します。小数表現でも整数と同値なら使用できます。数値入力と計算結果は、JSONで整数を正確に表せる`±9007199254740991`以内に限定します。有限な最大HPと率でも、積が精度範囲を超えた場合は拒否します。未知の要求キーは無視しません。

敵と術者は別の戦闘個体を前提とします。このAPIは個体IDや行動票を受け取らず、同一個体への効果合成・行動可否・習得・装備許可を判断しません。対象HP0は通常魔法と同じ数値プレビューとして許可しますが、死亡した敵への実行や回復の許可を意味しません。MP不足なら`ok: false / reason: insufficient_mp`を返します。

## Python正本と一致させる順序とHP下限

比較先は`src/kadoka_quest/core/battle.py`の`BattleEngine._attack(allow_counter=False)`です。回避・反撃は対象外です。

1. 対象への通常ダメージ・無効・吸収を、既存の`magic_skill_contract`で予測します。魔法には物理防御倍率を適用しません。耐性・揺らぎ・固定追加値・整数化・HP上限の規則は通常魔法と共用します。
2. 元の自傷率がPythonの真偽判定で有効な場合、代償量を`max(1, int(actor_max_hp × float(self_damage_ratio)))`とします。数値0の場合は代償量0です。
3. 術者の予測後HPを`max(1, actor_hp − 代償量)`とします。対象が魔法を無効化・吸収しても代償は発生します。HP不足で使用予測を拒否せず、術者のHP1を残します。

対象の効果と術者の代償は純粋計算です。結果として順序を表すだけで、HP/MPへ書き込みません。術者の防御力・耐性・揺らぎは代償量に使いません。無効・吸収でも使用時の残MPを消費量だけ減らして予測します。

成功結果は通常魔法のHP/MP予測を保持し、`scope`を`self_damage_magic_quote`にします。次の術者情報を加えます。

| 結果キー | 意味 |
| --- | --- |
| `self_damage` | HP1の下限で制限する前の計算上の代償量です。Pythonの代償ログに対応します。 |
| `self_dealt` | HP1の下限で制限した、実際の術者HP減少の予測量です。 |
| `remaining_actor_hp` | 代償後の術者HP予測です。最低1になります。 |
| `self_damage_ratio` | 有限数値へ変換した自傷率です。定義の元の表現は`prepare`の`skill`に保持します。 |
| `self_damage_enabled` | 元の率のPython互換の真偽判定で、代償が有効かどうかを示します。 |

たとえば最大HP123・現在HP7・率0.1では、`self_damage: 12 / self_dealt: 6 / remaining_actor_hp: 1`になります。現在HP1なら実減少は0ですが、計算上の代償量は12です。

## 開発者の実行方法と失敗時の対応

開発者は使用できるGodotとPythonを指定し、リポジトリのルートで次の検証を実行してください。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotのconsole実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_self_damage_magic.py tests/test_gdscript_magic_skill.py tests/test_gdscript_magic_action.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_self_damage_magic.py
```

テストは専用の要求JSONと一時戦闘個体を使い、実Godotと実Pythonの攻撃計算を比較します。反撃は無効にし、揺らぎだけを固定します。AI選択・実MP支払いの比較ではありません。プローブは元の要求ファイルのbyte、入力辞書、返却コピーの独立性も確認します。

性能検査は20000回・7サンプル・2000回の事前実行で、予測1回の中央値を測ります。中央値3000マイクロ秒以内、敵HP800・術者HP80・残MP2の予測、元の敵HP1000・術者HP100・MP20と入力の保持がすべて成立した場合だけ成功します。起動・読込・描画・実資源更新の性能は測りません。通常魔法と同じプローブの測定ループを使用します。

Godot未指定によるスキップや終了コード2は未検証です。開発者はGodotを指定して再実行してください。解析・実行診断があれば結果が出ても失敗とします。拒否結果の`reason`が`invalid_self_damage_ratio / invalid_actor_hp / invalid_self_damage_numbers`の場合は、それぞれ定義の率・術者資源・演算精度を確認してください。他の理由は通常魔法の契約に従います。入力を勝手に補修しないでください。

## 未接続・未検証の範囲

通常魔法の入口は、自傷付き魔法を引き続き拒否します。専用入口での習得・許可装備・最新行動票の検証とSessionへの実適用は、別の[自傷魔法行動契約](GDScript自傷魔法行動契約.md)へ接続しました。この予測API自体は非破壊のままです。回避・状態異常・反撃、AI、戦闘画面・演出、勝敗・報酬・教会復活、実GUI・配布export・リモートCIは別の単位です。保存JSON/schema、正規data/assetsは変更しません。

[移行実装単位](ワークフロー/GDScript移行実装単位.md) / [コードの入口](CODEMAP.md) / [GDScript開発案内](../gdscript/README.md)
