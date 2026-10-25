# Source E2E

期待動作と未対応一覧の正本は [E2E_EXPECTATIONS.md](../../docs/testing/E2E_EXPECTATIONS.md)。#201の決定的harnessと #202の起動・探索・イベント・保存（KQ-P01～P12）は実装済み。残りの主要操作はmissingで、#203（戦闘）、#204（牧場・個体・パーティ）などで追加する。基盤テストの成功だけでカタログをcoveredにしない。

各テストはカタログIDとGiven/When/Thenを示し、操作を本番runtime/command境界へ渡す。RNG・clock・SDL・セーブ/インポート領域を隔離し、永続化項目はruntime/Storeを作り直して再読込する。ゲーム結果を生成する専用ロジックやsleepによる待機を作らない。

E2E追加後は成功したテストのnode IDをカタログに登録する。通常のunit/integration/smokeを移動しただけでcovered扱いにしない。

## 実行とファイルの責務

```text
python -m pytest tests/e2e -q --basetemp=<専用の一時ディレクトリ>
```

pygame-ceとpytestを導入したPythonを使う。共有一時領域がWindowsでロックされる場合は、実行ごとに新しいbasetempを指定する。CI/qualityコマンドへの専用統合は #205。

- `harness.py`: pytest側のScenarioRunner。runごとに専用ディレクトリを作り、同じPythonの別プロセスを起動する。
- `worker.py`: ゲームimport前の保存先検証、SDL・clock・UUID境界の隔離。既存の本番composition root `KadokaQuest` を作る。
- `runtime_driver.py`: 本番 `RuntimeInputAdapter` / パスワードの `RuntimeMouseAdapter` へSDLイベントを渡し、`RuntimeOrchestrator` に要求を送る。frameはmainと同じmanager.refreshとfield/battle.tickのみ。ゲーム結果の実装を持たない。
- `launcher_driver.py`: 本番Player `launcher.main()` にSDLのクリック/文字入力を送る。実際の保存ボタンを通し、外部起動要求の選択セーブ先を受け取る。clock.tickは16msを進め次のイベントをqueueへ送るだけで、sleepしない。
- `render_observation.py`: 本番field/password rendererを実行し、実描画テキスト・画像選択・主人公の表示座標を観測する。各spyは元の描画/画像読込へ委譲し、ピクセル完全一致や代替描画を行わない。
- `scenario_clock.py`: sleepを使わない単調なミリ秒clock。プリセット名の日時も2000-01-01基準の同じclockから供給する。
- `observations.py`: 実際の状態・個体/AI・パーティ・モブ・戦闘・保存JSONを読んだcheckpoint。描画用movement.positionなど状態を変えるgetterは呼ばない。
- `conftest.py`: `scenario_runner`、保存済み開始位置、正規dataをコピーした明示的な小マップfixture。障害物/遷移はJSON上で準備し、実行中のアクターを直接差し替えない。
- `test_harness.py`: 基盤の校正・反復再現性・別シード・隔離・失敗診断・fixture非破壊を検証する。
- `test_field_journeys.py`: カタログID付きの新規開始、名前付きload、別名保存、移動/衝突/長押し、正規マップ遷移、会話、湧き場の暗号/取消と保存/reload。

## シナリオを書く

```python
def test_example(scenario_runner):
    report = scenario_runner.run([
        {"kind": "key_down", "key": "right", "label": "pressed"},
        {"kind": "advance", "ms": 200, "frame_ms": 20},
        {"kind": "key_up", "key": "right"},
        {"kind": "reload", "label": "loaded"},
    ], seed=7, start_ms=123)
    assert report["checkpoints"]["loaded"]["player"]["x"] == 20
```

`initial`/`final`と、任意の一意なlabelでcheckpointを取得する。比較対象は `checkpoints`（絶対パスを含まない）とする。報告のpathsは各runで異なる。エラーには操作番号・label/kindと本来の例外を残し、未知の要求を成功扱いにしない。

操作は `key_down` / `key_up`（pygameのキー名）、`text`（password用のUnicodeキー列）、`command`（target/action/plain payload）、`advance`、`reload`、`snapshot`。commandの必要なnowはclockから渡す。異なるnow、負の時間、0のframe_msは拒否する。advanceは16ms刻みが既定で、残り端数も実行する。フレーム間隔もシナリオの一部なので固定する。長い進行にはフレーム予算がある。

`reload`は同じ保存先から**Store・セッション・runtimeを作り直す**操作で、子プロセスの再起動ではない。game RNGは指定seedで再初期化、clockは継続、個体IDは保存値を再利用する。UUID生成はseedと初期セーブの既存個体ID一覧に基づく別乱数列で固定し、本番game RNGの消費数を変えない。既存セーブからの新規獲得で初期個体のID列をそのまま再発行しない。

`data_dir` / `asset_dir`で正規形式のfixtureを渡せる。`save_fixture`は初期セーブのコピー元で、専用profileへコピーしてから本番loader/Storeが読む。元fixtureは編集しない。モブ位置や勝敗などをharnessから直接注入するAPIは用意しない。

