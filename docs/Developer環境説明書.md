# Kadoka Quest Developer 環境説明書

## 目的

`KadokaQuestDeveloper` は「開発機能を追加したゲーム」ではなく、**Player版 Kadoka Quest を制作・検証・ビルドするための開発環境**である。

Developer版の責務は次の流れを1つの制作フローとして提供すること。

```text
Playerコンテンツ編集
↓
Project Validation
↓
Player Preview / Test Run
↓
Player Distribution Build
↓
Distribution Smoke Test
```

## 依存方向

```text
Developer UI / tools
        ↓
Developer workflow services
        ↓
共通 data/domain + Player runtime + build/smoke core
        ↓
Player data / assets
```

Player側からDeveloper UI・Developer workflow・Editorを参照してはいけない。

Developer側はPlayer runtimeと共通data/domainを利用してよい。これによりDeveloper内だけで成功する別実装を作らず、Playerで実際に動く経路を確認する。

## 正規データ

各EditorはPlayer runtimeが直接読み込む次の正規構造を編集する。

- `data/`
- `assets/`

Developer専用の中間形式へ保存してからPlayer用へ変換する方式を標準にはしない。

Player配布ビルド時にも、この正規 `data/` / `assets/` がそのまま配布物へコピーされる。

## Content Editors

Developer画面の左側はPlayerコンテンツ編集領域である。

現時点の主な入口:

- 個体・パーティ管理（開発用）
- Block Editor
- Map Editor
- Monster Editor
- Data Creator

Skill / Item / Asset / Balance等の編集機能は、追加時も同じDeveloper環境へ統合する。

## Player Workflow

Developer画面の右側は制作結果をPlayerとして確認する領域である。

### 1. Playerデータを検証

`ProjectValidator` がPlayerの `data/` / `assets/` をpygame UIに依存せず検証する。

主な検証:

- JSONが読み込めること
- Block IDの整合
- Mapのwidth/heightとtile配列の整合
- Mapが未知Block / Species / 遷移先を参照していないこと
- Speciesフォルダ名とSpecies IDの整合
- Lv1〜100のステータス定義
- Skill参照の整合
- Speciesが参照する画像Assetの存在

エラーはPlayer PreviewやBuildより前に発見できることを目的とする。

### 2. Player Preview / Test Run

Developer版からPlayer runtimeそのものを起動する。

- ソース実行: `launcher.py --play`
- frozen Developer版: Developer exe内に含まれる同一Player runtimeを `--player-preview` で起動

Developer専用ゲーム挙動を別実装してPreviewとして扱わない。

### 3. Player配布ビルド

BAT / CLI / Developer GUIはいずれも `kadoka_quest.developer.build_core` の共通処理を利用する。

```text
build_player.bat ─┐
tools/build/build.py ─┼→ build_core → dist/KadokaQuest/
Developer GUI ────────┘
```

ソース版のBAT/CLIはPyInstallerでPlayer runtimeを生成する。Developer配布版には、Developer自身を生成した時点と同じPlayer runtimeの**コンテンツなし雛形** `PlayerRuntimeTemplate/KadokaQuest/` を同梱する。

Developer配布版の「Player Build」はこの雛形を複製し、現在編集中の正規 `data/` / `assets/` と空の `UserData/` を組み合わせる。したがって配布Developer版の中でPyInstallerを再帰実行する必要がなく、Python環境がないPCでもPlayer成果物を生成できる。

PlayerRuntimeTemplateには `data/`、`assets/`、`UserData/` を保持しない。編集前のデータやCI用セーブがBuild結果へ混入することを防ぐ。

生成されるPlayer版へDeveloper UI/Editor/Build資材は追加しない。

### 4. Player配布物スモーク

`kadoka_quest.developer.distribution_smoke` を共通実装として使用する。

Player完成exeを外部プロセスとして起動し、少なくとも以下を検査する。

- Player launcher
- game runtime
- ranch manager
- `data/` / `assets/` 配置
- `UserData/` 初期化
- exit code

テスト後の `UserData` は配布用の空状態へ戻す。

## Developer配布版からのPlayerビルド

`KadokaQuestDeveloper.exe` は内部自動化コマンドを持つ。

```text
--validate-project
--player-preview
--build-player
--smoke-player-build
```

GUIはこれらと同じサービスを利用する。CI/CUIからも同じ経路を呼べるため、GUI専用処理にしない。

Developer配布版が生成するPlayer成果物は次に置く。

```text
KadokaQuestDeveloper/
├─ PlayerRuntimeTemplate/
│  └─ KadokaQuest/
│     ├─ KadokaQuest.exe
│     └─ _internal/
└─ dist/
   └─ KadokaQuest/
      ├─ KadokaQuest.exe
      ├─ _internal/
      ├─ data/
      ├─ assets/
      └─ UserData/
```

## ログ

Developer GUIからのBuild/Smokeはバックグラウンドプロセスで実行し、UIをビルド処理そのものに結合しない。

ソース実行時:

```text
build/developer/
├─ player-build.log
└─ player-smoke.log
```

Developer配布版:

```text
UserData/developer/
├─ project-validation.log
├─ player-build.log
└─ player-smoke.log
```

## CI保証

Windows distribution CIでは通常のPlayer/Developerビルドとスモークに加え、完成した `KadokaQuestDeveloper.exe` 自身に次を実行させる。

```text
Developer exe
↓
Player project validation
↓
同梱PlayerRuntimeTemplate + 現在のdata/assetsからPlayer配布物生成
↓
その生成Player exeをdistribution smoke
```

これにより「ソースではビルド可能だが配布Developer版からはビルドできない」状態を検出する。

## 今後の拡張

新しいEditor・Validator・Balance Analyzer・Simulation等は、可能な限りpygame UIから処理を分離し、Developer GUI / CLI / CI / Codex等から再利用できる単位として追加する。
