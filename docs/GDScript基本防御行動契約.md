# GDScript基本ぼうぎょ・終端解除契約（#251）

#230の[通常攻撃行動](GDScript通常攻撃行動契約.md)へ基本ぼうぎょを追加する限定契約です。全員をattack/defendだけで動かすruntime、手動個体コマンドUI、AI選択、戦闘Sceneの代用品は作りません。

## 正規定義と責務

engine/basic_defend_contract.gdはread-onlyの正規data/skills/skills.jsonから一意なid:defend / kind:defendを検証します。文書はschema_version=1とskills配列の2キー。defendの許容キーはid/display_name/description/kind/damage_multiplier/mp_costだけです。表示メタデータは文字列。未対応counter/protect_ally/status/target等はfalse/空の指定でも拒否します。他のdefend系スキルをこのAPIで実行しません。

mp_costは有限0だけ、省略0。damage_multiplierは#221の純粋数値検証へ委譲し、省略0.5。数値文字列は既存の数値契約と同じく許容し、bool/不正型/非有限値を拒否します。有限の0/負/1超のMOD倍率を勝手に修復しません。極端な有限倍率による攻撃演算の精度超過は通常攻撃のclaim前に拒否します。

- basic_defend_action.gdは新規Sessionのbetween_roundsで一度だけ定義を設定し、コピーしたfloat倍率だけを保持します。途中Session/再設定は拒否。
- battle_session.gdは資源Stateとは別のside+id別guardを所有します。新規開始時1、終端時1。HP/MP/行動順をAction側で作り直しません。
- battle_session_application.gdはread-only準備→候補Session→攻撃と防御の設定→begin_roundを調停し、全成功後だけ所有者を切り替えます。定義・数値検証やguard更新をapplicationへ蓄積しません。

## 要求と単一適用

公開application APIへresolve_basic_defend(request)とeffects()を追加します。

    {
      "ticket": {"round": 1, "slot": 0, "actor": {"side": "allies", "id": "owned_01"}},
      "skill_id": "defend"
    }

要求はこの2キーだけ、両方必須です。基本防御の対象は本人なのでtargetを指定しません。guard/damage_multiplier/MP/status/対象/乱数を上書きできません。ticketは#229の現在offeredの厳密な完全一致だけです。

1. 要求/skill_id/現在offered ticketを読み取り検証する。
2. Session.claimが最新死亡/逃走/敵なしを再確認する。
3. can_executeならSession.apply_defendが現在claimedの本人guardだけを変更する。HP/MPは変更しない。
4. 同じticketでfinishする。末尾ならその時点で全guardを解除する。

この間にawait/外部callbackはありません。不正/古い/重複/既claimed/未offered要求はclaim前に拒否し、資源・guard・cursor・pendingを保持します。最新actor死亡/逃走/敵なしは既存の取消へ進みexecuted=false、効果を付けません。内部適用/finishが予期せず失敗した場合、claimは消費済みで再利用や架空rollbackをしません。

成功はok / executed / scope:explicit_basic_defend_only / ticket / applied_guard / session / effects。applied_guardは今回適用した倍率、effectsはfinish後の現在状態なので、最終行動が防御ならapplied_guard=0.5でもeffectsは1です。取消も現在session/effectsを返します。失敗はreasonまたは既存数値error/message。

## 所有・読取・解除時点

#227/#228の個体資源snapshotは引き続き厳密な6キー（identity/stats/hp/mp/fled/alive）。guard/status等の入力拡張は拒否し、保存JSONへも書きません。Session.snapshotの従来キーも維持します。

別のplain読取契約effects()は以下の独立コピーです。

    {"scope":"basic_guard_only","teams":{"allies":{"owned_01":0.5},"enemies":{"enemy_01":1.0}}}

Session.guard(side+id)は所有者の現在倍率を返し、通常攻撃は対象のこの値だけを使います。リクエストの倍率は使いません。物理の通常/会心いずれにも掛かり、会心の防御力無視は保持します。既存finish_damage数値契約のmagic/drain_mpへは掛かりませんが、魔法行動を移植した証拠ではありません。

guardの解除はbegin_roundではなく、正しいfinish/取消/nextの進行がround_finishedまたは敵なしstoppedを確定した時です。死亡/逃走者を含む全参加者を1へ戻し、HP/MP/fledは保持します。資源操作で死亡した直後は倍率を保持し、次の正規進行操作で終端処理を行います。末尾の死亡候補をnextでskipした場合も解除します。進行中のbegin、未claim finish、不正順列、重複/古い操作、再設定では解除しません。stoppedは勝敗・報酬・復活成功ではありません。

## 検証と性能

tests/test_gdscript_basic_defend.pyは実Godotの既存run_normal_attack_probe.gdを拡張して比較します。選択だけを固定して実Python_take_actionのdefendを呼び、実_attack(allow_counter=False)と比較します。通常/会心境界、低攻撃高防御、装備威力/固定追加、揺らぎ、最低1/HP上限、既定/MOD倍率を確認します。

8体/同速/両陣営同ID/最大3round/死亡/逃走/敵なし/skip末尾と、実run_roundの末尾解除を比較します。参照側は選択の固定と明示通常攻撃を調停し、_check_endをmockとして勝敗保存を除外します。AI推論・学習の比較ではありません。privateコピーの個体/学習済AI/party/items/data/assetsをbyte hashで保護し、実セーブを使いません。不正/未知キー/非有限・未対応MOD、offered/claimed/stale/重複、コピー・個体・roundの独立性も確認します。

開発者専用check_gdscript_basic_defend.pyは標準20000回/7samples/2000warmup、8体中1段階のnext→4防御/4攻撃の巡回→finishを計測します。8段階ごとのround計画とguard解除を償却し、中央値3ms以内、実HP減少、最終guard1を検証します。初期構築/定義I/Oは計測外。assertの外で実処理を呼ぶためassert無効でも計測する処理は消えません。Godot不在はexit2 Unverified。AI/全8行動まとめ/描画/FPS/I/O/export性能ではなく、Playerへimportしません。

全スキル・特殊防御・状態異常・耐性・AI推論/学習・野生接触・BattleScene・勝敗/報酬保存・実敗北→教会復活・GUI/exportは後続です。
