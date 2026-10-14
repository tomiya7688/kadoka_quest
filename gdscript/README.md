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
- 住処の水の湧き場を調べて7文字のかな入力/仮想キーボード。決定・削除・取消、入力中の探索停止。`へいわなすみか` の一致で不足するまる/かどかを現在のセーブへ追加し、牧場一覧へ反映。
- はじまりの街/ロクター村の教会を調べて復活地点を保存。登録だけで移動/HP回復はせず、実際の敗北復活は未接続。
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

#221の[通常攻撃・防御・会心の数値契約](../docs/GDScript通常攻撃数値契約.md)は `engine/attack_numbers.gd` に実装済みです。会心乱数と0.92〜1.08の倍率を明示入力し、会心率1/16・防御無視・物理だけの防御軽減を比較できます。通常攻撃に効く許可装備の威力倍率/固定追加値も扱います。#230で通常攻撃、#251で[基本ぼうぎょと終端解除](../docs/GDScript基本防御行動契約.md)をSessionへ接続しました。共通の最終処理は魔法等にguardを掛けませんが、この数値契約だけで魔法・属性耐性・特殊防御・全スキルに対応するわけではありません。単体魔法の実装範囲は下の専用契約を確認してください。AI/戦闘Sceneは未接続で、ゲーム内で戦闘はまだできません。

ゲーム画面での戦闘、野生敵、戦闘AI判断/学習/リセット、固定モブの消滅イベント、個体編集、プリセットの更新/削除、外部個体取得/模擬戦、セーブ選択UI・コピー/インポート、各エディタ、ランチャー、教会でのHP回復/実敗北復活、配布exportは未実装です。教会は復活地点の登録だけを行い、未接続の回復/復活を成功として表示しません。単体HP回復のengine/application実適用は下の契約から検証できますが、戦闘画面には未接続です。Python版の置換・完成版ではありません。

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
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_password.py -q
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_ghost_acquisition.py -q
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_church.py -q
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_combatant.py -q
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_turn_order.py -q
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_battle_session.py -q
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_normal_attack_action.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_fixed_mobs.py
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_combatant.py
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_battle_session.py
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_normal_attack.py
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_basic_defend.py
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_physical_skill.py -q
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_magic_skill.py -q
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_physical_action.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_physical_action.py
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_physical_skill.py
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_magic_skill.py
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
#224は[暗号入力契約](../docs/GDScript暗号入力契約.md)。住処の（17,8）から上を向き、湧き場をEnter/Space/Eで調べます。7枠と46かなキー、入力欄で日本語入力、Tab/Spaceで仮想キー操作、Enter/テンキーEnterで決定、Backspaceで削除、Escで取消。入力中は時計/主人公/固定モブ/保存/管理を止め、閉じても追いつき移動しません。native Unicodeイベントと確定文字signalをheadlessで検証しますが、実IME・手動画面・exportの証拠ではありません。
#225は[おばけ取得契約](../docs/GDScriptおばけ取得契約.md)。未保存なら先にF5で保存してください。一致時は同種族を所有していない分だけLv1/初期AI/source:ghost_home_passwordで追加し、ghost_entrance_openを保存します。既存の名前/Lv/＋/AI/パーティ・保存済み位置・未知キーを保持し、2匹の住処での配置/会話/徘徊も変えません。取得後にF6/台帳で再走査します。部分保存時は追加済み個体を保持して理由を表示し、再入力で不足分のみ再試行します。全件原子性/並行writer排他は保証しません。
#226は[教会登録契約](../docs/GDScript教会登録契約.md)。はじまりの街は（18,10）、ロクター村は（14,9）から上を向いてEnter/Space/Eで教会を調べます。先にF5で保存し、既存revive_pointだけを検証済みの地点へ置き換えます。同一地点なら不要な再出力をせず、位置/編成/フラグ/未知キー/個体/AI/itemsを保持します。外部更新・破損・リンク・置換失敗は拒否し、保存後の照合から成功を表示します。登録だけで移動/HP回復せず、敗北復活は未接続です。
#227は[戦闘個体状態契約](../docs/GDScript戦闘個体状態契約.md)。pure StateがHP/MP/fled/aliveを持ち、read-only Builderが補正済み能力値と個体をplain snapshotへ投影します。初回最大値・HP0保持・MP不足/ちょうど消費・逃走後の生存除外を実GodotとPythonで比較し、保有JSON/学習AI/保存形式を変更しません。4体の戦闘チームと無制限の所有数を区別します。Scene/全スキル/AI/実敗北復活は未接続です。
#228は[行動順契約](../docs/GDScript行動順契約.md)。side+idで両陣営同IDを区別し、開始時生存者→明示shuffle→stable速度順を計算します。行動直前の最新HP/逃走/敵生存を確認しますが、未移植の状態異常/buffや攻撃/AIを成功扱いにしません。新規準備と行動中の最新snapshotを区別します。
#229は[戦闘Session契約](../docs/GDScript戦闘Session契約.md)。Stateを戦闘開始時だけ初期化して所有し、固定順カーソルとoffered→claimed→finishを扱います。重複取得は進まず、claimは一度だけ、最新死亡/逃走/敵なしは実行不可。HP/MPはラウンド間で保持します。

