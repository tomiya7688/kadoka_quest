# 0.ver.mdについて

0.は編集しないこと
バージョンアップ時にはここを更新すること

書き方
```markdown
    # 1. サンプル
        helloworldを出力する機能を追加
        変更したファイル
            start.py
            開発予定.md
            仕様書.md
        追加したファイル
            hello.py

```

# 96. GDScriptの単体魔法を実MP消費・HP適用へ接続

リモート取得と差分要約でincomingなしを確認しました（開始時ahead81/behind0）。GitHub CLIでP0なし、公開P1移行Issueのローカル実装済みを確認し、移行表の未起票候補から単体魔法の実行準備とSession適用を進めました。push・PR・Issue作成や状態変更は行っていません。既存game.py・開発予定・未追跡資料・実セーブは作業対象へ混在させていません。

combatant_builderは正規種族と許可装備から属性耐性を再構築します。elemental_resistanceはweak→normal→strong→immune→absorbの段階補正・両端・不明名と省略をPython正本に合わせます。＋選択は耐性を変更しません。magic_skill_contextは既存の開始情報検証だけを共用し、習得・許可装備・定義ID索引・耐性を独立保持します。資源snapshotの6キーと保存JSON/schemaは変更していません。

magic_skill_actionは厳密なticket/target/skill_id/varianceの4キーを受け、最新予約・習得・敵対象・現在MP/HPを検証して単一claim→実MP消費→HP変化→finishを同期実行します。属性吸収は新しいState/Sessionの数値回復へ委譲し、最大HPで止まります。無効・満タン吸収でもMPを消費します。死亡した対象は魔法で回復できず、低水準回復は逃走や教会復活の方針を変更しません。

基本ぼうぎょ・防御力・会心・装備の物理用威力倍率は魔法を軽減・増幅しません。選択した既知威力倍率は有限性の検証だけを行い、正本Pythonどおり使用しません。固定追加値は通常ダメージだけに適用します。未習得・不正・MP不足・未対応効果・死亡対象はclaim前に予約と資源を保持します。予約後の死亡・逃走・敵なしは資源を消費せず取り消します。二重実行・取得済み/不一致ticketは拒否します。自傷metal_burst・吸MP・状態異常・全体/ランダム攻撃等は効果を省略せず未対応として拒否します。

追加: magic_skill_action.gd・magic_skill_context.gd・elemental_resistance.gdとUID、魔法行動専用テスト、8体Session性能プローブとUID・性能CLI、魔法行動契約。更新: State/Session・Builder/application・共有行動プローブ、CODEMAP・形式仕様・GDScript/tools案内・移行表・関連予測/物理契約。本作業で読んだ共有処理・比較用関数・既存性能検査の不明瞭なコメントをJSON-like形式で具体化しました。コメント修正の前後でGDScript6ファイルの非コメント実行行が一致し、Pythonのコメントのみ4ファイルはHEADとのASTが一致します。説明規約や論文調査は引き続きGit除外し、全文書監査を完了したとは扱いません。

検証環境は実Godot 4.7.2とPython 3.14.7です。専用data/assets/個体/AI/items/partyコピーを使用し、実Python_take_actionの選択だけを固定してMP支払いと魔法のHP変化を比較しました。

- 魔法行動13テスト・145サブテストが通過しました。耐性・揺らぎ・固定加算・最新残HP・無効/吸収、正規7種族のレベルと装備、49段階補正、有限MOD・不正/非有限値、MP不足再選択、取消・二重実行、コピー・8体ラウンド間保持・上限回復・依存境界を確認しました。
- 既存の通常攻撃・物理行動・戦闘個体の関連41テスト・1309サブテストが通過しました。
- ヘッドレス全1035テスト・12306サブテストが通過しました（472.29秒）。Python 3.10構文ASTは追跡238ファイルで通過しました。実Python 3.10で全実行した証拠ではありません。
- 新しい魔法行動の標準性能検査は20000回・7サンプル・2000warmup、中央値1431.82usで3000us以内でした。8体の累積実MPと通常/無効/吸収/強耐性の実HP変化も確認しました。I/O・再構築・描画・AI・保存の性能ではありません。
- 物理行動の簡易性能は同じ2000回・3サンプル・200warmupで、変更前1182.42us→変更後1365.02us、いずれも3000us以内でした。並行検証による測定揺らぎは区別します。
- 既存Python runtime性能検査は標準条件で13項目すべて通過しました。実描画・exportの性能を測定した結果ではありません。
- 最新UPD上流main ae4636155b5e773d787cfccd1572808829601524を再導入し、Error0・既存Warning17/Attention100でした。コメント検査は324ファイル・2699宣言・0エラー、阻害lint・pip check・責務境界・Godot editor import・生成マップ/対象application図の鮮度・diff checkが通過しました。
- E2Eカタログは構造と参照を確認しました（covered12/missing25/intentionally-not-e2e1）。カタログだけを実E2E成功の証拠にはしません。

単体魔法をSessionへ接続した範囲だけの実装です。AI推論・学習、戦闘画面・演出、野生遭遇、全スキル、勝敗・報酬・教会復活、実GUI・配布export・リモートCIは未検証または未接続です。次の候補は自傷付きmetal_burstの数値契約で、実適用は別単位へ分けます。

# 95. GDScriptのMP付き単体魔法・属性耐性の純粋予測

リモート取得と差分要約でincomingなしを確認した（開始時ahead80/behind0）。GitHub CLIでP0なし、公開P1移行Issueのローカル実装済みを確認したため、移行表の未起票候補から単体魔法の予測だけを進めた。実際のMP支払い・SessionへのHP適用・戦闘画面はこの単位に含めない。push・PR・Issue作成と状態変更は行わない。既存のgame.py・開発予定・未追跡資料と実セーブを作業対象へ混在させない。

magic_skill_contractは指定IDの一意性・kind=magic・正のMP消費量・有限威力・属性・対応キーを検証し、入力を変更せず残MPを予測する。magic_numbersは魔力×威力×耐性をPythonと同じ順に整数化し、通常ダメージ・無効・吸収回復を分ける。通常ダメージの最終化は既存attack_numbersを共用する。防御力・会心・物理攻撃倍率・装備のスキル威力倍率は魔法へ適用しない。無効と吸収では装備固定追加値も使わない。属性省略はphysical、欠落耐性はnormal、未知耐性文字列は等倍とし、未知値はresistance_known=falseで分かるようにする。

正規weakenと同形式のMODに対応する。自傷付きmetal_burst、吸MPのpossess、ランダムのdice_magic、状態異常・全体攻撃・回避・反撃等は未対応であり、キーの値がfalse・0・空でも拒否する。現在HP/最大HP/MPは正規整数値と整合性を確認し、非有限値と整数精度上限超過を拒否する。魔法予測はファイル・Session・乱数源・AI・UIに依存せず、保存JSON/schema・正規data/assetsを変更しない。

追加: magic_skill_contract.gd・magic_numbers.gd・run_magic_skill_probe.gdと各UID、専用Pythonテスト、開発専用性能CLI、魔法予測契約。更新: CODEMAP、GDScript README、tools案内、移行表と本履歴。今回読んだ共有数値関数・Python比較元・開発検査ツールの曖昧な説明は、入力・結果・条件が分かるコメントへ具体化した。既存Python7ファイルのASTとGDScript2ファイルのコメントを除く実行行は変更前のGit版と一致する。ローカル説明規約は引き続きGit除外し、既存全文書の監査完了とは扱わない。

検証（2026-10-08、Python 3.14.7 / 実Godot 4.7.2）: 新規7件・1625サブテストが成功した。正規魔法と属性省略MODの1512組、有限MOD32組を実Python BattleEngine._attack(allow_counter=False)と比較した。耐性5種・未知/欠落・揺らぎ・装備追加・負威力・最低1・HP下限/回復上限・物理属性魔法の防御無視・MP不足/ちょうど・コピー独立性・入力JSONのbyte不変を確認した。会心乱数と学習の非呼出しも確認した。実魔法計算はmockへ置換せず、比較専用の揺らぎだけを固定する。反撃・AI選択・実MP支払いの検証とは扱わない。不正型・未知キー・重複・未対応定義・native NaN/Infと演算の精度超過を回帰へ残した。

関連60件・3564サブテストが成功した（32.41秒）。実Godotを指定したheadless全1022件・12161サブテストが成功した（425.39秒）。標準Godot editor import、宣言コメント318ファイル・2660宣言・0エラー、project rules、生成repo map/application図の鮮度、追跡Python236ファイルのblocking lintとPython 3.10構文AST、pip check、相対リンク検査、git diff --checkが成功した。図の初回検査は既定の全体図を誤って指定して古い図を報告したため、追跡されたapplication図の正しいsource/outputを指定して再確認した。全体図を書き換えたとは扱わない。

性能: 新規魔法予測は46.34us/回（標準20000回・7サンプル・2000回の事前実行、上限3000us）。既存物理予測は同条件の短縮計測で43.73→45.53us/回（2000回・3サンプル・200回の事前実行）となり、両方とも上限以内だった。標準Python性能検査13項目も変更前後とも成功した。環境変動を含む測定差は性能改善や完全な無退行の証明とは扱わない。最新UPD checkerのmain ae4636155b5e773d787cfccd1572808829601524を再導入し、Python対象はErrorなし・Warning17/Attention100で変更前と同じだった。UPDによるGDScript静的責務検査の成功とは区別する。

差分レビュー: R01/R02は対象が分かるAPIと検証順、R03/R08/R09は定義/MP検証・HP計算・プローブ・計測条件の単一責務を確認した。R04/R10は構造化宣言と意味のある処理目的のコメント、R05は数値/拒否/不変の回帰、R06/R11/R12は定義選択のO(一覧件数)と固定フィールド数の予測・数値共用・性能上限を確認した。R07は契約153行・数値135行・プローブ115行・テスト362行・CLI120行の用途別分離、R13は専用一時領域と限定stage、R14はMOD属性/ID対応と未対応効果の拒否、R15はローカル品質ゲートを確認した。R16は画面変更なしのため、実headlessの数値検証とE2Eカタログの構造確認を分けた。R17〜R20は新規仕様の背景・目的・手段・具体的操作・成功/失敗・保証しない範囲と日本語を確認した。既存全コードの適合監査ではない。

E2Eカタログは構造と参照だけ成功した（covered12/missing25/intentionally-not-e2e1）。実GUI、戦闘Scene、魔法の実適用、特殊効果・全スキル、AI、勝敗/報酬/復活、配布export、リモートCI、別Python版での実行は未検証。次は対応単体魔法の実行準備とSessionへの行動適用を候補とする。今回の23ファイルだけをローカルコミットし、公開操作は行わない。

# 94. ローカル説明規約の導入と既存コメントの具体化

Kadoka Questの説明を書くCodex向けに、単独で理解できる文への書き換えと根拠確認を扱う論文を調査し、ローカル専用の必須規約と調査メモを作成した。規約は設計・仕様・利用者向け案内・コメント・作業報告を対象とし、作業中に発見した曖昧な説明の即時修正を指示する。ローカル規約の本文と論文メモは公開管理しない。

実チェックアウトの.gitignoreは、ローカルAGENTS.override.mdとdocs/ローカルAI規約/を除外する。ローカルAGENTS.override.mdは、既存の追跡AGENTS.mdと追加の説明規約を読むようCodexへ指示する。作業用ワークスペースにも実チェックアウトの指示を参照するローカル転送指示を配置した。別のcloneやクラウドへローカル規約をGit経由で配布したとは扱わない。

今回読んだリモート差分要約ツールとGDScript戦闘準備の曖昧なコメントを、対象・入力・結果・副作用が分かる文へ修正した。戦闘資源snapshotとMP支払い可否の説明も具体化した。コードの実行内容・保存形式・ゲーム機能は変更しない。既存のユーザー変更と実セーブは変更せず、既存全文書の一括監査を完了したとは扱わない。

検証（2026-10-07）: 関連54件・1065サブテストと、実Godotを指定したheadless全1015件・10536サブテストが成功した（全体454.06秒）。変更PythonのASTとGDScript5ファイルのコメントを除いた実行行は、変更前のGit版と一致した。宣言コメント313ファイル・2629宣言・0エラー、project rules、生成repo mapとapplication図の鮮度、追跡Python234ファイルのPython 3.10構文とblocking lint、pip check、相対リンク3件、git diff --checkが成功した。E2Eカタログは構造・参照のみ確認した（covered12/missing25/intentionally-not-e2e1）。

Gitの除外確認では、実チェックアウトのローカル指示・必須規約・論文調査の3ファイルと、作業用ワークスペースの転送指示が除外され、Gitで追跡されていないことを確認した。既存AGENTS.mdは5779bytesのまま保持した。新しいCodexセッションでの自動読み込みと継続的なモデル遵守、人間の理解度測定、既存全文書の監査、GUI/E2E・別Python版の実行・配布・リモートCIは未検証。ゲームの責務境界と実行経路は変更していないため、設計検査ツールの更新や新しい性能計測は行わない。今回のGit除外設定・履歴・コメント修正だけをローカルコミットし、push・PR・Issueの公開操作は行わない。

# 93. GDScriptのMP付き単体物理スキル行動・Sessionへの実適用

リモート取得・要約でincomingなしを確認した。GitHub CLIでP0なし、P1移行候補#218と他移行Issueのローカル実装済みを再確認し、移行表の未起票候補から今回分を進めた。push/PR/Issue作成・状態変更は行わない。既存game.py/開発予定、未追跡の資料・reports、正規data/assetsと利用者セーブは保持する。

physical_skill_contextが開始時のfresh snapshot・習得ID・種族許可装備・正規定義の独立コピーを準備する。定義は重複を維持してID索引化し、毎行動の全カタログ走査を避ける。physical_skill_actionは別APIで最新offered・対象生存・正規定義・選択ID装備効果・現在MPを検証し、単一claim→実MP支払い→敵HP適用→finishを同期実行する。通常攻撃へIDを偽装せず、未知効果はfalse/空でも拒否する。不足・未習得・不正・重複は資源とofferedを保持し、死亡・逃走・敵なしは無消費で取消する。基本guardとラウンド間のHP/MP保持は既存Sessionへ委譲する。

combatant_builderは正規レベル/＋選択/装備再構築から独立skill_idsを加えるが、資源snapshotの6キーと保存JSON/schemaは変更しない。applicationはread-only準備と各Actionの開始・ルーティングだけを担当する。engineの計算は既存物理予測と共用し、I/O・乱数源・AI・UIを足さない。追加: engine/physical_skill_context.gd・physical_skill_action.gdとUID、run_physical_action_performance.gdとUID、専用テスト/性能CLI、物理行動契約。更新: Builder/application/共有headlessプローブと、CODEMAP/FORMATS/GDScript README/tools案内/純粋予測契約/移行表。

関連検証（実Godot 4.7.2 / Python 3.14.7）: 78件・2617サブテスト成功（74.70秒）。正規3スキル144組の実MP消費・HP/会心を実Python_take_actionと比較した。選択だけを固定し、MP支払い・物理実処理はmockへ置き換えない。学習/保存の非呼出しと個体/AI不変を確認した。有限MOD8組、レベル1/50/100と未装備/許可/不許可/不明装備、正規＋習得、最新MP不足・ちょうど支払い・同ticket再選択、重複/不正/native NaN/Inf、最新死亡/逃走/敵なし、8体同速/両陣営同ID/ラウンド間保持、開始/返却/入力コピー、専用data/assets/個体/AI/items/partyのbyte不変を検証した。初回の2サブテスト失敗は、既存契約が許容する乱数の数値文字列をテストが不正と扱っていたため修正し、互換性を正本との正例比較へ残した。

性能: 新しい実Godot物理行動は1306.28us/段階（標準20000回/7samples/2000warmup、8体、上限3000us）。実MP総消費426000とHP減少も一致した。既存通常攻撃は変更前2134.39→変更後1342.42us（2000回/3samples/200warmup、同じ上限以内）。環境変動を含む測定差を性能改善の証明とは扱わない。標準editor import成功、専用性能検査をPlayerからimportしない。

差分レビュー: R01/R02は目的が分かるAPIと検証→適用の直線的順序、R03/R08/R09は準備検証/行動所有/application調停/計測の単一責務、R04/R10は構造化宣言と目的・理由の内部コメントを確認した。R05は不正/境界/不足/重複/取消/コピーの回帰、R06/R11/R12は開始時O(定義数)の索引化と最大4体の検索・数値共用・性能閾値、R07はcontext173行/action173行/性能プローブ104行/専用テスト425行/CLI65行の用途別分離を確認した。R13は実セーブ非参照と限定stage、R14は正規ID/＋/MOD対応と未対応の拒否、R15はローカル品質ゲートの成功を確認した。R16はScene変更なしのため新規画面E2Eを対象外とし、実headless行動統合とカタログ構造の証拠を分ける。R17〜R20は新規仕様の背景・目的・手段・操作・期待結果・失敗対応と日本語を確認した。既存全コードの適合監査ではない。

最終検証（2026-10-07）: 実Godotを指定したheadless全1015件・10536サブテストが成功した（462.42秒）。project rules、宣言コメント313ファイル/2629宣言/0エラー、生成repo map/application diagram鮮度、追跡Python234ファイルのblocking lint、Python 3.10構文AST、pip check、相対リンク50件、git diff --checkが成功した。最新UPD checkerのmain ae4636155b5e773d787cfccd1572808829601524を再導入し、対象PythonのErrorなし・Warning17/Attention100は変更前と同じ。これはGDScript静的責務検査ではなく、実Godotの構文・参照・行動契約検証と区別する。標準Python性能検査13項目は変更前後とも成功した。E2Eカタログは構造・参照のみ成功（covered12/missing25/intentionally-not-e2e1）。新規UI/戦闘SceneのE2E成功とは扱わない。

戦闘Scene、魔法/耐性/状態異常/特殊防御/全スキル、AI、勝敗/報酬/復活、実GUI/IME、配布export、リモートCI、別Python版での実行はUnverified。次はMP付き単体魔法・属性耐性の純粋予測を候補とする。今回分だけローカルコミットし公開操作は行わない。

# 92. GDScriptのMP付き単体物理スキル定義・純粋予測

リモートを取得・要約し、incomingなしを確認した。GitHub CLIでP0/P1と移行候補を確認し、公開P1移行Issueはすべてローカル実装済みだったため、移行表の未起票候補を最小の前提単位へ分けた。今回は定義と数値予測だけ。MP付きスキルを通常attackへ偽装せず、実MP支払い・単一行動権・SessionへのHP適用・AI/Sceneは後続へ残す。公開Issue作成・状態変更やpushは行わない。

engine/physical_skill_contract.gdが正規skillsの指定ID一意性・metadata・kind・正のMP整数・有限威力/会心倍率を検証する。未知効果はfalse/空でも拒否する。quote_damageは未知要求/不正MP/不足を拒否し、元定義・入力資源を変更せずHP/MPの予測を返す。attack_numbers.gdからphysical_damageを共用し、従来のnormal_attackのattack限定とscopeを維持した。新規宣言は構造化コメント、各処理には目的・理由の通常コメントを付けた。

追加: physical_skill_contract.gdとUID、run_physical_skill_probe.gdとUID、tests/test_gdscript_physical_skill.py、tools/performance-check/script/check_gdscript_physical_skill.py、docs/GDScript物理スキル予測契約.md。更新: attack_numbers.gd、CODEMAP、GDScript README、tools案内、移行表。JSON/保存形式は変更せず、実セーブ・既存game.py/開発予定・data/assetsは変更しない。

