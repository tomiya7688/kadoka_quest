# GDScriptの取得済み予約による一回の速度強化

## 背景・目的と所有者

[参加者速度集合](GDScript戦闘Session速度保持契約.md)の更新だけでは、同じ行動予約で複数の対象を強化できます。Sessionのapply_speed_multiplierは、現在取得済みの行動予約識別子ticketに速度付与を結び付け、正常な付与を一回だけ許可します。

Sessionは現在予約との厳密一致とclaimed段階を確認し、内部所有者claimed_speed_updateへ正規の予約票を渡します。内部所有者は対象の最新生存と使用済み予約を確認し、倍率・期間・復元先の更新をbattle_speed_stateから[個体速度所有者](GDScript一時速度強化保持契約.md)へ委譲します。速度の最大値規則・数値検証・実効速度の計算をSessionや一回記録の所有者へ複写しません。

本契約は低水準の戦闘処理APIで、ゲーム画面に新しい操作は追加しません。スキル定義・習得・許可装備・MP支払い・友軍対象制限・期間範囲の正規化/抽選は上位行動の責務です。[ラウンド終端の一回期間経過](GDScript速度強化ラウンド終端契約.md)は接続し、ピオラ行動・Applicationの速度スキル入口・AI・画面は未接続です。Session.snapshot七キーと個体の数値snapshot六キー、保存JSON/schema、Pythonゲーム処理は変更しません。

## 開発者の呼び出し方法

開発者は、満HP/MP・未逃走の両陣営と全員の明示初期状態でstart_with_statusesを成功させ、begin_roundでラウンドを開始してください。次の例は、両陣営に個体ID sameが存在するSessionで、ラウンド開始直後に予約を取得して速度付与する関数本体の抜粋です。

```gdscript
var ticket = session.next_actor()["pending"]["ticket"]
var claimed = session.claim(ticket)
assert(claimed["can_execute"])
var before = session.snapshot()
var target = {"side": "allies", "id": "same"}
var applied = session.apply_speed_multiplier(ticket, target, {"multiplier": 1.5, "duration": 3})
assert(applied["ok"])
assert(applied["snapshot"]["speed_multiplier"] >= 1.5)
assert(session.snapshot() == before)
var repeated = session.apply_speed_multiplier(ticket, {"side": "enemies", "id": "same"}, {"multiplier": 2.0})
assert(repeated["reason"] == "speed_multiplier_already_applied")
var finished = session.finish(ticket)
assert(finished["ok"])
```

Sessionは速度を付与しただけではHP/MP・物理防御倍率・状態一覧・予約段階を変更しません。開発者は上位行動の全処理が成功してからfinish(ticket)を呼んでください。この例はMP消費や友軍対象を確認するスキル行動の実装を代用しません。

targetはside/idだけを持つ、存在する生存・未逃走の参加者です。低水準入口は本人・味方・敵を受け付け、攻撃/強化スキルの対象制限は代用しません。別陣営の同じ個体IDは独立した所有者です。

requestは必須multiplierと任意durationだけの辞書です。倍率は0以上9007199254740991以下の有限int/float、durationは省略/nullなら期間なし、明示する場合は同じ精度内の1以上の整数値です。bool・数値文字列・非有限値・Object・期間範囲配列・外部snapshot・未知キーは拒否します。開発者は期間範囲を上位行動で正規化/選択してから渡してください。

## 最新倍率と一回制限

個体速度所有者は倍率と残り期間を独立した最大値へ更新します。初めて期間付き強化を付与するときは現在倍率を復元先へ保持し、期間なし強化は必要なら復元先も引き上げます。例えば現在倍率1.5/残り2へ倍率1.3/期間5を別予約で付与すると、倍率1.5/残り5になります。期間なし倍率1.4を別予約で付与した場合、現在1.5/残り5を保持し、復元先だけ1.4以上になります。

Sessionはok=trueの付与を一回として記録します。弱い倍率で全速度値が変わらなくても、同じ予約の二回目はspeed_multiplier_already_appliedです。対象や要求内容を変えた再送も許可しません。ok=falseの不正要求は使用済みにせず、開発者は要求を修正して同じ取得済み予約で再試行できます。

速度の一回記録は治療・状態付与の一回記録と独立しています。同じ取得済み予約で速度付与一回・状態治療一回・状態付与一回を行えることは、その組合せのスキル実装や使用許可を意味しません。新しい予約と次ラウンドでは、速度を再付与できます。

