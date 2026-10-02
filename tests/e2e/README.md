# Source E2E

期待動作と未対応一覧の正本は [E2E_EXPECTATIONS.md](../../docs/testing/E2E_EXPECTATIONS.md)。#201の決定的harnessと基盤検証は実装済み。主要なユーザー操作シナリオは引き続きmissingで、#202（起動・探索・イベント・保存）、#203（戦闘）、#204（牧場・個体・パーティ）で追加する。基盤テストの成功だけでカタログをcoveredにしない。

各テストはカタログIDとGiven/When/Thenを示し、操作を本番runtime/command境界へ渡す。RNG・clock・SDL・セーブ/インポート領域を隔離し、永続化項目はruntime/Storeを作り直して再読込する。ゲーム結果を生成する専用ロジックやsleepによる待機を作らない。

E2E追加後は成功したテストのnode IDをカタログに登録する。通常のunit/integration/smokeを移動しただけでcovered扱いにしない。

## 実行とファイルの責務

```text
python -m pytest tests/e2e/test_harness.py -q --basetemp=<専用の一時ディレクトリ>
```

pygame-ceとpytestを導入したPythonを使う。共有一時領域がWindowsでロックされる場合は、実行ごとに新しいbasetempを指定する。CI/qualityコマンドへの専用統合は #205。

- `harness.py`: pytest側のScenarioRunner。runごとに専用ディレクトリを作り、同じPythonの別プロセスを起動する。
- `worker.py`: ゲームimport前の保存先検証、SDL・clock・UUID境界の隔離。既存の本番composition root `KadokaQuest` を作る。
- `runtime_driver.py`: 本番 `RuntimeInputAdapter` へSDLイベントを渡し、`RuntimeOrchestrator` に要求を送る。frameはmainと同じmanager.refreshとfield/battle.tickのみ。ゲーム結果の実装を持たない。
- `scenario_clock.py`: sleepを使わない単調なミリ秒clock。プリセット名の日時も2000-01-01基準の同じclockから供給する。
- `observations.py`: 実際の状態・個体/AI・パーティ・モブ・戦闘・保存JSONを読んだcheckpoint。描画用movement.positionなど状態を変えるgetterは呼ばない。
- `conftest.py`: `scenario_runner` fixture。
- `test_harness.py`: 基盤の校正・反復再現性・別シード・隔離・失敗診断・fixture非破壊を検証する。

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

## 隔離と検証境界

各子プロセスは `KADOKA_SAVE_DIR` / `KADOKA_SAVEDATA_ROOT` / `KADOKA_IMPORT_DIR` を新しいrun領域へ設定し、親の利用者セーブ先を上書きする。ゲームimportの前に設定するため、全テスト実行中に親でpath定数が既にimport済みでも影響しない。data/assetsは既定では正規リポジトリを読む。削除や利用者の実セーブ操作は行わない。

headless SDLでキーボードとsemantic commandを実行するsource E2Eであり、実ウィンドウの描画、マウス座標・virtual keyboardの見た目、Player/Developer EXE、ランチャーのクリック操作を検証したとは主張しない。外部管理アプリの起動は明示的な失敗にし、偽の成功結果や実プロセスを返さない。複数アプリ用driverは #204、simulationの本番依存解決は #214。harnessだけでsimulation hookを追加することはしない。
