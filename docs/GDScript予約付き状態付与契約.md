# GDScriptの取得済み予約による一回の状態付与

## 背景・目的・対応範囲

参加者状態集合battle_status_stateのapplyだけでは、同じ行動で異なる対象へ何度も付与を判定できます。Sessionのapply_status_applicationは、現在取得済みの行動予約識別子ticketに状態更新を紐づけ、正常な判定を一回だけ許可します。Sessionは付与確率や耐性の規則を再実装せず、最新の所有一覧へ一件追加を委譲します。

本契約は内部の低水準APIです。Sessionはこの入口でHP/MP・物理防御倍率・行動予約段階を変更しません。スキル定義/習得/許可装備・消費MP・対象の味方/敵制限・状態耐性再構築は上位の行動処理の責務で、[付与付き単体物理とApplication専用入口](GDScript状態付与付き物理行動契約.md)へ接続しました。魔法の状態付与・AI・画面・保存・継続効果は未接続です。

## 開発者の実行方法と例

開発者はGodotの検証用スクリプトの関数内で次を実行してください。味方と敵が同じIDでも、状態と予約は陣営別に扱います。次の例は敵sameへの付与だけを行います。

```gdscript
var Session = preload("res://engine/battle_session.gd")
var stats = {"hp": 30, "mp": 7, "attack": 10, "defense": 10, "magic": 10, "speed": 10}
var member = {"identity": {"id": "same", "species_id": "slime", "name": "比較個体"},
    "stats": stats, "hp": 30, "mp": 7, "fled": false, "alive": true}
var session = Session.new()
assert(session.start_with_statuses([member.duplicate(true)], [member.duplicate(true)],
    {"allies": {"same": []}, "enemies": {"same": []}})["ok"])
assert(session.begin_round([{"side": "allies", "id": "same"}, {"side": "enemies", "id": "same"}])["ok"])
var ticket = session.next_actor()["pending"]["ticket"]
assert(session.claim(ticket)["can_execute"])
var before = session.snapshot()
var target = {"side": "enemies", "id": "same"}
var request = {"effect": {"id": "bleeding", "display_name": "出血", "chance": 0.4},
    "resistance_level": "weak", "roll": 0.49}
assert(session.apply_status_application(ticket, target, request)["applied"])
assert(session.snapshot() == before)
assert(session.apply_status_application(ticket, {"side": "allies", "id": "same"}, request)
    ["reason"] == "status_application_already_applied")
assert(session.status({"side": "allies", "id": "same"})["snapshot"]["status_effects"].is_empty())
assert(session.finish(ticket)["ok"])
```

Sessionは基礎確率0.4/weak耐性から補正後確率0.5を受け、roll0.49が未満なので敵sameへ出血一件を追加します。Sessionは同じ予約を別の対象/状態ID/判定値へ使った二回目も拒否します。付与を行っただけでは予約は完了しません。開発者は上位行動の全処理が成功した後にfinish(ticket)を呼んでください。

## 条件・拒否・一回判定

開発者はstart_with_statusesで全参加者の初期状態を明示し、begin_round→next_actor→claimの成功後にapply_status_application(ticket, target, request)を呼んでください。Sessionはticketの厳密round/slot/actor一致とclaimed段階を既存予約検査で確認します。提示中・偽造・古い・完了済みの票は状態を変更しません。従来startで状態未設定ならstatus_not_configuredを返します。

targetはside/idだけの存在する生存・未逃走参加者です。Sessionの低水準付与入口は味方/敵/本人を許可し、攻撃スキルの対象制限を代用しません。Sessionは予約取得後の行動者/対象の死亡・逃走と両陣営の最新生存も確認します。targetが不正ならinvalid_actor_key、存在しなければactor_missing、死亡/逃走ならtarget_not_aliveです。対象検査が成功していても、行動者が死亡/逃走した場合や片方の陣営でも生存者がいなくなった場合はactor_cannot_apply_statusになります。

requestはeffectと任意resistance_level/rollだけを受けます。Sessionは[個体/参加者状態契約](GDScript参加者状態付与契約.md)へ要求を渡し、外部一覧・古い予測・任意HPMP・未知キーをfalse/0/空でも拒否します。付与確率・重複・rollの必要条件と不正値の拒否は[純粋付与契約](GDScript状態付与予測契約.md)を共用します。Sessionは乱数を生成しません。

