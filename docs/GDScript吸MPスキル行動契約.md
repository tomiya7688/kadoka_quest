# GDScript吸MP付き単体魔法の行動契約

## 背景と目的

吸MPの純粋予測だけでは、戦闘中のHP・MPや行動予約は変わりません。GDScriptの吸MP行動は、正規習得・許可装備・耐性と最新予約を検証し、とりつく（possess）の敵HP効果・敵MP喪失・術者MP回復を戦闘Sessionへ一度だけ適用します。GDScriptの吸MP行動はAI選択・戦闘画面・保存を行いません。

対応する吸MP定義は[吸MP予測契約](GDScript吸MPスキル予測契約.md)と同じです。kindはdrain_mp、mp_power省略時は0.12です。吸MP定義の状態異常・自傷・全体攻撃等の未知効果は、値がfalse・0・空でも拒否します。

## 開発者の呼び出し方法

開発者は正規個体レコードをbattle_session_application.startへ渡して戦闘を準備してください。戦闘準備は習得・許可装備・耐性を再構築し、通常/自傷魔法とは別の吸MP専用入口を同じSessionへ設定します。

開発者はnext_actorが提示した現在の行動予約識別子ticketを使い、次の4キーだけをresolve_drain_mp_skillへ渡してください。

```json
{
  "ticket": {"round": 1, "slot": 0, "actor": {"side": "allies", "id": "ally"}},
  "target": {"side": "enemies", "id": "enemy"},
  "skill_id": "possess",
  "variance": 1.0
}
```

開発者は例のticketを流用せず、実際のnext_actorの提示結果を使ってください。吸MP要求のtargetは生存する敵のside/id、varianceは有限の0.92〜1.08です。吸MP要求へHP・MP・mp_power・吸収量・装備・耐性・guard・会心値を追加すると拒否します。吸MP行動は術者の最大MPと敵の現在MPを最新Sessionから取得します。

通常入口resolve_magic_skillと自傷入口resolve_self_damage_magic_skillは吸MP定義を拒否します。吸MP専用入口resolve_drain_mp_skillは通常魔法・自傷魔法を拒否します。吸MP定義のmp_powerが0でも吸MP専用入口を使用してください。

低水準のengine/magic_skill_action.gdは、Magic.new(session, false, true)で吸MP専用になります。既存のMagic.new(session)は通常魔法、Magic.new(session, true)は自傷専用のままです。自傷/吸MPを同時にtrueとした構築設定はstartでinvalid_magic_modeへ拒否します。行動要求から魔法区分を変更することはできません。

## 実適用の順序と結果

吸MP行動は、現在提示中の予約・習得済みの一意な定義・許可装備・敵対象・揺らぎを、資源更新前に検証します。吸MP行動は開始時の古い現在MPや要求側のMPを使わず、Sessionの最新資源から予測します。

吸MP行動は予約を一度だけ取得した後、awaitや外部callbackを挟まず、次の順に担当資源処理を呼びます。

1. 吸MP行動は術者のMPを消費します。
2. 吸MP行動は敵へ魔法のHP効果を適用します。属性吸収なら最大HPまで回復し、無効なら敵HPを変更しません。
3. 吸MP行動は予測された敵MP喪失量drained_mpを敵の現在MPから引きます。
4. 吸MP行動は敵が失った実MP量を術者のMP回復へ渡し、術者最大MPで回復を制限します。
5. 吸MP行動は予約を完了し、ラウンド終端と両陣営の最新生存を判定します。

吸MP行動は最後の敵を倒した場合も、予約完了より前に敵のMPを奪います。吸MP行動は敵の無効/吸収耐性でMPを奪わず、術者のMP消費だけを残します。吸MP量は弱/強耐性倍率・揺らぎ・基本防御倍率・固定追加ダメージで変わりません。

吸MP行動の敵MP喪失量と術者MP回復量は異なる場合があります。魔力100・mp_power0.14・術者現在/最大MP100・消費MP5・敵MP80では、敵は14MPを失い、術者は5MPだけ回復します。吸MP行動は回復できなかった9MPを敵へ戻しません。

吸MP行動の成功結果はok=true / executed=true / scope=explicit_drain_mp_magic_onlyとなり、独立したticket・target・numbers・術者の実消費spent_mp・敵の実喪失drained_mp・術者の実回復recovered_mp・更新後sessionを返します。吸MP行動のnumbersは非破壊の予測結果であり、実喪失と実回復は行動結果のトップレベルにも別々に返します。

