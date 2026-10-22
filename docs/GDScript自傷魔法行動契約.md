# GDScript自傷付き単体魔法の行動契約

## 背景と目的

自傷魔法の純粋予測だけでは、戦闘中のHP・MPや行動予約は変わりません。この契約は、正規の習得・装備・耐性と最新の予約を検証し、メタルバーストの敵への効果と術者のHP代償をSessionへ一度だけ適用します。AIによる選択や戦闘画面は接続しません。

対応定義は[自傷魔法予測契約](GDScript自傷魔法予測契約.md)と同じです。通常魔法のキーに必須の有限self_damage_ratioだけを加えます。未知の効果は値がfalse・0・空でも拒否し、効果を省略した成功にしません。状態異常・吸MP・回避・反撃・全体攻撃は未対応です。

## 呼び出し方法

開発者は正規の個体レコードをbattle_session_application.startへ渡して戦闘を準備してください。startは習得・許可装備・耐性を再構築し、通常魔法とは別の自傷専用入口を同じSessionへ設定します。

次行動の取得結果に含まれる提示中のticketを使い、次の4キーだけをresolve_self_damage_magic_skillへ渡してください。

```json
{
  "ticket": {"round": 1, "slot": 0, "actor": {"side": "allies", "id": "ally"}},
  "target": {"side": "enemies", "id": "enemy"},
  "skill_id": "metal_burst",
  "variance": 1.0
}
```

ticketは例を流用せず、現在のnext_actorの取得結果を使ってください。targetは生存する敵のside/id、varianceは有限の0.92〜1.08です。HP・MP・代償率・耐性・装備・威力・guard・会心値を要求へ追加すると拒否します。

resolve_magic_skillは自傷付き定義を引き続き拒否します。resolve_self_damage_magic_skillは自傷率を持たない通常魔法を拒否します。自傷率が数値0でも、自傷専用入口を使用してください。

低水準のengine/magic_skill_action.gdは、構築時にMagic.new(session, true)を指定すると自傷専用になります。既定のfalseは通常魔法専用です。行動要求から区分を切り替えることはできません。魔法の共通処理を複写せず、区分に対応する定義検証と純粋予測を使います。applicationは要求を委譲し、数値計算や資源更新を行いません。

## 適用順序と結果

行動処理は、現在の提示中予約・習得・選択定義・敵対象・揺らぎを検証します。行動可能な場合は、Sessionの最新の術者HP・最大HP・MPと対象HPから予測します。要求側の数値や開始時の古い残HPは使いません。

予約を一度だけ取得した後、awaitや外部callbackを挟まず、次の順に適用します。

1. 術者のMPを消費します。
2. 敵へダメージを与えます。属性吸収なら最大HPまで回復し、無効ならHPを変えません。
3. 術者から予測された実HP減少self_dealtを引きます。
4. 行動予約を完了し、ラウンド終端や両陣営の生存を判定します。

代償の計算上の量self_damageと、HP1下限で制限した実減少self_dealtは異なる場合があります。実適用にはself_dealtを使うため、術者のHPは最低1残ります。敵が無効・吸収の場合や最後の敵を倒した場合も、終了処理の前に代償を支払います。数値0・文字列0・有限負率のMOD互換は予測契約に従います。

成功結果はok=true、executed=true、scope=explicit_self_damage_magic_onlyとなり、独立したticket・target・numbers・実支払量spent_mp・更新後sessionを返します。numbersには敵HP・残MPの予測に加え、self_damage・self_dealt・remaining_actor_hpがあります。

## 拒否・取消と保存境界

不正要求・未習得・未対応効果・不正または非有限の数値・MP不足・死亡対象は予約取得前に拒否します。提示中の予約とHP/MPを保持するため、同じticketで通常攻撃などを再選択できます。

next_actorの予約提示後、claim前に術者が死亡・逃走した場合や敵がいなくなった場合は、Sessionの単一claimが行動を取り消します。取消結果はok=true、executed=falseと理由を返し、MP・術者HPの代償は消費しません。取消は死亡を蘇生したり逃走を解除したりしません。偽造・取得済み・不一致・使用済みのticketは拒否し、二度目の支払いをしません。

自傷行動は戦闘用Sessionだけを更新します。個体レコード、学習AI、items、party、正規data/assets、保存JSON/schemaは変更しません。正規定義・習得・許可装備・耐性は開始時の独立コピーを使用します。開始後の入力や返却コピーの編集は所有資源へ伝播しません。

## 開発者の検証方法

開発者はGodotの実行ファイルをKADOKA_GODOT_EXECUTABLEへ設定し、利用者の実セーブとは別の保存先を使ってください。リポジトリのルートで次を実行してください。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotコンソール実行ファイル>'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_self_damage_magic_action.py tests/test_gdscript_magic_action.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_magic_action.py --self-damage
```

回帰テストは専用data/assets・保存コピーと学習しないPython戦闘を使います。選択と揺らぎだけを固定し、実_take_actionのMP消費・敵HP・術者HPを照合します。低HPは満タン初期化後の実ダメージで作ります。耐性・MOD率・MP不足・取消・重複・HP1・8体のラウンド間保持・コピー・保存ファイルのbyte不変も検証します。

性能検査は専用8体で、次行動取得から検証・予約取得・MP・敵HP・術者HP代償・完了までの1行動を測ります。20000回・7サンプル・2000回の事前実行と、8行動ごとのラウンド準備を含みます。標準反復で全員が生存するよう、最大HP10億に対して毎回代償1となる専用MOD率1e-9を使います。正規率0.1とHP1下限の正しさは回帰テストで確認します。

中央値3000us以内、8体のHP変化・生存・累積MP消費・累積術者代償が期待値と一致した場合だけ性能検査は成功します。起動・読込・再構築・描画・AI・保存は測りません。Godot未指定による終了コード2やテストスキップは未検証です。開発者はGodotを指定して再実行してください。診断・資源不一致・時間超過は失敗です。

## 未接続の範囲

AI推論・学習、戦闘Scene・演出、野生遭遇、全スキル、勝敗・報酬・教会復活は後続単位です。Sessionの終端判定をゲーム全体の勝敗処理の完成とは扱いません。実GUI・配布export・リモートCIの成功は、このヘッドレス検証では保証しません。
