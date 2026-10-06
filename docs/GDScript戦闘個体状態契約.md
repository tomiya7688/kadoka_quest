# GDScript戦闘個体状態契約（#227）

#219/#220の補正済み6能力値と個体identityから、新規戦闘のHP/MP・逃走・生存状態を作る独立した契約です。#221の通常攻撃数値を実行時HPへ適用する開発者probeはありますが、戦闘Scene・ターン進行・AI推論/学習・全スキル・勝敗/報酬/保存・実際の敗北→教会復活はまだ接続しません。

## 責務と初期化

`engine/combatant_state.gd` は純粋な数値状態を所有します。I/O・UI・乱数・個体AIに依存せず、`start(identity, stats)` と操作の結果はplain辞書です。返す辞書/配列は参照共有せず、呼出側の編集で内部状態は変わりません。

identityには非空文字列の `id / species_id / name` が必要です。IDは既存の安全なID規則を使います。statsには `hp / mp / attack / defense / magic / speed` が必要で、有限・非負・整数値・2^53−1以下だけを受け付けます。最大HPは1以上、最大MPは0も許可します。JSON数値を読むGodotはfloatを使うため、2.0等の整数値floatも受け付けます。bool/文字列/小数値/欠損/非有限/精度外は理由付き拒否し、代替値を補いません。

初回成功時のHP/MPは最大値、fledはfalseです。`start` に渡した追加hp/mp・AI・未知キーを戦闘状態として読んだり保存したりしません。identityと6能力値だけを投影します。初期化失敗時は未初期化のままで、正しい入力で再試行できます。一度成功した同じインスタンスへの再初期化は `already_initialized` で拒否します。

Python Combatant.__post_init__の `hp=0 / mp=0` は新規生成時の最大値初期化です。実行時のHP0は死亡状態であり、そのたびに最大HPへ戻す処理ではありません。新規戦闘には新しいStateを作り、既存戦闘のStateを作り直しません。

## スナップショット

```json
{
  "identity": {"id": "slime_01", "species_id": "slime", "name": "スライム"},
  "stats": {"hp": 30, "mp": 7, "attack": 10, "defense": 10, "magic": 10, "speed": 10},
  "hp": 30,
  "mp": 7,
  "fled": false,
  "alive": true
}
```

`snapshot()` は独立コピーを返し、未初期化時だけ空辞書です。`alive()` は初期化済みかつHP>0かつ未逃走。最大値はstats内、現在値はhp/mpです。AI/スキル/耐性/状態異常/guard等をこの小契約で移植済みとしません。

## 操作

- `take_damage(amount)` は検証済み非負整数をHP0まで適用し、requested/previous_hp/dealt/hp/aliveを返します。dealtは実際のHP減少量で、0ダメージ・過剰ダメージ・既にHP0でも正確です。
- `mp_cost(cost)` は書換なしでcost/affordable/mpを返します。`pay_mp(cost)` は不足時に `insufficient_mp / spent:0`、足りる時にspent/mpを返します。0消費とちょうど残りMPの消費も可能です。不正値/不足ではMPを変えません。
- `flee()` はHP/MPを保ちfledをtrueにします。changedは初回true/再度false。逃走済みはHPが残っていてもalive=falseです。
- `living(snapshots)` は全スナップショットの型/最大値/現在値/flags/同一チーム内ID重複を検証し、alive=trueの独立コピーを入力順で返します。不正があればindexと理由を返し、一部だけ成功した一覧を返しません。

これらは数値資源の操作であり、行動権限の判断ではありません。死亡/逃走後の支払や数値変更を行動成功としません。行動を許可する将来のターン層が最新aliveと対象の生存を先に確認します。この段階には回復/蘇生やターン終了処理を追加しません。

## 読み取り専用組み立て

`application/combatant_builder.gd` は `build({monster, ai})` で既存個体/schema契約→#219/#220再構築→純粋Stateを調停し、ok/snapshot/warnings/equipment/scopeを返します。scopeは `combatant_resources_only`。内部Stateオブジェクトは返さず、AI内容を実行しません。AI辞書/schemaの検証は既存契約の範囲だけで、AI全意味検証やBattleDataLoader全体の移植ではありません。

未知＋/不明または装備不可IDは#220同様に保持し、補正不適用のwarningsを返します。破損/未対応schema/必要表なし/再構築失敗は理由/detail付き拒否で、個体や原本を修復しません。Builder内で種族/装備読込を共用し、次の走査/新しい戦闘開始には新しいBuilderを作って外部編集を反映します。

`build_team(records)` は解決済み個体レコード0〜4体だけを組み立てます。5体以上は `active_team_limit` で拒否し、Pythonの `[:4]` のように黙って切りません。空チームは許可、null/欠損個体/重複は拒否します。保存 `current_party` のnull空き枠は戦闘前applicationで解決する別の仕事で、このAPIはstateを読む/編集しません。所有数/プリセット数には制限を追加せず、120体の単体buildも検証します。

## #221との接続と検証

`gdscript/tests/run_combatant_probe.gd` は専用コピー上で、全8種族×Lv1/10/50/100×＋選択×許可装備の最大HP/MP/statsをPython BattleDataLoaderと比較します。明示乱数の通常攻撃を繰り返し、各回の現在HPを#221 target_hpへ渡し、damageをStateへ適用します。Python BattleEngineの実HP減少/dealt/残りHP/aliveとの一致と、HP0以後に戻らないことを確認します。

`tests/test_gdscript_combatant.py` は0/過剰ダメージ、MP0/不足/ちょうど/0消費、逃走・生存一覧、未初期化/再初期化、型/非有限/境界、不正JSON/必要定義欠損、入力/返却値/個体同士の独立、保有個体/学習済AI/party/items/正規data/assetsのbyte不変を検証します。実ユーザー保存は使いません。Godotがない場合は理由付きskipで、成功を代用しません。

開発者専用 `tools/performance-check/script/check_gdscript_combatant.py` は実Godotで8体のinit/damage/MP/flee/snapshot/livingを計測します。標準は20000回・7samples・2000warmup、中央値1ms以内の余裕ある退行ガード。Playerにはimportせず、描画/FPS・I/O・実ターン戦闘の計測ではありません。

次のP1 [#228](https://github.com/tomiya7688/kadoka_quest/issues/228) は行動順・行動直前の生存/実行可否です。全スキル/AI/実戦闘・自動戦闘UI・敗北復活は後続へ分けます。手動画面/配布exportは未検証です。