検証: 関連51件・2466サブテスト成功（41.32秒、実Godot 4.7.2 / Python 3.14.7）。正規3スキル648組と有限MOD121組を実Python BattleEngine._attack(allow_counter=False)と比較した。数値・会心境界・guard・装備投影・最低1/HP上限、MP予測・コピー独立性・未知効果・不正型・native NaN/Inf・精度超過を確認した。AI選択・学習・実MP支払いを検証したとは扱わない。新規予測は54.77us/回（20000回/7samples/2000warmup、上限3000us）。通常攻撃は変更前のGit版を専用コピーへ復元し同条件で1219.64→1244.96us（2000回/3samples/200warmup、8体中1段階、いずれも上限3000us以内）。Godotの標準editor importも成功した。

差分レビュー: R01/R02は目的の分かるAPI名と直線的な呼出順、R03/R08/R09は純粋検証・数値共用・プローブ・計測条件所有の分離、R04/R10は構造化宣言と処理目的の通常コメントを確認した。R05は不正型/境界/未対応効果/コピーを回帰テストへ残し、R06/R11/R12はprepareのO(スキル件数)と固定フィールド数のquote・計算共用・計測結果を確認した。R07は単一用途の新規ファイル（契約153行・プローブ114行・テスト347行・検査117行）、R13は専用一時領域と原本/実セーブ非書込、R14はIDを固定しないMOD対応と未対応範囲の明示を確認した。R15はローカルの必須品質検査、R16はScene変更がないため新規画面E2Eを対象外とし、既存カタログの構造だけを確認する。R17〜R20は新規仕様の背景・目的・手段・開発者の具体的操作・期待結果・失敗対応と日本語を確認した。既存全コードの適合監査ではない。

最終検証: headless全1005件・10319サブテスト成功（498.88秒）。project rules、宣言コメント308ファイル・2598宣言、生成repo map/application diagram鮮度、追跡Python232ファイルのblocking lint、Python 3.10構文AST、pip check、変更文書の相対リンク、git diff --checkが成功した。最新UPD checkerのmain ae4636155b5e773d787cfccd1572808829601524を再導入し、対象PythonはErrorなし・Warning17/Attention100で変更前と同じ。GDScriptの静的責務検査まで成功したとは扱わず、実Godotによる構文・参照・契約検証と分ける。標準Python runtime性能検査は変更前後とも全項目成功した。E2Eカタログは構造・参照のみ成功（covered12/missing25/intentionally-not-e2e1）。

実GUI、IME、export、リモートCI、別Python版での実行、実際の物理スキル行動適用はUnverified。今回の13ファイルだけをローカルコミットし、ユーザーの既存変更を混在させない。push/PR/Issue作成・状態変更は行わない。

# 91. レビュー基準と共有コーディング規約

ユーザー指定の20禁止事項をR01〜R20として、rootのレビュー基準.mdとコーディング規約.mdへ記載した。レビュー基準はローカル専用として.gitignoreのroot指定で除外し、共有コーディング規約は追跡する。命名、状態と操作のクラス所有、単一責務・単一処理単位、宣言と処理ごとのコメント、バグ予防、計算量・実行性能、冗長性、安全操作、拡張性、CI/E2E、人間が読める設計・仕様、主語別の文体、背景・目的・手段・実行方法、日本語の読みやすさを必須基準にした。

AGENTSから共有規約を参照し、ローカルレビュー基準は存在するときだけ読む。clone/CIでignoredファイルが欠けても共有基準は読める。既存CODING_RULES/COMMENT_RULESにも参照を追加し、意味のある内部処理ごとの通常コメントを必須とした。指定upstreamの日本語正本Draft v0.9/main 5691767a8708407a568a75a242543a4add825253をGitHub CLIで再確認した。上流は内部通常コメントを許容するため、全コメントをJSON形式にする規則へ改変していない。

規約の作成だけで既存全コードが適合したとは扱わない。必要な検証が失敗した場合は修正要求、未検証なら保留とし、静的検査・単体/統合/headless/smoke・E2Eカタログ・実GUI・export・リモートCIの証拠を区別する。文書とignore設定だけの変更で、runtime/JSON/assets/実セーブや既存game.py/開発予定を変更しない。

検証（2026-10-07）: 関連32件・11サブテスト成功。実セーブと分離したheadless全998件・9550サブテスト成功（416.44秒）。両文書のR01〜R20の順序・重複なし、相対リンク、余分な行末空白、レビュー基準だけのignore、AGENTSの6000byte上限（5779byte）を確認した。project rules、宣言コメント304ファイル・2570宣言、生成repo map/application diagramの鮮度、Python 3.10構文互換性のAST検査230ファイル、追跡対象Python230ファイルのblocking lint、git diff --checkが成功した。最初の全フォルダlintはignoredの.venv/venv_3135内の第三者コードまで走査して71件を報告したため、Git管理されたプロジェクトコードを対象に再確認した。第三者ライブラリや検査条件は変更していない。

E2Eカタログは構造・参照だけを確認した（covered 12 / missing 25 / intentionally-not-e2e 1）。実GUI、配布export、リモートCI、別Python版での実行、既存全コードのR01〜R20適合監査はUnverified。runtime/責務境界の変更がないため、新しいUPD checker導入やhot path性能比較は今回の範囲に含めない。今回分だけローカルコミットし、push/PR/Issue変更は行わない。

# 90. GDScript基本ぼうぎょ・Session所有guard・ラウンド終端解除

P1 #251を実装した。pure basic_defend_contractが正規skillsの一意defend/kind:defend・有限MP0・既定倍率0.5だけを検証する。未対応counter/protect/status等はfalse/空でも拒否し、MOD原本を修復しない。basic_defend_actionは厳密な2キー要求→offered読み取り検証→最新生死による単一claim→本人guardだけ更新→finishを同期実行する。重複/古い/既claimed/不正要求は資源/効果/cursorを消費せず、死亡/逃走/敵なし取消は効果を適用しない。

Sessionは資源6キーsnapshotと別にside+id別guardを所有し、effects()を独立plainコピーで公開する。通常攻撃は対象の現在値だけを使い、物理会心にも軽減を掛ける。正常round_finished/敵なしstoppedで死亡/逃走者を含む全guardを1へ戻し、HP/MP/fledは保持する。不正/早すぎるbeginや未claim finishで解除しない。applicationはread-only準備と攻撃/防御の設定・行動ルーティングだけを調停し、全成功後だけ所有者を切り替える。

追加: gdscript/engine/basic_defend_contract.gd・basic_defend_action.gd、gdscript/tests/run_basic_defend_performance.gdと各UID、tests/test_gdscript_basic_defend.py、tools/performance-check/script/check_gdscript_basic_defend.py、docs/GDScript基本防御行動契約.md。更新: Session/通常攻撃/application/共有headlessプローブ、正常MODの既存テストfixtureに正規defendを追加、CODEMAP/FORMATS/README/契約/移行表/tools案内/コメント保守案内。本実装に全コードJSON-like宣言コメントを適用する。

検証（2026-10-07）: 最初の関連検証は未初期化ケースのプローブ側null参照1件を修正した。新規13件を含む最終関連61件・1927サブテスト成功（48.84秒、実Godot）。実Python_take_actionの基本防御、_attack(allow_counter=False)、run_roundの終端解除を限定比較する。288組の通常/会心境界・装備・揺らぎ・最低1/HP上限と16組の8体/同速/両陣営同ID/最大3round/死亡を比較。選択と終了保存はmock境界を明示し、AI推論・学習や勝敗の移植証拠とはしない。逃走/敵なし/skip末尾・不正/非有限/精度超過/未知キー/未対応定義・コピー独立性・private個体/AI/party/items/原本byte不変も確認する。

230追跡Pythonの3.10構文契約/致命的lint、新規2ファイルstyle、宣言コメント304ファイル・2570宣言漏れ0、project rules、生成REPO_MAP/application図freshness、diff成功。E2Eカタログ12 covered/25 missing/1除外は構造・参照だけ。最新UPD ae4636155b5e773d787cfccd1572808829601524を再取得しPython対象エラー0・警告17・注意100。GDScript全体をUPDで検査した結果ではなく、警告抑制/private forkは行わない。

全体998件・9550サブテスト成功（472.16秒、Python3.14.7 / pygame-ce2.5.8 / 実Godot4.7.2、skipなし）。全体開始後のテストだけの末尾補強（防御済み本人の死亡/逃走を実Python run_roundと比較、pendingなしの敵なし停止）も、新規13件・309サブテストの再実行で成功した。最終版の防御・コメント回帰28件・315サブテストも成功（76.02秒、skipなし）。runtime変更後の全体検証を行い、テスト補強でruntimeは変更していない。

標準性能（20000回/7samples/2000warmup）: 新規8体中1防御/攻撃と8段階ごとのguard解除は1728.00µs<=3000µs、実HP減少minimum_hp=999929000と全guard1を確認。初期構築/定義I/Oは計測外、HPは保持する。既存通常攻撃1350.11µs<=3000µs、Session段階838.30µs<=2000µs、8体資源429.17µs<=1000µs、plan+1check575.49µs<=2000µs、24モブ800.86µs<=2000µs、5枚会話8.41µs<=100µsも成功。Python13項目成功（24枠生成953.43µs、24体移動386.77µs）。描画/FPS/AI/全8行動まとめ/I/O/export性能ではない。cold8操作/1sample/0warmupの途中smokeは3240.12µsで時間上限を超えたが、実HP4減少とguard解除は成立した。閾値を変更せず標準中央値で成功を確認した。

終了前に既存リモート取得・圧縮ツールを実行しahead=75/behind=0、取り込む変更なし。#251はP1/gdscript/OPENを読み取り確認した。Issue完了や公開メッセージ、pushは行わない。

正規data/assets・Python runtime・実セーブ/個体AI・既存game.py/開発予定/未追跡メモ等は変更しない。全スキル/特殊防御/耐性/状態異常/AI/野生接触/戦闘Scene/勝敗・報酬保存/実敗北→教会復活は後続。手動GUI/export/リモートCIはUnverified。新たな全員attack/defend runtimeや手動個体コマンドUIは追加せず、ローカルコミットだけでpush/PR/Issue完了操作は行わない。次候補はMP消費を伴う単体物理スキルの限定行動契約（未起票のローカル案）。

# 89. 全コードのJSON-like宣言コメントと漏れ検査

ユーザーの全コード適用依頼を優先して#212の段階移行を拡張した。公開日本語正本Draft v0.9 / 5691767a8708407a568a75a242543a4add825253をGitHub CLIで確認し、Python/GDScriptの全クラス・関数・メソッド（非公開/ネスト/property/decorator/テスト/ツールを含む）、module/匿名scriptの入口、Windowsバッチの入口/ラベル、実行CIのヘッダーへ構造化コメントを追加した。内部説明/docstringは保持し、引数なしとvoid/Noneを明示する。1エントリの項目は短い形式へまとめ、全コード注釈による読解量増加を抑える。

戦闘の会心・物理guard・単一claim、HP/MP所有、保存の複数ファイル境界、共有ドットエディタのundo/penなどは実装と代表照合した。全コメントの自然言語品質を自動保証するとは扱わない。ゲームの実行ロジックは変更せず、JSON・画像・Scene/config・依存定義やlambdaをコメントのために作り替えない。

追加: tools/comment-check/script/check_comments.py、tests/test_comment_contract.py（15テスト）、docs/COMMENT_RULES.md。Developer/CI専用でゲームをimportしない静的検査により、299ソースファイル・2532宣言の項目/引数/宣言名/番号/既知キー重複を照合する。GDScriptの複数行/型付き配列シグネチャ、未知キーの保持、通常コメントの許容、不正/未解析/読込失敗、batchラベルを回帰検証する。upstream汎用validatorのforkではなく、導入時のupstreamツールは設計段階。Playerへ検査依存を追加しない。

更新: 追跡コード全域のコメント、AGENTS/CODING_RULES/CODEMAP/tools README、CIのコメント検査、本履歴。AGENTSは既存6000byte上限を維持する短い参照案内とした。次のGDScript実装は引き続き#251（基本ぼうぎょ）で、今回その機能を実装済みとはしない。

検証（2026-10-06）: Windowsで日本語UTF-8のrem注釈がOEM文字コードと衝突したため、バッチだけはupstreamで許容される英語キー/ASCII説明へ変更。既存の実cmd.exe・専用fake ghテスト条件は緩めず成功した。関連39件/11サブテスト成功、Python228ファイルの3.10構文契約/致命的lintと新規2ファイルのstyle、project rules、生成REPO_MAP/application図のfreshness、E2Eカタログの構造/参照（12 covered/25 missing/1除外）、diff成功。これはPython3.10実行や実GUI/export/リモートCIの完了を示さない。

225既存Pythonの実行ASTと60GDScript/7batchのコメント以外の実行内容を変更前と比較し一致。既存の未コミットgame.py/開発予定、未追跡メモ/評価/図表/reportsを保持し、game.pyは今回のヘッダーだけをindexへ分離する。実セーブ/個体AI/party/items/data/assetsを作業対象にせず、テストは専用一時領域で実行する。

最新版UPD ae4636155b5e773d787cfccd1572808829601524を再取得し、エラー0・警告17・注意100。コメントだけで行数判定の警告が13→17へ増える最小再現を確認したが、checker抑制/独自forkは行わない。上流の公開Issue投稿は明示承認が必要として停止されたため、許可なしでは投稿しない。GDScript全体をUPDで検査した結果ではない。

最終全体985件・9241サブテスト成功（408.98秒、Python3.14.7 / pygame-ce2.5.8 / 実Godot4.7.2、skipなし）。最初の全体検証でAGENTSが6008byteとなった1件を修正してから全体を再実行した。実セーブを使わず、標準Python性能13項目も成功（20000回/7samples/2000warmup、24枠生成1017.03µs<=5000µs、24体移動352.41µs<=1000µs）。今回runtime hot pathの実装変更はないため、新規Godot性能単位は追加しない。描画/FPS/export性能の検証ではない。リモート再取得でbehind=0、次の#251はOPEN。今回分をローカルコミットするだけでpush/PR/Issue完了は行わない。

# 88. GDScript版の通常攻撃行動・単一Session適用

P1移行単位#230を実装した。pure normal_attack_contractが正規グローバルattack定義とBuilderの許可装備から対応数値効果だけを独立コピーし、normal_attack_actionが厳密な明示要求→offered/最新対象・乱数/数値検証→単一claim→実HP適用→finishを同期実行する。Sessionには読み取り専用inspect_ticketを追加し、攻撃計算を蓄積しない。applicationはread-only準備/開始/行動の呼出調停だけ。Action設定は開始直後のfresh Sessionとの一致を必要とし、再設定を拒否する。

会心率1/16・防御力無視、正規attackのpower/critical_multiplier、装備のattack威力倍率/固定追加、Pythonの0方向切捨て・最低1・残HP上限を維持する。リクエストからの数値/装備/guard上書き、不正/古い/重複/既claimed ticket、味方/死者/逃走者/不在対象、非有限/精度超過、MP0以外・未移植定義効果をclaim前に拒否し、資源/cursorを消費しない。最新actor死亡/逃走/敵なしの正しい要求は攻撃せず候補を取消する。HP/MPは次ラウンドまで保持し、stoppedを勝敗/報酬成功と扱わない。防御行動は未接続でguard=1。

追加: 上記engine2ファイル/各uid、gdscript/tests/run_normal_attack_probe.gd/uid、tests/test_gdscript_normal_attack_action.py、tools/performance-check/script/check_gdscript_normal_attack.py、docs/GDScript通常攻撃行動契約.md。更新: Session/application/contentの公開skill読込、README/GDScript README、CODEMAP/FORMATS、数値/Session契約、移植境界説明書、移行単位表、tools README、本履歴。Python runtime・正規data/assets・実セーブは変更なし。既存game.py/開発予定/未追跡ファイルを保持する。

検証（2026-10-06）: テスト用最大HPの指定、JSON floatとState整数のcontext照合、比較用MOD表示名、不正schema型の比較例外を修正した。関連46件・1611サブテスト成功後、古いround ticket・fresh/context再設定・MOD/型境界を追加し、最終新規13件・533サブテスト成功（28.69秒）。最終全体970件・9235サブテスト成功（807.87秒、Python 3.14.7 / pygame-ce 2.5.8 / 実Godot 4.7.2、skipなし）。

486組の通常/会心境界・低攻撃高防御・装備/揺らぎ/過剰ダメージは実Python _attack(allow_counter=False)と比較。8体/同速/両陣営同IDの12組を最大3ラウンド、実run_round内の明示攻撃で順序/HP推移/死亡skip/敵なし停止と比較した。_take_actionは明示攻撃を選ぶstub、_check_endはmockで、AI/勝敗移植の証拠ではない。不正入力/対象/非有限/未対応/精度超過、重複/古い/既claimed、コピー独立性、正規8種族×Lv1/50/100の準備・許可装備、MOD power/会心倍率、学習AI/party/items/原本byte不変は専用コピーで確認。実セーブは使用しない。

新規2ファイルを含むPython226ファイルの致命的lint/構文、新規style、project rules、REPO_MAP/追跡application図、E2E参照、Godot importとUID生成、diffチェック成功。E2Eカタログ12 covered/25 missing/1除外は参照構造検査だけ。最新版UPD（ae4636155b5e773d787cfccd1572808829601524）を再取得しPython対象エラー0・警告13・注意100。GDScript全体をcheckerで検査した結果ではない。

終了前の既存リモート取得・圧縮ツールでもorigin/mainへのbehind=0で取り込む差分なし、P0なし。次のP1 #251（基本ぼうぎょの行動解決/ラウンド終端解除）を起票し、GitHub blocked-by=#230/#221を登録・照合した。防御/全スキル/状態異常/AI推論・学習/戦闘Scene/勝敗・報酬保存/実敗北→教会復活は未接続、手動GUI/exportはUnverified。今回分だけローカルコミットし、push/PR/Issue完了操作は行わない。

標準性能（20000回/7samples/2000warmup）: 新規8体中1通常攻撃next→検証/claim/実HP/finishは1757.01µs（上限3ms）で成功。8行動ごとのround計画を償却し、初期構築/定義I/Oは計測外。HPは保持し、実HP減少も確認する。呼出処理をassertの外へ置き、assert無効でも実処理を計測する。既存Session段階1059.06µs（上限2ms）、8体資源568.68µs（上限1ms）、8体plan＋1check933.22µs（上限2ms）、24体モブupdate+snapshot1105.19µs（上限2ms）、5枚会話6.60µs（上限100µs）も成功。Python13項目成功（24枠生成1689.57µs、24体移動661.04µs）。AI/全8行動/描画/FPS/I/O/exportの性能ではなく、開発者専用でPlayerへimportしない。

性能プローブの最終調整後、1行動/1sample/0warmupの独立smokeで敵HPが実際に8減少し、両陣営からのminimum_hpが999999992になることを確認した（標準性能計測の代替ではない）。最終関連48件・1618サブテスト成功（49.26秒、skipなし）。ステージ後のPython226構文/致命的lint・新規style/構造/生成文書/E2E参照/diffを再確認し、UPD mainのSHA一致と本体リモートbehind=0も再照合した。

# 87. GDScript版の戦闘Session・資源保持と段階カーソル

P1移行単位#229を実装した。pure `engine/battle_session.gd` が#227 Stateを戦闘開始時だけ所有し、#228の明示shuffle/stable速度順をラウンドごとに固定する。HP/MP/fledは次ラウンドまで保持し、途中snapshotを最大値へ戻すstart・成功後の再初期化を拒否する。開始失敗は未初期化のまま原子的に拒否し、再試行可能。

