# GDScriptの単体HP回復行動契約

## 背景と目的

単体HP回復の純粋予測だけでは戦闘資源を変更できません。heal_skill_action.gdは、開始時の習得・許可装備と最新の行動予約を確認し、生存する味方1体のHP回復と術者MP消費を同じSessionへ一度だけ適用します。AI選択・戦闘画面・保存は行いません。

対応定義は[回復予測契約](GDScript回復スキル予測契約.md)と同じです。small_healとhealy、およびkind=heal・正のmp_costを持つ互換MODを扱います。治療付きspirit_recoverや未知効果は、値がfalse・0・空でも拒否します。

## 開発者の呼び出し方法

開発者は保存個体レコードをbattle_session_application.startへ渡してください。準備処理はLv別習得と装備許可を再構築し、回復専用の行動処理を通常攻撃・物理・魔法と同じ候補Sessionへ設定します。初期化に失敗した場合は、使用中のSessionを部分更新しません。

開発者はnext_actorが現在提示したticketを使い、resolve_heal_skillへ次の3キーだけを渡してください。

```json
{
  "ticket": {"round": 1, "slot": 0, "actor": {"side": "allies", "id": "caster"}},
  "target": {"side": "allies", "id": "friend"},
  "skill_id": "small_heal"
}
```

開発者は例のticketを流用せず、実際の提示結果を使ってください。targetは行動者と同陣営の生存個体で、本人も指定できます。敵側の行動者はenemiesの仲間を指定できます。同じidが両陣営にあってもsideで区別します。敵・欠落・死亡・逃走対象は拒否します。HP0の数値予測は、回復行動による復活許可ではありません。

開発者は要求へ回復率・現在HP/MP・最大HP・魔力・装備・防御倍率・耐性・会心値・揺らぎを追加しないでください。回復行動はこれらの上書きを拒否し、回復対象を自動選択しません。

低水準のHeal.new(session).start(teams, skills)も利用できます。teamsは満HP/MPのsnapshot・skill_ids・equipmentを持つ両陣営、skillsはschema_version=1とskills配列です。回復行動はSession資源との一致を確認し、独立コピーと定義のID別索引を一度だけ保持します。再設定・開始後の消費済み資源・不一致は拒否します。通常/自傷/吸MP魔法の入口へheal定義を渡す使い方は対応しません。

## 実適用と結果

回復行動は要求・最新offered予約・習得済みの一意な定義・許可装備・対象を、予約取得前に検証します。回復予測はSessionの最新術者MP・対象HP・対象最大HPから計算します。回復量はmax(1, int(対象最大HP × 回復率))で、実回復は最大HPまでの空き量で制限します。回復率省略時は0.15です。有限MODの負/0回復率でも上限量は最低1になります。

回復行動はawaitや外部callbackを挟まず、単一claim→術者MP支払い→Session.healによるHP回復→finishの順に実行します。満HPの味方には実回復0でもMPを払います。術者の魔力・装備の攻撃用power_multiplier/fixed_bonus_damage・対象のguard・属性耐性・乱数は回復量に使いません。既知の装備攻撃数値は検証だけ行い、選択IDの未知装備効果や不正数値は拒否します。

成功結果はok=true・executed=true・scope=explicit_heal_skill_onlyです。独立したticket・target・numbers・実消費spent_mp・実回復healed・更新後sessionを返します。numbersは回復上限量heal_amount・予測healed・remaining_hp・mp_cost・remaining_mpを持つ非破壊予測です。トップレベルのhealedは、資源所有者が実際に回復した量です。

## 拒否・取消と保存境界

回復行動はMP不足・未習得・不正要求・未対応効果・対象不正・必要な積の精度超過をclaim前に拒否します。拒否ではoffered予約とHP/MP・guardを保持し、同じ予約で別行動を再選択できます。偽造・使用済み・取得済み・不一致ticketは拒否し、追加消費しません。

正しい要求に対して、提示後に術者が死亡/逃走した場合や敵がいなくなった場合は、Sessionへ予約取消を委譲します。取消結果はok=true・executed=falseと理由を持ち、HP/MPを消費しません。不正要求を行動取消と誤認して予約を消費することはありません。

回復行動は戦闘中のSessionだけを変更します。snapshotのidentity/stats/hp/mp/fled/aliveの6キー、保存JSON/schema、個体・学習AI・items・party・正規data/assetsは変更しません。開始後の入力編集や結果コピーの編集は、所有資源と開始情報へ伝播しません。数値資源APIのSession.healは死亡個体にも数値加算できますが、回復行動は生存検証で死亡対象を拒否します。

## 開発者の検証方法

開発者はリポジトリのルートでGodot consoleとPythonを指定して実行してください。回帰テストは専用コンテンツと専用保存コピーを使い、実セーブを使用しません。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotコンソール実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_heal_action.py tests/test_gdscript_heal_skill.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_magic_action.py --heal
```

回帰テストはAI選択だけを固定した、学習しない実Pythonの_take_actionでHP回復とMP支払いを比較します。Pythonの対象候補は1体だけで、自動対象選択の移植検証ではありません。テストは最新資源・満HP・本人回復・両陣営同ID・8体/2ラウンド・拒否/取消・装備許可・Lv別習得・数値精度・基本防御無視・専用保存コピーのbyte不変を確認します。

性能検査は専用8体の次行動取得→検証/claim→実MP消費→実HP回復→finishを測ります。標準は20000回・7サンプル・2000回事前実行で、8行動ごとのラウンド準備を含みます。大きな有限資源と専用回復率1e-9を使い、毎行動1HP回復・6MP消費を続けます。中央値3000us以内に加え、各行動の実回復・消費MPと8体の累積HP/MPを独立に確認します。正規率・満HP・上限直前は回帰テストへ分けます。起動・読込・初期再構築・AI・描画・保存は測りません。

Godot未指定のテストスキップと性能CLIの終了コード2は未検証です。開発者はGodotを指定して再実行してください。診断・資源不一致・時間超過は失敗です。開発者は拒否理由に応じて現在ticket・習得・対象の陣営/生存・定義の未知効果・現在MP・数値精度を確認してください。

## 未接続・未検証

[治療付き回復](GDScript治療付き回復行動契約.md)は構築時に固定した別区分と専用Application入口へ接続しました。本書の通常回復入口は治療付き定義を拒否し、状態を解除しません。AI推論/学習、戦闘Scene・演出、野生遭遇、勝敗・報酬・教会復活は未接続です。Sessionのstoppedは勝敗保存の完成ではありません。実GUI・配布export・リモートCIの成功は、ヘッドレス検証では保証しません。
