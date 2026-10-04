# Kadoka Quest GDScript版 — フィールド移植の試作

Godot 4.7.2で検証。`project.godot` をGodotからインポートし、F6ではなくF5（プロジェクト実行）で開始します。Pythonの起動やpygameは不要です。

```powershell
& '<Godotの実行ファイル>' --path '<このリポジトリ>\gdscript'
```

`data/` と `assets/` は既存Python版の正本を読み取り専用で利用します。複製・移動しません。別のコンテンツを試す場合は環境変数 `KADOKA_CONTENT_ROOT` に、その `data/` と `assets/` を含むディレクトリの絶対パスを指定できます。cwdには依存しません。

## 今回できること

- はじまりの街から起動し、現在の6マップを読込・描画。
- 矢印/WASDによるマス移動と長押しの連続移動。
- 地形・看板/岩などのblockingイベント・配置済み固定モブとの衝突。
- `step` と `interact` の移動ポイント。Enter/Space/Eで現在マスまたは正面のイベントを調べる。
- メッセージ看板。追加 `events/*.json` も読込。
- JSON指定の画像地形/キャラクター画像をnearestで表示。キャラクターは64px枠、縦横比保持。
- 固定モブの停止/ランダム/追跡移動を時間周期で更新。まる450ms/100%、かどか900ms/45%。プレイヤー・他モブ・壁・岩/看板と重ならない。移動/調べるイベント自体に色や印は付けない。
- 正面の固定モブにEnter/Space/Eで会話。デッキを一巡後に再抽選し、こちらを向いて停止。離れると既存の移動周期へ戻る。デッキ不正は理由を表示。
- ゲーム内のF5で現在のマップ・マス座標・向きを保存、F9で読込。次回起動時にも選択中のセーブから復元。
- 新規セーブの初回F5で主人公・ボールスライムの個体と初期パーティを生成。
- F6で現在パーティと保有個体の一覧。縦スクロールとキーボード操作に対応。
- 一覧からE/ボタンで現在パーティ4枠を編成。追加/解除/順番変更と明示的な保存・キャンセル。
- 編成のP/ボタンからパーティプリセットを新規保存・一覧選択・下書きへ読込。枠数は無制限。
- はじまりの街→牧場の台帳から、同じ一覧/編成/プリセット画面へ進む。
- 個体一覧にLv別の基礎能力値/Lv習得スキルと、＋/装備補正後の能力値/追加スキルIDを別々に表示。

## フィールドのセーブ／ロード

既定の保存先はGodotの `user://savedata/default/` で、Python版のリポジトリ内 `savedata/` とは別です。`user://` の実際の場所はGodot/OSのユーザーデータ設定に従います。移動ごとの自動保存はまだありません。セーブ名の選択画面も未実装のため、起動前の環境変数で切り替えます。

```powershell
$env:KADOKA_GDSCRIPT_SAVE_ROOT = 'C:\任意の専用フォルダ\savedata'  # 絶対パス
$env:KADOKA_GDSCRIPT_SAVE_NAME = '冒険1'  # 未指定ならdefault
& '<Godotの実行ファイル>' --path '<このリポジトリ>\gdscript'
```

