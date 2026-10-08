# GDScript吸MP付き単体魔法の予測契約

## 背景と目的

GDScript版はPython版の戦闘を小さな単位で移植します。吸MP付きのpossess（とりつく）は、敵への魔法効果に加えて、敵のMPを奪い術者のMPを回復する効果を持ちます。この契約は敵HP・敵MP・術者MPを、入力を変更せず予測します。実際の行動権取得・MP支払い・資源更新・AI判断・画面表示・保存は行いません。

## 定義を選択するAPI

開発者はgdscript/engine/drain_mp_skill_contract.gdのprepare(document, skill_id)へ、schema_version: 1とskills配列を持つ一覧、および空でない文字列IDを渡してください。処理は指定IDの欠落・重複を拒否し、成功時に原本と独立したskill辞書を返します。一覧の選択はmagic_skill_contract.select_definitionと共用し、選択後に吸MPの対応効果を検証します。

定義は[通常魔法の定義](GDScript魔法スキル予測契約.md#定義を選択するapi)のid / display_name / description / kind / power / element / mp_costに、任意のmp_powerを加えた形式です。kindは文字列drain_mp、整数化後のmp_costは正とします。power省略時は1.0、element省略時はphysicalを使います。

mp_powerは有限数値または有限の数値文字列を使います。省略時は0.12です。bool・null・非有限値・精度上限超過は拒否します。有限の負値・0もPythonと同じ最低1MPの吸収量になるため、独自に補修しません。prepareはmp_powerを有限floatへ正規化します。状態異常、自傷、全体攻撃、ランダム攻撃などの未対応キーは、false・0・空でも拒否します。

## 数値を予測するAPI

開発者はquote_damage(definition, request)へ、吸MP付き定義と数値要求を渡してください。prepareを省略しても同じ定義検証を行います。要求は[通常魔法の数値要求](GDScript魔法スキル予測契約.md#結果を予測するapi)に次の2キーを加えます。

| 追加する要求キー | 意味と条件 |
| --- | --- |
| actor_max_mp | 術者の最大MPです。非負の整数値で、current_mp以上とします。回復の上限に使います。 |
| target_mp | 敵の現在MPです。非負の整数値とし、奪う量の上限に使います。 |

current_mp・actor_max_mp・target_mpは文字列・bool・小数部分のある値を拒否します。小数表現でも整数と同値なら使用できます。要求に必要な魔力とMP消費量の数値変換は通常魔法と共用し、MP資源そのものの厳密な形式検証とは区別します。target_max_mpは計算に使わず、未知キーとして拒否します。

数値入力と必要な演算結果は、JSONで整数を正確に表せる±9007199254740991以内に限定します。術者回復量は最大MPまでの空き量で先に制限し、加算途中の精度超過を避けます。最大MP0も資源値としては許可しますが、この契約は正のMP消費を要求するため、使用予測はMP不足で拒否します。

敵と術者は別の戦闘個体を前提とします。APIは個体ID・行動票を受け取らず、行動可否・習得・装備許可・同一個体への効果合成を判断しません。敵HP0は数値プレビューとして許可しますが、死亡した敵への実行を許可するものではありません。未知の要求キーは無視しません。MP不足ならok: false / reason: insufficient_mpを返します。

## Python正本と一致させる計算順序

比較先はsrc/kadoka_quest/core/battle.pyのBattleEngine._attack(allow_counter=False)です。テストは独立した戦闘個体へ支払い後MPを設定して比較します。実際のMP支払いを担当する_take_actionの接続検証ではありません。

1. 術者の支払い後MPをcurrent_mp − mp_costとして予測します。
2. 敵への通常ダメージ・無効・吸収回復を、既存magic_skill_contractで予測します。耐性・揺らぎ・固定加算・整数化・HP上限は通常魔法と共用します。魔法には物理防御倍率を適用しません。
3. 選択した属性の耐性がimmuneまたはabsorbなら、MP吸収・回復量を0とします。術者のMP消費は予測に残ります。この分岐では未使用の魔力×mp_powerを計算しません。
4. その他の耐性では、吸MP上限量をmax(1, int(int(magic) × float(mp_power)))とし、敵が失うMPをmin(target_mp, 吸MP上限量)とします。
5. 術者が回復するMPをmin(敵が失うMP, actor_max_mp − 支払い後MP)とします。敵の残MPと術者の吸収後MPを別々に返します。

敵のHPが0になった場合でも、MP吸収は発生します。敵HPダメージが最低1になる場合も、MP吸収量は魔力とmp_powerから別に求めます。弱/強耐性の倍率、揺らぎ、物理防御倍率、装備の固定追加ダメージはMP吸収量を変更しません。未知の文字列耐性と耐性省略は通常魔法と同じ通常扱いです。

成功結果は通常魔法のHP予測・消費量・耐性情報を保持し、scopeをdrain_mp_skill_quoteにします。remaining_mpは吸収後の術者MPです。支払い直後のMPは別のキーで返します。

| 結果キー | 意味 |
| --- | --- |
| mp_after_payment | MP消費量を引いた直後の術者MP予測です。 |
| mp_drain_limit | 敵の残MPで制限する前の吸MP上限量です。無効/吸収では0です。 |
| drained_mp | 敵が実際に失うMPの予測量です。 |
| recovered_mp | 術者が実際に回復するMPの予測量です。drained_mp以下になります。 |
| remaining_target_mp | 敵の吸収後MP予測です。 |
| remaining_mp | 術者の吸収後MP予測です。 |
| mp_power | 有限floatへ正規化した吸MP係数です。 |
| mp_drain_blocked | 無効/吸収耐性でMP吸収が禁止されたかどうかを示します。 |

たとえば魔力100・mp_power0.14・現在/最大MP100・消費MP5・敵MP80では、敵から14MPを奪い、術者は5MPだけ回復します。結果はmp_after_payment: 95 / drained_mp: 14 / recovered_mp: 5 / remaining_mp: 100 / remaining_target_mp: 66です。回復できなかった9MPを敵へ戻しません。

## 開発者の実行方法と失敗時の対応

開発者は使用できるGodotとPythonを指定し、リポジトリのルートで次の検証を実行してください。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotのconsole実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_drain_mp_skill.py tests/test_gdscript_magic_skill.py tests/test_gdscript_self_damage_magic.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_drain_mp_skill.py
```

テストは専用の要求JSONと一時戦闘個体を使い、実Godotと実PythonのHP/MP計算を比較します。揺らぎだけを固定し、反撃と学習を無効にします。AI選択・実MP支払いの比較ではありません。要求ファイルのbyte、入力辞書、返却コピーの独立性も確認します。

性能検査は20000回・7サンプル・2000回の事前実行で、予測1回の中央値を測ります。中央値3000マイクロ秒以内、敵HP975・術者MP19・敵MP66、敵MP喪失/術者MP回復がともに14、元の敵HP1000・術者MP10/最大MP30・敵MP80と入力の保持がすべて成立した場合だけ成功します。起動・読込・描画・実資源更新の性能は測りません。通常魔法と同じプローブの測定ループを使います。

Godot未指定によるテストスキップや性能CLIの終了コード2は未検証です。開発者はGodotを指定して再実行してください。解析・実行診断があれば結果が出ても失敗です。拒否理由invalid_drain_mp_power / invalid_drain_mp_resources / invalid_drain_mp_numbersの場合は、それぞれ定義の係数・要求のMP資源・必要なMP積の精度を確認してください。その他の理由は通常魔法の契約を確認してください。入力を勝手に補修しないでください。

## 未接続・未検証の範囲

通常魔法・自傷魔法の予測と行動入口は、吸MP定義を引き続き拒否します。[吸MP行動契約](GDScript吸MPスキル行動契約.md)は最新予約・習得・許可装備・現在資源を検証し、専用入口でSessionへ実適用します。吸MP予測API自体は非破壊のままです。回避・状態異常・反撃、AI、戦闘Scene・演出、勝敗・報酬・教会復活、実GUI・配布export・リモートCIの完了を意味しません。保存JSON/schema、正規data/assets、実セーブは変更しません。

[移行実装単位](ワークフロー/GDScript移行実装単位.md) / [コードの入口](CODEMAP.md) / [GDScript開発案内](../gdscript/README.md)
