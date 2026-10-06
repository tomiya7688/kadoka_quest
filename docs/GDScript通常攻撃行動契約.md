# GDScript通常攻撃行動契約（#230）

#221の[数値契約](GDScript通常攻撃数値契約.md)を#229の[戦闘Session](GDScript戦闘Session契約.md)へ接続します。明示された通常攻撃を一度だけ現在HPへ適用する単位であり、AI選択や戦闘画面の完成ではありません。

## 責務と開始

- `data/content_repository.gd.load_skills()` は正規 `data/skills/skills.json` をread-onlyで返します。保存フォルダを読みません。
- `engine/normal_attack_contract.gd` はグローバルattack定義とread-only準備済み個体/装備を検証・投影します。JSON数値は既存Stateと同じ整数snapshotへ正規化してSessionとの一致を確認します。個体JSONや学習済AIは変更しません。
- `engine/normal_attack_action.gd` は検証→最新claim→HP適用→finishの同期処理を担当します。RNG/I/O/UI/AIに依存しません。
- `application/battle_session_application.gd` はPreparation→新規Session→content読込→Action設定→begin_roundの呼出調停です。全成功後だけ内部Session/Actionを切り替え、失敗はnot_startedのまま再試行できます。ダメージ計算や直接HP操作を持ちません。

公開application APIは `start / snapshot / begin_round / next_actor / resolve_normal_attack / resolve_basic_defend / effects`。層を越える入出力はplain dataで、内部RefCounted/Stateを返しません。各陣営4体までのactive制限と無制限の所有/プリセットは別です。

Action設定は開始直後のbetween_roundsと一致するfresh contextだけを許可し、未初期化Session/途中状態/別個体のcontext/成功後の再設定を拒否します。

## 行動要求

`resolve_normal_attack(request)` のキーは次の5つだけで、すべて必須です。

```json
{
  "ticket": {"round": 1, "slot": 0, "actor": {"side": "allies", "id": "owned_01"}},
  "target": {"side": "enemies", "id": "enemy_01"},
  "skill_id": "attack",
  "critical_roll": 0.5,
  "variance": 1.0
}
```

ticketは現在offeredの完全一致だけを許可します。round/slotは有限の非負整数、actor/targetは厳密なside+id。両陣営同IDを別個体として扱います。会心乱数は `[0,1)`、揺らぎは `[0.92,1.08]`。#221同様に有限の数値文字列も使用可能ですがbool/非有限/範囲外を拒否します。乱数生成や対象自動選択はこのAPIの責務ではありません。

通常の実行対象は最新snapshotに存在する生存敵だけです。味方/自身/不在/死亡/逃走した対象を拒否します。requestにattack/defense/equipment/guard/status等を加えても上書きできず、要求全体を拒否します。`defend` や魔法等のskill_idも未対応として拒否します。

## 定義と装備

グローバルschema_version=1のskills配列から、一意な `id: attack / kind: physical` を読みます。power/critical_multiplierは正規定義から使い、省略時1。mp_costは有限の0だけを許可し、0.5等も拒否します。許容フィールドはid/display_name/description/kind/power/mp_cost/critical_multiplier。それ以外のelement/status_effect/self_damage等は未移植として拒否し、MODの効果を黙って落としません。他skillは実行しません。

装備許可とstats補正は既存Builder/#220に委譲済みです。開始時に許可装備の `skill_modifiers.attack.power_multiplier / fixed_bonus_damage` だけを独立コピーで保持し、actorのside+idから取得します。元の返却値/入力を後から編集しても適用結果は変わりません。stat_multipliersは補正後statsに反映済み、resistance_steps/他skill_modifiersは通常physical攻撃では使用しません。未知の装備効果やattack補正の未知キーは拒否します。再初期化で装備を差し替えません。

## 一度だけの適用と失敗

