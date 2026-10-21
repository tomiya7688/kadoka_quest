# GDScriptの一時速度強化の保持契約

## 背景と目的

状態補正済みの行動順へ一時速度倍率を渡すには、最新の倍率だけでなく、残り期間と期限切れ時の復元先を戦闘個体ごとに保持する必要があります。速度所有者 `combatant_speed_state.gd` は、この三値だけを所有する独立したengine部品です。

速度所有者はPython正本の `BattleEngine._apply_multiplier` と `_tick_timed_buffs` の速度属性を移植します。速度所有者は、基礎能力値・出血などの状態一覧・実効速度計算・HP/MP・生死・逃走・行動予約・AI・保存を扱いません。実効速度の計算は[状態能力値補正契約](GDScript状態能力値補正契約.md)、順序計画は[状態補正行動順契約](GDScript状態補正行動順契約.md)が担当します。

## 開発者の呼び出し方法

開発者は、Godot内で戦闘個体ごとに速度所有者を生成し、startを一度だけ呼んでください。次の例は、倍率1.2を初期値にし、期間付き倍率1.5を弱い倍率1.3で延長した後、期間なし倍率1.4を復元先へ残します。

~~~gdscript
var SpeedState = preload("res://engine/combatant_speed_state.gd")
var state = SpeedState.new()
var started = state.start(1.2)
var applied = state.apply_multiplier({"multiplier": 1.5, "duration": 2})
var extended = state.apply_multiplier({"multiplier": 1.3, "duration": 3})
var permanent = state.apply_multiplier({"multiplier": 1.4})
var first = state.elapse_round()
var second = state.elapse_round()
var third = state.elapse_round()
var final_state = state.snapshot()
~~~

開始結果startedは `ok: true` です。延長直後のextended.snapshotは、倍率1.5・残り3ラウンド・復元先1.2になります。期間なし付与のpermanent.snapshotは、倍率1.5・残り3ラウンド・復元先1.4になります。三回目の経過結果thirdは `expired: true` になり、final_stateは倍率1.4・残り0・復元先1.4になります。

開発者は、各更新のokを確認してから次の操作へ進んでください。更新が拒否された場合、速度所有者は倍率・期間・復元先を変更しません。開発者はreasonに対応する要求だけを修正して再試行してください。失敗した初期化は再試行できますが、成功済み所有者のstartによる上書きはできません。

## APIと独立した読取形式

| API | 入力と結果 |
| --- | --- |
| start(initial_multiplier = 1.0) | startは0以上9007199254740991以下の有限な初期倍率を一度だけ保持し、期間なしの状態で成功結果とsnapshotを返します。 |
| apply_multiplier(request) | apply_multiplierはmultiplierと任意durationだけを受け、検証後に保持値を更新してsnapshotを返します。 |
| elapse_round() | elapse_roundは一ラウンド分だけ期間を減らし、今回期限切れしたかのexpiredとsnapshotを返します。 |
| snapshot() | snapshotは開始済みなら三キー辞書の新規コピー、未開始なら空辞書を返します。 |

snapshotの `speed_multiplier` は現在の倍率、`remaining_turns` は残りラウンド数、`baseline_multiplier` は期限切れ時の復元倍率です。残り0は期間付き強化なしを表します。期間付き強化がない場合、現在倍率と復元倍率は一致します。snapshotの編集は所有状態を変更しません。この三キー辞書は戦闘中だけの読取形式で、既存の六キー数値snapshotや保存JSONを拡張しません。

成功したstart/apply_multiplierは、ok・scope・snapshotを返します。scopeはそれぞれ `combatant_speed_started` と `combatant_speed_apply` です。elapse_roundの成功結果は `combatant_speed_elapsed` 区分とexpiredも含みます。拒否結果は `ok: false` とreasonだけを返し、部分更新したsnapshotは返しません。

## 倍率・期間・復元先の規則

- 速度所有者は現在倍率と新倍率の大きい方を残します。速度強化は倍率同士の乗算や、現在倍率を下げる減速処理ではありません。
- 期間付き強化がない状態でdurationを指定した場合、速度所有者は付与直前の現在倍率を復元先へ保存します。
- 期間付き強化の再付与では、速度所有者は倍率と残り期間をそれぞれ独立に最大値へ更新します。弱い倍率の長期間付与でも、強い現在倍率を延長後の期間いっぱい保持します。
- durationの省略とnullは期間なしの付与です。期間付き強化の途中で期間なし倍率を付与した場合、速度所有者は現在倍率と復元先をそれぞれ新倍率との最大値へ更新し、残り期間は変更しません。
- elapse_roundは残り期間が正の場合だけ一減らします。残りが0になる一回だけ、速度所有者は倍率を復元先へ戻しexpiredをtrueにします。期限切れ後や期間なしの経過は値を変更せずexpiredをfalseにします。
- elapse_roundは行動予約やラウンド番号を受けません。開発者は、ラウンド終端へ接続する際に全参加者を一回ずつ進める制御を別途実装してください。同じ所有者への経過APIの再呼出は、別の一回経過として扱います。

## 入力境界と拒否

倍率はintまたはfloatの有限数値で、0以上9007199254740991以下です。bool・文字列・非有限値・Object等の非数値・負値・精度上限超過は拒否します。初期倍率0も有効ですが、実効速度の最低1への制限はこの所有者では計算しません。

durationは省略/null、または1以上9007199254740991以下の整数値だけを受けます。JSON読込で生じる1.0などの整数値floatは受け、保持時にintへ変換します。0・負値・小数部のある値・bool・文字列・非数値・非有限値は拒否します。durationは正規スキルの期間抽選/正規化が済んだ値であり、生の範囲配列やスキル定義をこの所有者へ渡さないでください。

未開始の更新はnot_initialized、成功後のstartはalready_initializedです。付与要求が辞書以外ならinvalid_speed_buff_request、multiplier/duration以外のキーがあればunsupported_speed_buff_requestです。不正倍率はinvalid_speed_multiplier、不正期間はinvalid_speed_durationです。速度所有者は入力キー・倍率・期間の全検証が成功するまで保持状態を変更しません。

## 検証方法と未接続の境界

開発者は、Pythonのプロジェクト依存・pytestと使えるGodotを用意し、リポジトリルートでKADOKA_GODOT_EXECUTABLEへGodot実行ファイルを指定して、次のコマンドを実行してください。

~~~text
python -m pytest tests/test_gdscript_speed_state.py -v
python tools/performance-check/script/check_gdscript_speed_state.py
~~~

専用テストは、実Pythonヘルパーとの各中間状態の比較、初期化・再試行・再付与・期限切れ、不正/native値の拒否、八体の独立性、返却値/入力/保存ダミーの保持を確認します。専用性能検査は、新しい一所有者の開始・三付与・三回経過の七操作を、標準20000回・7サンプル・2000回事前実行で反復します。性能検査は七操作の全中間状態・全反復件数と中央値3000us以内を照合し、高速な拒否や更新欠落は合格にしません。

速度所有者はSession・Application・スキル行動・ラウンド終端へ未接続です。現在の状態付きSessionは、引き続き全参加者の倍率1で順序を計画します。期間保持単体の検証は、予約からの実付与、終端での一回経過、ピオラの実行、AI・戦闘画面の実装完了を意味しません。

専用性能検査は起動/I/O・AI・描画・保存を計測しません。Godot未指定の場合、専用性能CLIは終了コード2を返し、実Godotのテストはskipされます。開発者はskipを実行成功と扱わず、Godotを指定して再検証してください。実GUI・配布export・リモートCIはこの保持単位の検証とは別です。
