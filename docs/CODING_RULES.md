# Kadoka Quest Coding Rules

Kadoka Quest の実装では、責務を小さく保ち、呼び出し経路を明示する。

本規約は [UPD Commander Base Design](https://github.com/tomiya7688/upd-commander-base-design) の考え方を Kadoka Quest の既存アーキテクチャへ適用したものとする。

## 基本原則

- 1ファイル1責務を基本とする。
- 1関数1処理を基本とする。
- 1クラスは1つの明確な責務を持つ。
- 呼び出しを担当するものと、実処理を担当するものを分離する。
- UI、ゲーム処理、データ処理の境界を越える直接アクセスを原則として避ける。
- 既存の責務境界を越える機能追加では、呼び出し元へ処理を足すのではなく、適切な処理モジュールへ委譲する。

## UI / Process / Data

概念上、処理は次の3領域へ分離する。

### UI

入力受付、描画、UI状態、表示形式への変換を担当する。

UIはゲームルールや永続化処理を直接実装しない。

### Process

ゲームルール、計算、判定、状態遷移、アプリケーション上の意味処理を担当する。

Processはpygame等のUIフレームワークへ依存せず、表示方法を知らないことを基本とする。

### Data

ファイルI/O、設定読込、保存、シリアライズ、デシリアライズ、保存形式から利用形式への変換を担当する。

DataはUI表示判断やゲームルール判断を持たない。

## Commander相当の責務

Kadoka Questでは `*_command_app.py`、orchestrator、その他の呼び出し調停モジュールがCommander相当となり得る。

Commander相当のコードは次だけを担当する。

- 要求を受け取る。
- 呼び出す処理を選ぶ。
- 適切なService / Session / Processingへ処理を委譲する。
- 結果を次の処理または呼び出し元へ渡す。

以下の実処理をCommander相当へ蓄積しない。

- ダメージ等の数値計算
- 複雑な条件判定
- データ変換
- ファイル読み書き
- UI描画
- ゲームルールそのもの

判断基準は次の通り。

> どの処理を呼ぶかはCommander相当。処理をどう実行するかは処理モジュール。

## Messenger / Command境界

層を越える要求や返却値は、既存のcommand/application境界を利用する。

- command payloadはplain dataを維持する。
- UIイベント、pygame Surface、ファイルハンドル等を層間契約へ持ち込まない。
- 通信・ルーティング部へゲーム処理やデータ加工を実装しない。
- 隣接する責務境界を飛び越えて内部実装を直接呼ばない。

## ファイルと関数の分割

ファイル名から責務を一文で説明できない場合、分割を検討する。

関数名から1つの動作を説明できない場合、分割を検討する。

特に以下を分割の兆候とする。

- 1関数内で入力処理、計算、保存、描画を複数行う。
- 1ファイルが複数の独立した機能群を所有する。
- 条件分岐によって全く異なる責務を大量に処理する。
- Commander / orchestratorが具体的な処理内容を知りすぎる。
- 他の機能から内部状態を直接触る必要が増えている。

## Kadoka Questでの適用

既存構成では、おおむね次のように扱う。

- `ui/`: UI領域
- `core/`, `application/`, `apps/*_session.py`, `apps/*_service.py`: Process領域
- `data/`: Data領域
- `*_command_app.py`, `runtime_orchestrator.py`: Commander / routing相当

これは名称を強制する規則ではなく、責務と依存方向を守るための指針である。

新規コードを必ず `Commander` / `Messenger` という名前にする必要はない。

## 禁止・非推奨

- UIからData層の内部処理を直接呼ぶ。
- renderer内でゲーム状態を進行させる。
- Data層でゲームルールを判断する。
- command routerへ実処理を追加する。
- 便利だからという理由だけで巨大なmanager / utils / helperへ処理を集約する。
- 既存のSession / Service / Processingを迂回して内部状態を直接変更する。

## UPD Commander checker

Kadoka QuestではUPD CommanderのPython checkerを開発・CI時の静的検証として使用する。checker自体をPlayer runtimeへimportしたり、ゲームループから呼び出したりしてはならない。

標準実行:

```text
python -m pip install -r tools/upd-commander/requirements.txt
python tools/upd-commander/script/check.py
```

標準実行ではUPDのErrorを失敗扱いとする。WarningとAttentionは、既存の責務集中やContainer化候補を段階的に解消するための移行情報として表示するが、通常CIは失敗させない。

一時的な調査だけでErrorを非blocking表示したい場合は次を使用できる。

```text
python tools/upd-commander/script/check.py --advisory
```

`--advisory` は完了判定の代替には使用しない。

UPD checkerの指摘を避ける目的だけで形式的なCommander / Messenger / Serviceを増やしてはならない。分離により呼び出し回数・アロケーション・変換処理がホットパスで増える場合は、既存の単純な経路を優先してよい。

性能上やむを得ない局所例外は、UPD checkerが対応する理由付きignoreを対象規則だけへ付ける。

```python
value = fast_path(left, right)  # upd: ignore UPD203 - performance hot path
```

`all` による広域抑制は原則使用しない。

## 実行速度の保護

UPD設計適用によるオーケストレーション層の増加が本体速度へ露骨な退行を起こしていないか、開発用performance checkerで確認する。

```text
python tools/performance-check/script/check_runtime_performance.py
```

このcheckerは `AppCommand`、plain payload検証、`CommandBus` dispatch、およびcommand生成+dispatchのCPUコストを外部から計測する。計測処理はPlayer runtimeへ組み込まない。

CIの絶対時間には環境差があるため、閾値は細かな最適化競争ではなく、設計変更により処理コストが桁違いに増えた場合を検出するための余裕ある上限とする。性能を理由にUPD規約を例外化する場合は、可能なら変更前後のperformance checker結果を比較し、例外理由をコード上へ残す。

## 検証

- 通常のCIを通過すること。
- Pythonコード変更後はプロジェクトで定めるformatter / linter / testを実行すること。
- 新規依存がUI / Process / Dataの境界を破っていないことをレビューすること。
- 巨大化したファイルや関数は、機能追加の際に責務分割を優先すること。
- アーキテクチャ変更ではUPD checkerを実行し、runtime経路へ層を追加する変更ではperformance checkerも実行すること。
