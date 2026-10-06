# GDScript戦闘Session契約（#229）

#227のHP/MP・生死Stateを所有し、#228の固定行動順を1体ずつ消費します。攻撃/全スキル/AI/演出/勝敗/保存/教会復活は実行しません。Sceneへの接続もありません。個体別の手動コマンドUIを追加する契約ではありません。

## 所有と新規開始

`engine/battle_session.gd` はI/O・UI・乱数生成・AIに依存しない純粋Sessionです。`start(allies, enemies)` は各0〜4体の#227 snapshotを#228の厳密な型・数値・未知キー規則で検証します。同陣営の重複IDは拒否、両陣営同IDは許可。active制限を所有数/プリセット数へ適用しません。

startは新規戦闘だけです。hp/mpがstats最大値と一致し、fled=falseのsnapshotを受け付けます。途中のHP0/消費済MP/逃走を最大値へ戻す入力は `fresh_start_required` で拒否します。途中状態の復元APIではありません。失敗時は両チームとも未初期化のまま、正しい入力で再試行可能。成功後の再初期化は `already_initialized`。各個体に独立Stateを作り、既存ラウンド間で作り直しません。

`snapshot()` は `phase / round / cursor / order / pending / teams:{allies,enemies} / scope:base_battle_cursor` のplainコピーです。teamsは現在の#227 snapshot配列、orderはside+id配列です。初期phaseはnot_started、開始直後はbetween_rounds。RefCountedや内部Stateを層外へ返しません。入力/初期結果/plan/候補/チケット/全snapshotの編集は内部状態を変更しません。

## ラウンドと候補のプロトコル

1. `begin_round(shuffle_order)` はbetween_rounds/round_finishedからのみ実行可能。現在生存者の明示順列を#228へ渡し、stable速度順を固定します。不正順序でround/cursorを進めません。進行中/pending/停止後の開始は `round_not_available`。
2. `next_actor()` は予定順に最新生存を確認し、死亡/逃走者をskippedへ加えて飛ばします。敵がいなければstopped。生存候補があればstage:offeredのpendingを予約します。取得は実行開始ではなく、常にcan_execute=falseです。重複取得は同じpendingを返し、二重に進めません。
3. `claim(ticket)` はofferedに対して一度だけ最新生存を再確認します。成功時だけstage:claimed、can_execute=trueと最新friends/foesを返します。死亡/逃走/敵なしなら予約を消費しcan_execute=false、次またはstoppedへ進みます。重複claimは `already_claimed`。実際の行動解決は後続が同じ同期呼出経路で行い、claim後の非同期状態変更/並列解決は保証しません。
4. `finish(ticket)` はclaimedだけを完了し、pendingを消しcursorを一度だけ進めます。未claimは `pending_not_claimed`、二重完了や古いticketは `ticket_not_pending`。これは行動の効果/命中を計算する操作ではありません。

ticketはちょうど `{"round":1,"slot":0,"actor":{"side":"allies","id":"slime_01"}}` の3キーです。round/slotは有限・非負整数値・2^53−1以内、actorは#228の2キー。JSONの整数値floatは許可、bool/文字列/小数/未知キー/不正陣営は拒否します。現在pendingと全値が一致する必要があり、別roundの同じ個体へ再利用できません。

順序は候補ごとに再shuffle/再sortしません。round_finishedはカーソル末尾、stoppedは片陣営の生存者がいない条件です。空チームでも正しい順序を検証してからstoppedへ進みます。どちらも勝敗/報酬/復活の成功結果ではなくoutcomeを持ちません。pending取得を繰り返しても新しい実行権限を返しません。

## 資源操作と保持

`take_damage(key, amount) / mp_cost(key, cost) / pay_mp(key, cost) / flee(key)` はside+idで当該Stateへ委譲します。不明個体はactor_missing、不正keyはinvalid_actor_key。不正額/不足時の非破壊性、HP0上限、実減少量、MP0、逃走の冪等性は#227と同じです。

資源操作は候補を消費せず、死亡/逃走者へ数値操作できることも行動許可ではありません。next/claim/finishの時点で最新状態を評価します。ラウンドが終わってもHP/MP/fledを保持し、HP0を復活させません。未初期化の資源/ラウンド/候補操作はnot_initializedで拒否します。

## 読み取り専用開始調停

`application/battle_session_application.gd` の `start(allies_records, enemies_records, shuffle_order)` は既存read-only Preparation→新しいSession.start→begin_roundを調停します。全成功後だけ内部Sessionを公開用snapshotへ切り替えます。失敗時はnot_startedのまま、修復/書換なしです。返却はok/preparation/sessionのplain data。#230では[通常攻撃行動契約](GDScript通常攻撃行動契約.md)のread-only定義準備と行動ルーティングを追加し、begin_round/next_actor/resolve_normal_attackも公開しました。Session自体へ攻撃計算は追加しません。

準備のwarnings/equipmentは独立plain結果で保持しますが、Sessionの資源snapshotにAI/耐性/状態異常等を混ぜません。snapshot追加キーは未対応として拒否し、保有JSONの未知キーを削除しません。保存schema/ファイルを追加せず、個体/学習済AI/party/items/data/assetsを保持します。

## 検証範囲

`tests/test_gdscript_battle_session.py` / `gdscript/tests/run_battle_session_probe.gd` は実Godotを使います。8体・同速/速度差・両陣営同IDの60組を最大3ラウンド比較し、Python実run_roundの順序/生存判定と一致することを確認します。参照側の_take_actionを数値資源変更stub、_check_endをmockに置き換えた限定比較で、攻撃/AI/勝敗を移植した証拠ではありません。

3ラウンド連続の資源保持、途中の死亡/逃走、取得後の死亡/敵なし、二重取得/claim/finish・古いticket・不正順序・再初期化、不正型/非有限/未知キー/不正宛先、入出力/個体同士の独立性、8種族の開始準備を検証します。個体/学習済AI/party/items/data/assetsは専用コピーでbyte不変を確認し、実セーブは使いません。Godot未指定のskipは成功の代用ではありません。

`tools/performance-check/script/check_gdscript_battle_session.py` は開発者専用。標準20000回/7samples/2000warmup、8体Sessionのnext→claim→0ダメージ/0MP→finishを1段階ずつ計測します。8段階ごとの次round計画を償却し、中央値2ms以内の退行ガード。初期State構築は計測外、既存8体資源/plan性能ガードは維持します。Playerへimportせず、実攻撃/AI/8体全ラウンド/描画/FPS/I/O/exportの計測ではありません。

P1 [#230](https://github.com/tomiya7688/kadoka_quest/issues/230)で通常攻撃を接続しました。読み取り専用inspect_ticketは現在offered/最新生存を確認するだけで行動権を与えません。防御/戦闘Scene/全スキル/AI/勝敗保存/実敗北復活は後続。手動画面/exportはUnverifiedです。