Sessionはok=trueの付与判定を使用済みにします。IDなし・同ID存在・確率0以下・無効耐性・判定不成立でも、Sessionは同じ予約で再抽選させません。二回目はstatus_application_already_appliedです。ok=falseの不正要求は使用済みにせず、開発者は入力を修正して同じ取得済み予約で再試行できます。拒否時にHP/MP・防御・状態・予約段階を変更しません。

内部所有者claimed_status_updatesは、治療と付与の直近の正常判定済みticketを各一件だけ独立コピーで保持します。Sessionは現在の予約照合後、外部のJSON票ではなく内部の正規整数票を渡し、数値型の異なる辞書比較による一回制限の回避を防ぎます。JSON票と内部票を入れ替えた再送検証は[速度強化契約](GDScript予約付き速度強化契約.md)と共用します。専用所有者は対象/最新一覧の委譲と種類別の再判定防止を担当し、Sessionへの逆参照を保持せず、RefCountedの循環を作りません。資源所有者は生存読取だけに使います。

既存apply_status_cureは同陣営生存対象への治療一回を維持し、拒否理由/順序も維持します。治療と付与の制限は独立しているため、同じ予約で治療一回と付与一回を実行できます。これはその組合せを許可するスキルが実装済みという意味ではありません。次の予約やラウンドでは新しい判定ができます。状態は死亡・逃走・ラウンド終端で暗黙解除しません。

実付与結果はscope:combatant_status_applyを維持し、数値Session七キー/個体六キーと保存JSON/schemaを変更しません。原本・要求・返却ネストの編集は所有状態と使用済み記録へ伝播しません。処理は同期的で、複数スレッドの同時更新には対応しません。

## 検証方法と完了確認

開発者はリポジトリルートで使えるPython/Godotを指定して次を実行してください。共用fixtureは専用要求と五種類の保存ダミーのbyte保持を毎起動後に確認します。実セーブは使いません。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotの実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_session_status_application.py tests/test_gdscript_cure_heal_action.py tests/test_gdscript_session_status.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_cure.py --session-status-apply
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_cure.py --session-status
```

専用テストは実Python _try_apply_statusと付与結果を比較し、両陣営同ID・本人/味方/敵への付与・正常不成立の一回制限・不正要求からの再試行・死亡/逃走/敵全滅・予約段階・native不正値・治療との共存・ラウンド/物理防御解除・原本/返却値の独立性を実Godotで確認します。スキル選択やAIの検証ではありません。

--session-status-applyは八行動ごとに新しい八体Sessionと初回順序を構築し、各行動で予約提示→取得→別の敵対象への実付与→同予約で別対象への再判定拒否→個別/全体読取→完了を測ります。各反復で対象だけが三件→四件となり、他の状態と数値/防御は不変であることを確認します。固定八体の最終状態四件・満数値資源・完了状態・全反復確認数・原本を固定期待値へ照合します。重複や拒否だけの高速経路で通過しません。

標準20000回・7サンプル・2000回事前実行で、一付与判定中央値3000us以内が時間条件です。iterationsとwarmupは八の倍数にしてください。起動/I/O・MP消費・攻撃計算・耐性再構築・AI・描画・保存は計測しません。Godot未指定のskip/終了コード2は未検証です。開発者はGodotを指定して再実行してください。解析/実行診断・期待値不一致・時間超過は失敗です。

付与付き単体物理とApplication専用行動は実付与へ接続済みです。魔法の状態付与・継続効果・AI・画面は未接続で、実GUI・配布export・全E2E・リモートCIはこの低水準契約だけでは検証できません。低水準付与の成功を、ゲームの戦闘画面全体の移植完了として扱わないでください。

[Session状態保持](GDScript戦闘Session状態保持契約.md) / [治療付き回復](GDScript治療付き回復行動契約.md) / [形式仕様](FORMATS.md) / [コード入口](CODEMAP.md) / [移行単位](ワークフロー/GDScript移行実装単位.md)