GodotのJSON.parseは数値をfloatとして読みます。Sessionの予約照合は整数値floatを内部intと同じ番号として受け付けますが、Godotの辞書比較は数値型が違う予約票を同一としません。一回記録には照合済みの外部票ではなく、Session内部の正規整数票を渡します。速度・既存治療・既存状態付与の全入口は、JSON票→内部票と内部票→JSON票のどちらの再送も拒否します。各内部所有者は正規票を独立コピーし、過去の全予約ではなく直近一件だけを保持します。

## 拒否順と非変更境界

Sessionは未開始をnot_initialized、不正なticket形式/番号をinvalid_ticket、現在予約との不一致をticket_not_pending、提示中で未取得の票をpending_not_claimedで拒否します。正常な票でも従来startで速度未設定ならspeed_not_configuredです。古い票・完了済み票では速度を変更しません。

内部所有者は対象不正をinvalid_actor_key、不在個体をactor_missing、対象の死亡/逃走をtarget_not_aliveで拒否します。対象検査の後、取得後の行動者の死亡/逃走や片方の陣営に生存者がいない場合はactor_cannot_apply_speedになります。対象/生存検査の後に使用済み予約を確認し、未使用なら速度所有者の要求検証へ進みます。

速度要求の型不正はinvalid_speed_buff_request、未知キーはunsupported_speed_buff_request、倍率不正はinvalid_speed_multiplier、期間不正はinvalid_speed_durationです。拒否時に速度・残り期間・復元先・HP/MP・防御・状態一覧・予約・一回記録を変更しません。

成功はok=true/scope=combatant_speed_apply/snapshotの独立辞書です。返却snapshotはspeed_multiplier/remaining_turns/baseline_multiplierの三キーです。要求や返却値の編集は、所有速度と使用済み記録へ伝播しません。処理は同期的で、複数スレッドの同時更新には対応しません。

速度の更新は現在ラウンドの固定orderを再整列せず、次のbegin_roundだけが最新所有倍率を使います。補正前stats.speedは書き換えません。Sessionは正常終了または途中停止の終端で全員の残り期間を一回だけ進め、期限切れなら復元先へ戻します。途中のfinish・読取・不正要求・終端後再送は期間を減らしません。期間一の付与は、先頭/末尾のどちらで行っても付与ラウンドの終端で切れます。

倍率だけが精度内でも、基礎速度との積が上限を超える場合は次の行動順計画が拒否します。低水準付与入口は行動順計画まで実行せず、上位行動の予測/対応範囲の検証を代用しません。

## 検証方法と証拠の限界

開発者はリポジトリルートで使えるPython/Godotを指定し、次を実行してください。専用要求と個体/AI/items/party/stateの保存ダミーは起動前後でバイト不変を確認し、実セーブを使いません。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotの実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_claimed_speed.py tests/test_gdscript_session_speed.py tests/test_gdscript_session_status_application.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_speed_update.py
```

集中検証は、実Pythonの倍率更新との全中間状態一致、弱い再付与・期間なし・同IDの陣営分離・八体、予約段階/最新生存/旧票/不正/native値、拒否後再試行、no-opの一回消費、入力票編集後の保持、JSON票と内部票の混在再送、治療/状態付与との共存、現在順固定・次回反映・終端だけの期間経過を確認します。

性能検査は同IDの両陣営各四体を使い、八行動ごとに初期倍率1.2のSessionと初回順序を新規構築します。一段階はnext→claim→別陣営の同IDへ倍率1.5/期間一の実付与→別対象への再送拒否→独立読取/全保持確認→finishです。終端前の各段階を固定入力から追跡し、終端で八体全員が倍率1.2/残り0/復元先1.2へ戻ることと、資源・状態・防御・実順序・最後の成功/再送拒否・全反復確認件数・原本保持を独立期待値へ照合します。更新済み対象へのno-opや拒否だけの高速経路、早期減算、期限復元漏れは通しません。

標準20000段階・7サンプル・2000段階事前実行で一段階中央値3000us以内を要求します。iterationsとwarmupは八の倍数です。初期構築と保持確認は計測に含みますが、起動/I/O・MP支払い・AI・描画・保存は含みません。Godot未指定のskip/終了コード2は未検証です。解析/実行診断・期待値不一致・上限超過は失敗です。開発者は原因を修正して再検証してください。

実GUI・配布export・リモートCIは別の証拠です。低水準速度付与の成功を、ピオラや戦闘画面全体の移植完了として扱わないでください。
