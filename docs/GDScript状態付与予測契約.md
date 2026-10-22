# GDScriptの状態一件の付与予測契約

## 背景・目的・実装範囲

GDScript版の戦闘状態へ付与処理を接続する前に、Python版BattleEngine._try_apply_statusの重複防止・状態耐性・成功判定を独立して照合する必要があります。本契約は、状態一件を付けた場合の新しい一覧を予測し、実個体・HP/MP・Session・AI・保存データを変更しません。

開発者は、Godotからpreload("res://engine/status_apply_contract.gd")で得たスクリプトへ、prepare_application(request)またはquote_application(request)を呼び出してください。prepare_applicationは成功率と判定値の要否を返し、quote_applicationは明示した判定値で付与結果を返します。現時点ではプレイヤー用画面から直接操作できません。

正規data/skills/skills.jsonには状態付与用status_effect定義がありません。出血攻撃の比較データは独立したテスト定義であり、標準スキルを追加しません。正規ghost/maru/kadoka/metal_slimeの出血耐性immuneはread-onlyで検証します。耐性の種族/装備からの再構築、スキルの習得/対象/消費MP、攻撃で実ダメージを与えた場合だけの付与可否は本契約の責務ではありません。

## 開発者が渡す要求

例えば開発者はquote_applicationへ次の要求を渡してください。

```json
{
  "effect": {"id": "bleeding", "display_name": "出血", "chance": 0.4},
  "status_effects": ["poison"],
  "resistance_level": "weak",
  "roll": 0.49
}
```

付与予測は基礎確率0.4をweak倍率1.25で0.5へ補正し、roll0.49が0.5未満なのでapplied:trueを返します。resulting_status_effectsは["poison", {"id":"bleeding","display_name":"出血","removable":true}]となります。元要求と現在一覧は変更しません。

| 要求キー | 付与予測が認識する条件 |
| --- | --- |
| effect | 付与予測はeffectを必須辞書として受けます。id/display_nameは指定時に文字列、removableは指定時にboolに限定します。 |
| status_effects | 付与予測はstatus_effectsを必須の順序付き配列として受けます。配列要素は文字列または辞書です。 |
| resistance_level | 付与予測は新規状態に対応する耐性一件を文字列で受け、省略時はnormalを使います。耐性一覧全体は受けません。 |
| roll | quote_applicationはrollを有限数値の0以上1未満に限定します。省略/nullは未指定です。prepare_applicationはrollキーを受けません。 |

付与予測はeffect.idの前後にあるPython str.strip対象のASCII/Unicode空白を除きます。現在一覧のIDは空白を変更せず、文字列状態は文字列そのもの、辞書状態はidまたは省略時の空文字列で新規IDと比較します。新規IDなし/空文字列、同IDが既にある場合は付与しません。重複時は継続時間の延長や元状態の置換を行いません。

付与予測はeffect.chance省略時に0を使い、有限数値または数値文字列を受けます。bool・非有限値・絶対値9007199254740991超過は拒否します。有限の負値は付与なしになります。型検査と未知要求検査は、ID欠落・重複・確率0の場合にも省略しません。Pythonが不正型を暗黙変換できる全範囲への互換を主張しません。

状態定義と現在一覧は、[治療予測の状態形式](GDScript状態治療予測契約.md)と共用のstatus_effect_contractで検査します。配列を深さ0として最大32段、有限数値の絶対値9007199254740991以内のJSON値に限定します。Object・循環・過深な値・非文字列辞書キーはコピー前に拒否します。

付与予測は未知MOD状態IDとJSON互換拡張情報をコピーして保持します。例えばdurationやmetadataは情報として返しますが、持続時間・出血ダメージ・能力値低下・行動不能は実行しません。effectの拡張キーは実行命令ではありません。requestの未知キーはfalse/0/空でも拒否します。

## 耐性と判定値の要否

| 状態耐性名 | 付与予測が基礎確率へ掛ける倍率 |
| --- | --- |
| very_weak | 状態付与予測はvery_weakで基礎確率を1.5倍にします。 |
| weak | 状態付与予測はweakで基礎確率を1.25倍にします。 |
| normal | 状態付与予測はnormalで基礎確率を1倍にします。 |
| resist | 状態付与予測はresistで基礎確率を0.75倍にします。 |
| strong | 状態付与予測はstrongで基礎確率を0.5倍にします。 |
| immune | 状態付与予測はimmuneで基礎確率を0倍にします。 |