1. 要求、現在offered ticket、敵対象、明示乱数、補正後statsと装備からの数値を検証します。読み取り専用 `Session.inspect_ticket()` は行動権を与えず、cursor/HPを変更しません。
2. `Session.claim()` が最新の死亡/逃走/敵生存を再確認して、単一の実行権を取得します。
3. #221が算出したdamageを当該Session Stateへ適用し、actual HP減少を保持します。
4. 同じticketをfinishしてcursorを一度だけ進めます。敵なしならstopped、順序末尾ならround_finished。stoppedを勝敗/報酬成功と扱いません。

処理の間にawait/外部callbackはありません。数値はPython同様の0方向切捨て、通常会心率1/16、会心は防御力を無視、最低1ダメージ、実減少は残りHPまで。現在HP/MP/fledは次ラウンドまで保持します。#251で対象の現在guardをSessionの信頼済み読取から取得します。一時攻撃倍率は1。基本防御は別の[行動契約](GDScript基本防御行動契約.md)で適用し、ラウンド終端で解除します。

| 結果 | HP/MPとcursor |
| --- | --- |
| 不正要求/対象/乱数/精度超過、unsupported、stale/重複/既claimed ticket | claim前に拒否し、全資源/cursor/pendingを保持。offeredなら正しい入力で再試行可。 |
| offered後にactor死亡/逃走、または敵なし | 正しい要求・存在する敵側key・乱数を検証後、claimが候補を取消。executed=false、ダメージなし、cursorは一度進む。敵なし時は指定対象が死亡済みでも攻撃せず停止する。 |
| 攻撃成功 | executed=true。numbersのdamage/dealt/remaining_hpと新sessionを返し、MPは変更しない。 |
| 内部HP適用/finishの予期しない失敗 | action_application_failed/action_finish_failed。claimは消費済みで再適用を許可しない。自動rollbackや成功偽装は行わない。通常検証済みの同期経路では到達しない。 |

成功結果は独立plainな `ok / executed / scope: explicit_normal_attack_only / ticket / target / numbers / session`。取消時は `ok:true / executed:false / reason / session`。数値拒否は#221のerror/message、それ以外はreason付き失敗です。HP0の相手への数値計算は#221単独で可能ですが、行動APIは死亡対象への攻撃を許可しません。

## 検証と範囲

`tests/test_gdscript_normal_attack_action.py` / `gdscript/tests/run_normal_attack_probe.gd` が実Godotを使用します。通常/会心境界/低攻撃・高防御/揺らぎ/装備/過剰ダメージを実Python `_attack(allow_counter=False)` と比較します。8体/同速/両陣営同ID/死亡skip/最大3ラウンドは実run_roundを使用し、_take_actionだけを明示通常攻撃選択に差し替え、_check_endをmockにして結果保存を除外します。これはAI選択や勝敗移植の証拠ではありません。

重複/古い/既claimed/不正ticket、対象/乱数/非有限/精度超過/未対応定義、コピー独立性、正規種族/Lv/装備/MOD powerを確認します。個体/学習済AI/party/items/data/assetsのbyte不変は専用コピーで検証し、実セーブを使いません。

`tools/performance-check/script/check_gdscript_normal_attack.py` は開発者専用。標準20000回/7samples/2000warmup、8体Sessionの1候補取得→検証/claim/実HP適用/finishを計測します。8行動ごとのround計画は償却、初期構築/定義I/Oは計測外。中央値3ms以内の退行ガードで、既存カーソル段階の2msとは異なり数値検証と実HP適用を含みます。HPを毎回リセットせず保持します。AI/全8行動/描画/FPS/I/O/export性能ではありません。Godot不在はexit2のUnverified、Playerへimportしません。

特殊防御/全スキル/状態異常/耐性/AI推論・学習/野生接触/戦闘Scene/勝敗・報酬保存/実敗北→教会復活は後続単位です。手動GUIとexportはUnverifiedです。全モンスターを通常攻撃だけで動かすruntimeを代用品として追加しません。

#251の[基本ぼうぎょとラウンド終端解除](GDScript基本防御行動契約.md)をローカル実装しました。未pushのIssueは完了操作しません。
