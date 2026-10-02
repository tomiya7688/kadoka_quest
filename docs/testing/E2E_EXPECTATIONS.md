# E2E期待動作カタログ（#200 / 親 #199）

この表をユーザー操作シナリオの正本とする。内部関数一覧やunitカバレッジ表ではない。#201の決定的harnessは実装済み（`tests/e2e/README.md`）。基盤の再現性・隔離テストは主要操作フローの代替ではないため、下記は引き続き `missing`。既存テストの根拠は末尾に示すが、それだけでE2E対応済みとはしない。

## 対応状況と読み方

`covered` は本番entrypoint/composition root・runtime/command境界から操作し、ThenをassertするE2Eがある状態。永続化を伴う場合はJSON確認と状態を作り直したreloadまで含む。`missing` は未実装または期待値の検証が不足している状態。`intentionally-not-e2e` は理由を明示した除外。現在の数はチェックコマンドから取得し、別の集計表を手動保守しない。

```text
python tools/e2e-catalog/script/check_e2e_catalog.py
python tools/e2e-catalog/script/check_e2e_catalog.py --missing
```

各表の列名・IDを維持する。Persistenceは `yes`（保存結果とreloadを検証）または `no`（画面・実行時状態のみ）。E2E欄は未対応時 `-`、対応時は ``tests/e2e/test_file.py::test_name`` または ``tests/e2e/test_file.py::TestClass::test_name``。複数は `<br>` で区切る。範囲を満たすテストが通ったときだけcoveredへ更新する。

チェックツールは文書形式とテスト定義の**静的な存在**を検査する。テストの成功・操作経路・期待値の十分さは保証しない。coveredテストを削除すると、その行を実効missingとして報告して失敗する。テストを復元するか、Statusをmissing、E2Eを `-`、理由を未対応理由へ戻す。unit/integrationテストを参照してcoveredにすることも拒否する。

## Player / ゲーム操作

