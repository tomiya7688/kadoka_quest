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
- 固定モブは初期地点に静止表示（まだAI移植前）。移動/調べるイベント自体に色や印は付けない。
- ゲーム内のF5で現在のマップ・マス座標・向きを保存、F9で読込。次回起動時にも選択中のセーブから復元。
- 新規セーブの初回F5で主人公・ボールスライムの個体と初期パーティを生成。
- F6で現在パーティと保有個体の一覧。縦スクロールとキーボード操作に対応。
- 一覧からE/ボタンで現在パーティ4枠を編成。追加/解除/順番変更と明示的な保存・キャンセル。

## フィールドのセーブ／ロード

既定の保存先はGodotの `user://savedata/default/` で、Python版のリポジトリ内 `savedata/` とは別です。`user://` の実際の場所はGodot/OSのユーザーデータ設定に従います。移動ごとの自動保存はまだありません。セーブ名の選択画面も未実装のため、起動前の環境変数で切り替えます。

```powershell
$env:KADOKA_GDSCRIPT_SAVE_ROOT = 'C:\任意の専用フォルダ\savedata'  # 絶対パス
$env:KADOKA_GDSCRIPT_SAVE_NAME = '冒険1'  # 未指定ならdefault
& '<Godotの実行ファイル>' --path '<このリポジトリ>\gdscript'
```

