# GDScriptの戦闘状態一覧の保持・一件治療/付与契約

## 具体例と目的

例えば、状態所有者combatant_status_stateは、解除不可の「特殊拘束」、毒、眠りの順に保持した一覧へ、成功率3%・判定値0.02の治療要求を受けます。`combatant_status_state`は特殊拘束を飛ばし、所有する一覧から毒一件だけを除きます。状態所有者の一覧には特殊拘束と眠りが残り、初期化に渡した元の配列は変わりません。

治療付きHP回復`spirit_recover`をSessionへ接続するには、非破壊の数値予測とは別に、戦闘中の最新状態一覧を保持する部品が必要です。状態所有者は一覧の初期化・独立読取・変更しない治療/付与予測・一件治療/付与の実更新を担当します。状態所有者は[純粋治療契約](GDScript状態治療予測契約.md)と[純粋付与契約](GDScript状態付与予測契約.md)へ候補・確率・判定を委譲し、規則を二重実装しません。

状態所有者はHP/MP、生死、逃走、行動予約、スキル習得、AI、保存処理を持ちません。[専用Session開始](GDScript戦闘Session状態保持契約.md)では参加者ごとに保持/読取し、[治療付き回復行動](GDScript治療付き回復行動契約.md)は現在取得済み予約一回の治療を状態所有者へ委譲します。状態所有者単体の治療成功は、スキル一回分の行動実行やMP消費が完了したことを意味しません。

## 開発者の呼び出し方法

入口は`gdscript/engine/combatant_status_state.gd`です。開発者は、戦闘個体ごとに状態所有者を生成し、初期状態の配列を明示して`start`を一度呼んでください。次のコードはGodot内で実行する例です。

```gdscript
var StatusState = preload("res://engine/combatant_status_state.gd")
var state = StatusState.new()
var effects = [
    {"id": "special_lock", "display_name": "特殊拘束", "removable": false},
    {"id": "poison", "display_name": "毒"},
    "sleep"
]
var started = state.start(effects)
var request = {"cure_chance": 0.03, "roll": 0.02}
var prediction = state.quote_cure(request)
var before = state.snapshot()
var applied = state.cure(request)
var after = state.snapshot()
```

状態所有者の開始が成功すると、`started.ok`はtrueになります。予測結果`prediction`は毒一件を除いた一覧を返しますが、予測後の`before.status_effects`には元の三件が残ります。実適用結果`applied`は`cured: true / cured_name: "毒" / candidate_index: 1`を返し、`after.status_effects`には特殊拘束と眠りが残ります。

開発者は、確率・判定値だけを`cure`へ渡してください。状態所有者は呼び出し時の最新一覧で候補を選び直すため、外部の予測結果・候補位置・残存一覧を更新命令として受けません。予測後に別の治療が成功していても、古い一覧を上書きしません。

状態所有者の`cure`には行動予約や重複実行防止の識別子がありません。開発者が成功する要求を二回呼ぶと、二回目は更新後の一覧の次の候補を治療します。現在のSessionは取得済みの行動予約一回につき一度だけ実治療を受け付けます。状態所有者単体には予約による実行制限を追加せず、付与のSession予約制御は別の未実装単位です。

## 最新一覧への一件付与

状態所有者は新規状態候補を一件だけ末尾へ追加します。例えば空一覧へ出血定義の基礎確率0.4・weak耐性・roll0.49を渡すと、補正後確率0.5の判定が成立し、出血一件を保持します。開発者は、空一覧で新規開始する次の独立したGodot例を実行してください。

```gdscript
var StatusState = preload("res://engine/combatant_status_state.gd")
var state = StatusState.new()
var started = state.start([])
var request = {
    "effect": {"id": "bleeding", "display_name": "出血", "chance": 0.4},
    "resistance_level": "weak",
    "roll": 0.49
}
var preparation = request.duplicate()
preparation.erase("roll")
var prepared = state.prepare_application(preparation)
var predicted = state.quote_application(request)
var unchanged = state.snapshot()
var applied = state.apply(request)
var after = state.snapshot()
```

状態所有者のprepare_applicationはeffectと任意resistance_levelだけを受け、最新一覧の独立コピー・候補・補正後確率・roll_requiredを返します。prepare_applicationはrollキーをnullでも拒否し、一覧を変更しません。quote_applicationとapplyはeffectと任意resistance_level/rollだけを受けます。どの付与APIも外部status_effects、古いresulting_status_effects、予測結果、候補位置、MP等の未知要求を拒否します。