候補取得はoffered予約でcan_execute=false、claimだけが最新死亡/逃走/敵生存を再確認して一度だけcan_execute=trueを返す。claimedに対するfinishだけがcursorを一度進める。二重取得/claim/完了、未claim完了、古い/不正ticket、進行中のround開始を拒否し、死亡/逃走者をskipする。stoppedは勝敗/報酬/復活の成功結果ではない。side+idとround/slotで同IDの両陣営・古い同個体の候補を区別する。

資源操作は当該Stateへ委譲するだけで攻撃/AI実行を代用しない。各陣営4体と無制限の所有/プリセットを区別し、#228のstrict snapshot/未対応状態異常/速度buff拒否、独立plain入出力を維持する。applicationはread-only Preparation→Session.start→begin_roundを調停し、全成功後のみ内部Sessionを切り替える。公開は開始とsnapshotだけで、RefCountedを層外へ返さない。

追加: 上記engine/applicationと各uid、`gdscript/tests/run_battle_session_probe.gd`とuid、`tests/test_gdscript_battle_session.py`、`tools/performance-check/script/check_gdscript_battle_session.py`、`docs/GDScript戦闘Session契約.md`。
更新: turn_orderの安全なkey検証公開、README/GDScript README、CODEMAP、FORMATS、#227/#228仕様への導線、移植境界説明書、移行単位表、tools README、本履歴。Python runtime・正規data/assets・実セーブは変更なし。以前からのgame.py/開発予定/未追跡ファイルは保持する。

検証（2026-10-06）: 新規17テスト・230サブテスト。最初の参照テストの個体属性名を修正して関連51件・1165サブテスト成功（36.38秒、skipなし）。全体957件・8702サブテスト成功（391.42秒、Python 3.14.7 / pygame-ce 2.5.8 / 実Godot 4.7.2、skipなし）。テスト2行の127文字折返し後、#221も含む最終関連69件・2020サブテスト成功（42.68秒）。

8体/同速/両陣営同IDの60組を最大3ラウンド、Python実run_roundの順序/最新生存と比較した。参照側の_take_actionは資源変更stub、_check_endはmockで、攻撃/AI/勝敗移植の証拠ではない。3ラウンド資源保持、途中/取得後の死亡・逃走・敵なし、重複/古い/不正ticket・順序・再初期化、不正型/非有限/未知キー・宛先、初期結果/入力/返却値/個体同士の独立性、8種族の新規開始を確認。個体/学習済AI/party/items/data/assetsのbyte不変は専用コピーで検証し、実セーブは使わない。

新規2ファイルを含む追跡Python224ファイルの致命的lint、新規style/構文、project rules、REPO_MAP/追跡application図、E2E参照、Godot import/正規コンテンツ6000frame headless起動、diffチェック成功。専用起動保存rootは作成されない。E2Eカタログ12 covered/25 missing/1除外は参照構造検査だけ。最新版UPD（ae4636155b5e773d787cfccd1572808829601524）を再取得し、Python対象エラー0・警告13・注意100。GDScript全体をcheckerで検査した結果ではない。

標準性能（20000回/7samples/2000warmup）: 新規8体Sessionの1候補next/claim/0ダメージ・0MP/finishは719.86µs（上限2ms）で成功。8段階ごとのround計画を償却し、初期State構築は計測外。Python13項目成功（24枠生成834.61µs、24体移動334.55µs）。既存Godot24体update+snapshot724.21µs（上限2ms）、5枚会話4.87µs（上限100µs）、8体資源状態411.81µs（上限1ms）、8体plan＋1回の最新check585.67µs（上限2ms）も成功。実攻撃/AI/8体全ラウンド/描画/FPS/I/O/exportの性能ではなく、開発者専用でPlayerへimportしない。

終了前の既存リモート取得・圧縮ツールでもorigin/mainへのbehind=0で取り込む差分なし。次のP1 #230（通常攻撃行動→Session）を起票し、GitHub blocked-by=#229/#221を登録・照合した。Scene/攻撃・全スキル/状態異常/AI推論・学習/勝敗・報酬保存/実敗北→教会復活は未接続、手動画面/exportはUnverified。今回分だけローカルコミットし、push/PR/Issue完了操作は行わない。

# 86. GDScript版の行動順・最新の実行可否

P1移行単位#228を実装した。pure `engine/turn_order.gd` が#227 snapshotの生存味方→敵収集、明示shuffle順検証、補正済み速度のstable降順計画と、行動直前の最新HP/fled/敵生存確認を担当する。side+idで両陣営同IDを区別し、0と1の速度はPython Combatant.speed同様に同速として扱う。Godotの不安定sortへ同速を任せず、最大8体へのstable insertionを使う。

`application/turn_preparation.gd` はread-only Builderから新規戦闘snapshotと計画を組み立てるだけで、行動/保存/AIを実装しない。開始準備を既存戦闘のラウンドごとのHP最大値再生成に使わず、行動直前は現在のsnapshotを入力する。HP0/逃走なら実行不可、敵生存者なしならstopを返すが、勝敗/報酬/復活の成功結果ではない。順序消費や行動済み/pendingは次のSession単位へ分ける。

#227の型/数値/最大値/整合性、各陣営4体/重複とshuffle欠損/重複/未知対象を検証し、自動補完しない。未対応snapshot/identity/stats追加キーを拒否し、状態異常/速度buffを適用済みと扱わない。保有JSONの未知キーは削除せず、入力/返却値を独立コピーにする。所有数/プリセット数は無制限のまま。

追加: 上記engine/applicationと各uid、`gdscript/tests/run_turn_probe.gd`とuid、`tests/test_gdscript_turn_order.py`、`docs/GDScript行動順契約.md`。
更新: 既存combatant probe/性能checker、README/GDScript README、CODEMAP、FORMATS、戦闘状態契約の導線、移植境界説明書、移行単位表、tools README、本履歴。Python runtime・正規data/assets・実セーブは変更なし。以前からのgame.py/開発予定/未追跡ファイルは保持する。

検証（2026-10-06）: 新規16件（順序96組、8体混合100組、最新生存72組、正規準備108組の計376サブテスト）。初回関連52件成功後に128文字のtest行を127文字以内へ折返し、最終関連52件・1790サブテスト成功（33.33秒、skipなし）。同一shuffleをPythonの実run_roundへ注入して実際にsortされたリストを比較した。参照側の行動/勝敗はmockで止めた部分比較で、AI/攻撃/勝敗移植の証拠ではない。0体/片側空/HP0/逃走/同速/速度差/両陣営同ID、最新死亡/逃走/敵なし、不正型/非有限/精度外/追加snapshotキー/不正shuffle、入力/返却値独立性を確認した。正規8種族×Lv1/50/100×＋/許可装備の開始準備をPython BattleDataLoaderと比較し、個体/学習済AI/party/items/data/assetsのbyte不変を専用コピーで確認した。実セーブは使わない。

全体940件・8472サブテスト成功（382.58秒、Python 3.14.7、pygame-ce 2.5.8、実Godot 4.7.2、skipなし）。追跡Python222ファイルの致命的lint、新規style、project rules、REPO_MAP/追跡application図、E2E参照、Godot import/正規コンテンツ6000frame headless起動、diff --check成功。専用起動保存rootは作成されない。E2Eカタログ12 covered/25 missing/1除外は参照構造の検査だけで、ゲーム全体の移植証拠ではない。最新版UPD（ae4636155b5e773d787cfccd1572808829601524）を再取得しPython対象エラー0・警告13・注意100。

標準性能（20000回/7samples/2000warmup）: Python13項目成功（24枠生成1035.83µs、24体移動377.04µs）。Godot既存24体update+snapshot823.64µs（上限2ms）、5枚会話デッキ選択6.69µs（上限100µs）。combatantガードは8体資源状態402.50µs（上限1ms）と、新規8体plan＋1回の最新check642.77µs（上限2ms）で成功した。8回行動/実ラウンド/AI/描画/FPS/I/O/exportの性能を計測したものではなく、開発者専用でPlayerにimportしない。

既存リモート取得・圧縮ツールでも最終確認し、origin/mainへのbehindは0で取り込む差分なし。次のP1 #229（戦闘SessionのState保持・ラウンドカーソル）を起票し、GitHub blocked-byを#228へ登録・照合した。戦闘Scene/攻撃・全スキル/状態異常/AI推論・学習/勝敗・報酬保存/実敗北→教会復活は未接続、手動画面/exportは未検証。今回分だけローカルコミットし、push/PR/Issue完了操作は行わない。

# 85. GDScript版の戦闘個体HP/MP・生死状態

P1移行単位#227を実装した。pure `engine/combatant_state.gd` が戦闘専用HP/MP/fled/alive、read-only `application/combatant_builder.gd` が既存個体/schema→#219/#220再構築→独立plain snapshotを担当する。新規生成は最大HP/MP、同じインスタンスの再初期化を拒否し、HP0から勝手に復活しない。非負整数値のダメージ・MP費用と実減少/不足結果、HPが残っている逃走者も除く順序保持の生存一覧を扱う。

入力/返却値は独立、6能力値/型/有限/整数/2^53−1以内・identityを検証し、失敗時は理由付き拒否で補完/修復しない。4体のactiveチームは5体以上を黙って切らず、所有数は無制限のまま。未知＋/不明・装備不可IDは#220のwarningsを保持する。数値操作は死亡/逃走者の行動権限を代用せず、最新生存の確認は後続ターン契約へ分ける。戦闘状態を保有個体/AI/state/itemsへ保存しない。

追加: 上記engine/application、`gdscript/tests/run_combatant_probe.gd`と各uid、`tests/test_gdscript_combatant.py`、`tools/performance-check/script/check_gdscript_combatant.py`、`docs/GDScript戦闘個体状態契約.md`。
更新: README/GDScript README、CODEMAP、FORMATS、移植境界説明書、移行単位表、tools README、本履歴。Python runtime・正規data/assets・実セーブは変更なし。以前からのgame.py/開発予定・未追跡ファイルは保持する。

検証（2026-10-06）: 初回関連69件成功後に、破損/必要定義欠損・独立living返却・未知ID・数値操作の責務境界を補強した。新規18件・559サブテスト、最終関連72件・3948サブテスト成功（61.12秒、skipなし）。全8種族×Lv1/10/50/100×＋選択×許可装備をPython BattleDataLoaderのstats/初期HP/MP/aliveと比較した。HP0/過剰/0ダメージ、MP0/不足/ちょうど/0費用、逃走・生存順、未初期化/再初期化、不正型/非有限/精度外、独立2個体と入力/返却値、4枠対120体所有を確認した。#221へ各回の現在HPを渡し、24組の連続通常攻撃をPython BattleEngineと比較し、保有個体/学習済AI/party/items/正規data/assetsのbyte不変を専用コピーで確認した。実セーブは使わない。

全体924件・8096サブテスト成功（371.21秒、Python 3.14.7、pygame-ce 2.5.8、実Godot 4.7.2、skipなし）。新規styleの継続行7箇所を修正し、検査再実行時のsandbox multiprocessing pipe拒否は単一workerで再試行して成功した。追跡Python221ファイルの致命的lint、新規style、project rules、REPO_MAP/追跡application図、E2E参照、Godot import/正規コンテンツ6000frame headless起動、diff --check成功。専用起動保存rootは作成されない。E2Eカタログ12 covered/25 missing/1除外は参照構造の検査だけでゲーム全体の移植の証拠ではない。最新版UPD（ae4636155b5e773d787cfccd1572808829601524）を再取得しPython対象エラー0・警告13・注意100。

新しいGodot性能ガード（20000回/7samples/2000warmup）は8体init+damage+MP+flee+snapshot+livingの中央値456.97µs（上限1ms）で成功した。Playerへのbenchmark importなし、I/O/描画/FPS/実ターン戦闘の計測ではない。既存リモート取得・圧縮ツールでも再確認し、origin/mainへのbehindは0で取り込む差分なし。
標準Python性能13項目も成功（24枠生成922.08µs、24体移動326.03µs）。既存Godot標準ガード（20000回/7samples/2000warmup）は24体update+snapshot731.79µs（上限2ms）、5枚会話デッキ選択4.84µs（上限100µs）で成功。これらの余裕あるホットパス上限内の確認であり、手動画面の体感/FPS・保存I/O性能を保証したものではない。

戦闘Scene/ターン/全スキル/耐性・状態異常/AI推論・学習/勝敗・報酬保存/実敗北→教会復活は未接続。手動画面/exportは未検証。次のP1 #228（ラウンドの行動順・実行可否）を起票し、GitHub blocked-byを#227へ登録・照合した。今回分だけローカルコミットし、push/PR/Issue完了は行わない。

# 84. GDScript版の教会復活地点登録・保存

P1移行単位#226を実装した。正規church/reviveを実Enter/Space/Eから、純粋なrevive_point_contract→application/church_registration→既存Data保存へ接続した。地点の辞書/map_id/name/整数x/y、対象マップid・範囲・通行地形・blockingイベントを検証する。Dataのマップ読込もid/有限正整数の寸法/events配列を確認し、型違いをint変換で黙認しない。UI/rendererは保存を担当しない。

既存stateのrevive_pointだけをイベントの辞書コピーで置き換える。入力地点の未知キーをPython FieldProgressStore.register_churchと同様に保持し、既存の保存位置/方向/current_party/flags/他stateキーと個体/学習済みAI/items/parties/metaは変えない。同じ地点ならstateの再出力もしない。schema/方向/revive_pointを省略した旧形式では、登録するキー以外を補間しない。未保存は先にF5を案内し、教会から保存フォルダ/初期個体を勝手に生成しない。

既存stateとdigestを捕捉し、commitで再照合/対象マップ再読込を行う。既存save_profileの期待digest/リンク拒否/atomic state置換を使い、保存後に期待state全体を確認してから成功を表示する。外部更新・破損・未対応schema・不正保存位置・置換失敗は理由付き失敗で、以前の保存を削除/修復/巻き戻ししない。Dataの書込成功後に照合が失敗した場合もok:false/saved:trueと確認失敗を表示する。検証後〜書込の競合窓/並行writer完全排他の限界は従来どおり。

登録だけで主人公を移動させず、モブ/会話/時計や編成を初期化しない。暗号/一覧/編成/プリセットmodalとechoでは教会登録を漏らさない。HP回復・全滅判定・実戦闘・敗北→教会復活は未接続と表示する。復活地点の再起動保持は実敗北復活の検証ではない。

追加: `gdscript/engine/revive_point_contract.gd`、`gdscript/application/church_registration.gd`、`gdscript/tests/run_church_probe.gd`と各uid、`tests/test_gdscript_church.py`、`docs/GDScript教会登録契約.md`。
更新: `gdscript/application/field_application.gd`、`gdscript/data/content_repository.gd`、README/GDScript README、CODEMAP、FORMATS、移植境界説明書、移行単位表、本履歴。Python runtime・正規data/assets・実セーブは変更なし。以前からのgame.py/開発予定等のユーザー変更は保持する。

検証（2026-10-06）: 初回関連でリンク拒否自体は成功したが、テスト自身のprivate junctionを作る前のファイル一覧と、別名を含む作成後の一覧を比較した1件が失敗した。比較基準をsetup完了後に合わせ、ctypesの継続行styleを修正した。最終関連33件・2118サブテスト成功（66.22秒、skipなし）。新規13件・58サブテストが対象。正規2教会/実E・Enter・Space→保存→別プロセス再起動、同一地点/旧形式/未知キー、Python StateStore/FieldProgressStore読込と地点コピー、個体/AI/items/party/原本保持、型違い/不正マップ・座標・地形/blockingイベント/保存を専用コピーで確認した。

外部更新はbegin後の変更と書込直前のData digest再照合で保持し、再試行で最新stateを使える。書込後外部更新と虚偽の成功返却は開発者probeだけのfault注入で、登録/保存成功を偽装しないことを確認した。実Windowsの読込可能・置換不可ハンドルでは前のstate/一時ファイル清掃/解除後再試行と、同一地点の書込不要を確認した。private junctionでもリンク先を書き換えず拒否する。実セーブは使わない。

全体906件・7537サブテスト成功（352.57秒、Python 3.14.7、pygame-ce 2.5.8、実Godot 4.7.2、skipなし）。最新版UPD（ae4636155b5e773d787cfccd1572808829601524）を再取得しPython対象エラー0・警告13・注意100。Python217ファイル致命的lint、新規style/構文、project rules、REPO_MAP/追跡対象application図、E2E参照、Godot import/正規コンテンツ6000frame headless起動、diff --check成功。専用起動保存rootは作成されない。E2Eカタログ12 covered/25 missing/1除外は参照構造の検査だけで、ゲーム全体の移植の証拠ではない。

標準Python性能13項目成功（24枠生成884.89µs、24体移動385.11µs）。Godot標準性能ガード（20000回/7samples/2000warmup）は24体update+snapshot835.24µs（上限2ms）、5枚会話デッキ選択5.29µs（上限100µs）で成功。教会登録は低頻度のI/O操作で新しいフレーム内ホットパスではなく、既存ガードで退行を確認した。登録I/Oのレイテンシや描画/FPSを計測したものではない。既存リモート取得・圧縮ツールでも最終確認し、origin/mainへのbehindは0で取り込む差分なし。

手動画面の視認性、Windows IME、配布exportは未検証。次のP1 #227（戦闘個体のHP/MP・生死状態）を起票し、GitHub blocked-byを#226へ登録した。#219/#220/#221の補正済み能力値/通常攻撃数値を実行時状態へ接続する前提で、戦闘Scene/ターン/全スキル/AI/実敗北復活はさらに別単位。今回分だけローカルコミットし、push/PR/Issue完了操作は行わない。

# 83. GDScript版の暗号一致後のおばけ取得・保存

P1移行単位#225を実装した。#224の正規湧き場→7文字入力→password_matchedを、純粋な不足種族/フラグ計画とapplication取得サービスへ接続する。個体/初期AIは既存plain契約、JSON公開/置換は既存Dataを使う。UIは保存せず、2種族の所有と保存内容を再検証してから成功を表示する。取得後は所有一覧を再走査し、牧場/F6と別プロセス再起動で確認できる。

Python reacquire_ghostsと同じmaru→kadokaの不足分だけをLv1/経験0/＋なし/装備null/source=ghost_home_passwordで作る。既存の同種族が1体でもあれば追加せず、名前/Lv/＋/装備/取得元/学習AIや重複個体を変更しない。flags.ghost_entrance_openをtrueにし、既存の保存済み位置/向き/復活地点/party/他フラグ/未知キーを保持する。パーティへ自動追加せず、未保存のフィールド位置も保存しない。所有数/保存スロットの上限を追加しない。住処の2体/徘徊/会話を取得状態によって削除・初期化しない。

新規プロフィールは既存管理画面と同様に先にF5で保存する。取得から初期個体や正規Python保存先を勝手に作らない。既存AI/state/所有フォルダの破損は理由付き拒否で、保存を修復しない。不足全種族の定義・Lv1再構築を公開前に検証し、暗号画面を開いた時のstate digestを各公開前/フラグ保存前に再照合する。外部更新や置換失敗を成功として扱わない。

複数ファイル全体はトランザクションではない。1体公開後の失敗、2体公開後のstate置換失敗等はcreated/flag_saved/partial/stage/errorと「部分保存」を返す。公開済み個体や以前の保存を削除/巻き戻さず、再入力で最新所有を再走査して不足分だけを作る。検証後〜書込の並行writer競合窓は残り、全体排他/原子性を主張しない。誤答/取消は取得サービスを呼ばず書き込まない。

