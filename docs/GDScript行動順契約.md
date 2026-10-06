# GDScript行動順・実行可否契約（#228）

#227のplain戦闘スナップショットから、ラウンド開始時の順序と、各行動直前の生存条件を計算します。順序を実際に消費するSession・攻撃/スキル/AI・勝敗・戦闘画面・演出はまだ接続しません。

## 純粋APIと識別子

`engine/turn_order.gd` はI/O・UI・乱数生成・AI・資源変更を持ちません。味方 `allies` と敵 `enemies` は各0〜4体の#227 snapshot配列です。同陣営の重複IDは拒否し、両陣営に同じIDがある模擬戦は許可します。保存個体のIDへ陣営名を付け足したり変更したりしません。

行動の識別子は2キーだけの `{"side":"allies","id":"slime_01"}` です。sideはallies/enemies、idは非空の安全な文字列。idだけや連結文字列で識別せず、別陣営の同じ個体IDを混同しません。キーやsnapshot、返却する生存一覧は独立コピーです。

- `participants(allies, enemies)` は入力を検証し、開始時の生存者を味方枠順→敵枠順の識別子配列membersにします。
- `plan(allies, enemies, shuffle_order)` は生存者全員の明示された順序を検証した後、speed降順にします。同速はshuffle順を保ちます。返却は `ok / initial / order / scope:base_turn_order`。
- `check_actor(key, latest_allies, latest_enemies)` は最新HP/fled/aliveと相手陣営の生存者で判断します。過去のplanや初期HPをキャッシュしません。返却は `ok / can_act / stop / reason / actor / friends / foes`。friends/foesは現在生存しているsnapshotの入力枠順です。

## シャッフルと速度

shuffle_orderはparticipants全員をちょうど1回ずつ含む配列が必要です。欠損/重複/未知対象/戦闘不能者/不正陣営/型違いを自動補完せず、理由と必要なindexを返します。開始時の生存者が0体の場合は空配列だけを許可します。片側が空でも計画は反対側の生存者を含み、check_actorで敵なしを判断します。

Python `run_round` の「味方→敵を収集、shuffle、speed降順のstable sort」と同じ順です。Godotの不安定なsortへ同速を任せず、最大8体へのstable insertionで保持します。速度は#220補正済み `stats.speed` を使い、Python Combatant.speedの未補正時と同じ `max(1, speed)` とします。0と1は同速です。GodotとPythonの乱数生成器の列やseed互換は保証せず、呼出側が決めたshuffle結果を入力します。

## 最新状態での拒否と停止

対象個体が存在し、敵側の生存者がいて本人も生存なら `can_act:true / stop:false / reason:ready`。本人がHP0/逃走なら `can_act:false / stop:false / reason:actor_not_alive`。敵の生存者がいなければ本人の状態に関わらず `can_act:false / stop:true / reason:no_living_foes` を返します。これはラウンドを打ち切れる情報であり、勝利/敗北/報酬/教会復活の成功結果ではありません。

型/不正snapshot/未知個体などは `ok:false` でcan_actを返しません。消えた個体はactor_missingで拒否し、「死亡した」と代用しません。順序確定後に死亡/逃走した個体の識別子は計画中に残りますが、実行前checkで除外します。checkだけでは順序に予定された候補か/行動済みかを証明しません。それらは後続Session/カーソルの責務です。

## 対応範囲の明示

snapshotは#227の6キー `identity / stats / hp / mp / fled / alive`、identityはid/species_id/nameの3キー、statsは6能力値だけです。#227の型/有限/非負整数/最大値/整合性を再検証します。追加のstatus_effects/speed_multiplier/timed_buff等や未知の実行時キーは、値が空や1でもunsupported_combatant_fieldsで拒否します。状態異常/速度buffを無視して対応済みにしたり、任意のeffective_speedを適用したりしません。

この厳密さは戦闘実行時の小契約に対するもので、保有monster.json/AI/正規コンテンツの未知キーを削除する仕様ではありません。生存だけでMP使用・命中/回避・耐性・AI判断・スキル対象・逃走率などの実行権限を全て判定した扱いにしません。

## 読み取り専用調停

`application/turn_preparation.gd` の `prepare(allies_records, enemies_records, shuffle_order)` は既存CombatantBuilderで新規個体snapshotを作り、Order.planへ渡します。返却は `ok / teams:{allies,enemies} / plan / scope:base_turn_preparation`。再構築失敗は陣営/detail付き拒否で、保存・修復・AI推論は行いません。

これは新規戦闘の開始準備であり、既存戦闘のラウンドごとにrecordsから最大HPを再生成する経路ではありません。行動中は保有recordsから再buildせず、既存戦闘の最新snapshotを純粋Orderへ渡します。戦闘中のState保持と順序消費は次のP1 [#229](https://github.com/tomiya7688/kadoka_quest/issues/229)です。4体のactive制限と無制限の所有/プリセットは従来どおりです。

## 検証

`tests/test_gdscript_turn_order.py` / `gdscript/tests/run_turn_probe.gd` は実Godotを使い、96のshuffle順/速度組、100の8体混合、0体/片側空/戦闘不能/逃走/同じIDの両陣営、最新生存、型/非有限/精度外/未知キー/不正shuffleを確認します。Pythonの実run_roundへ同一shuffleを注入し、実際にstable sortされたリストと比較します。参照側の行動と勝敗処理はtest mockで止めた部分比較で、AI/攻撃/勝敗の移植証拠ではありません。

正規8種族×Lv1/50/100×＋/許可装備の新規準備をPython BattleDataLoaderと比較し、入力/返却値の独立性と保有個体/学習済AI/party/items/data/assetsのbyte不変を専用コピーで確認します。実セーブは使いません。Godot指定なしのskipは移植成功ではありません。

既存 `check_gdscript_combatant.py` を拡張し、8体のplan＋1回の最新checkを実Godotで標準20000回/7samples/2000warmup・中央値2ms以内で測ります。既存の8体資源状態ガード1msも維持します。Playerにはimportせず、8回行動/実ラウンド・描画/FPS・I/O・exportの性能を測ったものではありません。手動画面/exportは未検証です。
