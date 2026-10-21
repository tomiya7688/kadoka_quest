# GDScriptの速度強化をラウンド終端で一回だけ進める契約

## 背景・目的と責務

[予約付き速度付与](GDScript予約付き速度強化契約.md)は、倍率・期間・復元先を保持しますが、ラウンド終了に期間経過を接続しなければ期限付き強化が残り続けます。本契約は、GDScriptの戦闘Sessionが開始したラウンドを閉じる際に、全参加者の速度期間を一回だけ進める仕組みを説明します。

Sessionの非公開終端処理_end_roundは、round_activeからround_finishedまたはstoppedへ段階を切り替えます。速度集合battle_speed_stateのelapse_roundは、死亡・逃走を含む全所有者へ一回ずつ経過を委譲します。[個体速度所有者](GDScript一時速度強化保持契約.md)だけが残り期間の減算と倍率復元を行います。Sessionと集合は速度の計算式・最大値・復元規則を再実装しません。

本契約は低水準の戦闘内部処理です。ピオラの定義・習得・MP支払い・味方対象制限・期間範囲の選択、AI、画面、勝敗・報酬は別単位です。Sessionのstoppedは、生存者が片側にいなくなった機械的停止であり、勝利や教会復活を実行するものではありません。

## 終端になる条件と一回性

Sessionは、最後の予約のfinish、next_actorでの死亡末尾のスキップ、または最新生存に基づく途中停止でラウンドを閉じます。取得前に行動不能となった予約をclaimが取り消し、その取消が終端になった場合も一回経過します。空陣営を含む開始では、正常なラウンド計画の直後にstoppedへ閉じます。

Sessionの_end_roundは、現在段階がround_activeでない場合は何も変更しません。Sessionは経過を委譲する前に終端段階を保持するため、終端後のnext_actorや予約再送では同じラウンドを二回進めません。Sessionは外部向けのelapse_round APIを公開しません。

ラウンド途中のfinish、予約の提示・取得、付与、状態の読取、不正な要求、失敗したbegin_roundは、速度期間を減らしません。最後の生存行動が完了しても、死亡した候補がorder末尾に残る場合は、next_actorが末尾を飛ばして終端に到達するまで期間を保持します。

期間一の強化は、先頭行動と末尾行動のどちらで付与しても、そのラウンドの終端で期限切れになります。速度更新で現在ラウンドのorderは再整列しません。次のbegin_roundは、期限切れで復元した後の所有倍率から順序を計画します。

## 開発者の呼び出し方法

開発者は、新規Sessionをstart_with_statusesで開始し、全参加者の明示初期状態を渡してください。開始とbegin_roundの成功を確認してから、公開の予約操作と付与APIを使ってください。次の抜粋は、二体の行動順が確定したSessionで、先頭から期間一の強化を付与して二体分を完了します。

~~~gdscript
var ticket = session.next_actor()["pending"]["ticket"]
var claimed = session.claim(ticket)
assert(claimed["can_execute"])
var target = {"side": "allies", "id": "same"}
var applied = session.apply_speed_multiplier(ticket, target, {"multiplier": 1.5, "duration": 1})
assert(applied["ok"])
assert(session.speed(target)["snapshot"]["remaining_turns"] == 1)
var finished = session.finish(ticket)
assert(finished["ok"])
var last = session.next_actor()["pending"]["ticket"]
var last_claimed = session.claim(last)
assert(last_claimed["can_execute"])
var last_finished = session.finish(last)
assert(last_finished["ok"])
assert(session.snapshot()["phase"] == "round_finished")
assert(session.speed(target)["snapshot"]["remaining_turns"] == 0)
~~~

開発者は各APIの成功を確認し、拒否された要求だけを修正してください。上の抜粋は、API呼出をassertの外へ置いた開発用検証です。配布用の行動処理はassertが除去されても拒否時に進まないよう、通常の条件分岐で返却値を検査してください。

速度集合のelapse_roundは、未開始ならok=false/reason=not_initializedで拒否し、開始済みならok=true/scope=battle_speed_elapsedを返します。空集合の経過も成功します。集合はラウンド番号を所有しないため、集合APIを直接二回呼ぶと二回経過します。開発者はSession利用時に集合APIを追加で呼ばず、Sessionの一回制御を使用してください。

## 保持する状態と互換性

終端では、速度の残り期間を一減らし、0になった個体だけ倍率を復元先へ戻します。期間なしと期限切れ済みの速度は変更しません。弱い長期間の再付与と、強化中の期間なし付与による復元先更新は、個体所有者の規則を維持します。

Sessionは全参加者の物理防御倍率も従来どおり1へ戻します。速度期間の経過はHP/MP・死亡/逃走・状態一覧・基礎stats・現在orderを変更しません。従来startは速度所有者を作らず、防御解除だけを維持します。数値Session七キー、個体数値六キー、三キー速度読取と保存JSON/schemaは変更しません。経過の走査対象は最大八体の戦闘参加者だけで、保有モンスター数を制限したり全件を走査したりしません。

Python正本のrun_roundは、途中決着でも死亡・逃走を含む全参加者へ_tick_timed_buffsを呼びます。GDScriptの速度経過はこの対象範囲に合わせます。Python版の行動・期限処理は変更せず、Python正本を読んだ際に見つけた曖昧な説明だけを具体化します。

## 検証方法と証拠の限界

開発者は使えるGodot/Pythonを設定し、リポジトリルートで次を実行してください。専用テストは個体/AI/items/party/stateの保存ダミーと入力のバイト保持を起動前後に確認し、実セーブを使いません。

~~~powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotの実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_speed_round.py tests/test_gdscript_claimed_speed.py tests/test_gdscript_session_speed.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_speed_update.py
~~~

集中テストは、全八体と空/未開始集合、先頭/末尾からの付与、正常終了、完了/次候補/取得取消による途中停止、死亡末尾スキップ、終端後再送、不正要求と読取の非減算、再付与と復元先、期限後の次回順序を検査します。中間の倍率・期間・復元先は、実Pythonの倍率ヘルパーへ照合します。

標準性能検査は20000段階・7サンプル・2000段階事前実行と3000us上限を維持します。八行動ごとに初期倍率1.2の新規Sessionを作り、全員へ倍率1.5/期間一を実付与して再送を拒否し、終端で全員が倍率1.2/残り0/復元先1.2になることを固定期待値へ照合します。経過前の期待速度は製品snapshotから逆算せず、各段階の固定付与を独立に追跡します。拒否やno-opだけ、早期減算、復元漏れを性能成功にしません。初期構築と保持検査は計測に含み、起動/I/O・AI・MP支払い・描画・保存は含みません。

Godot未指定のskip/終了コード2は未検証です。診断・固定結果不一致・時間上限超過は失敗として原因を修正してください。実GUI・配布export・リモートCIはヘッドレス検証と別の証拠です。本契約の成功をピオラ行動や戦闘画面の移植完了とは扱わないでください。