| ID | 機能/画面 | Given | When | Then | Persistence | E2E | Status | 理由/次の担当 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| KQ-P01 | Player起動 | 正規data/assetsと隔離セーブ | Player入口からゲーム開始 | fieldモードで現在マップが表示され、Developer編集機能が出ない | no | - | missing | game composition rootのharnessは #201。Player入口・表示のシナリオは未対応。#202 |
| KQ-P02 | 新規ゲーム | 未使用のセーブ名 | ランチャーで新規作成して開始、再起動 | starting_town、主人公とボールスライムの個体、最大4枠の初期パーティが作られ、同IDが復元される | yes | - | missing | ランチャー→runtime→reload未対応。#202 |
| KQ-P03 | ロード | 異なる位置/パーティを持つ2セーブ | 名前を選択してロード、再起動 | 選択したセーブのマップ/整数座標/個体/パーティ/所持品/AIを復元し、他セーブを変更しない | yes | - | missing | 名前切替とプロセス相当再生成未対応。#202 |
| KQ-P04 | 別名保存 | 個体AI・アイテム・プリセット付きセーブA、未使用名B | 別名Bへ保存しBをロード | Aの内容をBに複製し、個体ID/AI/所持品/編成を維持する。B編集後もAは元のまま | yes | - | missing | フォルダ複製後の操作・reload未対応。#202 |
| KQ-P05 | フィールド移動 | 敵のいない通行可能な1マス先 | 移動入力後に時刻を進め、再起動 | 指定方向へ整数座標が1マス進み、向きと表示位置が同期する。保存座標も同じ | yes | - | missing | 入力adapter→runtime→保存未対応。#202 |
| KQ-P06 | 衝突 | 壁/岩/看板/固定モブ/野生個体で塞がれた隣マス | 対象へ歩こうとする | 同じマスへ侵入せず、位置を維持する。敵への接触戦闘はP16で検証 | no | - | missing | 各障害を本番移動経路で操作するケース未対応。#202 |
| KQ-P07 | 長押し | 複数マスの通路、固定clock | 方向キーを長押しし、離して時刻を進める | リピート待機後に連続移動し、離した後は移動が止まる | no | - | missing | sleepに依存しないキー入力列未対応。#202 |
| KQ-P08 | 触れる移動ポイント | step遷移が地形と同じマスにある | そのマスへ歩き、再起動 | targetのmap_id/座標へ1回遷移し、移動先が復元される | yes | - | missing | 編集JSONとruntimeの遷移連携未対応。#202 |
| KQ-P09 | 調べる移動ポイント | interact遷移の隣にいる | 通り過ぎる、戻って調べる、再起動 | 通過だけでは遷移せず、調べたときだけ指定先へ移る。新緑の森の岩から住処に入れる | yes | - | missing | activation差と既存入口のシナリオ未対応。#202 |
| KQ-P10 | NPC会話 | 複数台詞デッキの固定モブが正面にいる | 時刻を進めながら複数回話す | 正面のNPCは勝手に移動せず、デッキを一巡するまで同じ台詞を繰り返さない | no | - | missing | NPC入力と周期更新を合わせた経路未対応。#202 |
| KQ-P11 | 住処の暗号 | まる/かどか未所有、住処の湧き場にいる | 調べ、7文字の「へいわなすみか」を入力、再起動 | 入力画面からfieldへ戻り2個体と取得フラグが保存される。住処の2体は残る | yes | - | missing | イベント→入力→取得→reload未対応。#202/#204 |
| KQ-P12 | 暗号誤答/取消 | 湧き場で入力中、2個体未所有 | 8文字目を入力、誤答を送信、取消 | 入力は7文字以内、誤答では仲間が増えず、取消でfieldへ戻る | no | - | missing | パスワード画面操作列未対応。#202 |
| KQ-P13 | 固定モブ消滅 | despawn=true、再出現可/不可の2モブ | 会話または固定戦勝利、マップ再入場、reload | 消滅し、再出現可だけ初期位置へ戻る。不可は保存後も消えたまま | yes | - | missing | 消滅・再入場・保存を跨ぐ経路未対応。#202/#203 |
| KQ-P14 | 野生個体AI | random/chase/idle、既定seed/clockのfixture | 主人公を止めて時刻を進め、chaseへ視認させる | idleは静止、randomは周期で徘徊、chaseは視認時に通常より速く追跡する。個体は重ならない | no | - | missing | 時刻/RNG注入の代表シナリオ未対応。#201/#202 |
| KQ-P15 | 野生ポップ | pop_rate=0/100、小数weight、通常/メタル域のfixture | マップへ入り、対象個体と遭遇 | 0では生成なし。100は有効枠で生成し、設定の種族/Lv/AIを利用する。ball_slimeは湧かない | no | - | missing | 編集→出現→遭遇の境界未対応。#202 |
| KQ-P16 | 野生遭遇 | 有効な個体が主人公の正面にいる | 接近入力またはfield更新 | 1回だけbattleへ切替。接触個体の種族/Lvを引継ぎ、開始成功後だけその個体を消費する | no | - | missing | 接触→battle開始の操作シナリオ未対応。#202/#203 |
| KQ-P17 | コマンド戦闘 | 固定seedの通常戦、味方複数 | キーボードで「戦う」、演出時刻を進める | 味方全体がAIで行動し、ログとHP/MP変化が行動順に見える。個別命令は不要 | no | - | missing | 入力→推論→解決→演出の期待値未対応。#203 |
| KQ-P18 | オート戦闘 | 通常戦と固定clock | オートをON、時刻を進め、OFF | 演出中の重複行動を防ぎ、待機後に次の行動を開始する。OFF後は自動進行しない | no | - | missing | 時刻依存を固定したオート操作未対応。#203 |
| KQ-P19 | 勝利/経験値/AI | 経験値の閾値直前の味方、通常敵 | 勝利まで戦い、field復帰してreload | 勝利を1回確定し、撃破経験値と必要なLv上昇、AI学習が保存される。終了操作を繰返しても二重加算しない | yes | - | missing | 報酬確定・復帰・reload未対応。#203 |
| KQ-P20 | 敗北/教会復活 | 登録済み教会と別位置で通常戦 | 全滅し終了、再起動 | fieldへ戻り、戦闘位置ではなく登録教会のmap_id/座標で復活する。保存位置も教会 | yes | - | missing | 敗北→移動→reload未対応。#203 |
| KQ-P21 | 逃走 | 逃走判定を固定した戦闘fixture | 逃走成功と失敗をそれぞれ操作 | 成功なら終了後fieldへ戻る。失敗ならbattleを継続し、勝利経験値を与えない | no | - | missing | 乱数固定の逃走結果シナリオ未対応。#203 |
| KQ-P22 | 状態異常/解除 | 解除可能/解除不能な状態と固定RNGのfixture | 効果を受け、解除行動を使う | 状態が行動/対象へ正しく影響し、解除成功で対象状態だけ消える。失敗/解除不能は残る | no | - | missing | 戦闘入力から状態変化を観測する経路未対応。#203 |
| KQ-P23 | 属性/耐性/防御 | weak/normal/strong/immune/absorb、物理/魔法のfixture | 同条件の攻撃、防御、固定会心判定 | 耐性に応じたHP変化、無効は0、吸収は上限まで回復。防御倍率は物理だけ、会心は相手防御力を無視 | no | - | missing | 複数防御規則をruntime戦闘経路で確認するケース未対応。#203 |
| KQ-P24 | 道具/スキル使用イベント | 必要道具・スキルとradius付きイベント | 範囲外/誤った指定/正しい指定で使用しreload | 条件に合う場合だけイベントが発動し、gain_itemなら所持数が増えて復元される | yes | - | missing | 使用入力→イベント→inventory保存未対応。#202 |
| KQ-P25 | 牧場/編成反映 | 現在編成[A,B]、所有個体C | 牧場でAを外しCを追加、閉じてreload | fieldとJSONの編成が[B,C]になる。Aは所有したまま、戦闘参加は最大4枠 | yes | - | missing | 子プロセス相当終了→再読込未対応。#204 |
| KQ-P26 | パーティプリセット | 所有個体と欠損IDを含むプリセット | 新規保存/更新/読込、再起動 | 編成と順序を復元し欠損IDを空き扱いにする。所有数・保存枠数に固定上限を設けない | yes | - | missing | 管理操作→ファイル→reload未対応。#204 |
| KQ-P27 | 個体進行/装備 | Lv/＋選択/装備を持つ個体 | 保存し再起動 | 名前・Lv・経験値・＋選択・装備が同じで、種族定義から能力/スキルを再構築する。装備許可は装備側の対象種族に従う | yes | - | missing | 所有個体の操作と再構築を跨ぐケース未対応。#204 |
| KQ-P28 | AI傾向閲覧/リセット | 同種族で攻撃/回復履歴が違う2個体 | 牧場で切替、F5、片方だけリセット、reload | 5項目の傾向が履歴に追従し、未学習/不足を区別する。リセットした個体だけ未学習に戻り、Lv等は維持 | yes | - | missing | 管理画面テストはあるがゲーム/牧場/reloadのE2E未対応。#204 |
| KQ-P29 | セーブ全体復元 | 位置/教会/編成/アイテム/進行フラグ/個体AI/プリセットが変化した状態 | 保存、runtimeとStoreを作り直し同名セーブをロード | state.json、items/items.json、monsters/*/monster.json・ai.json、parties/*.jsonの指定値が一致し、補間中の小数座標を保存しない | yes | - | missing | 全永続化対象の独立再生成ケース未対応。#202/#204 |
| KQ-P30 | 模擬戦施設 | 自分と対戦登録個体、AI/経験値の事前snapshot | 受付を開いて相手を選び、閉じて勝利/敗北、reload | requestを1回消費し模擬戦を開始する。双方のAIと経験値/通常報酬は変化せず、敗北でも教会へ移動しない | yes | - | missing | 受付→request→戦闘→終了→reload未対応。#203、依存の明示化は#214 |

## Developer / 制作操作

編集・ビルド用fixtureは隔離したプロジェクト複製を使い、本物のdata/assetsを書き換えない。

| ID | 機能/画面 | Given | When | Then | Persistence | E2E | Status | 理由/次の担当 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| KQ-D01 | ブロック編集→Preview | 既知ブロックを使う隔離マップ | 通行可否/見た目を編集して保存、Player Previewで移動 | 保存した正規JSON/画像をPlayerが読み、見た目と衝突が編集値どおりになる | yes | - | missing | Editor→正規保存→Player起動未対応。#199追加ケース |
| KQ-D02 | マップ作成/移動点 | 既存マップと新規ID | 一覧で選択、新規作成、地形と重なるstep/interact移動点を配置・保存、Preview | 新マップJSONが再読込でき、地形を維持してP08/P09の動作になる。ゲームでは編集用マーカーを描画しない | yes | - | missing | マップUIからPlayer実行まで未対応。#199追加ケース |
| KQ-D03 | 固定モブ編集 | 隔離マップと有効種族 | モブの初期位置/AI/周期/会話/消滅条件を編集・保存、Preview | 初期位置から出現し、設定した動作と会話/再出現条件をPlayerが使う | yes | - | missing | 固定モブ編集→Player読込未対応。#199追加ケース |
| KQ-D04 | モンスター/ドット編集 | 新規種族IDと64×64画像 | 種族を作成、戦闘/4方向画像とLvスキルを編集して保存・再読込 | 正規種族フォルダが揃い、各画像とスキルを読める。共通ドット編集でズーム/移動/undoが対象画像に適用される | yes | - | missing | Editor間の共通操作とruntime読込未対応。#199追加ケース |
| KQ-D05 | 検証失敗の導線 | 不正な参照先を含む隔離data | Project Validation、Preview/Buildを要求 | 不正箇所を報告し、検証失敗のまま成果物完成と表示しない | no | - | missing | Developer境界の失敗経路未対応。#199追加ケース |
| KQ-D06 | Player Build/配布 | 検証済みの編集済みdata/assets、利用可能なビルド環境 | DeveloperからPlayer Build、配布物をsmoke起動 | 正規data/assetsが配布物に入り、Player入口が起動し隔離UserDataを使用する。Developer機能を含めない | yes | - | missing | 重いdistribution E2E。sourceとは分離し、#50/#205と連携 |
| KQ-D07 | 個体取得/再走査 | imports/acquireに未所有ID、既存ID、不正フォルダ | 開発用取得操作で2回再走査、reload | 有効な未所有IDだけを1回コピーし、重複を上書きせず、不正をスキップする。取得したmonster/AIを復元する | yes | - | missing | 管理操作→コピー→再走査→reload未対応。#204 |

## 意図的な除外

| ID | 機能/画面 | Given | When | Then | Persistence | E2E | Status | 理由/次の担当 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| KQ-X01 | 純粋な画面装飾 | 操作/状態/可読性の仕様が変わらない | 枠色や装飾だけを調整 | 操作や保存結果に変化がない | no | - | intentionally-not-e2e | ピクセル全比較は要求しない。目視/描画テストで確認。入力範囲や可読性を変える場合は除外を適用しない |

## 既存の根拠と不足

ここは索引であり、期待値の詳細を複製しない。更新時は該当CODEMAP行から実装とテストへ戻る。

- 起動/保存/移動/NPC/暗号/個体/編成: `tests/test_core.py`、`tests/test_app_smoke.py`、`docs/FORMATS.md`。本番入口からreloadまでの共通E2Eは未整備。
- 野生移動/出現/遭遇: `tests/test_field_ai_movement.py`、`tests/test_wild_spawn_runtime.py`、`tests/test_wild_encounter_flow.py`。個別のruntime統合検証を持つが、入力列と永続化を含む共通E2Eではない。
- 戦闘/勝敗/報酬: `tests/test_battle_flow_service.py`、`tests/test_battle_rewards.py`、`tests/test_enemy_flee.py`、`tests/test_battle_resistance.py`、`tests/test_battle_status_cure.py`。
- アイテム使用イベント: `tests/test_field_use_events.py`。使用条件・保存を個別に検証済み。
- AI表示: `tests/test_ai_tendency_ui.py`。実管理画面ループの切替/更新/リセットは検証済みだが、ゲーム→牧場→再起動のシナリオは未対応。
- 模擬戦: `tests/test_simulation_facility.py`、`tests/test_simulation_manager.py`。受付と戦闘の既存統合テストをE2Eと混同しない。
- Developer/配布: `tests/test_developer_workflow.py`、`tests/test_distribution_paths.py`、`tests/test_distribution_savedata.py`。ビルドstubやsource smokeは完成配布物のE2Eを代替しない。

## 更新と実行の運用

ユーザー観測可能な機能の追加/変更では、対応行のGiven/When/Thenを更新し、既存IDは改名しない。新しい操作シナリオは新IDを付ける。Persistence=yesは保存JSONと再生成後の復元値をThenに含める。fixtureの具体的なseed/時刻/期待数値は対応するE2Eテストで固定し、ランダムに成功するまで再試行しない。

E2Eは本番と同じcomposition root/command/data/save経路を使う。headless SDLと入力adapterは利用してよい。単一関数のunit、複数内部部品のintegration、起動可否のsmoke、完成配布物のdistributionはそれぞれ別の証拠として報告する。画面画像やログだけで状態の成功を決めない。

#201でharness、#202～#204でsourceシナリオ、#205でCI/統一品質コマンド/完了条件への組込みを行う。Developerの重い配布物検証はsource E2Eから分離する。現段階のチェックツール成功はE2Eが実装・成功した意味ではない。