初回F5では `state.json`、`meta.json`、`items/items.json` と `monsters/`、`parties/` を作成します。形式は [Named save data](../docs/FORMATS.md#named-save-data) に合わせ、主人公とボールスライムをLv1で生成して `current_party` へ入れます。個体IDはランダムな `monster_<12桁hex>`、各個体は既存形式の `monster.json / ai.json` を持ちます。保存先の変更やセーブ名の指定だけではフォルダを作らず、F9も読込だけです。

既存セーブでは `state.json` の `map_id` と `player.x/y/direction` だけを更新し、進行フラグ・復活地点・現在パーティ・未知キーを引き継ぎます。向きのない旧形式は正面で復元します。既存の個体・AI・アイテム・パーティプリセット・metaファイルは書き換えません。既存セーブへ初期仲間を自動追加せず、前段階で作った空のセーブも勝手には変更しません。新規開始を試すには未使用のセーブ名を指定します。既存Pythonセーブを試すときは専用のコピーを使い、両版を同じ保存先で同時実行しないでください。

壊れたJSON、未対応schema、存在しないマップ、範囲外や壁/看板/固定モブ上の座標は、読込・上書きを拒否して理由を表示します。一時ファイルからの置換に失敗しても、以前の `state.json` を削除しません。読み直した内容のdigestが変わった場合も保存を拒否します。初回作成は複数ファイル一括トランザクションではなく、失敗時に未完成のフォルダが残る場合があります。JSONの再出力によりstateの空白や数値表記は変わり、Godotの数値精度を超えるMOD値の無損失往復は保証しません。

個体の2ファイルは固有の一時フォルダに書いてから公開します。state保存が後で失敗しても、次の初回保存は公開済みの主人公/ボールスライムを再利用し、同種の初期仲間を重複生成しません。初回保存前の既存個体に破損があれば生成を拒否し、修復や削除を自動実行しません。並行する複数writerの排他はまだ保証しません。

## 個体・パーティの確認

ゲーム内のF6で一覧を開き、F6またはEscで閉じます。↑↓、PageUp/Down、Home/Endと縦スクロールバー・ホイールで移動できます。開いている間は主人公の移動、調べる、F5/F9を止めます。

一覧は先頭4つのパーティ枠と全保有個体を表示し、所有数にプログラム上の上限を設けません。表示項目は名前・種族・Lv・＋選択数・装備ID・AIプロファイル/作戦・戦闘経験回数です。＋効果/装備補正の計算やステータス・スキル再構築、AI判断/学習はまだ実装していません。既存のAI JSONは保持・確認するだけです。

一覧を開く際に個体フォルダを再走査しますが、これは所有フォルダ内の読込で、外部importsからの獲得ではありません。欠損/破損・不正ID・未対応schema・未知種族の個体は注意を表示して除外し、元ファイルは削除/修復しません。パーティの欠損IDは「読込不可」、nullは空き枠として表示し、保存された順番やIDは書き換えません。個体IDには日本語も使用でき、フォルダ名とJSON内のIDの一致が必要です。

## 現在パーティの編成

F6の一覧でEまたは「パーティを編成する」を押します。新規プロフィールは先にフィールドのF5で保存してください。左の4枠から編集する枠、右の保有個体から仲間を選び、「選択個体を入れる」または右リストのEnterで入れ替えます。「選択枠から外す」またはDeleteでnullの空き枠にできます。順番を変えるときは元の枠を空けてから別枠へ入れます。同じ個体の複数枠への追加は拒否します。主人公の固定枠は設けず、空編成もPythonの現行管理と同様に許可します。

↑↓・Home/End・PageUp/Downで選択、Tab/Shift+Tabでリストとボタンを巡回できます。保有数に合わせて右リストがスクロールします。Ctrl+S/「編成を保存」で反映、Esc/F6/「キャンセル」で下書きを破棄して一覧へ戻ります。閉じる操作で自動保存しません。編成中は移動・調べる・F5/F9を止めます。

保存は既存 `state.json.current_party` だけを4枠のID/null配列へ変更します。保存済み位置・フラグ・未知キーと個体/AI/items/meta/プリセットを保持します。未保存のフィールド位置はそのままで、編成保存は位置保存の代わりにはなりません。変更なしで保存した場合はstateも書き換えません。

保存前に所有フォルダを再走査し、選択個体を再検証します。欠損/重複の既存IDは自動修復せず、該当枠を明示的に外してください。5枠以上や不正な枠型は編成を開く時点で拒否し、切り捨てません。編集中のstate外部更新、破損JSON、置換ロック等の保存失敗では上書きせず下書きを残します。外部更新時はキャンセルして編成を開き直してください。digest確認は並行writerの完全な排他ではありません。

## 未移植

戦闘、野生敵、AI判断/学習/リセット、固定モブの徘徊/会話、暗号/仲間取得、牧場への導線、個体編集/パーティプリセット、外部個体取得/模擬戦、セーブ選択UI・コピー/インポート、各エディタ、ランチャー、配布exportは未実装です。教会などは「未移植」を表示し、副作用を起こしません。Python版の置換・完成版ではありません。

現在はsource checkout専用です。正本がGodotのresource root外にあるため、export済みexeでこのまま共有コンテンツを読めるとは主張しません。配布時のコンテンツ配置とexportは別段階で検証します。

## 責務と検証

`engine/field_engine.gd` は純粋な辞書の空間判定、`engine/field_save_contract.gd` と `monster_record_contract.gd` は保存/個体/初期AIの純粋な契約、`data/` はJSON/名前付き保存/個体フォルダのI/O、`application/field_session.gd` は一時状態、`field_persistence.gd` は永続化の調停、`owned_roster.gd` は検証とゲーム固有の初期仲間選択、`field_application.gd` はSceneの接続、`ui/` は入力/描画/画像変換です。rendererはゲーム状態を変更しません。正規data/assetsはread-only、書込は選択したGodot用セーブに限定します。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotのconsole実行ファイル>'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_bootstrap.py tests/test_gdscript_save.py tests/test_gdscript_roster.py tests/test_gdscript_party.py -q
$env:KADOKA_GDSCRIPT_SAVE_ROOT = 'C:\任意の検証専用フォルダ\savedata'
$env:KADOKA_GDSCRIPT_SAVE_NAME = 'smoke'
& $env:KADOKA_GODOT_EXECUTABLE --headless --path gdscript --editor --import
& $env:KADOKA_GODOT_EXECUTABLE --headless --path gdscript --quit-after 3
```

Python版FieldEngineとの同一入力/出力比較、正本の読込一致、実Sceneの入力・移動ポイント・F5/F9と別プロセス再起動、旧形式・名前付きセーブの互換、保存失敗時の不変性をheadlessで検証します。テストは実セーブを使わず一時コピーに保存します。Windowsでは実ファイルの置換ロックも検証します。Godotの指定がない環境では実エンジンテストは理由付きskipになります。skipは移植成功ではありません。

関連: #10/#111、[移植境界](../docs/移植境界機能説明書.md)。次の段階では個体・戦闘などを、既存の期待動作カタログと比較しながら移植します。今回のテストをPython版のE2Eカタログ全項目の移植済み証拠とは扱いません。

Godot APIの根拠: [コマンドライン](https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html)、[JSON](https://docs.godotengine.org/en/stable/classes/class_json.html)、[Image](https://docs.godotengine.org/en/stable/classes/class_image.html)。
保存I/O: [user://](https://docs.godotengine.org/en/stable/tutorials/io/data_paths.html)、[FileAccess](https://docs.godotengine.org/en/stable/classes/class_fileaccess.html)、[DirAccess](https://docs.godotengine.org/en/stable/classes/class_diraccess.html)。
一覧/編成UI: [ScrollContainer](https://docs.godotengine.org/en/stable/classes/class_scrollcontainer.html)、[ItemList](https://docs.godotengine.org/en/stable/classes/class_itemlist.html)。

編成の責務: `engine/party_selection.gd` は純粋な4枠の下書き/選択規則、`application/party_editor.gd` は下書き所有と保存前再検証、`ui/party_view.gd` は入力/表示と操作signal。Sceneは結果表示と接続、既存Dataはstateのatomic更新を担当します。