付与予測は補正後確率を最大1へ制限します。未知名と空文字列はPython runtimeに合わせて等倍にします。ダメージ専用absorb/reflectは、状態付与ではPythonに合わせて確率0へ制限します。この扱いは、absorb/reflectを正規状態耐性として許可するデータ仕様変更ではありません。

prepare_applicationは新規IDがあり、同IDがなく、基礎確率と補正後確率が正の場合だけroll_required:trueを返します。quote_applicationはroll_required:trueなら、補正後確率が1でもrollを要求します。quote_applicationはrollが補正後確率未満のときだけ一件を末尾へ追加し、等しい値では付与しません。

IDなし・重複・基礎確率0以下・無効耐性の場合、quote_applicationはrollを要求しません。ただしquote_applicationは判定不要でも指定済み不正rollを拒否します。契約は乱数を生成せず、roll_requiredはPython正本が一回の乱数を使用する条件を示します。

## 結果と失敗時の対応

prepare_applicationはok:true、独立effects、正規化候補effect、status_id、apply_chance、roll_required、outcomeを返します。候補effectからchanceを除き、idを正規化し、display_name/removableの省略時だけID/trueを補います。候補effectはまだ実個体へ登録された状態ではありません。

quote_applicationはok:true、scope:status_apply_quote、status_id、apply_chance、roll_required、applied、applied_name、outcome、独立resulting_status_effectsを返します。不成立時のapplied_nameはnullです。成立時はeffect.display_nameの空文字列を状態辞書に残したまま、表示用applied_nameにIDを使います。

outcomeはmissing_id、already_present、zero_chance、immune、roll_failed、appliedのいずれかです。準備だけの成立可能な候補はoutcome:readyとなります。付与予測は入力と返却値のネストを共有しません。現在一覧の件数nと拡張情報の総要素数mに対し、形式検査・重複走査・コピーはO(n+m)です。毎呼び出しのI/Oや状態所有者の生成は行いません。

拒否結果はok:falseとreasonだけで、部分的な成功一覧や確率を返しません。reasonはinvalid_status_apply_request、unsupported_status_apply_request、invalid_status_definition、invalid_status_effects、invalid_status_chance、invalid_status_resistance、invalid_status_apply_roll、missing_status_apply_rollです。開発者は対応する要求型/キー/数値/判定値を修正してください。予測処理は保存JSONを自動補修しません。

## 開発者の検証方法

開発者はリポジトリルートで使えるPython/Godotを指定し、次のコマンドを実行してください。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotの実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_status_apply.py tests/test_gdscript_status_cure.py tests/test_battle_bleeding.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_cure.py --status-apply
```

付与比較テストは学習なしの実Python _try_apply_statusをコピー個体へ実行し、実Godotの成功/不成立・最終一覧・表示名・乱数要否を照合します。テストは元要求と個体記録/AI/HPMPの不変、返却ネストの独立性、五種類の専用保存ダミーと要求JSONのbyte不変も確認します。実セーブは検証に使いません。

性能検査は四件の元一覧に対し、weak耐性・基礎確率0.4・roll0.49のネスト付き出血一件を毎回成功予測します。標準20000回・7サンプル・2000回事前実行で一予測中央値3000us以内、期待した五件の結果一覧、固定元要求の保持がすべて成功条件です。起動/I/O/描画/AI/Session実更新/保存は計測しません。

Godot未指定のテストスキップとCLI終了コード2は未検証です。開発者はGodotを設定して再実行してください。解析/実行診断・結果不一致・時間超過は失敗です。付与の状態所有者/Session実更新・継続効果・攻撃スキルとの統合・AI・実GUI・export・リモートCIは本単位では未検証です。数値snapshotと保存JSON/schemaは変更しません。

[コード入口](CODEMAP.md) / [移行単位](ワークフロー/GDScript移行実装単位.md) / [Godot開発案内](../gdscript/README.md)
