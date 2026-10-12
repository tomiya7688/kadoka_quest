# GDScriptの治療付きHP回復行動

例えば、最大HP1000・現在HP990の味方が解除不可状態・毒・眠りを持つ場合、spirit_recoverはHPを10回復し、判定が成立すれば毒だけを除きます。解除不可状態と眠りは残ります。正規定義spirit_recoverの表示名は「きあいでなおす」で、消費MP4・回復率0.03・治療確率0.03です。明示判定値roll=0.02なら毒を解除します。この数値例は検証用の対象能力であり、正規種族のLv60能力値を表しません。

純粋な予測や状態保持だけでは、戦闘中の予約と資源を一度だけ更新できません。この契約の目的は、開始時の習得・許可装備・正規定義と、現在の行動予約/HP/MP/状態を確認してから、一回の予約でMP支払い・HP回復・一件治療・予約完了を行うことです。ゲーム画面・AI・保存処理ではなく、開発用の明示行動APIです。

## 開発者の開始手順

開発者は、data/を含むプロジェクトルートで読取専用content_repository.gdを構築し、battle_session_application.gdへ渡してください。保存個体の再構築・Lv別習得・＋選択・装備許可は既存Builderへ委譲します。正規HeroはLv60でspirit_recoverを習得し、Lv59の行動選択は未習得として拒否します。

開発者はApplication.start_with_statuses(allies_records, enemies_records, shuffle_order, initial_statuses)を呼んでください。初期状態は全参加者についてside/id別に明示し、状態なしも[]で指定します。各陣営の参加数は最大四体ですが、所有数の制限ではありません。同じIDでもallies/enemiesは別の個体です。初期状態の欠落・余分・不正、データ読込・行動設定・初回順序の失敗では、Applicationは候補Sessionを公開せず、未開始状態を保持します。開発者は入力を直して同じ未開始Applicationで再試行できます。

従来のApplication.start(allies_records, enemies_records, shuffle_order)は状態未設定の入口を維持します。従来開始では治療付き行動を構築せず、resolve_cure_heal_skillはnot_initializedとして拒否します。通常HP回復のresolve_heal_skillは治療付き定義を引き続き拒否します。

低水準の開発者は、Session.start_with_statusesで数値資源/初期状態を開始し、Heal.new(session, true).start_cure_heal(teams, skills, initial_statuses)を呼んでください。専用行動は、ラウンド開始前・満資源でSessionと一致する数値/状態と、独立した習得/装備/定義を一度設定します。開始情報不一致・再設定・区分違いは拒否します。通常のHeal.new(session).start(teams, skills)はHP回復専用のままです。行動要求から構築区分を切り替える入口はありません。

## 行動要求と判定値

開発者はnext_actorが実際に提示した行動予約識別子ticketを使い、resolve_cure_heal_skillへticket・target・skill_idと任意rollだけを渡してください。次のJSONは形式例で、開発者は例のticketを流用しないでください。

```json
{
  "ticket": {"round": 1, "slot": 0, "actor": {"side": "allies", "id": "caster"}},
  "target": {"side": "allies", "id": "friend"},
  "skill_id": "spirit_recover",
  "roll": 0.02
}
```

targetは行動者と同陣営の生存参加者で、本人も指定できます。敵側の行動者はenemiesの仲間を指定します。敵・欠落・死亡・逃走対象は拒否します。治療付き行動は対象を自動選択せず、死亡個体を復活させません。

治療付き行動は[純粋統合予測](GDScript治療付き回復予測契約.md)を使います。解除可能な候補がある場合、確率0/1でも有限な0以上1未満のrollが必要です。候補なしならrollを省略でき、渡したrollも治療判定には使いません。状態の順序・解除不可の除外・確率の0〜1制限・候補一件の選択は共用治療契約へ委譲します。行動処理は乱数を生成しません。

開発者はHP/MP・回復率・治療確率・状態一覧・残存一覧・候補位置・装備・実行モードを行動要求へ追加しないでください。治療付き行動は未知キーをfalse/0/空でも拒否します。開始時に選ばれる定義/習得と、Sessionが現在所有する資源/状態だけを使います。

## 実更新と一回治療の制約

治療付き行動は、厳密要求・現在の提示票・習得済み一意定義・許可装備・対象・現在資源/状態をclaim前に検証します。MP不足や不正では、提示中の予約・HP/MP・状態・防御倍率を保持します。開発者は同じ未取得予約で別の正しい行動を指定できます。

