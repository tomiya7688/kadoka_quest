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