## ランチャー・描画・仮想キー

`launcher` stepの `frames` はフレームごとの入力配列。各入力は `click`（pos）、`key`（pygameキー名、任意unicode）、`text`（文字列）。Button/TextFieldの本番handleで処理され、create/copy/set_activeをテストから直接代替実装しない。1 stepにつきゲーム開始は1回まで。OSのPopen境界で起動先を受け取り、その保存先の本番MonsterStore/StateStore/PartyStoreをKadokaQuestへ注入して組み直す。これは子プロセス内のcomposition root引き継ぎで、ゲームwrapperのプロセスを起動した証拠ではない。

テストの私有launcher-projectに正規のgame.pyをコピーし、launcherのPROJECT_ROOTをその領域に限定する。これにより通常source入口の任意legacy-save検索が利用者の旧savesへ触れない。data/assetsとpackageは正規ソースを使用する。保存メタデータのdatetime.now境界も固定clockを使う。

`render` stepはSurfaceへ本番描画し、最後の観測をcheckpointの `render` に残す。fieldでは実際の表示位置を確定させるので、通常のreadonly snapshotとは分けて明示的に使う。`password_click`（valueが仮名、backspace/submit/cancel）は本番password_controlsの矩形中心へ実mouseイベントをpostする。独自の暗号処理を呼ばない。戦闘mouseと他画面のrenderはこのdriverには未対応。

checkpointの `saved_profiles` は名前別の実保存JSON、`active_save` は本番SaveDataManagerの選択値、`launcher_runs` は実際の生成コントロールとhandoff名。変更元セーブや別セーブが不変なことも比較する。

## 隔離と検証境界

各子プロセスは `KADOKA_SAVE_DIR` / `KADOKA_SAVEDATA_ROOT` / `KADOKA_IMPORT_DIR` を新しいrun領域へ設定し、親の利用者セーブ先を上書きする。ゲームimportの前に設定するため、全テスト実行中に親でpath定数が既にimport済みでも影響しない。data/assetsは既定では正規リポジトリを読む。削除や利用者の実セーブ操作は行わない。

headless SDLのクリック/キーボードと本番renderer/semantic commandを実行するsource E2Eであり、実ウィンドウの視認性・マウス操作、ピクセル完全一致、Player/Developer EXE、OSの実プロセス起動を検証したとは主張しない。外部管理アプリの起動は明示的な失敗にし、偽の成功結果や実プロセスを返さない。複数アプリ用driverは #204、simulationの本番依存解決は #214。harnessだけでsimulation hookを追加することはしない。

## Godot版のE2E

Godot版のE2Eは、Python版のharnessとは別に `godot_harness.py` と `gdscript/tests/e2e_driver.gd` が実行します。開発者は、`KADOKA_GODOT_EXECUTABLE` にGodot 4.7.2のコンソール実行ファイルを設定してから、次のコマンドを実行してください。Godotが見つからない環境では、Godot版のE2Eはskipになります。skipはGodot版のE2Eが成功したことを意味しません。

```text
python -m pytest tests/e2e/test_godot_title_journeys.py tests/e2e/test_godot_harness.py -q --basetemp=<専用の一時ディレクトリ>
```

- `godot_harness.py`: `GodotScenarioRunner` は、テストごとの専用フォルダと専用の保存先を所有します。`run(steps)` を呼ぶたびに、新しいGodotプロセスを `--headless --fixed-fps 60` で起動します。二回目以降の `run` は同じ保存先を使うため、利用者がゲームを終了して起動し直す操作と同じ再起動になります。`KADOKA_GDSCRIPT_SAVE_NAME` を外して起動するため、利用者と同じくタイトル画面から始まります。新しいcheckoutでは、最初の実行前に資源のimportを一度だけ行います。
- `e2e_driver.gd`: project.godotの `run/main_scene` を読み込み、本番の起動と同じく現在の画面に設定します。操作は `Input.parse_input_event` へキーと確定文字を送るだけで、保存・移動・画面切替のメソッドを直接呼びません。観測は画面の状態を読み取るだけです。
- `saved_states()` は各セーブの state.json を、`saved_files()` は保存先の全ファイルを読みます。再開しただけでセーブが変わらないことの比較に使います。

操作は `key`（ENTER・ESCAPE・TAB・SPACE・BACKSPACE・方向キー・F5・F9）、`text`（IMEを通さない確定文字）、`hold`（keyとframes）、`frames`（count）、`wait_scene`（nameとmax_frames）、`snapshot`（一意なlabel）です。`initial` と `final` は自動で記録します。未知の操作、未対応のキー、上限までに切り替わらない画面、重複したlabelは、操作番号付きの失敗になります。

Godot版のE2Eは、headlessのGodotで実際の起動画面・入力経路・保存先・プロセスの再起動を検証します。実ウィンドウの表示、IME、物理ゲームパッド、配布exportを検証したとは主張しません。