付与準備/予測と実更新は[純粋付与契約](GDScript状態付与予測契約.md)の型・耐性・確率・ID・JSON互換性・判定値の規則を共用します。初期化前はnot_initialized、要求が辞書でなければinvalid_status_apply_request、未知要求ならunsupported_status_apply_requestを返します。純粋契約による定義/確率/耐性/rollの拒否理由はそのまま返し、拒否時に所有一覧を変更しません。

付与予測quote_applicationはscope:status_apply_quoteと独立resulting_status_effectsを返し、所有一覧を変更しません。実更新applyは呼び出した時点の最新一覧で再判定し、applied:trueの場合だけ候補を深くコピーして所有一覧へ一件追加します。applyは外部の一覧全体で状態を置換せず、返却値を編集しても所有一覧へ変更を伝播させません。applyの結果区分はscope:combatant_status_applyです。

状態所有者はok:trueとapplied:trueを区別します。IDなし・同ID存在・基礎確率0以下・無効耐性・判定不成立は操作として正常な付与なしで、一覧を保持します。同IDが存在するとroll不要になりますが、指定済み不正rollは拒否します。未知MOD IDとJSON互換拡張情報は保持し、継続時間・出血ダメージ・能力値低下・行動不能は実行しません。

同IDへの二回目のapplyは、同IDを重ねたり状態を置換/延長したりしません。治療cureで状態を除いた後は、applyで同IDを再び付与できます。異なるIDへのapplyはそれぞれ更新できるため、一行動につき一度だけ付与する制御とは異なります。状態所有者はHP/MP・生死・逃走・行動予約・スキル習得・耐性の種族/装備再構築を持たず、付与要求の条件制御は後続のSession/行動接続で実装してください。数値snapshot六キーと保存JSON/schemaは変更しません。

## 初期化・独立性・更新範囲

| 公開API | 条件と結果 |
| --- | --- |
| `start(effects)` | 状態所有者が未開始なら、順序付き配列を検証して深いコピーを保持します。空配列も有効です。不正な一覧では開始済みにせず、正常な一覧で再試行できます。開始済みの所有者は再初期化を拒否し、治療後の一覧をリセットしません。 |
| `snapshot()` | 状態所有者が未開始なら空辞書を返します。開始済みなら`{"status_effects": [...]}`だけを、ネスト情報も独立したコピーで返します。 |
| `quote_cure(request)` | 状態所有者が開始済みなら、最新の一覧を使って一件治療を予測します。状態所有者は予測によって一覧を変更しません。 |
| `cure(request)` | 状態所有者が開始済みなら、最新の一覧で再判定し、成立時だけ最初の解除可能な候補一件を除きます。不成立・候補なし・拒否では所有一覧を変更しません。 |

状態所有者は、初期入力・開始結果・snapshot・治療結果の配列やネスト辞書を外部が編集しても、所有一覧へ変更を伝播させません。数値所有者`combatant_state.snapshot()`の`identity / stats / hp / mp / fled / alive`という六キーは変更せず、状態一覧のsnapshotは別の結果です。

## 入力と判定の条件