追加: `gdscript/{engine,application}/ghost_acquisition.gd`と各uid、`tests/test_gdscript_ghost_acquisition.py`、`docs/GDScriptおばけ取得契約.md`。
更新: `gdscript/application/field_application.gd`、`engine/monster_record_contract.gd`、`tests/run_password_probe.gd`、`tests/test_gdscript_password.py`、README/GDScript README、CODEMAP、FORMATS、暗号入力契約、移植境界説明書、移行単位表、本履歴。Python runtime・正規data/assets・実セーブは変更なし。以前からの無関係なgame.py/開発予定等は保持する。

検証（2026-10-05）: 初回関連でGodot取得は成功したが、Python正本比較fixtureのProgressSession初期化不足により4サブテストが失敗した。fixtureを正本の状態所有へ合わせ、継続行styleを修正した。最終関連22件・2049サブテスト成功（62.44秒、skipなし）。実Sceneの正規イベント/実キーから不足2/1/0体と再入力/再起動、Python reacquire_ghosts/MonsterStore/StateStore/default_aiとの出力比較、既存AI/個体/party/位置/未知キー保持を専用コピーで確認した。128個体/126名前付きスロット、既存フラグだけ残った再取得、誤答/取消/未保存、外部更新、破損定義/AI/state/flags/所有フォルダも検証する。

2体目公開失敗はテスト専用fault注入で確認した。実Windowsの読込可能・置換不可ロックでは、2体公開後のstate失敗/以前のstate保持/一時ファイル清掃/解除後の不足0体再試行を確認した。公開後の外部変更も専用コピーで拒否し、既存ID/AIを残したまま再試行できる。実セーブは使わない。

全体893件・7479サブテスト成功（316.81秒、Python 3.14.7、pygame-ce 2.5.8、実Godot 4.7.2、skipなし）。最新版UPD（ae4636155b5e773d787cfccd1572808829601524）を再取得しPython対象エラー0・警告13・注意100。標準Python性能13項目成功（24枠生成951.96µs、24体移動362.45µs）。Godot標準性能ガード（20000回/7samples/2000warmup）は24体update+snapshot776.47µs（上限2ms）、5枚の会話デッキ選択4.87µs（上限100µs）で成功。取得は低頻度操作でホットパスを変更せず、描画/FPSの計測ではない。

Python216ファイル致命的lint、新規style/構文、project rules、REPO_MAP/追跡対象application図、E2E参照、Godot import/専用保存rootで正規コンテンツ6000frame headless起動、diff --check成功。起動だけでは保存フォルダを作らない。E2Eカタログ12 covered/25 missing/1除外は参照構造の確認のみで、ゲーム全体の移植の証拠ではない。

手動画面の視認性、Windows IME候補/確定、配布exportは未検証。次のP1 #226（教会イベントで復活地点を登録・保存）を起票し、GitHub blocked-byを#225に登録した。#226はcheckpoint登録のみで、実際の敗北→教会復活/HP回復とは別単位。今回分だけローカルコミットし、push/PR/Issue完了操作は行わない。

# 82. GDScript版の湧き場7文字暗号入力と仮想キーボード

P1移行単位#224を実装した。純粋な `engine/password_session.gd` がPython PasswordSessionと同じopen/append/backspace/submit/cancel、7文字上限、KANA_KEYS、完全一致、案内/誤答/activeを所有する。UIはnative LineEditの確定文字/仮想かなButton/実キーをplain操作signalへ変換し、7枠を描画する。Sceneは正規ghost_homeのpassword_spring、入力中の停止、結果signalを接続する。日本語確定文字は1文字ずつ渡し、native文字キーを重複追加しない。IME変換中のEnter/Backspace/Escはnative側へ委ねるが、実IMEの手動検証は未実施。