## 数値MP回復と保存境界

combatant_state.restore_mp(amount)は有限・精度上限以内の非負整数を検証し、最大MPまでの空き量で回復を制限してから加算します。数値MP回復はrequested・previous_mp・restored・現在mp・aliveを返します。数値MP回復はbool・数値文字列・小数部分・NaN/Inf・精度上限超過を拒否し、不正時の資源を保持します。

battle_session.restore_mp(key, amount)はside/idを検証して資源所有者へ委譲します。数値MP回復はHP・fled・行動順・予約・段階を変更しません。数値MP回復は死亡/逃走個体のMPにも適用できますが、HP0の復活や逃走解除・行動許可を意味しません。

既存のSession.pay_mpも数値減算であり、生存や行動権の許可処理ではありません。吸MP行動はclaim前に敵の生存を検証済みのため、HP効果で死亡した敵へ予測済みのMP喪失だけを適用できます。吸MP行動は死亡済みの敵を新たな対象として選択できません。

吸MP行動は戦闘Sessionだけを変更します。保存個体・学習AI・items・party・正規data/assets・保存JSON/schemaは変更しません。戦闘資源snapshotのidentity/stats/hp/mp/fled/aliveの6キーも変更しません。正規定義・習得・許可装備・耐性は開始時の独立コピーとし、開始後の入力編集や返却コピーの編集は実行中の資源へ伝播しません。

## 拒否・取消

吸MP行動は不正要求・未習得・未対応効果・不正数値・必要な積の精度超過・MP不足・死亡対象をclaim前に拒否します。吸MP行動の拒否は提示中ticketとHP/MPを保持するため、同じ予約で通常攻撃などを再選択できます。

next_actorの提示後、claim前に術者が死亡/逃走した場合や敵がいなくなった場合、Sessionの単一claimは予約を取り消します。吸MP行動の取消結果はok=true / executed=falseと理由を持ち、MP消費・MP移転を行いません。偽造・取得済み・不一致・使用済みticketは拒否し、二度目の消費や回復を行いません。

## 開発者の検証方法

開発者はGodotのconsole実行ファイルを指定し、リポジトリのルートで次の検証を実行してください。吸MPテストは専用コンテンツ・保存コピーを使用し、利用者の実セーブは使用しません。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotコンソール実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_drain_mp_action.py tests/test_gdscript_magic_action.py tests/test_gdscript_self_damage_magic_action.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_magic_action.py --drain-mp
```

吸MP回帰テストは選択と揺らぎだけを固定し、学習しない実Pythonの_take_actionでMP支払い・敵HP/MP・術者MPを照合します。吸MPテストは満タン初期化後の資源減算で低HP/MPを作り、開始契約を緩めません。吸MPテストは耐性・MOD係数・最新資源・拒否/取消・重複予約・基本防御無視・8体/両陣営同ID/2ラウンド保持・保存コピーbyte不変も確認します。

吸MP性能検査は専用8体で次行動取得→検証/claim→MP消費→敵HP効果→敵MP喪失/術者MP回復→finishの1行動を測ります。標準条件は20000回・7サンプル・2000回の事前実行です。吸MP性能検査は大きな有限資源と専用係数0.7を使い、通常/強耐性では7MPを奪い、無効/吸収では奪いません。初回の満タン回復で味方2体が各2MPを回復できないケースも含みます。

吸MP性能検査は時間中央値3000us以内に加え、各行動の敵喪失・術者回復・両者の実MP、8体の累積MP純減とHP変化・生存を確認します。吸MP性能検査の累積MP検証は完全な8体ラウンドを前提とするため、非標準の総反復数が8未満または8の倍数でない場合はcomplete_rounds_requiredで失敗します。吸MP性能検査は起動・読込・初期再構築・AI・描画・保存を測りません。

Godot未指定によるテストスキップや性能CLIの終了コード2は未検証です。開発者はGodotを指定して再実行してください。開発者は解析/実行診断・資源不一致・時間超過を失敗として扱い、拒否理由に応じて要求のticket・対象・定義・最新MP・精度を確認してください。

## 未接続・未検証

GDScript吸MP行動のAI推論/学習、戦闘Scene・演出、野生遭遇、勝敗・報酬・教会復活は別の実装単位です。Sessionのstoppedはゲーム全体の勝敗保存の完成ではありません。実GUI・配布export・リモートCIの成功は、このヘッドレス検証では保証しません。
