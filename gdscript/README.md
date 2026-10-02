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

## フィールドのセーブ／ロード

既定の保存先はGodotの `user://savedata/default/` で、Python版のリポジトリ内 `savedata/` とは別です。`user://` の実際の場所はGodot/OSのユーザーデータ設定に従います。移動ごとの自動保存はまだありません。セーブ名の選択画面も未実装のため、起動前の環境変数で切り替えます。

```powershell
$env:KADOKA_GDSCRIPT_SAVE_ROOT = 'C:\任意の専用フォルダ\savedata'  # 絶対パス
$env:KADOKA_GDSCRIPT_SAVE_NAME = '冒険1'  # 未指定ならdefault
& '<Godotの実行ファイル>' --path '<このリポジトリ>\gdscript'
```

初回F5では `state.json`、`meta.json`、`items/items.json` と `monsters/`、`parties/` を作成します。形式は [Named save data](../docs/FORMATS.md#named-save-data) に合わせますが、まだ主人公や初期仲間の個体生成はしません。保存先の変更やセーブ名の指定だけではフォルダを作らず、F9も読込だけです。

既存セーブでは `state.json` の `map_id` と `player.x/y/direction` だけを更新し、進行フラグ・復活地点・現在パーティ・未知キーを引き継ぎます。向きのない旧形式は正面で復元します。既存の個体・AI・アイテム・パーティプリセット・metaファイルは書き換えません。ただし、これはフィールド保存のみの互換性で、モンスターやAIをゲーム内で利用できるという意味ではありません。既存Pythonセーブを試すときは専用のコピーを使い、両版を同じ保存先で同時実行しないでください。

壊れたJSON、未対応schema、存在しないマップ、範囲外や壁/看板/固定モブ上の座標は、読込・上書きを拒否して理由を表示します。一時ファイルからの置換に失敗しても、以前の `state.json` を削除しません。読み直した内容のdigestが変わった場合も保存を拒否します。初回作成は複数ファイル一括トランザクションではなく、失敗時に未完成のフォルダが残る場合があります。JSONの再出力によりstateの空白や数値表記は変わり、Godotの数値精度を超えるMOD値の無損失往復は保証しません。

## 未移植

戦闘、野生敵、AI/学習、固定モブの徘徊/会話、暗号/仲間取得、牧場、個体生成/管理、セーブ選択UI・コピー/インポート、各エディタ、ランチャー、配布exportは未実装です。教会などは「未移植」を表示し、副作用を起こしません。Python版の置換・完成版ではありません。

現在はsource checkout専用です。正本がGodotのresource root外にあるため、export済みexeでこのまま共有コンテンツを読めるとは主張しません。配布時のコンテンツ配置とexportは別段階で検証します。

## 責務と検証

`engine/field_engine.gd` は純粋な辞書の空間判定、`engine/field_save_contract.gd` は保存の純粋な検証/組立、`data/` はJSON/名前付き保存のI/O、`application/field_session.gd` は一時状態、`application/field_persistence.gd` は永続化の調停、`application/field_application.gd` はSceneの接続、`ui/` は入力/描画/画像変換です。rendererはゲーム状態を変更しません。正規data/assetsはread-only、書込は選択したGodot用セーブに限定します。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotのconsole実行ファイル>'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_bootstrap.py tests/test_gdscript_save.py -q
$env:KADOKA_GDSCRIPT_SAVE_ROOT = 'C:\任意の検証専用フォルダ\savedata'
$env:KADOKA_GDSCRIPT_SAVE_NAME = 'smoke'
& $env:KADOKA_GODOT_EXECUTABLE --headless --path gdscript --editor --import
& $env:KADOKA_GODOT_EXECUTABLE --headless --path gdscript --quit-after 3
```

Python版FieldEngineとの同一入力/出力比較、正本の読込一致、実Sceneの入力・移動ポイント・F5/F9と別プロセス再起動、旧形式・名前付きセーブの互換、保存失敗時の不変性をheadlessで検証します。テストは実セーブを使わず一時コピーに保存します。Windowsでは実ファイルの置換ロックも検証します。Godotの指定がない環境では実エンジンテストは理由付きskipになります。skipは移植成功ではありません。

関連: #10/#111、[移植境界](../docs/移植境界機能説明書.md)。次の段階では個体・戦闘などを、既存の期待動作カタログと比較しながら移植します。今回のテストをPython版のE2Eカタログ全項目の移植済み証拠とは扱いません。

Godot APIの根拠: [コマンドライン](https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html)、[JSON](https://docs.godotengine.org/en/stable/classes/class_json.html)、[Image](https://docs.godotengine.org/en/stable/classes/class_image.html)。
保存I/O: [user://](https://docs.godotengine.org/en/stable/tutorials/io/data_paths.html)、[FileAccess](https://docs.godotengine.org/en/stable/classes/class_fileaccess.html)、[DirAccess](https://docs.godotengine.org/en/stable/classes/class_diraccess.html)。
