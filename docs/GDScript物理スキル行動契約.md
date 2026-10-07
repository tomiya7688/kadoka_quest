# GDScript物理スキル行動契約

## 背景・目的

通常攻撃・基本ぼうぎょの次に、MPを払う単体物理スキルを戦闘Sessionへ接続します。前単位の予測だけでは、習得や装備許可の確認、行動権取得、実MP消費・HP更新を保証できません。

本単位では、正規のたいあたり・ころがる・つつくと同形式のMODスキルを、一度だけ適用します。これは未起票のローカル移行単位です。公開Issueの完了や全スキル移植ではありません。

## 手段と責務

- application/combatant_builder.gdは、既存JSONからレベル・＋選択・種族別装備許可を再構築します。習得skill_idsを独立コピーで渡し、資源snapshotの6キーは維持します。
- engine/physical_skill_context.gdは、fresh snapshot・習得ID・装備の許可種族と外形を検証します。正規定義を開始時にID別へ索引化します。重複を保持して選択時に拒否し、未対応スキルを勝手に削除・修復しません。
- engine/physical_skill_action.gdは、最新ticketと資源を確認し、検証成功後だけ単一claim→MP支払い→敵HP適用→finishを同期実行します。
- [physical_skill_contractの予測](GDScript物理スキル予測契約.md)と既存physical_damageを数値の正本として共用します。通常attackへ別IDを偽装しません。
- application/battle_session_application.gdは、read-only準備とActionの開始・要求ルーティングだけを担当します。初期化が全成功するまで内部所有者を切り替えません。

engineはI/O・乱数源・AI・UIを持ちません。保存JSON/schemaと正規data/assetsは変更しません。

## 開始時の契約

Action.start(teams, skills)は、Sessionがbetween_roundsで、未初期化の場合だけ成功します。teamsはallies/enemiesで、それぞれ最大4体です。個体はsnapshot、skill_ids、equipmentを持ちます。snapshotは既存のidentity/stats/hp/mp/fled/aliveの6キーです。

HP/MPが最大値、fledがfalseのfresh snapshotを既存Stateと同じ整数表現へ正規化し、Sessionの開始資源と一致することを確認します。skill_idsは空でない文字列の配列です。Actionは資源を複製して所有せず、開始時の定義・習得・装備だけを独立コピーとして保持します。

非空equipmentはallowed_species_idsに本人の種族を含む必要があります。application側で装備不可・不明IDと判断した装備は空辞書になり、IDと警告は元レコードに保持し、補正を加えません。pure開始APIへ許可のない非空装備を直接渡した場合は拒否します。raw要求から装備や習得を渡せません。

## 行動要求

application.resolve_physical_skill(request)またはpure Action.resolve(request)を呼びます。要求は次の5キーだけです。

| キー | 内容 |
| --- | --- |
| ticket | next_actorで得た、現在offeredの単一行動権 |
| target | 敵のsideとid。生存・未逃走の対象 |
| skill_id | 開始時に習得している正規のMP付き単体物理ID |
| critical_roll | 明示会心乱数。0以上1未満 |
| variance | 明示揺らぎ。0.92以上1.08以下 |

数値は既存の有限数値変換を共用します。数値文字列も同じ規則で扱い、bool・NaN/Inf・演算精度超過は拒否します。現在MPはSessionの正規整数を使用します。power、guard、equipment、skill_ids、current_mp等の追加キーは拒否します。attackとdefendは各専用APIへ渡してください。

定義はid・display_name・description・kind:physical・power・正のmp_cost・critical_multiplierだけを許容します。mp_costのPython互換0方向切捨て、有限負値の威力・会心倍率、会心1/16×倍率、防御無視、物理guard、揺らぎ、最低1・HP上限は予測と同じ規則です。

装備は選択IDのskill_modifiers[skill_id].power_multiplierと固定追加だけを投影します。attack用の補正を物理スキルへ流用しません。選択IDの追加効果はfalse/空でも拒否します。他スキル向け効果はそのスキルを選択した時点で検査します。

## 成功・拒否・取消

成功はok:true、executed:true、scope:explicit_physical_skill_only、ticket、target、numbers、spent_mp、sessionを返します。numbersの残HP/MP予測は実資源と一致し、spent_mpは実際に支払った値です。最後にfinishしてcursorを一つ進めます。返却辞書を編集してもSessionや開始コンテキストは変更されません。

MP不足はinsufficient_mp、未習得はskill_not_learned、未対応スキル/装備効果は対応する拒否理由です。不正・古い・重複・既claimedの要求、死亡対象、装備効果の拒否ではHP/MP・guard・cursor・offeredを消費しません。MP不足等の後でも、同じticketで通常攻撃へ変更できます。

offered後に行動者が死亡・逃走した場合、または敵が全員死亡・逃走した場合は、正しい要求をSession.claimの取消規則へ渡します。ok:true/ executed:falseで、MP支払い・HP適用を行いません。死亡対象がいても別の敵が生存している場合はtarget_not_aliveで再選択できます。

await/callbackを挟まない検証と適用により、成功後の通常Session操作は検証済みになります。万一支払い・適用・finishに内部失敗が発生した場合は理由付き失敗とし、取得済みticketを再利用しません。非同期実装や任意の外部Session実装に対するトランザクション保証ではありません。

ラウンド終端のguard解除は既存Sessionへ委譲します。HP/MPは次ラウンドも保持します。両陣営が同じidを持ってもsideとidで区別します。

## 開発者の実行方法

利用者がゲーム画面から選ぶ機能はまだありません。開発者は実Godotのパスを設定し、rootで次を実行してください。

    $env:KADOKA_GODOT_EXECUTABLE = '<Godot consoleの絶対パス>'
    & '<検証用Python>' -m pytest tests/test_gdscript_physical_action.py tests/test_gdscript_normal_attack_action.py tests/test_gdscript_basic_defend.py -q
    & '<検証用Python>' tools/performance-check/script/check_gdscript_physical_action.py

テストは専用data/assets/個体/AI/items/partyコピーを使い、元データや利用者の保存先を書きません。実Python_take_actionの選択だけを固定し、実MP支払いと物理行動を比較します。AI推論や学習を移植した証拠にはしません。

成功時は件数と性能を表示します。Godot未指定は実エンジンテストをskipし、性能検査はexit2/Unverifiedにします。解析・実行エラーや閾値超過は失敗です。パスと診断を確認して再実行してください。

性能検査は標準20000回・7samples・2000warmupで、8体中のnext→検証→claim→MP→HP→finishを一段階ずつ測ります。8行動ごとのround準備を含め、開始時I/O・再構築・warmupは計測外です。中央値3ms以内に加え、実HP減少と累積MP支払いも確認します。描画・AI・FPS・保存の性能は保証しません。

## 受け入れ条件と未検証範囲

正規3スキルの会心境界・guard・装備ID別補正・揺らぎ・HP上限、有限MODとMP変換、ちょうど支払い・不足・最新資源、再選択・重複・取消、レベルと＋習得・装備不可、8体同速/両陣営同ID/ラウンド間保持、コピーとprivateファイルのbyte不変を検証します。

単体魔法・属性耐性・状態異常・反撃・庇い・全体/ランダム攻撃・特殊防御・一時攻撃倍率・AI・戦闘Scene・勝敗/報酬/復活・実GUI・配布export・リモートCIは範囲外です。次の候補は、MP付き単体魔法の定義・数値予測と属性耐性を、状態異常等と分けて契約化する単位です。