治療付き行動は、単一claim→MP支払い→上限付きHP回復→Session.apply_status_cure→finishを同期実行します。回復量は対象の最大HPを基準にし、満HPでもMPを消費して治療判定を行います。回復量へ術者魔力・装備攻撃補正・物理防御倍率・属性耐性を適用しません。回復と治療の間にawait/外部callbackを挟みません。同じSessionを複数スレッドで同時更新する使い方には対応しません。

Session.apply_status_cure(ticket, target, request)は現在取得済みの行動票、生存する行動者/同陣営対象・生存敵と状態設定を確認します。requestはcure_chanceと任意rollだけです。Sessionは状態所有者へ最新一覧からの一件治療を委譲し、外部の予測結果や残存一覧を適用しません。正しく判定した一回は、治療不成立や候補なしでも使用済みにします。同じ取得済み票での再治療はstatus_cure_already_appliedとなり、確率を再抽選できません。不正要求で拒否した場合は使用済みにせず、正しい要求で再試行できます。

正しい要求の提示後に術者が死亡/逃走した場合や敵がいなくなった場合、治療付き行動はSessionへ予約取消を委譲します。取消はok=true・executed=falseで、追加MP消費・HP回復・状態解除を行いません。取消の場合も、候補に必要な不正rollを正常な取消と扱わず、拒否して票を保持します。使用済み/偽造/取得済み/古い票は追加更新しません。

成功結果はok=true・executed=true・scope=explicit_cure_heal_skill_onlyです。独立したticket/target、純粋統合予測numbers、実spent_mp/healed、状態所有者の実一件治療結果cure、更新後の数値sessionと独立statusesを返します。numbersの予測結果を編集しても所有資源/状態は変わりません。Session.snapshotの七キー、個体数値のidentity/stats/hp/mp/fled/alive六キーを維持し、状態一覧は数値とは別の読取です。

状態付与・毒等の継続効果・眠りによる行動取消・残存ターンの更新・戦闘後保存はこの契約に含みません。未知MOD状態・重複・JSON互換の拡張情報は一覧として保持しますが、効果を実装した証拠ではありません。個体/学習AI/items/party、正規data/assets、保存JSON/schemaは変更しません。

## 検証方法と成功条件

開発者はリポジトリルートで使えるGodot/Pythonを指定し、次を実行してください。検証は専用要求と個体/AI/items/party/stateの保存ダミーを使います。正規JSONは読取専用で、検証前後のbyte保持も確認します。実セーブを検証に使いません。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotの実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_cure_heal_action.py tests/test_gdscript_heal_action.py tests/test_gdscript_cure_heal_skill.py tests/test_gdscript_session_status.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_cure.py --cure-action
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_magic_action.py --heal
```

限定テストは実Pythonの_take_actionを、学習せず・明示対象/判定値だけ固定して呼び、最新HP/MP・一件治療・候補なし・確率境界/有限MODを実Godotと比較します。自動AI対象選択の検証ではありません。八体/二ラウンドと第三ラウンドの候補なし、同IDの陣営分離、正規HeroのLv59/60、原子的開始失敗/再試行、通常入口の治療拒否、取消・未知効果/要求・型/非JSON値・MP不足・対象不正・重複・入力/結果独立性を確認します。

--cure-actionは八体の次行動提示→実回復/MP消費/毒一件解除→完了を測ります。八行動ごとに新しいSession/専用行動と初期状態を正規APIで構築し、その構築・傷つける準備・初回ラウンドも計測へ含めます。解除済みや候補なしの高速経路で反復せず、各行動が実HP1回復・MP6消費・毒一件解除に一致することを確認します。計測用の大きな有限資源と回復率1e-9/治療確率1は性能だけの条件で、正規確率や能力値の変更ではありません。

標準性能は20000回・7サンプル・2000回事前実行で、一行動中央値3000us以内です。総行動数は八の倍数が必要です。固定八体の最終数値/状態、最後の実適用、全反復の確認数と原本保持がすべて一致した場合だけ成功します。--healは従来HP回復行動の回帰性能で、新規状態構築を含む--cure-actionとは別の条件です。

Godot未指定のskip/終了コード2は未検証です。開発者はGodotを指定して再実行してください。解析/実行診断・資源/状態不一致・時間超過は失敗です。AI推論/学習・戦闘Scene/演出・遭遇・勝敗/報酬/教会復活・実GUI・配布export・全E2E・リモートCIは未接続/未検証です。新規行動の成功をゲーム全体の移植完了とは扱いません。

[状態保持](GDScript戦闘Session状態保持契約.md) / [開始準備](GDScript治療付き回復準備契約.md) / [通常HP回復](GDScript回復スキル行動契約.md) / [形式仕様](FORMATS.md) / [コード入口](CODEMAP.md)