初回F5では `state.json`、`meta.json`、`items/items.json` と `monsters/`、`parties/` を作成します。形式は [Named save data](../docs/FORMATS.md#named-save-data) に合わせ、主人公とボールスライムをLv1で生成して `current_party` へ入れます。個体IDはランダムな `monster_<12桁hex>`、各個体は既存形式の `monster.json / ai.json` を持ちます。保存先の変更やセーブ名の指定だけではフォルダを作らず、F9も読込だけです。

既存セーブでは `state.json` の `map_id` と `player.x/y/direction` だけを更新し、進行フラグ・復活地点・現在パーティ・未知キーを引き継ぎます。向きのない旧形式は正面で復元します。既存の個体・AI・アイテム・パーティプリセット・metaファイルは書き換えません。既存セーブへ初期仲間を自動追加せず、前段階で作った空のセーブも勝手には変更しません。新規開始を試すには未使用のセーブ名を指定します。既存Pythonセーブを試すときは専用のコピーを使い、両版を同じ保存先で同時実行しないでください。

壊れたJSON、未対応schema、存在しないマップ、範囲外や壁/看板上の座標は、読込・上書きを拒否して理由を表示します。保存は現在のモブ占有も検証しますが、原本の初期地点は現在の占有ではありません。読み込み時はプレイヤーを先に確保し、そこに初期配置されるモブを空きマスへ移します。一時ファイルからの置換に失敗しても、以前の `state.json` を削除しません。読み直した内容のdigestが変わった場合も保存を拒否します。初回作成は複数ファイル一括トランザクションではなく、失敗時に未完成のフォルダが残る場合があります。JSONの再出力によりstateの空白や数値表記は変わり、Godotの数値精度を超えるMOD値の無損失往復は保証しません。

個体の2ファイルは固有の一時フォルダに書いてから公開します。state保存が後で失敗しても、次の初回保存は公開済みの主人公/ボールスライムを再利用し、同種の初期仲間を重複生成しません。初回保存前の既存個体に破損があれば生成を拒否し、修復や削除を自動実行しません。並行する複数writerの排他はまだ保証しません。

## 個体・パーティの確認

街の西側の牧場入口をEnter/Space/Eで調べて入り、奥の台帳（14,5）の正面から同じキーで調べます。既存の一覧が開き、E/ボタンで編成、編成のP/ボタンでプリセットへ進めます。台帳はblockingのため通り抜けません。Esc/F6で一覧を閉じると同じ牧場の位置・向きへ戻ります。画面を開くだけでは個体/AI/保存JSONを変更せず、個体編集・AI変更はまだできません。

ゲーム内のF6で一覧を開き、F6またはEscで閉じます。↑↓、PageUp/Down、Home/Endと縦スクロールバー・ホイールで移動できます。開いている間は主人公の移動、調べる、F5/F9を止めます。

一覧は先頭4つのパーティ枠と全保有個体を表示し、所有数にプログラム上の上限を設けません。名前・種族・Lv・＋選択数・装備ID・AIプロファイル/作戦・戦闘経験回数に加え、補正前の6基礎能力値/Lv習得スキルと、＋/装備補正後の能力値/＋追加を含むスキルIDを別々に表示します。基礎値は明示Lv表、スキルは宣言順のlearnsetから復元し、重複を除きます。成長式の結果はデータ生成時のLv表を利用し、欠損行を自動補間しません。能力値/スキルJSONの破損は注意を表示し、有効な個体/AIやパーティID自体は残します。AI判断/学習はまだ実装していません。既存のAI JSONは保持・確認するだけです。

＋効果は選択IDの重複を除き、種族plus.jsonの宣言順で加算/倍率を適用し、倍率ごとにPythonと同じ偶数丸めを行います。その後、装備側のallowed_species_idsで許可された装備の能力倍率を適用し、最後に各値を最低1にします。追加スキルもLv習得→＋定義順で重複を除きます。計算時に選択数/段階/前提条件を自動修正しない点も現Python版と同じです。不明な選択ID、未知の能力値/効果、装備不可/不明装備は理由を表示して補正せず、元のIDを保持します。破損した補正定義では「補正後を読込不可」と表示し、基礎値を完成値の代用にしません。計算結果を個体へ保存せず、装備/＋編集UIや装備の戦闘用効果はまだありません。詳しい計算境界は[形式仕様](../docs/FORMATS.md#gdscriptフィールド試作の保存)を参照してください。

一覧を開く際に個体フォルダを再走査しますが、これは所有フォルダ内の読込で、外部importsからの獲得ではありません。欠損/破損・不正ID・未対応schema・未知種族の個体は注意を表示して除外し、元ファイルは削除/修復しません。パーティの欠損IDは「読込不可」、nullは空き枠として表示し、保存された順番やIDは書き換えません。個体IDには日本語も使用でき、フォルダ名とJSON内のIDの一致が必要です。

## 現在パーティの編成

F6の一覧でEまたは「パーティを編成する」を押します。新規プロフィールは先にフィールドのF5で保存してください。左の4枠から編集する枠、右の保有個体から仲間を選び、「選択個体を入れる」または右リストのEnterで入れ替えます。「選択枠から外す」またはDeleteでnullの空き枠にできます。順番を変えるときは元の枠を空けてから別枠へ入れます。同じ個体の複数枠への追加は拒否します。主人公の固定枠は設けず、空編成もPythonの現行管理と同様に許可します。

↑↓・Home/End・PageUp/Downで選択、Tab/Shift+Tabでリストとボタンを巡回できます。保有数に合わせて右リストがスクロールします。Ctrl+S/「編成を保存」で反映、Esc/F6/「キャンセル」で下書きを破棄して一覧へ戻ります。閉じる操作で自動保存しません。編成中は移動・調べる・F5/F9を止めます。

保存は既存 `state.json.current_party` だけを4枠のID/null配列へ変更します。保存済み位置・フラグ・未知キーと個体/AI/items/meta/プリセットを保持します。未保存のフィールド位置はそのままで、編成保存は位置保存の代わりにはなりません。変更なしで保存した場合はstateも書き換えません。

保存前に所有フォルダを再走査し、選択個体を再検証します。欠損/重複の既存IDは自動修復せず、該当枠を明示的に外してください。5枠以上や不正な枠型は編成を開く時点で拒否し、切り捨てません。編集中のstate外部更新、破損JSON、置換ロック等の保存失敗では上書きせず下書きを残します。外部更新時はキャンセルして編成を開き直してください。digest確認は並行writerの完全な排他ではありません。

## パーティプリセット

F6 → E → P、または編成画面の「プリセット」ボタンで開きます。保存済みプロフィールの `parties/*.json` を一覧表示し、枠数にプログラム上の上限を設けません。↑↓・Home/End・PageUp/Downと縦スクロールに対応し、Tab/Shift+Tabで一覧・名前・各ボタンを巡回します。名前欄のHome/End/Deleteは通常の文字編集です。

- 新規保存: 名前を入力して名前欄のEnter、または「下書きを追加保存」。現在の下書き4枠を新しいプリセットへ保存します。現在パーティのstateは変更しません。
- 読込: 一覧から選びEnter、または「選択を下書きへ読込」。編成画面へ戻り、下書きだけを置き換えます。Ctrl+S/「編成を保存」で現在パーティへ反映するか、Esc/キャンセルで破棄してください。
- 再走査: F5/「一覧更新」。ここでのF5はフィールド保存ではありません。F9や移動・調べるは停止します。
- 戻る: Esc/F6/「編成へ戻る」。下書きを保持して編成へ戻ります。明示的に追加保存したプリセットは、その後に現在パーティの下書きをキャンセルしても残ります。

JSONはPython版と同じ `schema_version / name / members` です。表示名は日本語を使えます。新規ファイル名はASCIIの安全な名前（80文字まで、空なら `party`、Windows予約名は `party_` を付加）から作り、同名なら `_2`、`_3` と追加します。既存プリセットの上書き・削除は行いません。

読込時はファイルと所有個体を再走査し、消失/読込不可の個体はnullの空き枠として注意を表示します。既存のプリセット自体は修正しません。既知個体の重複、不正な枠型、5枠以上、壊れたJSONや未対応schemaは下書きへ適用せず、変更前の下書きを残します。無効な一覧ファイルは除外し、注意件数と先頭の理由を表示します。追加保存も個体を再検証し、失敗時に以前のファイルを削除しません。並行する複数writerの排他はまだ保証しません。

## 未移植

#221の[通常攻撃・防御・会心の数値契約](../docs/GDScript通常攻撃数値契約.md)は `engine/attack_numbers.gd` に実装済みです。会心乱数と0.92〜1.08の倍率を明示入力し、会心率1/16・防御無視・物理だけの防御軽減を比較できます。通常攻撃に効く許可装備の威力倍率/固定追加値も数値契約で扱います。共通の最終処理は魔法等にguardを掛けませんが、魔法/耐性/全スキルを実装したわけではありません。戦闘Scene/ターンには未接続で、ゲーム内で戦闘はまだできません。

戦闘、野生敵、戦闘AI判断/学習/リセット、固定モブの消滅イベント、暗号/仲間取得、個体編集、プリセットの更新/削除、外部個体取得/模擬戦、セーブ選択UI・コピー/インポート、各エディタ、ランチャー、配布exportは未実装です。教会などは「未移植」を表示し、副作用を起こしません。Python版の置換・完成版ではありません。

現在はsource checkout専用です。正本がGodotのresource root外にあるため、export済みexeでこのまま共有コンテンツを読めるとは主張しません。配布時のコンテンツ配置とexportは別段階で検証します。

## 責務と検証

`engine/field_engine.gd` は純粋な辞書の空間判定、`engine/field_save_contract.gd` と `monster_record_contract.gd` は保存/個体/初期AIの純粋な契約、`data/` はJSON/名前付き保存/個体フォルダのI/O、`application/field_session.gd` は一時状態、`field_persistence.gd` は永続化の調停、`owned_roster.gd` は検証とゲーム固有の初期仲間選択、`field_application.gd` はSceneの接続、`ui/` は入力/描画/画像変換です。rendererはゲーム状態を変更しません。正規data/assetsはread-only、書込は選択したGodot用セーブに限定します。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotのconsole実行ファイル>'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_bootstrap.py tests/test_gdscript_save.py tests/test_gdscript_roster.py tests/test_gdscript_party.py tests/test_gdscript_presets.py tests/test_gdscript_ranch.py -q
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_progression.py tests/test_gdscript_modifiers.py -q
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_attack_numbers.py -q
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_fixed_mobs.py -q
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_dialogue.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_fixed_mobs.py
$env:KADOKA_GDSCRIPT_SAVE_ROOT = 'C:\任意の検証専用フォルダ\savedata'
$env:KADOKA_GDSCRIPT_SAVE_NAME = 'smoke'
& $env:KADOKA_GODOT_EXECUTABLE --headless --path gdscript --editor --import
& $env:KADOKA_GODOT_EXECUTABLE --headless --path gdscript --quit-after 3
```

Python版FieldEngineとの同一入力/出力比較、正本の読込一致、実Sceneの入力・移動ポイント・F5/F9と別プロセス再起動、旧形式・名前付きセーブの互換、保存失敗時の不変性をheadlessで検証します。テストは実セーブを使わず一時コピーに保存します。Windowsでは実ファイルの置換ロックも検証します。Godotの指定がない環境では実エンジンテストは理由付きskipになります。skipは移植成功ではありません。

関連: #10/#111、[移植境界](../docs/移植境界機能説明書.md)。次の段階では個体・戦闘などを、既存の期待動作カタログと比較しながら移植します。今回のテストをPython版のE2Eカタログ全項目の移植済み証拠とは扱いません。
[P1の移行実装単位](../docs/ワークフロー/GDScript移行実装単位.md)を依存順で進めます。#218の牧場テストは正規の街入口/台帳イベント→実Sceneのキー→編成/プリセット→明示保存/取消・再起動を専用コピーで検証します。Python版の管理子プロセスや実ウィンドウ操作の証拠ではありません。
#219は `engine/monster_progression.gd` の純粋な再構築、Dataの種族表読込、`application/monster_progression.gd` の個体との結合を分け、一覧は結果だけを表示します。同種族の読込キャッシュは1回の一覧走査だけ。全8種族の全100Lv、成長式で生成した表と明示編集、習得境界、旧形式/不正データ、原本/個体/AIの不変を実Godotで比較します。
#220は純粋な `engine/monster_modifiers.gd / stat_numbers.gd`、Dataのplus/equipment読込、`application/monster_reconstruction.gd` の結合により補正結果を追加します。基礎結果は従来の契約のまま保持し、一覧は両方を表示します。同種族のplus読込と装備カタログの読込は走査内で共用し、次の走査で更新を反映します。全8種族×3Lv×8選択パターン×7装備状態、丸め/宣言順/重複、装備許可/拒否、破損定義、同種同Lvの個体差、一覧と再走査、個体/AI/原本byte不変を専用コピーで検証します。
#221は通常攻撃・基本防御倍率・共通の最終ダメージの純粋な数値APIです。実GodotとPython BattleEngineで通常/防御/会心・乱数境界・装備数値効果・原本/AI不変を比較します。演出/ターン/スキル全種類/耐性/AIの移植完了とは扱いません。
#222は[固定モブ周期移動](../docs/GDScript固定モブ移動契約.md)をSceneへ接続します。管理画面では時計/移動/補間が止まり、閉じても滞在時間分の追いつき移動を行いません。再入場で初期配置へ戻り、既存の非復活消滅フラグを読むだけで、移動中の座標/乱数/時計を保存しません。
#223は[固定モブ会話契約](../docs/GDScript固定モブ会話契約.md)です。正面のモブをイベントより先に選び、向きを反転して会話し、正面停止と周期再開へ接続します。会話はmodalではなくstatus表示で、移動キーで離れられます。カード残数/前回台詞は実行時だけで再入場/読込時にリセット。取得前後で住処の2体を隠しません。戦闘モブは理由付き未移植、会話後の消滅設定も明示し、実際には消去/保存しません。

Godot APIの根拠: [コマンドライン](https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html)、[JSON](https://docs.godotengine.org/en/stable/classes/class_json.html)、[Image](https://docs.godotengine.org/en/stable/classes/class_image.html)。
保存I/O: [user://](https://docs.godotengine.org/en/stable/tutorials/io/data_paths.html)、[FileAccess](https://docs.godotengine.org/en/stable/classes/class_fileaccess.html)、[DirAccess](https://docs.godotengine.org/en/stable/classes/class_diraccess.html)。
一覧/編成UI: [ScrollContainer](https://docs.godotengine.org/en/stable/classes/class_scrollcontainer.html)、[ItemList](https://docs.godotengine.org/en/stable/classes/class_itemlist.html)。

編成の責務: `engine/party_selection.gd` は純粋な4枠の下書き/選択規則、`application/party_editor.gd` は下書き所有と保存前再検証、`ui/party_view.gd` は入力/表示と操作signal。Sceneは結果表示と接続、既存Dataはstateのatomic更新を担当します。

プリセットの責務: `engine/party_preset_contract.gd` は純粋な形式/名前/欠損枠の契約、`data/party_preset_store.gd` は一覧/読込/新規JSONのI/O、`application/party_presets.gd` は所有個体の検証と下書きへの適用、`ui/party_preset_view.gd` は入力/フォーカス/表示とsignalです。実Sceneのキー/クリック・再起動、Python PartyStoreでの読込、121ファイルの一覧、不正/外部変更/実Windows読込ロック、state/個体/AI/元プリセットの不変性を専用コピーで検証します。日本語テキストのイベント入力は検証しますが、実IME・ウィンドウの視認性・exportの証拠ではありません。