#230は[通常攻撃行動契約](../docs/GDScript通常攻撃行動契約.md)。applicationがread-only開始と明示通常攻撃を調停し、pure resolverが検証後だけclaim→実HP適用→finishを行います。不正入力/重複で資源やcursorを消費しません。正規attack定義/許可装備は開始時にコピーし、リクエストからの装備/guard上書きは拒否します。#251の基本防御と後述のMP付き単体物理は別APIで接続しました。それ以外のスキル/AI/Scene/勝敗保存は未接続です。
保存I/O: [user://](https://docs.godotengine.org/en/stable/tutorials/io/data_paths.html)、[FileAccess](https://docs.godotengine.org/en/stable/classes/class_fileaccess.html)、[DirAccess](https://docs.godotengine.org/en/stable/classes/class_diraccess.html)。
一覧/編成UI: [ScrollContainer](https://docs.godotengine.org/en/stable/classes/class_scrollcontainer.html)、[ItemList](https://docs.godotengine.org/en/stable/classes/class_itemlist.html)。

編成の責務: `engine/party_selection.gd` は純粋な4枠の下書き/選択規則、`application/party_editor.gd` は下書き所有と保存前再検証、`ui/party_view.gd` は入力/表示と操作signal。Sceneは結果表示と接続、既存Dataはstateのatomic更新を担当します。

プリセットの責務: `engine/party_preset_contract.gd` は純粋な形式/名前/欠損枠の契約、`data/party_preset_store.gd` は一覧/読込/新規JSONのI/O、`application/party_presets.gd` は所有個体の検証と下書きへの適用、`ui/party_preset_view.gd` は入力/フォーカス/表示とsignalです。実Sceneのキー/クリック・再起動、Python PartyStoreでの読込、121ファイルの一覧、不正/外部変更/実Windows読込ロック、state/個体/AI/元プリセットの不変性を専用コピーで検証します。日本語テキストのイベント入力は検証しますが、実IME・ウィンドウの視認性・exportの証拠ではありません。

MP付き単体物理スキルの[予測契約](../docs/GDScript物理スキル予測契約.md)は元の定義とHP/MPを変更しません。物理スキルの[行動契約](../docs/GDScript物理スキル行動契約.md)は、正規習得・許可装備・最新資源を検証し、一回分の行動権取得・MP支払い・HP適用・行動終了をSessionへ接続します。不足・不正・未対応効果では行動権を消費しません。AIとゲーム画面には未接続です。開発者は上記の専用テストと性能検査を実行してください。

MPを消費する単体魔法の[予測契約](../docs/GDScript魔法スキル予測契約.md)は、属性耐性による通常ダメージ・無効・吸収回復と残MPを、入力を変更せず予測します。[魔法行動契約](../docs/GDScript魔法スキル行動契約.md)は正規習得・許可装備・耐性を準備し、最新予約を検証して実MP消費・HP変化・終了処理をSessionへ接続します。基本ぼうぎょは魔法を軽減せず、自傷・状態異常・全体攻撃等は拒否します。AIとゲーム画面には未接続です。

開発者はGodotとPythonを指定し、リポジトリのルートで次の魔法行動専用検証を実行してください。データとセーブは専用コピーを使い、未指定のGodotによるスキップは未検証です。数値予測だけの検査とは区別してください。

```powershell
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_magic_action.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_magic_action.py
```

[自傷魔法予測契約](../docs/GDScript自傷魔法予測契約.md)はmetal_burstの敵HP・術者のHP代償・残MPを、入力を変更せず予測します。[自傷魔法行動契約](../docs/GDScript自傷魔法行動契約.md)は専用入口から予測をSessionへ実適用します。無効・吸収・最後の敵の撃破でも代償が発生し、術者HPは最低1残ります。計算上の代償と実HP減少を区別します。AI・画面は未接続です。開発者は上記と同じGodot/Python環境で、次の予測と実適用の専用検証を実行してください。実セーブは使用しません。

```powershell
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_self_damage_magic.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_self_damage_magic.py
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_self_damage_magic_action.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_magic_action.py --self-damage
```

[吸MPスキル予測契約](../docs/GDScript吸MPスキル予測契約.md)はpossessの敵HP・敵MP喪失・術者MP回復を、入力を変更せず予測します。[吸MPスキル行動契約](../docs/GDScript吸MPスキル行動契約.md)は専用入口から最新予約・習得・敵対象・資源を検証し、Sessionへ実適用します。MP消費後に回復し、敵のMP喪失と術者最大MPによる回復上限を分離します。敵を倒した後もMPを奪い、無効/吸収耐性では奪いません。AI・画面は未接続です。開発者は上記と同じGodot/Python環境で次の検証を実行してください。実セーブは使用しません。

```powershell
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_drain_mp_skill.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_drain_mp_skill.py
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_drain_mp_action.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_magic_action.py --drain-mp
```

[単体HP回復予測契約](../docs/GDScript回復スキル予測契約.md)はsmall_heal/healyと互換MOD定義の回復上限量・最大HPで止まる実回復量・消費後MPを、入力変更なしで予測します。MP不足・不正資源・治療付き定義や未知効果を拒否します。HP0の数値予測は復活許可を意味しません。予測APIはSessionを変更せず、実適用は[回復スキル行動契約](../docs/GDScript回復スキル行動契約.md)へ接続しています。AI・画面は未接続です。開発者はリポジトリルートで、環境変数KADOKA_GODOT_EXECUTABLEに使えるGodotの実行ファイルを設定し、次の専用検証を指定したPythonで実行してください。実セーブは使用しません。

```powershell
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_heal_skill.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_heal_skill.py
```

[状態異常一つの治療予測契約](../docs/GDScript状態治療予測契約.md)は、解除不可を飛ばした最初の候補一件を明示確率・判定値で予測し、原本を変えない残存一覧を返します。候補なしでは判定不要、候補があれば確率0でも判定が必要です。未知ID/拡張情報は保持しますが、状態付与/継続効果を実装済みとしません。Session実治療は専用行動から状態所有者へ委譲します。治療付き回復の予測は別の専用契約へ委譲し、既存HP回復APIの治療付き定義拒否を維持します。AI・画面は未接続です。開発者はリポジトリルートで、使えるPythonとGodotの実行ファイルを指定して次を実行してください。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotの実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_status_cure.py tests/test_battle_status_cure.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_cure.py
```

[戦闘状態一覧契約](../docs/GDScript戦闘状態一覧契約.md)の所有者は、初期配列を独立保持し、予測で一覧を変えず、最新の一覧で成立した治療候補一件だけを除きます。例えば特殊拘束・毒・眠りの順に状態がある場合、成功した治療は毒だけを除きます。外部の一覧上書き・古い予測の持ち込みを拒否し、入力と返却値のネスト編集も所有状態へ伝播させません。状態所有者自体はHP/MPと行動予約を扱わず、Sessionの専用治療行動が数値更新と状態治療を調停します。保存・AI・画面は未接続です。開発者はリポジトリルートで使えるPythonとGodotを指定し、次を実行してください。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotの実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_combatant_status.py tests/test_gdscript_status_cure.py tests/test_gdscript_combatant.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_cure.py --status-state
```

[治療付きHP回復予測契約](../docs/GDScript治療付き回復予測契約.md)はspirit_recoverの回復上限・最大HPで止まる実回復量・消費後MPと一件治療を既存純粋契約で予測します。例えばHP99/100・MP10・毒あり・判定値0.02なら、実回復1・残MP6・毒一件の除去を予測します。満HPでもMP消費と治療を予測し、不正・不足では部分成功を返しません。実資源・Session・AI・画面は変更しません。開発者はリポジトリルートで、使えるPythonとGodotを指定して次の検証を実行してください。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotの実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_cure_heal_skill.py tests/test_gdscript_status_cure.py tests/test_battle_status_cure.py tests/test_gdscript_heal_skill.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_cure.py --cure-heal
```

[治療付きHP回復準備契約](../docs/GDScript治療付き回復準備契約.md)は、開始資源・習得・許可装備と全参加者に一致する明示初期状態を検証し、専用入口から習得済み定義を選びます。例えば正規HeroのLv59は「きあいでなおす」（spirit_recover）を選べず、Lv60なら選択できます。返却データは編集可能な通常辞書で、準備だけではSessionに登録しません。開発者が成功データを[専用Session開始](../docs/GDScript戦闘Session状態保持契約.md)へ渡すと、数値とは別に状態を独立保持/読取できます。従来開始は状態未設定です。[専用Application開始と治療付き回復](../docs/GDScript治療付き回復行動契約.md)も接続しました。通常開始/通常回復は維持し、AI/画面/保存は未接続です。開発者はリポジトリルートで上記Godot/Pythonを指定して次を実行してください。実セーブは使用しません。

```powershell
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_cure_heal_context.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_cure.py --cure-context
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_session_status.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_cure.py --session-status
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_cure_heal_action.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_cure.py --cure-action
```

[単体HP回復行動契約](../docs/GDScript回復スキル行動契約.md)は予測をSessionへ接続し、最新予約・習得・許可装備・生存する味方1体を検証して実MP消費・最大HPまでのHP回復・予約完了を行います。本人も指定でき、満HPでもMPを払います。不正・不足では予約と資源を保持し、死亡/逃走対象を復活させません。治療付き回復は別の専用行動に接続済みで、AI・戦闘画面は未接続です。開発者はリポジトリルートで、環境変数KADOKA_GODOT_EXECUTABLEに使えるGodotの実行ファイルを設定し、次の専用検証を指定したPythonで実行してください。実セーブは使用しません。

```powershell
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_heal_action.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_magic_action.py --heal
```

[状態一件の付与予測契約](../docs/GDScript状態付与予測契約.md)は重複を防ぎ、状態耐性で補正した確率と明示rollから新しい一覧を返します。例えば基礎確率0.4・weak耐性・roll0.49なら出血一件の成功を予測します。元一覧・実状態/Session・HPMP・保存は変更せず、継続効果/AI/画面は未接続です。開発者はリポジトリルートで上記Python/Godotを指定し、次を実行してください。

```powershell
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_status_apply.py tests/test_gdscript_status_cure.py tests/test_battle_bleeding.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_cure.py --status-apply
```

[個体状態所有者の一件付与](../docs/GDScript戦闘状態一覧契約.md#最新一覧への一件付与)は、最新一覧で付与を再判定し、成功した候補一件だけを独立保持します。例えば出血付与後の再付与は重ならず、治療で除いた後は再付与できます。準備/予測は状態を変えず、古い一覧/予測の上書きを拒否します。付与のSession予約は専用入口へ接続しました。付与付き攻撃行動・継続効果・AI・画面は未接続です。開発者はリポジトリルートで使えるPython/Godotを指定し、次を実行してください。

```powershell
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_owned_status_application.py tests/test_gdscript_combatant_status.py tests/test_gdscript_status_apply.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_cure.py --status-apply-state
```

[参加者状態集合の一件付与](../docs/GDScript参加者状態付与契約.md)は、陣営sideと個体idで指定した一体へ付与を委譲します。例えば味方と敵のIDが両方sameでも、enemies/sameへの付与は味方sameを変更しません。準備/予測は非破壊で、実付与は最新一覧で重複を防ぎます。付与のSession予約は専用入口へ接続しました。付与付き攻撃行動・AI・画面は未接続です。開発者はリポジトリルートで上記Python/Godotを指定し、次を実行してください。

```powershell
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_roster_status_application.py tests/test_gdscript_owned_status_application.py tests/test_gdscript_session_status.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_cure.py --roster-status-apply
```

[予約付き一回付与](../docs/GDScript予約付き状態付与契約.md)はSession.apply_status_applicationから現在取得済み票と最新生存を確認し、指定一体の所有状態へ更新を委譲します。同じ票の二回目は対象/状態IDを変えても拒否し、不正条件は修正して再試行できます。治療と付与は各一回の独立制限です。付与付き攻撃行動・AI・画面は未接続です。開発者はリポジトリルートで使えるPython/Godotを指定し、次を実行してください。

```powershell
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_session_status_application.py tests/test_gdscript_cure_heal_action.py tests/test_gdscript_session_status.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_cure.py --session-status-apply
```