状態一覧は[純粋治療契約の対応形式](GDScript状態治療予測契約.md#状態一覧の対応形式)をそのまま使います。文字列またはJSON互換辞書の順序付き配列とし、辞書の`id / display_name`は文字列、`removable`はboolに限定します。未知のMOD ID・同IDの重複・JSON互換の拡張情報は情報として保持します。非有限数値・絶対値`9007199254740991`超過・深さ32超過・循環・Objectは拒否します。拡張情報の保持は、継続効果や持続時間の更新を実装済みとする意味ではありません。一件付与は下記専用APIで実装し、Sessionの付与行動は未接続です。

治療要求は必須の`cure_chance`と任意の`roll`だけです。未知キーはfalse・0・空でも拒否します。状態一覧・`candidate_index`・`remaining_status_effects`・`mp_cost`などを治療要求へ追加しないでください。

成功率`cure_chance`は有限数値または数値文字列を受け、0〜1へ制限します。明示判定値`roll`は0以上1未満の有限数値だけを受け、文字列・boolを拒否します。候補があれば成功率0/1でも判定値が必要で、`roll < 制限後の成功率`の場合だけ成立します。候補がなければ判定値の省略/nullを受けますが、指定済みの不正値は拒否します。状態所有者は乱数を生成/消費しません。

## 成功結果と拒否への対応

状態所有者の成功予測は`scope: status_cure_quote`、成功した治療操作は`scope: combatant_status_cure`を返します。治療操作の成功`ok: true`と、治療の成立`cured: true`は別です。候補なしや判定不成立でも操作は成功し、`cured: false`を返します。

状態所有者の予測/治療結果は、純粋治療契約の`candidate_index / roll_required / cure_chance / cured / cured_name / remaining_status_effects`を保持します。残存一覧は独立コピーであり、候補なし/不成立では全件が残ります。開始成功は`ok: true`と独立した`snapshot`を返します。

| 拒否理由`reason` | 条件と開発者の対応 |
| --- | --- |
| `not_initialized` | 状態所有者が未開始で予測/治療を要求した場合です。開発者は正しい初期配列で`start`を成功させてください。 |
| `already_initialized` | 状態所有者が開始済みで再び`start`を要求した場合です。開発者は別の戦闘個体/新しい戦闘用に新しい所有者を作成してください。 |
| `invalid_status_cure_request` | 状態所有者へ辞書以外の治療要求を渡した場合です。開発者は確率と任意判定値を持つ辞書を渡してください。 |
| `unsupported_status_cure_request` | 状態所有者への治療要求に未知キーがある場合です。開発者は一覧上書きや予測結果の持ち込みを削除してください。 |
| `invalid_status_effects / invalid_cure_chance / invalid_cure_roll / missing_cure_roll` | 共用治療契約が状態一覧・確率・判定値の条件を満たさないと判定した場合です。開発者は該当入力を訂正してください。 |

状態所有者の拒否結果は`ok: false / reason`です。状態所有者は拒否で初期入力・保持中一覧・保存JSONを自動補修しません。

## 検証方法と完了確認

開発者はリポジトリルートで使えるPythonとGodotを指定し、次を実行してください。検証は専用ダミー領域を使い、利用者のセーブは使用しません。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotの実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_combatant_status.py tests/test_gdscript_status_cure.py tests/test_gdscript_cure_heal_skill.py tests/test_gdscript_combatant.py -q
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_owned_status_application.py tests/test_gdscript_combatant_status.py tests/test_gdscript_status_apply.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_cure.py --status-state
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_cure.py --status-apply-state
```

専用テストは、実Godotのquote→cure→quote→cureを学習なしPython正本`BattleEngine._try_cure_status`と照合します。予測非変更・最新一覧での連続一件治療・未開始/再初期化の拒否・厳密入力・原本/返却値のネスト独立性を確認します。共用起動/保存fixtureにより、専用ダミーの個体/AI/items/party/stateと要求JSONのbyte不変も確認します。

状態所有者の性能検査`--status-state`は、解除不可2件・ネスト付き毒・眠りを持つ新しい所有者の開始→予測→読み取り→実治療→読み取りを測ります。各反復で毒一件を実際に除くため、候補なしの高速経路へ偏りません。標準20000回・7サンプル・2000回事前実行で、一回中央値3000us以内と開始四件・予測後四件・治療後三件・原本保持が全部一致した場合だけ成功します。起動・ファイルI/O・Session・描画・AI・保存の時間は含めません。

付与性能検査--status-apply-stateは、四件で新規開始→判定値の要否準備→予測→読取→出血一件実追加→読取→判定値なしの同ID再付与→読取を毎反復で実行します。標準20000回・7サンプル・2000回事前実行で一サイクル中央値3000us以内、初期四件・予測前後四件・更新後五件・重複後五件・固定原本保持を照合します。計測は準備/構築/読取を含み、拒否や重複だけの高速経路で通過しません。起動/I/O/Session/描画/AI/保存は計測しません。

Godot未指定のスキップ/性能終了コード2は未検証です。開発者はGodotを指定して再実行してください。解析/実行診断・期待値不一致・時間超過は失敗です。状態所有者の付与は検証しますが、付与のSession/攻撃行動接続・継続効果・AI・戦闘画面・実GUI・配布export・リモートCIは本単位では検証しません。治療付き回復のSession実行は別の行動契約/テストへ委譲します。正規data/assets・保存JSON/schemaは変更しません。

[コードの入口](CODEMAP.md) / [移行実装単位](ワークフロー/GDScript移行実装単位.md) / [GDScript開発案内](../gdscript/README.md)