Enter/テンキーEnterで決定、Backspaceで削除、Esc/やめるで取消、Tab/Shift+Tab/Spaceで仮想キー操作。入力中は主人公/固定モブ/補間/時計とF5/F9/F6を停止し、直接の位置保存/読込・一覧/編成開始も拒否する。開閉時の長押し時間をresetし、滞在分の追いつき移動を起こさない。一致はpassword_matched、取消はpassword_cancelledのplain結果。誤答は入力を保持する。一致しても「取得と保存は未移植 (#225)」を表示し、仲間加入成功は装わない。住処の2体は取得状態に関わらず残す。入力・結果は実行時だけで保存形式/フラグ/個体/AIを変更しない。

追加: `gdscript/engine/password_session.gd`、`ui/password_view.gd`、`tests/run_password_probe.gd`と各uid、`tests/test_gdscript_password.py`、`docs/GDScript暗号入力契約.md`。
更新: `gdscript/application/field_application.gd`、`ui/field_input.gd`、README/GDScript README、CODEMAP、FORMATS、移植境界説明書、移行単位表、本履歴。Python runtime・正規data/assets・実セーブは変更なし。以前からの無関係なgame.py/開発予定等は保持する。

検証（2026-10-05）: 初回関連44件のうち3件失敗を確認した。nativeのprogrammatic insertはtext_changedを発行しないため、複数文字確定はadapter signalテストと明示した。保存位置fixtureが水上だったため通行可能な（17,8）へ修正。headlessの64×64仮ウィンドウを正式な960×540に合わせて矩形を検証した。仮想キーのTab/Spaceテストは実キー同様に論理/物理keycodeを設定した。新規11件・2032サブテスト成功（14.56秒、skipなし）。純粋状態の同一操作列、空/誤答/不正文字/上限/終了後/Unicode、正規湧き場→実Unicode/native LineEdit/実mouse click/Tab/Space/決定/取消、modal停止と30秒滞在後の周期再開、取得前後の原本/個体/AI/items/parties/meta byte不変を専用コピーで確認した。

全体882件・7462サブテスト成功（349.84秒、Python 3.14.7、pygame-ce 2.5.8、実Godot 4.7.2、skipなし）。最新版UPD（ae4636155b5e）を再取得しPython対象エラー0・警告13・注意100。Python標準性能13項目成功（24枠生成約1.41ms、24体移動約0.53ms）。新しい7文字入力は低頻度操作でホットパスではなく、既存ガードで退行を確認する。Python215ファイル致命的lint、新規style/構文、project rules、REPO_MAP/追跡対象application図、E2E参照、Godot import/専用保存rootの正規コンテンツ6000frame headless起動、diff --check成功。E2Eカタログ12 covered/25 missing/1除外は参照構造の確認のみで、全移植の証拠ではない。

Godot標準性能ガード（20000回/7samples/2000warmup）は24体update+snapshot約0.853ms（上限2ms）、5枚の会話デッキ選択約5.91µs（上限100µs）で成功。入力配送/描画/FPSを計測したものではない。

手動画面の視認性、Windows IME候補/確定、exportは未検証。次は#225の暗号一致後のまる/かどか取得・保存。#224はローカル実装済み/未pushとしてIssueを閉じない。

# 81. GDScript版の固定モブ会話デッキと正面停止連携

P1移行単位#223を実装した。純粋なdialogue_deckへ文字列検証/Unicode空白除去/一巡/再抽選を分離し、controllerが各モブのカード状態と向きを所有する。Sessionがプレイヤー正面のモブをイベントより先に選び、Sceneが実Enter/Space/Eキーを接続してplain結果をstatusへ表示する。echo/管理modalではカードを消費しない。話しかけるとモブがこちらを向くため既存の正面停止が働き、離れると次の周期で移動する。会話自体はmodalではなく、他のモブやフィールド時計は停止しない。

有効な文字列デッキはPython next_dialogueと同じshuffle→末尾pop、補充時の前回末尾回避を使う。単一/重複カードは原本どおり保持し、全角/ノーブレーク等の空白をPython str.stripと同じ集合で除去する。未設定/非配列/非文字列カード/有効台詞なしは理由付き拒否で、Pythonの不正型文字列化/「……」fallbackは流用しない。会話プール/前回台詞は保存せず再入場/読込で初期化する。仲間取得前後で住処の2体を隠さない。

固定戦闘・未知interactionは未移植を表示しカード/RNGを消費しない。会話後消滅設定は台詞と未移植注意だけで除去/保存しない。湧き場の暗号/仲間取得・条件付き戦闘セリフ・野生戦闘を代用の成功処理で埋めない。

追加: `gdscript/engine/dialogue_deck.gd` とuid、`tests/test_gdscript_dialogue.py`、`docs/GDScript固定モブ会話契約.md`。
更新: `gdscript/engine/fixed_mob_controller.gd`、`application/{field_session,field_application}.gd`、`tests/run_fixed_mobs_probe.gd`、`tools/performance-check/script/check_gdscript_fixed_mobs.py`、README/GDScript README、CODEMAP、FORMATS、移動契約、移植境界説明書、移行単位表、tools README、本履歴。Python runtime・正規data/assets・保存形式は変更なし。

検証（2026-10-05）: 初回関連47件・1850サブテスト成功（35.77秒）。取得前後fixtureを正規ghost_entrance_openフラグと実際の所有フォルダの有無へ整え、継続行styleを修正した。最終新規12件・877サブテスト成功（10.54秒、skipなし）。実GodotとPythonで37デッキ×23回=851条件の選択/残数/前回カード/RNG消費を比較した。単一/重複/全29種Unicode空白・ゼロ幅文字、巡回境界、個別状態/再初期化、不正診断、正面対象/4方向/実キー/echo、占有/停止/周期再開、管理modal、イベント優先、取得前後の住処2体、原本/個体/AI/assets byte保持を専用コピーで確認した。

最新版UPD（ae4636155b5e）を再取得しPython対象エラー0・警告13・注意100。実Godot性能ガードには24体update+snapshotに加え、5枚の会話デッキ選択/効果生成（24体の最後の対象）を追加した。手動ウィンドウの視認性・FPS・exportは未検証。
全体871件・5430サブテスト成功（240.70秒、Python 3.14.7、pygame-ce 2.5.8、実Godot 4.7.2、skipなし）。標準Python性能13項目成功（生成24枠約0.95ms、移動24体約0.37ms）。Godotの標準20000回/7sample/2000warmupは24体update+snapshot約0.715msで2ms以下、会話約4.90µsで100µs以下。Python214ファイル致命的lint、新規style/構文、project rules、REPO_MAP/追跡対象application図、E2E参照、Godot import/専用保存rootの正規コンテンツ6000frame headless起動、diff --check成功。Python E2Eカタログは12 covered/25 missing/1除外で、#204完了や全移植の証拠ではない。

次のP1/gdscript単位として#224（湧き場の7文字暗号入力/仮想キーボード）と#225（まる/かどか取得・保存）を起票し、GitHubのblocked-byを#223→#224→#225に登録した。UI判定と複数ファイルの取得処理を別単位にし、未接続を加入成功として表示しない。次は#224。

実セーブと既存ユーザー作業を保持し、今回分だけローカルコミットする。push/PR/Issue完了操作は行わない。#218〜#223の最初の移行6単位はローカル実装済みだが、ゲーム全体の移植完了ではない。

# 80. GDScript版の固定モブ時間周期移動とマス占有

P1移行単位#222を実装した。clock/RNG注入型の純粋なfixed_mob_controller、独立した乱数アダプタ、フィールド時間を所有するSession、snapshotを描くUIへ分離した。主人公が動かなくてもidle/random/chaseを時間周期で更新する。既存JSONのinterval/chanceを利用し、まる450ms/100%、かどか900ms/45%を反映。最低100ms、各締切1試行/追いつき連打なし、180msのsmoothstep補間。管理一覧/編成/プリセット中は時計・移動・補間が停止する。

プレイヤー/他モブ/地形/岩・看板・台帳と重ならない。enabled/既存despawned_fixed_mobs/respawn設定を読んで再入場で原本の初期配置へ戻す。重複/範囲外/通行不能の初期地点は空きマスへ移し、満員なら重ねず理由付き未配置。Python正本のblockingイベント無視と満員時の重複は、Issue条件を優先してGodotで安全側へ強化した。Python runtimeは変更しない。会話デッキ/消滅効果/野生/接触戦闘は未移植で、基本の正面移動停止だけを現Python移動規則から移した。

位置保存を実モブ占有で検証する。原本の初期地点は現在占有ではないため、そこからモブが動けばプレイヤーが入り保存/復元できる。読込ではプレイヤーを先に確保し、重なる初期モブを再配置する。プレイヤー位置を自動修復しない。モブの実行中位置/時計/RNG/補間を保存せず、個体/AI/items/原本JSON/画像を保持する。

追加: `gdscript/engine/{fixed_mob_controller,field_random}.gd`、`gdscript/tests/run_fixed_mobs_probe.gd` と各uid、`tests/test_gdscript_fixed_mobs.py`、`tools/performance-check/script/check_gdscript_fixed_mobs.py`、`docs/GDScript固定モブ移動契約.md`。
更新: `gdscript/application/{field_session,field_application,field_persistence}.gd`、`engine/field_save_contract.gd`、`ui/field_view.gd`、`tests/test_gdscript_save.py`、README/GDScript README、CODEMAP、FORMATS、移植境界説明書、移行実装単位表、tools README、本履歴。Python runtime・正規data/assets・保存形式は変更なし。

検証（2026-10-05）: 初回関連でJSON由来float配列との正面比較とテスト時計初期化等4件が失敗し、整数要素比較/Scene入場後process停止/正本constructor指定へ修正した。関連44件・1001サブテスト成功（42.11秒）。正常配置の40設定×15時刻=600条件を同じ乱数roll/方向順でPythonと実Godot比較した。AI/確率/締切/回数/補間と入力不変、正規まる/かどか設定、全blockingイベント、占有/初期化/満員/再出現設定、実Sceneの静止中更新/全管理modal停止/描画の副作用なし、補間中の論理占有、元モブ配置での保存/別プロセス再起動と既存JSON/個体AI byte保持を専用コピーで確認した。

全体859件・4553サブテスト成功（290.74秒、Python 3.14.7、pygame-ce 2.5.8、実Godot 4.7.2、skipなし）。その後RNGの生成をSession側のcompositionへ明示分離し、テストstyleの継続行とルーティング表を整えた。最新版UPD（ae4636155b5e）を再取得しPython対象エラー0・警告13・注意100。標準Python性能13項目成功（生成24枠約1.46ms、移動24体約0.41ms）、追加の実Godot性能ガードも24体update+snapshot約0.764msで2ms以下を達成（標準20000回/7sample/2000warmup）。描画/FPS/exportの証拠ではない。

Python213ファイル致命的lint、構造規約、REPO_MAP/追跡対象application図、E2E参照チェックも成功。Python E2Eカタログは12 covered/25 missing/1除外のままで、全機能移植や#204完了とは扱わない。
最終境界整理後の関連119件・1129サブテスト成功（132.27秒、skipなし）。新規Python style/構文、Godot import、正規コンテンツを専用保存rootで6000frame headless起動、diff --check成功。

境界: 手動ウィンドウ操作/視認性、配布exportは未検証。会話デッキ/会話時の向き/消滅イベント、固定戦闘、野生/接触戦闘、暗号取得、戦闘AIは今回未移植。実セーブと既存ユーザー作業を保持し、対象だけローカルコミットする。push/PR/Issue完了操作は行わない。次は#223の会話デッキと正面停止連携。

# 79. GDScript版の通常攻撃・防御・会心の数値契約

P1移行単位#221を実装した。純粋なattack_numbersへ通常攻撃、基本防御倍率、共通の最終ダメージを分離した。2つの乱数を明示入力し、Python/Godotのseed列一致には依存しない。UI/ファイルI/O/AIや実戦闘状態へ依存せず、plain入力も変更しない。通常攻撃以外のkind/skill_idは未移植の理由付きで拒否する。#220の補正後能力値/許可装備から数値を渡す経路をprobeで比較し、既存のフィールドSceneへはまだ接続しない。

Python正本と同じ途中/最後のint切捨て、0.92〜1.08の揺らぎ、最低1、現在HPによる実与ダメージ制限を使用。会心率は1/16、ちょうど1/16は非会心で、会心時は防御力を使わない。会心でも物理guardは掛かり、非物理の最終数値には掛からない。攻撃一時倍率、通常攻撃の威力/会心率倍率、許可装備のattack威力補正と固定追加を数値として扱う。バフ消費/guard設定や解除/生死対象選択は行わない。入力不正/非有限値/安全な整数精度を超える演算は理由付き失敗で、代替ダメージを作らない。

追加: `gdscript/engine/attack_numbers.gd`、`gdscript/tests/run_attack_probe.gd` と各uid、`tests/test_gdscript_attack_numbers.py`、`docs/GDScript通常攻撃数値契約.md`。
更新: README、GDScript README、CODEMAP、FORMATSの実行時数値境界への参照、移植境界説明書、移行実装単位表。Python runtime・正規data/assets・保存形式は変更なし。

検証（2026-10-04）: 初回関連37件・2300サブテスト成功（35.67秒）。通常/防御/会心の600組、1/16の厳密な境界と16等分入力の1会心、会心の防御無視とguard維持、低攻撃/高防御、乱数の上下限/近接境界、切捨て順、装備威力/固定追加、非物理へのguard漏れ、HP0/過剰ダメージ、数値文字列、不正型/非有限/精度超過、入力不変を実GodotとPython BattleEngineで比較した。再構築から許可/拒否/未知装備を渡す48ケース、破損時の代用禁止と個体/AI/party/種族/装備/画像原本のbyte保持を専用コピーで確認した。

style検査でテストの継続行インデント2件を修正し、未移植スキルの入力拒否を追加した。最終新規18件・855サブテスト成功（11.90秒）。全体846件・3954サブテスト成功（319.68秒、Python 3.14.7、pygame-ce 2.5.8、実Godot 4.7.2、skipなし）。仕様更新後のルーター/優先度/数値29件・860サブテストも成功（21.15秒）。Godot importと正規コンテンツのheadless起動、Python211ファイルの致命的lint、新規テストstyle/構文、project rules、REPO_MAP/追跡対象application図、E2E参照、diff --check成功。

最新版UPD（ae4636155b5e）を再取得し、Python対象エラー0・警告13・注意100。標準Python性能ガード（20000回/7sample/2000warmup）は13項目成功: 生成24枠約1.77ms、移動24体約0.50ms。GodotのFPS/全責務の証拠ではなく、Scene未接続の純粋数値は別の比較probeで検証した。Python E2Eカタログは12 covered/25 missing/1除外で、全機能移植や#204完了とは扱わない。

境界: 戦闘Scene/ターン進行、勝敗/経験値/保存、全スキル、回避/耐性/吸収/状態異常/反撃、AI推論/学習、演出、配布exportは未接続/未移植。魔法等は共通最終数値へのguard漏れだけを検証し、全魔法計算の移植を主張しない。実ウィンドウの手動操作/視認性・IME・exportは未検証。既存ユーザー変更と実セーブを保持し、今回分だけをローカルコミットする。push/PR/Issue完了操作はしない。次は#222の固定モブ周期移動/占有。

# 78. GDScript版の＋選択・装備制限/能力値補正

P1移行単位#220を実装した。種族plus/全装備のread-only読込をData、選択済み効果/装備whitelist/偶数丸めを純粋engine、基礎結果との結合と走査内キャッシュをapplication、補正前後と理由の表示を一覧へ分離した。既存の基礎値/習得スキル契約は補正前のまま残し、個体別modifiersへ補正後の能力値と＋追加スキルを返す。1走査内の同種族plusと装備I/Oを共用し、次の走査では外部変更を反映する。

選択IDの重複を除き、効果はJSON定義順で適用する。加算/各倍率の偶数丸め→許可装備の各能力倍率→最後に最低1制限というPython正本と同じ計算順。装備許可は装備側allowed_species_idsだけで、未記載/空は不可、重複装備定義は最後を採用する。計算時に選択数/段階/前提条件を修復しない点も現Python版と同じ。未知選択/装備IDや装備不可は理由付き無補正で元IDを残す。破損/不正型/非有限値/精度超過は補正結果を失敗にし、基礎値を完成値へ代用しない。有効な個体/AI/partyは保持し、計算結果を原本へ保存しない。

追加: `gdscript/engine/{monster_modifiers,stat_numbers}.gd`、`gdscript/application/monster_reconstruction.gd`、`gdscript/tests/run_modifiers_probe.gd` と各uid、`tests/test_gdscript_modifiers.py`。
更新: monster_progressionの数値変換共通化、content_repository、owned_roster、roster_view、基礎値テストのUI文言、README、GDScript README、FORMATS、CODEMAP、移植境界説明書、移行単位表。

検証（2026-10-04）: 新規20件を含む関連36件・2534サブテスト成功（37.55秒）。全8種族×3Lv×8選択パターン×7装備状態の1344比較、正負の丸め/近接境界、宣言順と逐次丸め、重複/未知ID/前提不一致/選択数超過、追加スキルの重複除去、許可/拒否/未記載whitelistと重複装備、旧形式/数値文字列/不正定義、入力と返却値の独立、走査内I/O共用と再走査の外部更新を実GodotとPythonで確認した。同種同Lvで異なる個体補正、補正前後の一覧と失敗理由、個体/AI/party/種族/装備原本のbyte保持を専用コピーで検証した。

初回の全テストはサンドボックスの一時ディレクトリへのアクセス拒否で検証できず、専用一時領域への権限付き再実行で解消した。新規テストの未使用import/行折返しもlintに合わせて修正した。最終全テスト828件・3099サブテスト成功（245.65秒、Python 3.14.7、pygame-ce 2.5.8、実Godot 4.7.2）。Godot import/正規コンテンツのheadless起動、Python210ファイルの致命的lint、新規テストstyle/構文、構造規約、REPO_MAP/追跡対象application図、E2E参照、diff --checkも成功。仕様更新後のルーター/優先度/補正31件・1450サブテストも実Godot指定で成功（24.62秒、skipなし）。

最新版UPD（ae4636155b5e）を再取得し、Python対象のエラー0・警告13・注意100を確認した。標準Python性能ガード（20000回/7sample/2000warmup）は13項目成功: 生成24枠約1.24ms、移動24体約0.45ms。いずれもGodotのFPS/全責務の証拠ではない。GodotのI/O回数と原本不変性は専用probeで別に確認した。Python E2Eカタログは12 covered/25 missing/1除外のままで、全機能移植や#204完了とは扱わない。

境界: ＋の特性/耐性と装備のskill_modifiers/fixed_bonus_damage/resistance_steps等の戦闘効果、装備/＋編集UI、戦闘進行、AIは今回未移植。実ウィンドウの視認性/手動操作、IME、配布exportは未検証。実セーブ/正規JSON/画像/既存ユーザー作業を保持し、今回分だけをローカルコミットする。push/PR/Issue完了操作は行わない。次は#221の通常攻撃・防御・会心の数値契約。

# 77. GDScript版のLv別基礎能力値・習得スキル

P1移行単位#219を実装した。種族stats/skillsのread-only読込をData、明示Lv行の整数化と順序付きlearnsetの重複除去を純粋engine、個体Lvとの結合をapplication、結果表示を既存の所有一覧へ分離した。1回の一覧走査では同種族の読込を共用し、再走査では読み直す。個体/AI/パーティIDや種族原本を再出力せず、基礎値だけが不正でも個体自体を除外/修復せず警告する。

Python正本のstats_atと同じ明示Lv1〜100表を利用する。成長式はサンプル生成時に展開されるため、Godot固有のformula形式や欠損行の補間は追加しない。schema省略、learnset省略、習得level省略、有限数値/整数文字列の整数化を扱う。不正型/bool/非有限値/未対応schema/安全な整数精度を超える値は拒否する。基礎値を完成能力値とは表示せず、＋/装備補正と＋由来の追加スキルが未反映であることを明記する。次は#220。

追加: `gdscript/engine/monster_progression.gd`、`gdscript/application/monster_progression.gd`、`gdscript/tests/run_progression_probe.gd` と各uid、`tests/test_gdscript_progression.py`。
更新: content_repository、owned_roster、roster_view、README、GDScript README、FORMATS、CODEMAP、移植境界説明書、移行単位表。

検証（2026-10-04）: 新規16テスト・1089サブテストを含む関連41件・1175サブテスト成功（52.58秒）。全8種族×全100Lv、Python成長式で生成した表/手動編集優先/新種族の表、全習得境界、旧形式、順序/重複、範囲外Lvの契約、不正/非有限/精度超過、unsafe IDとJSON破損、結果を変更しても入力不変、走査内キャッシュと次走査の読込、一覧の未補正表示、外部変更の再構築、個体/AI/原本byte保持を実Godotで確認した。

初回のテストは補正確認fixtureに存在しない＋/装備IDを使い1件失敗した。正規定義からIDを選び、実在装備と未習得の＋スキルへ修正して解消した。検証コマンドの初期パス指定不足、venvまで含んだlint、一時pycacheの書込先、追跡対象ではない図の既定出力指定も修正した。プロジェクトPython 209ファイルの致命的lint、新規テストのstyle/構文、構造規約、REPO_MAP/追跡対象application図、E2E参照、diff --checkは成功した。

最終全テスト808件・1654サブテスト成功（240.73秒、Python 3.14.7、pygame-ce 2.5.8、実Godot 4.7.2）。Godot importと正規コンテンツのheadless起動成功。最新UPD（ae4636155b5e）はPython対象にエラー0・警告13・注意100であり、GDScriptの責務の証拠とは区別する。Python E2Eカタログは12 covered/25 missing/1除外のままで、全面移植や#204完了とは扱わない。

標準Python性能ガード（20000回/7sample/2000warmup）は13項目成功: 生成24枠約1.20ms、移動24体約0.34ms。Godotの再構築速度/FPSや全責務の検証ではない。Godotの同種族I/O共用と再走査時の再読込は専用probeで別途検証した。

境界: ＋/装備補正、戦闘/AI/エディタは未移植。実ウィンドウの視認性/手動操作、IME、配布exportは未検証。実セーブ/正規JSON/画像/ユーザー作業を保持し、今回分だけをローカルコミットする。push/PR/Issue完了操作は行わない。

# 76. GDScript移行単位の起票と牧場の管理導線

GDScript移行をP1内の優先枠とし、GitHub CLIでgdscriptラベルと実装単位#218〜#223を作成した。P0は引き続き緊急復旧専用。#220←#219、#221←#220、#223←#222のblocked-byを登録し再取得して確認した。start_task.batはP0を先に探し、P1ではgdscript付きの候補を一般P1より先に返す。実GitHubの読み取りでも#218の選択を確認した。

最初の#218をローカル実装した。はじまりの街→牧場の既存データをそのまま使い、台帳(14,5)の手前(14,6)からEnter/Space/Eで所有一覧を開く。F6と同じ再走査・画面を共用し、一覧のEから現在編成、編成のPからプリセットへ進む。開くだけ/取消では保存せず、戻る時は現在地・向きを保持する。各管理画面では長押し移動・調べる・フィールド保存/読込を止める。新規未保存や破損stateは理由を表示し、自動修復しない。個体編集・AI変更やPython子アプリ起動は追加しない。

既存の実Godotキー入力probeにkey_down/key_up/tickを追加し、離したフレームも処理して離散入力と長押しを区別した。牧場専用9テスト・8サブテストは正規の街/牧場の入口、台帳の衝突、3調査キー、管理中の入力停止、明示編成保存/再起動、取消時のbyte不変、新規/破損時の拒否、再走査と不正個体フォルダの保持、Esc/F6からの探索再開を検証する。

追加: `docs/ワークフロー/GDScript移行実装単位.md`、`tests/test_gdscript_ranch.py`。
更新: field_application、run_party_probe、start_task.bat、test_task_priority、AGENTS、README、GDScript README、FORMATS、CODEMAP、ワークフロー/優先度方針/context、移植境界説明書、E2E期待値の境界注記。

検証（2026-10-04）: 新規導線/優先度の18テスト・13サブテスト成功（17.71秒）、既存編成/プリセット48テスト・45サブテスト成功（62.15秒）。最終全テスト792件・565サブテスト成功（172.41秒、Python 3.14.7、pygame-ce 2.5.8、実Godot 4.7.2）。Godot import/正規コンテンツのheadless起動、style/致命的lint・構文、構造規約、生成資料、E2E参照、diff --check成功。

最新UPD checker（ae4636155b5e）は既存Python対象にエラー0・警告13・注意100。標準性能ガード（20000回/7sample/2000warmup）は13項目成功: 生成24枠約0.85ms、移動24体約0.34ms。これらはGodotの全責務/FPSを検証するものではない。Python E2Eカタログは12 covered/25 missing/1除外のまま。今回のGodot牧場テストをPythonの子プロセス管理導線や#204の完了の代用にはしない。

実セーブ・正規data/assets・既存ユーザー作業は変更しない。実ウィンドウの視認性/手動操作、IME、配布exportは未検証。GitHubにはIssue/ラベル/依存関係を反映するが、コードは今回分だけのローカルコミットとしpush/PR/Issue完了操作はしない。未pushの#218はローカル実装済みとして再実装せず、次は#219（Lv別基礎能力値・習得スキル）へ進む。

# 75. Issue優先度をP0〜P4へ整理

P0を緊急対応専用として通常は空け、P1は優先対応、P2は普通/新規既定、P3は後回し、P4は将来/長期保留とする方針を追加。P0には緊急性・影響・復旧条件を求め、単に重要な設計/コンテキスト改善をP0にしない。AGENTS・両ワークフロー・CODEMAPから正本の方針を参照する。

ユーザー指示に基づきGitHub CLIでpriorityラベルをp0〜p4へ統一した。旧high/medium/lowはP1/P2/P3へ引き継ぎ、緊急障害ではないCODEMAPのIssue #22をcriticalからP1へ変更。P4を新設し、変更後の未完了P0が空であることを再取得して確認した。Issue本文/状態/完了チェックは変更しない。未分類Issueをタイトルだけで一括振分けしない。

start_task.batはP0 → P1 → P2 → P3 → P4の順で最古の候補を1件返す。同順位の依存関係や子Issueの実装済み状態は本文とコードで別に判断する。gh呼出しをcall経由にし、テスト専用gh.cmdでもバッチへ制御を返せるようにした。実GitHubへの読み取り実行でもP0空→P1のIssue #22選択を確認した。

追加: `docs/ワークフロー/Issue優先度方針.md`、`tests/test_task_priority.py`。
更新: AGENTS、CODEMAP、context/WORKFLOW、ワークフロー、tools/README、start_task.bat。

検証: 関連11テスト・5サブテスト成功。実cmd.exeと専用ghで5段階の選択順、下位問い合わせ停止、最初の番号だけの選択、該当なし/認証失敗/表示失敗の終了コードを検証。テストからGitHubへの書込みは行わない。最終全テスト781件・557サブテスト成功（176.55秒、Python 3.14.7、pygame-ce 2.5.8、Godot 4.7.2）。style/致命的lint・構文、構造規約、生成資料、E2E参照、diff --check成功。

GitHubラベルと#22の優先度は反映済み。文書/ツール変更はローカルコミットのみでpush/PRは行わない。ゲームruntime・保存形式・実セーブは変更せず、既存のユーザー作業も保持する。

# 74. GDScript版のパーティプリセット

F6 → E → P/プリセットボタンから新規保存・一覧・下書きへの読込を追加。名前欄のEnterで追加保存、一覧のEnterで読込、F5で再走査、Esc/F6で下書きを保持して編成へ戻る。Tab/Shift+Tab、Home/End/Page、クリックと縦スクロールに対応し、フィールド操作を停止する。

Python互換のschema/name/members形式で、同名は `_2` 等の別ファイルとして追加し、既存プリセットを上書き/削除しない。ファイル数に上限を設けず、日本語表示名と安全なASCIIファイル名を使う。読込は下書きだけを置換し、現在パーティの反映は編成画面の明示保存。新規プリセットを明示保存した後に編成をキャンセルしても、そのプリセットは残す。

純粋な形式/欠損枠契約、ファイルI/O、検証/下書き適用、入力/表示/signalを分離。保存/読込時に所有個体を再走査し、消失/読込不可IDはnullと注意へ変換、重複した既知ID・不正型・5枠以上・破損JSON/未対応schemaは適用せず元の下書きを保持する。プリセット操作だけではstate/個体/AI/items/metaを変更しない。

追加: `gdscript/{engine/party_preset_contract.gd,data/party_preset_store.gd,application/party_presets.gd,ui/party_preset_view.gd}` と各uid、`tests/test_gdscript_presets.py`。
更新: field_application、party_editor、party_selection、party_view、run_party_probe、README、GDScript README、FORMATS、CODEMAP、移植境界説明書。

検証: 最終の新規23テスト・28サブテスト成功（29.42秒、実Godot 4.7.2）。キー/クリックの新規保存・選択読込・明示state保存、Unicode文字入力/名前編集/フォーカス、121ファイルのスクロール、同名追加とPython PartyStore互換、再起動、欠損枠、破損/外部変更、実Windows読込ロック、取消/失敗時の下書きと既存ファイルの不変を専用コピーで確認した。既存編成25テスト・17サブテストも成功。

初回検証のWindows fixtureパスと一覧ソート後のクリック位置を修正した。一覧失敗時の初期フォーカスを補い、partiesがフォルダではなくファイルである場合のDirAccess例外を検出して、明示的な型/オープン失敗ガードへ修正した。既存ファイルを残したまま理由を表示する回帰テストも成功した。

最終全テスト774件・552サブテスト成功（147.90秒、Python 3.14.7、pygame-ce 2.5.8、Godot 4.7.2）。Godot import/正規コンテンツのheadless起動、style/致命的lint・構文、構造規約、生成資料、E2E参照、diff --check成功。実セーブ・正規data/assets・Python runtimeは変更しない。

最新UPD checker（ae4636155b5e）は既存Python対象にエラー0・警告13・注意100。標準性能ガード（20000回/7sample/2000warmup）13項目成功: 生成24枠約1.61ms、移動24体約0.53ms。これらはGDScriptの性能/全責務の証拠ではない。Python E2Eカタログは12 covered/25 missing/1除外のままで、全面移植や#204完了とは扱わない。

境界: プリセット更新/削除、牧場導線、個体編集、戦闘/AI、外部取得/模擬戦は未移植。実IME/ウィンドウの視認性・手動操作、配布exportは未検証。並行writerの排他は未対応。今回分だけのローカルコミットとし、GitHub push/PR/Issue完了操作は行わない。

# 73. GDScript版の現在パーティ編成

F6一覧のE/ボタンから4枠の編成画面を開けるようにした。左右のリストで枠と所有個体を選択して追加/解除/配置変更し、Ctrl+S/保存ボタンで反映、Esc/F6/キャンセルで下書きを破棄する。↑↓、Home/End、PageUp/Down、Tab/Shift+Tabとクリックに対応。編成中はフィールド移動/調べる/F5/F9を停止する。

下書きと選択規則は純粋なparty_selection、所有と再検証はparty_editor、入力/表示/signalはparty_view、Sceneは接続に分離。保存はstate.current_partyだけを4枠のID/null配列へ更新し、保存済み位置と他のキー、既存個体/AI/items/meta/プリセットを保持する。未保存の現在地はそのまま残し、次のF5でも新しい編成を保持する。空編成を許可し、個体自体は削除しない。

同一個体の重複を拒否し、保存直前に個体フォルダを再走査する。欠損/重複の既存枠は明示解除で修正、不正型/5枠以上は切り捨てず開く時点で拒否。外部state更新・破損JSON・Windows置換ロック等は上書きを拒否して下書きを残す。変更なし/キャンセルはstateのbyteも維持する。digest確認は並行writerの完全な排他ではない。

追加: `gdscript/{engine/party_selection.gd,application/party_editor.gd,ui/party_view.gd,tests/run_party_probe.gd}` と各uid、`tests/test_gdscript_party.py`。
更新: field_application、roster_view、README、GDScript README、FORMATS、CODEMAP、移植境界説明書。

検証: 最終の編成テスト25件・17サブテスト成功（43.01秒、実Godot 4.7.2）。キーのみ/クリックの追加・解除・保存、Tab巡回とEnter保存、取消のbyte保持、Python形式/日本語ID/未知キー、再起動、123体一覧、外部更新/破損、選択個体のAI消失、未選択の不正個体、欠損/重複の明示解除、不正型/枠溢れ、新規保存前の拒否、Windowsの実ファイル置換ロック、位置保存との連携を専用コピーで検証した。

初回キー検証ではHome/Endのリスト選択が変わらず9件失敗した。UI側へHome/End/PageUp/Downの選択移動を追加して解消した。最終レビューでは省略可能なLvがUIで直接参照されていたため、契約と同じLv1の既定値へ合わせ、旧形式の回帰テストを追加した。実セーブ/正規コンテンツ/Python runtimeは変更しない。

最終全テスト751件・524サブテスト成功（159.13秒、Python 3.14.7、pygame-ce 2.5.8、Godot 4.7.2）。Godot 4領域は旧形式の追加前に62件・489サブテスト成功し、追加後は編成25件の集中テストと全体で再検証した。最初の個体一覧の集中テストでは既存pytest cacheの警告が出たため、その後の検証ではcacheproviderを無効化し、明示的な一時ディレクトリを使った。

最新UPD checker（ae4636155b5e）は既存Python対象にエラー0・警告13・注意100。標準性能ガード（20000回/7sample/2000warmup）13項目成功: 生成24枠約3.84ms、移動24体約0.61ms。これらはGDScriptの走査速度/FPSや全責務の検証ではない。Godot import/正規コンテンツのheadless起動、lint/構文、構造規約、生成資料、E2E参照、diff --check成功。最初のlint globはPowerShellから未展開で渡されたため、rgで列挙した引数へ修正した。

境界: プリセット、牧場導線、個体編集、戦闘/AI、外部取得/模擬戦は引き続き未移植。実ウィンドウの視認性/手動操作、配布exportは未検証。Python E2Eカタログの全面移植や#204の完了とは扱わない。今回分だけのローカルコミットとし、GitHub push/PR/Issue完了操作は行わない。

# 72. GDScript版の初期個体／所有一覧

新規stateの初回F5で主人公・ボールスライムのLv1個体と初期パーティを生成。既存と同じmonster.json/ai.jsonを使い、初期AI辞書はPython default_aiと一致する。個体の2ファイルは固有の一時フォルダへ書いてから公開し、state保存が後で失敗した場合は再試行で公開済み初期個体を再利用する。既存stateへ仲間を勝手に追加しない。

F6で全保有個体と先頭4パーティ枠を読み取り専用表示。名前・種族・Lv・＋数・装備ID・AIプロファイル/作戦/戦闘経験を確認でき、縦スクロールバー/ホイール・↑↓・PageUp/Down・Home/End、F6/Escで閉じる操作に対応。一覧中の移動/調べる/F5/F9は停止。個体数にプログラム上の上限を設けず、日本語IDと未知JSONキーも読込/保持する。欠損/破損・不正ID/Lv・未知種族・未対応schemaは注意を表示し、元ファイル/欠損パーティIDを削除/修復しない。

追加: `gdscript/{engine/monster_record_contract.gd,data/monster_store.gd,application/owned_roster.gd,ui/roster_view.gd,tests/run_roster_probe.gd}` と各uid、`tests/test_gdscript_roster.py`。
更新: field_application、field_persistence、field_save_store、README、FORMATS、CODEMAP、移植境界説明書。

検証: 新規16テスト・78サブテストを含め、最終全テスト726件・507サブテスト成功（116.62秒、Python 3.14.7、pygame-ce 2.5.8、Godot 4.7.2）。AI初期値35条件、7種族×5Lvの個体JSON契約、初期パーティ/再起動/再保存、既存の日本語ID・学習済みAI/未知キー/party順序の不変、120体スクロールとmodal入力停止、実ホイール・上方向キー、不正個体11条件、既存ID/パス拒否8条件、state置換失敗後の再試行、欠損種族/不正孤立個体の初回保存拒否を検証した。以前の空セーブへ仲間を追加しないことも確認。

headlessの物理Windowが64pxだったため、当初のホイールprobeはゲーム座標を画面外へ送っていた。Viewportの実変換とマウス入場通知で本番入力経路に合わせて修正し、UIのスクロール処理を代替しない。初期fixtureのID引数重複と診断用assert整形も修正した。Godotインポート/正規コンテンツのheadless起動、lint/構文、構造規約、生成資料、E2E参照、diff --check成功。

最新UPD checker（ae4636155b5e）は既存Python対象にエラー0・警告13・注意100。既存Python性能ガードは標準20000回/7sample/2000warmupで13項目成功（生成24枠約2.11ms、移動24体約0.67ms）。初回性能実行のimportエラーはPYTHONPATH=srcで解消した。これらはGDScriptのFPS/ファイル走査速度の実測や、Python E2Eカタログの全面移植ではない。

境界: 能力値/スキル/＋効果/装備補正、AI判断/学習/リセット、編成変更、牧場/外部個体取得/模擬戦は未移植。実ウィンドウでの視認性・手動操作、配布export、並行writer排他は未検証/未対応。保存先はPython版と分離したままで、既存個体/AI/items/parties/metaの書換えなし。正規data/assetsとPython runtimeは変更なし。ローカルコミットのみでGitHub push/PR/Issue完了操作は行わない。

# 71. GDScript版のフィールド保存／復元

F5で現在マップ・マス座標・向きを保存、F9で読込、別プロセスでの次回起動時にも復元するようにした。既定保存先はPython版と分離した `user://savedata/default/`。環境変数で名前付きフォルダを選択でき、初回F5でstate/meta/itemsと空のmonsters/partiesを作る。既存stateの位置以外のキーを引き継ぎ、個体/AI/items/プリセット/metaの既存ファイルは書き換えない。向きのない旧形式は正面で復元する。

純粋なfield_save_contract、JSON/名前付き保存I/O、field_persistence調停、Sceneの適用を分離。破損JSON、未対応schema、欠損マップや壁/看板/NPC上などの不正位置は読込・上書きを拒否。変更digestを確認し、同一フォルダの固有一時ファイルから置換する。置換失敗時に以前のstateを削除するfallbackは使わない。

追加: `gdscript/{engine/field_save_contract.gd,data/json_documents.gd,data/field_save_store.gd,application/field_persistence.gd,tests/run_save_probe.gd}` と各uid、`tests/test_gdscript_save.py`。
更新: field_application、bootstrapテストの保存先隔離、README、FORMATS、CODEMAP、移植境界説明書。

検証: Godot 4.7.2の実Scene/入力・別プロセス再起動、Python StateStoreでの生成形式読込、2つの名前付きセーブの独立、未知キーと所有ファイルの不変、破損/不正位置10条件、名前19条件、digest不一致、Windows実ファイルロックでの保存失敗と固有一時ファイル回収を検証。関連22テスト・394サブテスト成功。旧形式のF9復元方向の確認も加えた最終全テスト710件・429サブテスト成功（67.56秒、Python 3.14.7、pygame-ce 2.5.8）。初回全体実行はbasetempの親未作成で133 setupエラー、専用親フォルダ作成後の再実行で解消した。

Godotインポート/正規コンテンツでのheadless起動、style/致命的lint、構文、構造規約、生成資料、E2Eカタログ参照、diff --check成功。最新UPD checker（ae4636155b5e）は既存Python対象にエラー0・警告13・注意100。既存Python性能ガードは標準試行数で13項目すべて成功。カタログはPython版の12 covered/25 missing/1除外のまま、Godot全機能の移植済みとは扱わない。

境界: フィールド保存のみ。初期個体生成、AI/戦闘/牧場、セーブ選択UI/コピー/インポートは未移植。既存Pythonセーブの正本は使わずコピーで試す。複数ファイルの初回作成一括原子性、複数writer排他、数値精度外のMOD値の無損失往復は保証しない。正規data/assetsとPython runtimeは変更なし。実ウィンドウ手動操作・配布export・Godot FPSは未検証。GitHub push/PR/Issue完了操作は行わない。

# 70. GDScript版のフィールド移植を開始

ユーザーのGDScript開始指示により、独立した `gdscript/project.godot` とフィールドSceneを追加。はじまりの街から正規の6マップ/ブロック/キャラクターPNGをread-onlyで読み、長押しマス移動、地形/固定モブ/看板/岩の衝突、step/interactの移動ポイント、メッセージを接続した。engineの純粋な空間判定、data読込、sessionの一時状態、applicationの調停、uiの入力/描画を分離。#111のpython/unity開始用READMEも追加したが、既存Pythonファイルの大移動は行わない。

追加: `gdscript/` のGodot設定/Scene/engine/data/application/ui/tests/README、`python/README.md`、`unity/README.md`、`tests/test_gdscript_bootstrap.py`。
更新: README、CODEMAP、移植境界説明書。

検証: Godot 4.7.2の実エンジンで13テスト・比較365サブテスト成功。衝突優先度/6マップの移動/イベント/前方マス/通行/軸経路のPython契約一致、追加JSON読込、path traversal拒否、正本と専用セーブの不変、押下/リピート/解放、実Sceneの移動/step/interact接続を検証。Godotインポートと正規データでのheadless起動成功。最終全テスト701件・サブテスト400件成功（64.37秒）。最新UPD checkerは既存Python対象にエラー0・警告13・注意100で成功。Godot未指定の環境では実エンジンテストは理由付きskipで、成功とは扱わない。

境界: source checkout専用の初回試作。戦闘/野生敵/AI/固定モブ徘徊や会話/暗号取得/牧場/セーブ/エディタ/ランチャー/exportは未移植。未対応イベントは明示し副作用なし。Python runtime・保存形式・正規data/assetsは変更なし。実ウィンドウでの視認性/手動操作と配布物は未検証。#111や移行EpicをGitHubで完了扱いにしない。

最終補助検証: 新規テストのstyle lintと構文、全体の致命的lint、構造規約、生成repo map/class diagram、E2Eカタログ参照、diff --check成功。既存Python性能ガードは標準試行数で13項目すべて成功。これはGodotのFPS/描画性能の実測ではない。

# 69. 起動・フィールド・イベント・save/load E2E（Issue #202）

本番PlayerランチャーへSDLのクリック/文字入力を送り、新規作成・名前選択・別名保存を通した後、選択先の本番Store/runtimeを組み直すsource journeyを追加。街の開始地点/初期個体、異なるマップのセーブ復元と別セーブ不変、コピー後の独立性、移動方向の実画像/描画位置、5種類の衝突、長押し、正規の街端/新緑の森の岩とactivation差、まるの会話デッキ/正面停止、湧き場の仮想キー・取得・誤答/取消・保存/reloadを検証。カタログP01～P12に実テストを登録し、対応済み12・未対応25・意図的除外1となった。

追加: `tests/e2e/{launcher_driver,render_observation,test_field_journeys}.py`。
更新: E2Eのconftest/runtime_driver/worker/observations/test_harness/README、E2E_EXPECTATIONS、CODEMAP。

検証: 新journey16件と基盤11件、計27件成功。最終版27件を2回連続成功（新規開始・暗号取得などはテスト内でも同seedを反復）。最終全テスト688件・サブテスト35件成功。lint、構造規約、生成資料、カタログ参照、diff --check成功。利用者セーブを指定した親環境でも、ランチャーから専用セーブへ切り替わり、sentinel/別セーブ/コピー元fixtureが不変なことを検証。

境界: 私有プロジェクトに正規wrapperをコピーして任意legacy-save検索を隔離。外部起動要求を受け取った先のcomposition rootを使うが、OSの実プロセス起動やwrapper実行の証拠ではない。headlessの本番renderer/画像選択とmouse adapterを使うが、実画面の視認性・マウス操作・配布EXE・ピクセル完全一致は未検証。ゲーム処理と保存形式は変更なし。詳細な戦闘journeyは #203、管理アプリは #204、CI/quality専用統合は #205。

# 68. 決定的Source E2E基盤（Issue #201）

本番KadokaQuest・入力アダプター・runtime・loader/Storeを使う別プロセスのharnessを追加。ゲームimport前にセーブ/インポート先を専用領域へ切り替え、headless SDL・seed付きgame RNG・手動clock・別乱数列のUUID・固定日時を設定する。sleepやゲーム結果の代替実装は使わない。保存JSONと状態checkpointを観測し、Store/セッション/runtimeを作り直すreloadを用意。初期セーブfixtureはコピーして使い、新規獲得時に初期個体のID列を再発行しない。

追加: `tests/e2e/{__init__,conftest,harness,worker,scenario_clock,runtime_driver,observations,test_harness}.py`。
更新: `tests/e2e/README.md`、E2E_EXPECTATIONS、CODEMAP。

検証: 最終基盤テスト11件を3回連続で成功（各回の同一seed反復と戦闘反復も一致）。別seedで本番の野生配置が変化すること、固定時間で長押し移動/オート戦闘/ログ再生が進むこと、親のセーブ先を使わないこと、コピー元fixtureのJSONが不変なこと、新規獲得・reload・エラーの操作位置を検証。最終全テスト672件・サブテスト35件成功（Python 3.14.7、pygame-ce 2.5.8）。構造規約・生成資料・lint・カタログ検査も成功。ゲームruntimeと保存形式の変更なし。

未検証: 実ウィンドウの描画/マウス、配布EXE、ランチャーのクリック操作、複数アプリの牧場フロー。管理アプリ起動は未対応として明示的に失敗させ、harness専用のsimulation hookは追加しない。主要37フローは引き続きmissingで、基盤テストをcoveredへ混同しない。次は #202～#204、CI/quality専用統合は #205。

# 67. E2E期待動作カタログ（Issue #200）

Player/Developerの主要37シナリオにGiven・When・Then・保存/reload・対応E2E・未対応理由を記録。現時点のE2E対応済みは0、未対応37、装飾のみの除外1。既存unit/integration/smokeをE2Eと混同しない。カタログの形式とtests/e2e内の定義参照を静的チェックし、対応テストの削除時は実効missingとして失敗させる。新機能時の更新手順と専用領域を追加。harness本体は #201。

追加: `docs/testing/E2E_EXPECTATIONS.md`、`tests/e2e/README.md`、`tools/e2e-catalog/script/check_e2e_catalog.py`、`tests/test_e2e_catalog.py`。
更新: WORKFLOW、CODEMAP、tools/README。

検証: 関連21件、最終全テスト661件・サブテスト35件成功。テスト削除/定義欠落/不正参照/不完全な期待値を検証。Python 3.10のCLIとPowerShellの日本語パイプ出力、構造規約・生成資料・lint成功。共有pytest一時領域でのWinError 5は専用領域へ切替後に解消。チェック成功はE2E実行成功を意味しない。ゲームruntime・保存形式の変更なし。

# 66. 個体管理のAI学習傾向表示（Issue #184）

牧場と開発用個体管理の個体情報に5項目の傾向ゲージと日本語段階を追加。未学習・データ不足を空ゲージで明示し、個体切替・AIリセット・F5/フォーカス復帰での再読込に追従する。両画面は同じパネルを使用し、スキルや状況の生テーブルを表示しない。

追加: `ui/ai_tendency_panel.py`、`tests/test_ai_tendency_ui.py`。
更新: ranch_manager、manage（種族一覧の表示/操作位置を調整）、両AI機能説明書、CODEMAP、生成REPO_MAP。

検証: 関連42件、全テスト644件・サブテスト35件成功。両画面ループのイベントによる個体切替・F5・フォーカス復帰・リセットを検証し、未学習/学習済みの描画画像を目視確認。構造規約・生成資料・lint成功。最新UPDエラー0（警告13・注意100）。既存開発用Managerは追加委譲メソッドで13メソッドとなりUPD401警告の対象。実ウィンドウでの手動操作は未確認。

# 65. AI学習傾向サマリ（Issue #183）

既存の学習データから攻撃性・回復優先・MP節約・瀕死時防御・格上への強気を計算する読み取り専用APIを追加。未学習/データ不足と有効な中立値を区別し、MOD定義による分類、状況別記録、AIリセットに対応する。ゲージは選択確率ではなく学習スコアの相対表示。学習アルゴリズム・保存形式は変更しない。画面組込みは #184。

追加: `core/ai_tendencies.py`、`tests/test_ai_tendencies.py`、AI学習傾向サマリ機能説明書。
更新: `apps/ai_inspector.py`、個体AI可視化説明書、CODEMAP、生成REPO_MAP。

検証: 関連142件・サブテスト7件、全テスト638件・サブテスト35件成功。構造規約・生成資料・lint成功。最新UPDエラー0（警告12・注意100）。UI組込みと実画面検証は次Issueの範囲。

# 64. マップ設定による野生ポップ抽選（Issue #153）

ポップ率を生成候補1枠ごとに判定し、種族の小数相対重み、Lv、AIの順に抽選。0%は生成なし。通常域は生成時Lvを戦闘へ引継ぎ、メタル域は従来の遭遇時パーティ連動Lvを優先する。個体未指定の野生戦開始も同じ抽選を使用する。

追加: `kadoka_engine/wild_spawn.py`、`tests/test_wild_spawn_runtime.py`、野生ポップ抽選機能説明書。
更新: hidden_enemy_controller、core/spawn_levels、apps/game、エディタの案内、性能計測（生成24枠）、関連仕様/FORMATS/CODEMAP/生成REPO_MAP。

検証: 関連124件、全テスト607件・サブテスト35件成功。エディタ保存→ゲーム再読込で0/100%・小数重み・Lv・AIを確認。ゲーム/エディタのヘッドレス起動終了、Python 3.10抽選スモーク、構文/構造/生成資料整合性成功。最新UPDエラー0（警告12・注意100）。
性能は標準回数で全項目基準内。生成24枠は約1.22ms（上限5ms）、既存移動24体は約0.41ms（上限1ms）。過去の移動性能超過に対するコード修正ではなく、今回の環境での測定結果。閾値は変更していない。旧一時venvでpygame.versionが欠落していたため、新規の検証専用venvを使用した。実ウィンドウの手動プレイは未確認。

# 63. マップのポップ率・AI比率編集（Issue #152）

出現設定に「マップ全体 / AI」タブを追加。0〜100%のポップ率、random/chase/idleの相対重み、AI継承切替、比率表示に対応。両タブの未反映入力を一括検証して保存し、不正値による部分反映を防ぐ。旧マップの省略キーと個別AI/MOD項目は保持する。

追加: `kadoka_engine/spawn_controls.py`、`ui/map_spawn_form.py`、`tests/test_map_spawn_controls.py`、マップポップ率AI編集機能説明書。
更新: map_editor、spawn_table_dialog、出現テーブル説明書、FORMATS、CODEMAP、生成REPO_MAP。
ゲーム内のポップ率判定・小数種族重み抽選は #153。既存のフィールド移動性能超過は今回未変更・未解決。

検証: 関連117件、全テスト577件・サブテスト35件成功（Python 3.14）。Python 3.10で設定処理スモーク成功。最新UPDエラー0（警告12・注意100）、構文/未定義名・構造・生成索引/図の整合性成功。ヘッドレスのイベント操作、描画画像、エディタ起動終了スモークを確認。実ウィンドウの手操作は未確認。

# 62. マップ出現テーブル編集UI（Issue #151）

従来の出現Lv画面を、候補一覧と種族一覧に独立スクロールバーを持つ編集画面へ変更。種族・重み・Lv範囲を編集し、相対比率を表示。重複種族も1行ずつ編集/削除し、フラグやMOD独自項目を保持する。

未反映入力の保護、Ctrl+S、反映/保存前の入力検証を追加。旧JSONの既定値と新規入力の初期値を区別する。ポップ率/AI編集UIとゲームの抽選処理は後続Issueで、今回変更しない。

追加: `kadoka_engine/spawn_table.py`、`ui/spawn_table_dialog.py`、`tests/test_spawn_table_editor.py`、野生出現テーブル編集機能説明書。
更新: `apps/map_editor.py`、Lv範囲/出現契約説明書、FORMATS、CODEMAP、生成REPO_MAP。

検証: 関連82件、全テスト558件・サブテスト35件成功。最新UPDエラー0（警告12・注意98）、構文/未定義名チェック、構造と生成索引/図の整合性成功。ヘッドレスのイベント操作・描画画像確認・エディタ起動終了スモークを実施。実ウィンドウの手操作は未確認。前回からのフィールド移動性能超過は今回変更しておらず未解決。

# 61. 野生ポップ設定のデータ契約（Issue #150）

pop_rate（0〜100%）、種族の相対重み、Lv範囲、移動AI比率を検証する純粋関数と、旧マップの既定値を非破壊で補完する関数を追加。DataValidatorへ接続し、不正な数値・全0重み・未知AI・初期専用種族を検出する。

追加: `kadoka_engine/spawn_settings.py`、`tests/test_spawn_settings.py`、野生ポップ設定データ契約機能説明書。
更新: `data_validator.py`、`field_ai.py`、FORMATS、CODEMAP、生成REPO_MAP。

UIとpop_rateのゲーム反映、小数の種族重みによる抽選は後続Issue。既存マップ原本・実セーブ・ゲーム中の抽選処理は変更しない。前回の移動性能超過は今回の対象外で未解決。

検証: 関連86件、全テスト538件・サブテスト35件成功（Python 3.14）。Python 3.10で契約処理・同梱データ検証成功。最新UPDエラー0（警告12・注意97）、構造チェック・生成索引/図の整合性成功。GUI操作・出現率のゲーム反映は対象外。

# 60. 野生接触から戦闘・フィールド復帰（Issue #149）

接触判定は実際の戦闘開始成功を返し、仲間なし・フィールド外・既存戦闘ありの場合は開始しない。戦闘生成成功後に接触個体を除去することで、生成失敗時の個体消失を防ぐ。起動時の案内を可視モンスターの仕様へ合わせた。

追加: `tests/test_wild_encounter_flow.py`、野生接触戦闘フロー機能説明書。
更新: `apps/game.py`、既存地域/レベルテストのフィールドモード指定、CODEMAP、生成REPO_MAP。
正規コマンド経路で種族/Lvの引継ぎ、勝利・敗北・逃走・スカウト・敵逃走と復帰を検証。通常域/メタル域のレベル決定時点、残数3体未満の再生成、教会復活は従来仕様を維持。実画面操作は未検証。

検証: 全テスト484件・サブテスト35件成功、UPDエラー0、索引整合性成功。性能は今回未変更の `wild-movement-24` が標準回数での再測定でも1.43ms（基準1ms）となり未解決。AI抽選は再測定で基準内、戦闘/フィールドのルーティングは基準内。性能閾値は変更していない。

# 59. 複数追跡個体の経路分散（Issue #148）

次3マスの短期予約と1280msの混雑履歴を参照し、近傍の別経路を選ぶ。予約・混雑は追加コストとし、一本道では同じ経路を共有する。現在のキャラクター位置への進入は禁止したまま。複数追跡の迂回中は、視認済み地点の短期記憶を最大4秒維持する。探索範囲とノード数を制限し、広域探索は行わない。

追加: `kadoka_engine/chase_traffic.py`、`tests/test_chase_traffic.py`、追跡経路分散機能説明書。
更新: 野生個体コントローラー、性能チェック、FORMATS、CODEMAP、AI移動説明書、生成REPO_MAP。
初回視認条件、random/idle、戦闘AI、セーブ形式は変更しない。接触から戦闘への全体確認は次の #149。

# 58. 野生個体のAI別移動（Issue #147）

出現時に割り当てたAIに応じてrandomの徘徊、idleの静止、chaseの視認時追跡を切り替える。視認と追跡モードを分離し、追跡型だけを加速する。見失うと通常周期へ戻り、全種類で地形・主人公・固定モブ・他個体の占有を守る。旧個体のAI省略時は従来挙動を維持する。

追加: `tests/test_field_ai_movement.py`、野生個体AI移動機能説明書。
更新: 野生個体コントローラー、既存ゲーム移動テスト、24体移動の性能計測、FORMATS、CODEMAP、AI割当説明書。
複数追跡個体の経路分散は #148 以降。戦闘AI・セーブ・固定モブの行動は変更しない。

# 57. 野生個体の移動AI割当（Issue #146）

出現時にrandom/chase/idleを相対重みで抽選し、個体のaiへ保持する。出現項目→マップ→種族→既定値の順に設定を選び、不正値は次へ戻す。同種族でのAI混在、seed再現性、移動後の保持を検証する。スライム・おばけ・メタルスライムに編集可能な種族初期値を追加した。

追加: `kadoka_engine/field_ai.py`、`tests/test_field_ai_assignment.py`、野生個体AI割当機能説明書。
更新: 野生個体コントローラー、フィールド読込・ゲーム接続、種族JSON、出現率テスト、性能チェック、FORMATS、CODEMAP、生成REPO_MAP。
今回は割当のみ。AI別の実際の移動切替は #147、エディタの入力UIは #39 の後続作業。戦闘AI・実セーブ・既存の移動条件は変更しない。

# 56. 野生モンスターのフィールド可視化（Issue #145）

野生個体を種族・向きごとの既存field spriteで表示する。出現時と移動時に向きを記録し、カメラ・画面端のクリップ・欠損画像の代替表示に対応した。個体移動AI・出現率・占有・戦闘開始条件は変更しない。

追加: `tests/test_wild_enemy_rendering.py`、野生モンスター可視化機能説明書。
更新: `ui/field_renderer.py`、`kadoka_engine/hidden_enemy_controller.py`、README、FORMATS、CODEMAP、フィールドアクター説明書。
移動AI割当と追跡分散は #146以降、地域追加・接続は別作業。

# 55. メタルエリアのパーティ連動Lv（Issue #144）

`encounter_context: metal_area` の野生戦生成で、換算Lvの2位±3を使用する。まる・かどかはLv-10（最低1）、上位差20以上または1体編成は1位±5、出現Lvは1〜100。計算は純粋関数へ分離し、遭遇ごとの最新編成を使用する。通常マップの固定Lv・所有個体・模擬戦は変更しない。

追加: `core/spawn_levels.py`、`tests/test_spawn_levels.py`、メタルエリア動的レベル機能説明書。
更新: 野生個体生成、性能チェック、FORMATS、CODEMAP、出現モンスターレベル範囲説明書、生成REPO_MAP。
地域自体の追加・接続（#141）は今回に含めない。

# 54. メタルスライム専用撃破経験値（Issue #143）

種族JSONの係数で `300 + Lv×35 + floor(Lv²/10)` を計算する。通常敵の経験値と独立させ、通常・旧互換経路で同じ純粋計算を利用する。メタルのみは基礎点8なし、通常敵は従来の式、混成は両者を合計する。生存・逃走個体を除外し、非勝利・模擬戦への誤付与を防ぐ。味方の成長速度・保存形式は変更しない。

追加: `core/battle_rewards.py`、`tests/test_battle_rewards.py`、種族別撃破経験値機能説明書。
更新: メタル種族定義、Combatant、戦闘読込・報酬処理、性能チェック、FORMATS、CODEMAP、戦闘セッション・敵逃走説明書、生成REPO_MAP。
中盤地域追加（#141）・メタル域の動的レベル（#144）は別作業。

# 53. メタルスライムの地域別逃走（Issue #142）

通常域15%・メタル域60%のターン逃走率を種族JSONへ追加し、マップの出現コンテキストで切り替える。敵の行動枠で判定し、味方と模擬戦は対象外。逃走個体は対象選択・状態異常・経験値から除外し、全員逃走は撃破勝利と区別する。画面には逃走済みと表示する。

追加: `tests/test_enemy_flee.py`、敵の地域別逃走機能説明書。
更新: メタルスライム種族定義、戦闘エンジン・状態・読込・野生戦開始・経験値処理・戦闘描画、性能チェック、FORMATS、CODEMAP、戦闘責務分離機能説明書、生成REPO_MAP。
中盤地域追加・接続（#141）と専用経験値式（#143）、動的レベル（#144）は本変更に含めない。

# 52. 中盤用のメタル1%マッププリセット（Issue #141 継続）

エディタから新規作成できる中盤通常域のひな形を追加した。出現weightはスライム60・おばけ39・メタルスライム1で、種族抽選ごとのメタル出現率が1%になる。Lv20〜25は編集用の初期値。3マス幅の道を設け、既存マップや接続は変更しない。

確率・実際の抽選へのweight受け渡し・エディタの新規作成と既存データの保全をテストする。プレイ可能な中盤地域の追加・接続は未実施で、Issue #141全体は引き続き未完了。保存形式・ランタイムコードの変更はない。

追加: `data/map_presets/midgame_field.json`。
更新: `tests/test_metal_spawn_tables.py`、マッププリセット機能説明書、`docs/CODEMAP.md`、`docs/ver.md`。

# 51. 序盤のメタルスライム出現を撤去（Issue #141 前半）

はじまりの森と新緑の森からメタルスライムの出現行だけを削除した。スライム・おばけの相対weightとレベル範囲は変更しない。序盤6マップの出現表・進行フラグを変えた候補一覧・森の再配置をテストする。

現行データには中盤マップがないため、通常域で1%出現させる対象は未設定。中盤地域の追加または中盤用プリセットの準備方針を確認してから続ける。Issue #141全体はまだ完了していない。逃走率・専用経験値・メタルエリアは後続Issueで扱う。

更新: `data/maps/{greenwood,fresh_forest}/map.json`、`docs/ver.md`。
追加: `tests/test_metal_spawn_tables.py`。

# 50. 未使用の互換propertyを削除（Issue #140）

呼出側の移行後に未使用となった9個の `KadokaQuest` propertyだけを削除した。使用中の25個と旧処理APIは維持する。実装・ツール・起動スクリプトへの削除名参照の再混入検査を追加し、各説明書に所有者側の置換先を記載した。外部Python拡張が削除名を使う場合は移行が必要だが、JSON形式・UI・ゲーム規則は変更しない。

更新: `src/kadoka_quest/apps/game.py`、`tests/test_session_ownership.py`、状態所有者棚卸し、戦闘・パーティ選択・画像取得・暗号入力・管理プロセスの説明書、生成REPO_MAP、`docs/ver.md`。

# 49. 描画・コマンド・評価側のSession直参照（Issue #139）

戦闘・フィールド・暗号画面とメインループ、評価ツールを互換propertyからSession参照へ移行。画像と代替表示情報は専用Providerへ渡し、戦闘コマンドの正規経路は `ProgressSession` を参照する。旧外部caller向けの互換経路は残した。

画面8ケースの旧実装とのピクセル一致を確認し、Sessionだけで描画する回帰テストを追加。評価ツールが帰還後の消去済み戦闘を読む不具合も修正した。UI・保存形式・ゲーム規則は変更していない。

追加: `tests/test_session_renderers.py`。
更新: `src/kadoka_quest/` の描画・画像Provider・ゲームループ・戦闘コマンド・評価ツール、関連テスト、性能チェックの通常経路、CODEMAP、状態所有者棚卸し、戦闘セッション説明書、生成REPO_MAP、`docs/ver.md`。

# 48. 進行・フィールド状態をSessionへ移譲（Issue #138）

`ProgressSession` に進行辞書、`FieldSession` にマップエンジン・Controllerの所有を移した。ゲーム側は互換propertyを維持し、状態を二重化しない。マップ切替の保存・再配置順序と、管理画面から再読込した辞書を既存の戦闘処理が参照することをテストした。

個別テストで再現したコマンドの循環importも修正。`application.RuntimeOrchestrator` の公開APIを遅延読込で維持し、読込順ごとの別プロセステストを追加した。UI・JSON形式・戦闘規則は変更していない。

追加: `apps/{progress_session,field_session}.py`、`tests/{test_session_ownership,test_command_imports}.py`。
更新: `apps/game.py`、`application/__init__.py`（各実装は `src/kadoka_quest/` 配下）、CODEMAP、状態所有者棚卸し、生成REPO_MAP、`docs/ver.md`。

# 47. ゲーム状態と互換窓口の棚卸し（Issue #137）

`KadokaQuest` の状態の正本、残る処理責務、27個の互換propertyを整理した。後続Issue #138〜#140の移行順と確認事項を定め、CODEMAPから案内する。戦闘描画が現状はゲーム全体の互換viewを参照する点も説明書に反映。実装・保存形式・ゲーム挙動は変更していない。

追加: `docs/KadokaQuest状態所有者棚卸し.md`。
更新: `docs/CODEMAP.md`、`docs/戦闘セッション責務分離機能説明書.md`、`docs/ver.md`。

# 46. 決定的なREPO_MAP生成（Issue #122）

`tools/code-docs/script/generate_repo_map.py` で `src/` の公開シンボル・引数索引を生成できるようにした。実装本文・docstring・既定値の内容は出力せず、固定順で生成する。`--check` をCIへ追加し、AGENTS/CODEMAPから必要な箇所だけ検索する導線を用意した。

追加: 生成ツール、`docs/generated/REPO_MAP.md`、`tests/test_repo_map.py`。
更新: `AGENTS.md`、`docs/CODEMAP.md`、`tools/README.md`、`.github/workflows/python-app.yml`、`docs/ver.md`。

# 45. マージ後のドットエディタ退行とテスト不整合の修正

9月17日の競合解消で欠落した `CANVAS_SIZES`、ブロックのサイズ選択・再読込、ペンの連続補間を復元。サイズ変更はUndo可能で、モンスターは64×64を維持し、Kadokaパレット変換と共存する。サイズ復元・透明ピクセル・固定サイズの回帰テストを追加した。

現行の模擬戦ロスターとコンポーネント別ライセンスにテストを追従させ、パッケージのlicense欄は既存 `LICENSE` を参照する形式に更新。Windowsの `CON` を存在判定するとデバイスを検出するため、未作成確認はディレクトリの列挙で行う。

更新: `src/kadoka_quest/ui/pixel_editor.py`, `src/kadoka_quest/apps/block_editor.py`, `tests/test_pixel_editor_canvas.py`, `tests/test_project_metadata.py`, `tests/test_simulation_manager.py`, `tests/test_save_name_validation.py`, `pyproject.toml`, `docs/ver.md`。

# 44. CODEMAPを現行構成へ更新（Issue #121）

AGENTSからCODEMAPへ直接案内し、主実装・優先テスト・仕様書を1行で特定できるようにした。現行の模擬戦、戦闘進行、Developer配布、CIを索引化し、パスの基準を明記。ROUTESのフィールド参照先も `kadoka_engine` に修正した。

更新: `AGENTS.md`, `docs/CODEMAP.md`, `docs/context/ROUTES.md`, `tests/test_project_metadata.py`, `docs/ver.md`。
自動REPO_MAP生成は子Issue #122で扱う。

# 42. 模擬戦施設の専用個体サービス

`SimulationFacilityService` を追加し、`imports/simulation/` に限定した模擬戦用個体の作成・一覧・削除・相手パーティ編成と、AI更新・恒久報酬のない戦闘生成を分離した。通常の所有個体フォルダには書き込まない。

追加したファイル

- `src/kadoka_quest/apps/simulation_facility_service.py`
- `tests/test_simulation_facility_service.py`

更新したファイル

- `docs/CODEMAP.md`
- `docs/外部個体取込責務分離機能説明書.md`
- `docs/ver.md`

# 43. 模擬戦受付UI

牧場とは別の `simulation_manager.py` を追加した。模擬戦専用個体を作成・外部フォルダから再読込・削除し、相手パーティへ追加または除外できる。受付は `SimulationFacilityService` だけを使用し、通常の所有個体・パーティ保存へ直接触れない。

追加したファイル

- `simulation_manager.py`
- `src/kadoka_quest/apps/simulation_manager.py`
- `tests/test_simulation_manager.py`

更新したファイル

- `src/kadoka_quest/apps/simulation_facility_service.py`
- `tests/test_app_smoke.py`
- `docs/ver.md`

# 41. リモート要約ツールのWindows UTF-8対応

`tools/remote-context` がWindowsのcp932コンソールでもGitのUTF-8差分を正しく読み書きできるようにした。文字化けや復号例外で同期判断が止まらない。

更新したファイル

- `tools/remote-context/script/sync_remote_context.py`
- `tests/test_remote_context.py`
- `docs/ver.md`

# 40. AGENTS段階的読込ルーター

`AGENTS.md` にContext Budget原則を明記し、最初にIssueとCODEMAPの該当1行だけを読む運用へ固定した。CODEMAPが戦闘、フィールド、エディタ、データなど領域ごとの次の資料を案内し、全体仕様の常読を防ぐ。

更新したファイル

- `AGENTS.md`
- `docs/ver.md`
- `tests/test_project_metadata.py`

# 39. リモート変更要約ツール

作業開始時にリモート変更を圧縮して確認する `tools/remote-context/script/sync_remote_context.py` を追加した。fetch後にコミット、変更ファイル、統計、境界付き差分を表示し、マージ判断のための再探索を減らす。

追加したファイル

- `tools/remote-context/script/sync_remote_context.py`

更新したファイル

- `docs/CODEMAP.md`
- `scripts/run_python.bat`
- `docs/ver.md`

# 38. 1作業単位のワークフロー

`docs/ワークフロー/ワークフロー.md` を、1つのIssueまたは独立作業を完了するまでの手順へ整理した。開始時にリモート変更を取得・確認・安全に取り込み、未コミット変更を保護してから実装する流れを明記している。

更新したファイル

- `docs/ワークフロー/ワークフロー.md`
- `docs/ver.md`

# 37. タスク別CODEMAP

実装タスクから主実装・関連テスト・仕様書・境界を一度に引ける `docs/CODEMAP.md` を追加した。詳細仕様を複製せず、ファイル移動時に索引だけを更新できる軽量な一覧にしている。

追加したファイル

- `docs/CODEMAP.md`

更新したファイル

- `AGENTS.md`
- `docs/ver.md`

# 36. 実装Issueの自己完結テンプレート

GitHub Issue Forms に、Codexへ渡す実装タスク用の短いテンプレートを追加した。目的・対象・変更しない範囲・受け入れ条件・検証を必須にし、既存挙動・データ契約・移植境界などは必要な場合だけ記入する。

追加したファイル

- `.github/ISSUE_TEMPLATE/implementation.yml`

更新したファイル

- `docs/Codexコンテキスト運用.md`
- `docs/ver.md`

# 35. Codexコンテキスト削減

毎回読み込む `AGENTS.md` を不変の作業規則・アーキテクチャ境界・主要データ契約だけに圧縮し、詳細仕様を必要時だけ読む運用へ変更した。

変更したファイル

- `AGENTS.md`
- `docs/ver.md`

追加したファイル

- `docs/Codexコンテキスト運用.md`

# 34. 戦闘中のAI判断ログ

AIがスキルを選んだ直後に、現在の戦術と選択スキルに実際に影響した習熟・状況別学習を戦闘ログへ表示するようにした。説明生成は選択処理と分離され、AIの選択・学習・保存内容を変更しない。

変更したファイル

- `docs/ver.md`
- `src/kadoka_quest/core/battle.py`

追加したファイル

- `docs/戦闘AI判断ログ機能説明書.md`
- `src/kadoka_quest/core/battle_decision_explanation.py`
- `tests/test_battle_decision_explanation.py`

# 33. 個体AIの可視化

個体・パーティ管理画面に、AIプロファイル、行動指針、学習済みスキル傾向、状況別の学習傾向を表示するようにした。表示用の集計は保存データを変更せず、絶対値の大きい傾向から最大3件を示す。

変更したファイル

- `docs/ver.md`
- `src/kadoka_quest/apps/manage.py`

追加したファイル

- `src/kadoka_quest/apps/ai_inspector.py`
- `tests/test_ai_inspector.py`

# 32. ヘッドレスゲーム評価

未訪問マップを優先する幅優先のフィールド探索計画、意味コマンド経由の自動操作、戦闘・暗号画面・到達不能・停止理由を残すJSON評価ログを追加した。既定の評価セーブはレポート横の隔離フォルダで、通常セーブを変更しない。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/launcher.py`

追加したファイル

- `game_evaluator.py`
- `docs/ゲーム評価機能説明書.md`
- `src/kadoka_quest/devtools/evaluation_log.py`
- `src/kadoka_quest/devtools/field_explorer.py`
- `src/kadoka_quest/devtools/game_evaluator.py`
- `tests/test_game_evaluator.py`

# 31. バランス調整ツール

同レベルの種族ペアをAI学習なしで再現可能に大量模擬戦させ、対戦履歴、勝率、順位、Lv100能力値を基準にした能力値・耐性の改善候補をJSON出力するCLIを追加した。分析結果は助言専用で、ゲームデータを自動変更しない。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/ver.md`
- `docs/評価/評価者からのフィードバック.md`
- `src/kadoka_quest/apps/launcher.py`

追加したファイル

- `balance_analyzer.py`
- `docs/バランス調整ツール機能説明書.md`
- `src/kadoka_quest/devtools/__init__.py`
- `src/kadoka_quest/devtools/balance_analyzer.py`
- `tests/test_balance_analyzer.py`

# 30. マップ出現モンスターレベル範囲

マップエディタに種族ごとの出現最小Lv・最大Lvを編集する画面を追加。未登録種族は重み10で追加し、既存出現項目は範囲だけを更新する。出現Lvは1〜100かつ最小値以下最大値のJSON契約として、データ検証も追加した。ボールスライムは初期獲得専用のため、出現設定とデータ検証の両方で拒否する。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/ver.md`
- `docs/評価/評価者からのフィードバック.md`
- `src/kadoka_engine/data_validator.py`
- `src/kadoka_quest/apps/map_editor.py`
- `tests/test_data_validator.py`

追加したファイル

- `docs/出現モンスターレベル範囲機能説明書.md`
- `tests/test_map_spawn_ranges.py`

# 1. マッププリセット

マップエディターへ、現在のマップをプリセットとして保存する機能、現在のマップへ適用する機能、プリセットから新規マップを作成する機能を追加。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/map_editor.py`
- `src/kadoka_quest/data/repository.py`
- `tests/test_core.py`

追加したファイル

- `docs/マッププリセット機能説明書.md`
- `src/kadoka_quest/data/map_presets.py`

# 2. データクリエイター

種族、レベル、個体名、任意の個体IDを指定して、既存形式のモンスター個体を生成する開発ツールを追加。現在のセーブ、獲得用、模擬戦用の3種類の生成先に対応。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/launcher.py`
- `src/kadoka_quest/data/monsters.py`
- `tests/test_app_smoke.py`
- `tests/test_core.py`

追加したファイル

- `data_creator.py`
- `docs/データクリエイター機能説明書.md`
- `src/kadoka_quest/apps/data_creator.py`
- `src/kadoka_quest/data/developer_monster_creator.py`

# 3. 状況をもとにした学習

個体AIへ、自分のHP、味方の損耗、MP、人数差、敵の残HP、敵とのレベル差を使う軽量な状況別学習を追加。模擬戦の学習禁止とAIリセットの進行保持は維持。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/core/ai.py`
- `src/kadoka_quest/core/battle.py`
- `tests/test_core.py`

追加したファイル

- `docs/状況学習機能説明書.md`
- `src/kadoka_quest/core/battle_context.py`

# 4. 移動の滑らかさ

マス単位の入力・当たり判定・イベント・セーブを維持したまま、主人公と固定モブの表示位置およびカメラ追従を短時間補間する機能を追加。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/移動補間機能説明書.md`
- `src/kadoka_quest/core/grid_movement.py`

# 5. 移植可能な処理・画面・データ境界

フィールドの通行、方向、キャラクター衝突、イベント検索、視線判定をpygame非依存の処理層へ移動。フィールド描画をUI層へ分離し、GDScript／Lua移植時に使う通常データだけの入出力契約を仕様化。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/移植境界機能説明書.md`
- `src/kadoka_quest/core/field_engine.py`
- `src/kadoka_quest/ui/field_renderer.py`

# 6. モンスター種族の新規作成

モンスターエディターの種族一覧先頭へ「＋ 新規作成」を追加。レベル1～100、習得スキル、＋1～＋10を含む4 JSONと、戦闘・前後左右の64×64 PNG 5枚を一括生成する。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/monster_editor.py`
- `tests/test_core.py`

追加したファイル

- `docs/モンスター種族新規作成機能説明書.md`
- `src/kadoka_quest/data/species_creator.py`

# 7. ドットエディターの編集可能パレット

モンスターとブロックで共有するドットエディターへ、`#RRGGBB` によるペン色の追加、重複色の選択、選択色の削除を追加。最大16色とし、透明色および最後の不透明色は削除できないようにした。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/block_editor.py`
- `src/kadoka_quest/apps/monster_editor.py`
- `src/kadoka_quest/ui/pixel_editor.py`
- `tests/test_core.py`

追加したファイル

- `docs/ドットエディターパレット機能説明書.md`

# 8. ドットエディターの画像編集基本機能

共通ドットエディターへ、輪郭内の連続領域を塗るバケツ、しきい値指定の近似色統合、縦横比維持・最近傍縮小・中央配置による画像読込を追加。モンスターとブロックの両画面で利用でき、各操作をCtrl+Zで戻せるようにした。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/block_editor.py`
- `src/kadoka_quest/apps/monster_editor.py`
- `src/kadoka_quest/ui/pixel_editor.py`
- `tests/test_core.py`

追加したファイル

- `docs/ドットエディター画像編集機能説明書.md`
- `src/kadoka_quest/ui/pixel_operations.py`

# 9. コマンド駆動アプリ基盤 第1段階

pygame入力ループからフィールド・戦闘・暗号入力処理への直接呼出しを廃止し、`target / action / payload` の共通コマンドへ変換して対象アプリへ配送する基盤を追加。移動方向もキーコードではなく意味名で渡し、各コマンドアプリをpygame非依存にした。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `src/kadoka_quest/application/__init__.py`
- `src/kadoka_quest/application/app_command.py`
- `src/kadoka_quest/application/command_bus.py`
- `src/kadoka_quest/apps/field_command_app.py`
- `src/kadoka_quest/apps/battle_command_app.py`
- `src/kadoka_quest/apps/password_command_app.py`

# 10. 戦闘責務分離 第2段階

戦闘画面描画、計算、AI学習、AI推論、データ読込を独立モジュールへ分離。BattleEngineは各責務を注入可能にし、通常戦だけが学習する契約と既存の公開関数・カタログ属性を維持した。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/game.py`
- `src/kadoka_quest/core/ai.py`
- `src/kadoka_quest/core/battle.py`
- `tests/test_core.py`

追加したファイル

- `docs/戦闘責務分離機能説明書.md`
- `src/kadoka_quest/core/battle_inference.py`
- `src/kadoka_quest/core/battle_learning.py`
- `src/kadoka_quest/core/combatant.py`
- `src/kadoka_quest/data/battle_data.py`
- `src/kadoka_quest/ui/battle_renderer.py`

# 11. フィールドアクター責務分離 第3段階

固定モブの実行時状態・会話・占有・移動と、非表示エンカウント敵の出現・視認・追跡・徘徊を、pygameおよび保存I/Oに依存しない2つの状態機械へ分離。ゲーム本体の既存公開メソッドとリスト属性は互換窓口として維持した。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/フィールドアクター責務分離機能説明書.md`
- `src/kadoka_quest/core/fixed_mob_controller.py`
- `src/kadoka_quest/core/hidden_enemy_controller.py`

# 12. フィールドセッション責務分離 第4段階

主人公の整数座標・向き・長押し移動・表示補間、NPC/イベントの効果解釈、現在地・復活地点・拾得品・進行状態の保存、マップ/ブロック読込と入口座標補正を4つの独立責務へ分離。既存のゲーム本体属性とメソッドは互換窓口として維持した。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/フィールドアクター責務分離機能説明書.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/フィールドセッション責務分離機能説明書.md`
- `src/kadoka_quest/apps/field_event_app.py`
- `src/kadoka_quest/core/player_field_controller.py`
- `src/kadoka_quest/data/field_data.py`
- `src/kadoka_quest/data/field_progress.py`

# 13. 実行時オーケストレーター 第5段階

画面モード、共通コマンドバス、実行時アプリ登録、フィールド効果から別アプリへの配送を `RuntimeOrchestrator` へ集約。管理画面にも独立コマンド境界を追加し、固定モブ実体などの実行時オブジェクトをコマンドpayloadへ含めない契約に変更した。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/フィールドセッション責務分離機能説明書.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/application/__init__.py`
- `src/kadoka_quest/apps/battle_command_app.py`
- `src/kadoka_quest/apps/field_command_app.py`
- `src/kadoka_quest/apps/field_event_app.py`
- `src/kadoka_quest/apps/game.py`
- `src/kadoka_quest/apps/password_command_app.py`
- `tests/test_core.py`

追加したファイル

- `docs/実行時オーケストレーター機能説明書.md`
- `src/kadoka_quest/application/runtime_orchestrator.py`
- `src/kadoka_quest/apps/manager_command_app.py`

# 14. 戦闘セッション責務分離 第6段階

戦闘の開始・終了、コマンド選択、時間差ログ演出、行動中個体、オート戦闘時刻、通常戦・模擬戦、固定モブ戦の識別をpygame非依存の `BattleSession` へ集約。戦闘計算、AI推論・学習、保存、描画との境界および既存公開属性を維持した。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/実行時オーケストレーター機能説明書.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/battle_command_app.py`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/戦闘セッション責務分離機能説明書.md`
- `src/kadoka_quest/apps/battle_session.py`

# 15. 暗号入力セッション責務分離 第7段階

水の湧き場の仮想キーボードについて、許可文字、7文字上限、入力文字列、案内・誤答メッセージ、正解判定、取消状態をpygame非依存の `PasswordSession` へ集約。正解後のまる・かどか獲得と進行保存はゲーム進行側に維持した。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/実行時オーケストレーター機能説明書.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/暗号入力セッション責務分離機能説明書.md`
- `src/kadoka_quest/apps/password_session.py`

# 16. キャラクター画像取得責務分離 第8段階

種族定義からの戦闘立ち絵・前後左右フィールド画像のパス解決、RGBA PNG読込、フィールド透明余白の切詰め、縦横比を維持した最近傍拡大、取得失敗を含むSurfaceキャッシュを `CharacterImageProvider` へ集約した。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/実行時オーケストレーター機能説明書.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/キャラクター画像取得責務分離機能説明書.md`
- `src/kadoka_quest/ui/character_image_provider.py`

# 17. 管理ツールプロセス責務分離 第9段階

牧場管理ツールのPythonプロセス生成、二重起動防止、実行中判定、終了通知の一度だけの消費を `ManagerProcessService` へ集約。ゲーム側は意味結果の表示と終了後のセーブ再読込だけを担当するようにした。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/実行時オーケストレーター機能説明書.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/管理ツールプロセス責務分離機能説明書.md`
- `src/kadoka_quest/apps/manager_process_service.py`

# 18. 実行時入力アダプター責務分離 第10段階

pygameの終了・キーダウン・キーアップを、画面モードと戦闘状態に応じたプレーンな意味コマンド要求へ変換する `RuntimeInputAdapter` を追加。メインループからフィールド・戦闘・暗号入力のキー分岐を除去した。

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/実行時オーケストレーター機能説明書.md`
- `docs/開発予定.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/実行時入力アダプター責務分離機能説明書.md`
- `src/kadoka_quest/ui/runtime_input_adapter.py`

# 19. 実行時マウスアダプター責務分離 第11段階

- パスワード画面の仮想キーボード、消去、決定、取消の当たり判定を `RuntimeMouseAdapter` へ分離
- 戦闘画面の戦う、スカウト、道具、逃げるの当たり判定を同じアダプターへ分離
- 左クリックだけを意味コマンド要求へ変換し、右クリック、戦闘終了後、演出中は操作要求を生成しない
- `Button` は描画用として維持し、ゲームループからコールバック実行と画面固有 `collidepoint` を除去
- 保存JSONの形式変更なし

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/実行時オーケストレーター機能説明書.md`
- `docs/実行時入力アダプター責務分離機能説明書.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/実行時マウスアダプター責務分離機能説明書.md`
- `src/kadoka_quest/ui/runtime_mouse_adapter.py`

# 20. フィールドパーティ選択状態責務分離 第12段階

- `FieldPartySession` を追加し、フィールドで選択中のパーティ枠と次のプリセット巡回位置を分離
- 選択枠を0～3に制限し、現在のパーティ人数に合わせて従来どおり循環補正
- `FieldCommandApplication` の `party.select` はゲーム属性へ直接代入せず公開操作を呼ぶ
- `game.py` の既存 `selected_party / preset_index` APIは互換プロパティとして維持
- パーティ、プリセット、個体AIの保存JSON形式は変更なし

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/ver.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/実行時オーケストレーター機能説明書.md`
- `src/kadoka_quest/apps/field_command_app.py`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/フィールドパーティ選択状態責務分離機能説明書.md`
- `src/kadoka_quest/apps/field_party_session.py`

# 21. フィールドパーティ永続操作責務分離 第13段階

- `FieldPartyService` を追加し、プリセット保存・順次読込・作戦変更・AIリセットをゲーム本体から分離
- 既存の `FieldPartySession` と `PartyStore / StateStore / MonsterStore` を依存注入して調停
- パーティなし・プリセットなしの場合は従来どおり状態を変更しない
- 時刻供給を差し替え可能にし、プリセット名生成を決定的にテスト
- 保存JSONの場所、キー、最大4枠、無制限プリセット規則は変更なし

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/ver.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/実行時オーケストレーター機能説明書.md`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/フィールドパーティ永続操作責務分離機能説明書.md`
- `src/kadoka_quest/apps/field_party_service.py`

# 22. 外部個体取込責務分離 第14段階

- `MonsterImportService` を追加し、取得用フォルダ再走査と模擬戦用フォルダ読込をゲーム本体から分離
- 模擬戦の `BattleEngine` を必ず `learning_enabled=False` で生成
- 外部個体なし・不正個体では戦闘を開始せず従来の案内を返す
- ゲーム本体はサービス結果を受け、戦闘セッション開始と画面遷移だけを担当
- `monster.json / ai.json`、取得先、模擬戦非コピー規則は変更なし
- Iドライブ上のPythonを使用せず、CドライブのPython 3.13.5とpygame-ce 2.5.8で検証

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/ver.md`
- `docs/コマンド駆動アプリ基盤機能説明書.md`
- `docs/実行時オーケストレーター機能説明書.md`
- `src/kadoka_quest/apps/game.py`
- `tests/test_core.py`

追加したファイル

- `docs/外部個体取込責務分離機能説明書.md`
- `src/kadoka_quest/apps/monster_import_service.py`

# 23. Python 3.13.5並行実行環境

- CドライブのPython 3.13.5からプロジェクト内に `venv_3135` を作成
- `scripts/run_python.bat` は `venv_3135` を優先し、存在しない場合だけ既存 `.venv` を使用
- 3.13.5使用時はpygame同梱DLLとWindows基本ディレクトリを優先し、利用不能なドライブ上のDLLを参照しない
- Python版の選択を起動スクリプトに限定し、ゲーム本体・公開JSON・pygame非依存コアは変更なし
- `pyproject.toml` の対応範囲 `Python >= 3.10` を維持
- 仮想環境本体は `.gitignore` 対象とし、ソース管理へ含めない

変更したファイル

- `.gitignore`
- `AGENTS.md`
- `README.md`
- `docs/ver.md`
- `run_game.bat`

追加したファイル

- `docs/Python3135並行環境機能説明書.md`
- `scripts/run_python.bat`
- `tests/test_environment_contract.py`

# 24. ドットエディタ連続描画

- 高速ドラッグ時に前回の論理ドットから現在の論理ドットまで整数直線で補間
- モンスターエディタとブロックエディタの共通 `PixelArtEditor` へ一度だけ実装
- 左ドラッグの着色と右ドラッグの透明化の両方へ適用
- キャンバス外へ出た場合は線分を切り、再進入時の意図しない長い線を防止
- 1回のドラッグを引き続き1回のUndo履歴として管理
- 中央ボタンでペン入力が始まらないよう入力条件を明確化

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/ver.md`
- `docs/開発予定.md`
- `src/kadoka_quest/apps/block_editor.py`
- `src/kadoka_quest/apps/monster_editor.py`
- `src/kadoka_quest/ui/pixel_editor.py`
- `tests/test_core.py`

追加したファイル

- `docs/ドットエディタ連続描画機能説明書.md`

# 25. MODデータ一括検証

- 起動を停止せず全問題を収集するpygame非依存 `DataValidator` を追加
- JSON構文、ブロック、マップ、種族、Lv別能力、スキル、＋分岐、装備、耐性を一括検査
- 検証語彙を `data/project.json` へ切り出し、ゲーム固有名を検証処理から分離
- ランチャー起動時に問題件数を表示
- 問題コード・JSONパス・説明を表示するスクロール対応の検証画面を追加
- ブロック・マップ・モンスターエディタの保存直後にも全体検証を実行
- 問題が存在してもゲーム・エディタの起動は継続可能
- 正常な同梱データで問題0件を確認

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/FORMATS.md`
- `docs/ver.md`
- `docs/評価/評価者からのフィードバック.md`
- `docs/開発予定.md`
- `src/kadoka_quest/apps/launcher.py`
- `src/kadoka_quest/apps/block_editor.py`
- `src/kadoka_quest/apps/map_editor.py`
- `src/kadoka_quest/apps/monster_editor.py`
- `tests/test_app_smoke.py`

追加したファイル

- `data/project.json`
- `data_validator.py`
- `docs/MODデータ一括検証機能説明書.md`
- `docs/評価/過去のフィードバック.md`
- `src/kadoka_quest/apps/data_validator.py`
- `src/kadoka_quest/data/data_validator.py`
- `tests/test_data_validator.py`

# 26. エンジン分離 第1段階

- 再利用可能コード用の `kadoka_engine` パッケージを新設
- MODデータ検証本体を `kadoka_engine.data_validator` へ移動
- 汎用検証側から `kadoka_quest.paths` と固定データルートへの依存を除去
- ゲーム・各エディタがデータルートを明示して汎用エンジンを利用
- 旧 `kadoka_quest.data.data_validator` は既定パス付き互換アダプターとして維持
- `kadoka_engine` からKadoka Quest本体・pygameへの逆依存を禁止する自動テストを追加
- 3層分離全体は未完了のため、評価者フィードバックは継続項目として保持

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/MODデータ一括検証機能説明書.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/block_editor.py`
- `src/kadoka_quest/apps/data_validator.py`
- `src/kadoka_quest/apps/launcher.py`
- `src/kadoka_quest/apps/map_editor.py`
- `src/kadoka_quest/apps/monster_editor.py`
- `src/kadoka_quest/data/data_validator.py`
- `tests/test_data_validator.py`

追加したファイル

- `docs/エンジン分離第1段階機能説明書.md`
- `src/kadoka_engine/__init__.py`
- `src/kadoka_engine/data_validator.py`
- `tests/test_engine_boundaries.py`

# 27. フィールドエンジン分離 第2段階

- フィールド規則、座標補間、固定モブ、見えない敵、主人公移動の5責務を `kadoka_engine` へ移動
- エンジン内部の相互参照を `kadoka_engine` 内で完結
- ゲーム本体とフィールド描画が新しいエンジンAPIを直接利用
- 旧 `kadoka_quest.core` の5モジュールは同じクラスを再公開する互換窓口として維持
- `kadoka_engine` のKadoka Quest・pygame逆依存禁止テストを継続
- 旧importと新importのクラス同一性を自動テスト
- 3層分離全体は未完了のため、評価者フィードバックは継続項目として保持

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/ver.md`
- `docs/エンジン分離第1段階機能説明書.md`
- `src/kadoka_engine/__init__.py`
- `src/kadoka_quest/apps/game.py`
- `src/kadoka_quest/core/field_engine.py`
- `src/kadoka_quest/core/fixed_mob_controller.py`
- `src/kadoka_quest/core/grid_movement.py`
- `src/kadoka_quest/core/hidden_enemy_controller.py`
- `src/kadoka_quest/core/player_field_controller.py`
- `src/kadoka_quest/ui/field_renderer.py`
- `tests/test_engine_boundaries.py`

追加したファイル

- `docs/フィールドエンジン分離第2段階機能説明書.md`
- `src/kadoka_engine/field_engine.py`
- `src/kadoka_engine/fixed_mob_controller.py`
- `src/kadoka_engine/grid_movement.py`
- `src/kadoka_engine/hidden_enemy_controller.py`
- `src/kadoka_engine/player_field_controller.py`

# 28. 公開ライセンス・セキュリティ整備

- プロジェクト本体のコード、JSONデータ、通常アセットにMIT Licenseを明記
- まる・かどかの画像、キャラクターデザイン、派生ドット絵だけをObake Character License v1.1の例外として明記
- パッケージメタデータにもMITを設定
- 実プロジェクトのバージョンと非公開連絡先を示すSECURITYポリシーを追加
- ライセンス表記とセキュリティポリシーを検査するテストを追加

変更したファイル

- `README.md`
- `docs/ver.md`
- `pyproject.toml`

追加したファイル

- `LICENSE`
- `LICENSES/Obake-Character-License-v1.1.md`
- `SECURITY.md`
- `tests/test_project_metadata.py`

# 29. ブロック用可変キャンバス

- 共有ドットエディタに1 / 2 / 4 / 8 / 16 / 32 / 64 / 128の正方形キャンバスを追加
- ブロックエディタから保存前にキャンバスサイズを選択可能化
- 変更は最近傍法による1回のUndoとして扱い、PNGの実寸を保存・再読込
- モンスターの64×64画像契約は維持

変更したファイル

- `AGENTS.md`
- `README.md`
- `docs/ver.md`
- `src/kadoka_quest/apps/block_editor.py`
- `src/kadoka_quest/ui/pixel_editor.py`

追加したファイル

- `docs/可変キャンバス機能説明書.md`
- `tests/test_pixel_editor_canvas.py`
