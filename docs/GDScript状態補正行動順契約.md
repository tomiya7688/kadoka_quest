# GDScriptの状態補正済み行動順

## 背景・目的・範囲

基礎速度だけの行動順では、出血や一時速度倍率による順序の変化を再現できません。`engine/status_turn_order.gd` は、最新状態と明示された一時倍率から実効速度を求め、生存者の順序を計算します。補正式は[状態能力値補正](GDScript状態能力値補正契約.md)、同速時の安定順序は[基礎行動順](GDScript行動順契約.md)へ委譲します。

状態補正行動順の契約は開発者向けの純粋APIで、画面操作ではありません。状態補正行動順の契約はHP/MP・状態・一時倍率・行動予約を保持または更新せず、I/O・乱数生成・AIを行いません。状態付きSessionのラウンド開始は、一時倍率なしの明示1で本契約へ接続しました。倍率の保持と期限管理、継続効果、AI、戦闘画面への接続は未実装です。状態補正行動順の追加では、従来の基礎順序API、数値snapshot六キー、Session七キー、保存JSON/schema、Pythonのゲーム動作と白黒GUIを変更しません。

## 開発者の呼び出し方法

開発者は `preload("res://engine/status_turn_order.gd")` の `plan(request)` へ、次の五キーだけを持つ辞書を渡してください。

```json
{
  "allies": [{
    "identity": {"id": "shared", "species_id": "slime", "name": "味方"},
    "stats": {"hp": 30, "mp": 10, "attack": 20, "defense": 20, "magic": 10, "speed": 11},
    "hp": 30, "mp": 7, "fled": false, "alive": true
  }],
  "enemies": [{
    "identity": {"id": "shared", "species_id": "slime", "name": "敵"},
    "stats": {"hp": 30, "mp": 10, "attack": 20, "defense": 20, "magic": 10, "speed": 10},
    "hp": 30, "mp": 7, "fled": false, "alive": true
  }],
  "statuses": {"allies": {"shared": ["bleeding"]}, "enemies": {"shared": []}},
  "speed_multipliers": {"allies": {"shared": 1.0}, "enemies": {"shared": 1.0}},
  "shuffle_order": [{"side": "allies", "id": "shared"}, {"side": "enemies", "id": "shared"}]
}
```

`allies` と `enemies` は各0〜4体の厳密な数値snapshot列です。`stats.speed` はLv・＋・装備の補正後で、状態と一時倍率をまだ掛けていない値を指定してください。基礎順序契約と同じ型・有限性・整数性・精度上限・HPMP整合性を再検証します。同陣営のID重複と、snapshotへ追加した状態/倍率などの未知キーは拒否します。別陣営の同じIDは許可します。

`statuses` と `speed_multipliers` は、それぞれ `allies/enemies` だけの二辞書です。各陣営の辞書には、生存・死亡・逃走に関わらず全参加者のIDを過不足なく一回ずつ指定してください。状態/倍率の入力では、空の陣営にも空辞書が必要です。状態なしは `[]`、一時倍率なしは `1` を明示してください。状態補正行動順の契約は不足した一覧や倍率を暗黙補完しません。

`statuses` の各値は最新の状態一覧です。状態能力値契約は一覧全体のJSON互換性・深さ32以下を検証し、IDが厳密に `bleeding` の状態が一件以上あれば速度へ0.9倍を一度だけ掛けます。未知IDやJSON互換の拡張情報は補正を増やしません。`speed_multipliers` の各値は0以上9007199254740991以下の有限数値で、boolや数値文字列は拒否します。

実効速度は `max(1, int(base_speed * speed_multiplier * status_multiplier))` です。状態能力値契約は一時倍率を先に掛け、最後だけ整数化します。状態能力値契約は、速度に一時倍率を掛けた途中積が精度上限を超える場合、出血後の積が上限内でも拒否します。開発者は状態補正行動順が返した補正済み速度を補正前の速度として再入力しないでください。

`shuffle_order` は生存者全員の `side/id` を一度ずつ含む明示順です。乱数の生成器やseedの互換は提供しません。生存者が0体なら空配列だけを許可します。死亡/逃走者・未知対象・重複・キー欠損・追加キーは拒否します。同速の参加者は明示順を維持します。片側が空でも、生存する反対側の順序を返します。順序の成功は戦闘継続や勝敗を意味しません。

## 成功・失敗・非変更

味方の補正前速度11・出血・一時倍率1と、敵の補正前速度10・状態なし・一時倍率1を指定した要求では、行動順契約は味方速度9・敵速度10と次の結果を返します。

```json
{
  "ok": true, "scope": "status_turn_order",
  "initial": [{"side": "allies", "id": "shared"}, {"side": "enemies", "id": "shared"}],
  "order": [{"side": "enemies", "id": "shared"}, {"side": "allies", "id": "shared"}],
  "speeds": {"allies": {"shared": 9}, "enemies": {"shared": 10}}
}
```

`initial` は生存者の味方枠順→敵枠順、`order` は実効速度の降順です。`speeds` は死亡/逃走者も含む全参加者の実効速度です。返却する二つの識別キー列は、互いにも入力にも参照を共有しません。速度辞書も独立しています。呼出元が返却値を編集しても、入力や次回の計算は変化しません。

状態補正行動順の契約は、要求型/五キー集合、数値参加者、状態辞書のID集合、一時倍率辞書のID集合、全員の能力値予測、生存者の明示順の順に検証します。状態補正行動順は個体の予測を味方→敵の枠順で行い、死亡/逃走者の不正状態や倍率も拒否します。状態補正行動順は不正な要求に対して `ok=false/reason` と必要な `field/side/id/index/detail/limit` を返し、`initial/order/speeds/scope` の部分成功を返しません。

要求型不正は `invalid_status_turn_request`、五キー集合不一致は `invalid_status_turn_fields`、対応辞書の型/陣営不正は `invalid_turn_map`、参加者ID集合の不一致は `turn_context_mismatch` です。状態/倍率の不正と途中精度超過は状態能力値契約の理由へ `side/id` を加えて返します。数値参加者と明示順の不正は基礎順序契約の理由を保持します。開発者は拒否対象の入力を修正して再計算してください。拒否でも元の資源・状態・倍率・明示順は変更しません。

状態補正行動順の契約は各呼び出しの入力から再計算し、速度や状態をキャッシュしません。状態順序の検証と補正は状態/拡張情報の総要素数に対して線形、安定整列は参加者数の二乗です。状態順序の参加者は最大八体で、探索やコピーを所有モンスター全件へ広げません。

## Sessionの状態付きラウンド開始

状態異常を付与または治療した戦闘では、開始時の状態だけで計算すると次ラウンドの速度が古いままになります。`engine/battle_session.gd` は、状態付き開始で保持した最新一覧をラウンド開始のたびに読み、`status_turn_order.plan` へ委譲します。Session自身は補正式や整列を実装しません。Sessionは各陣営最大四体だけを対象にし、保有個体全件を走査しません。

開発者は新規Sessionへ `start_with_statuses(allies, enemies, initial_statuses, initial_speed_multipliers)` を呼び、成功後に `begin_round(shuffle_order)` を呼んでください。末尾の初期倍率は省略/nullなら全員1、明示辞書なら全参加者のside/idと厳密一致する有限非負倍率です。Sessionは全参加者の補正前能力値・現在資源・最新状態と、独立保持した現在倍率を純粋契約へ渡します。ラウンド開始要求では外部倍率を受け付けません。[Session速度保持契約](GDScript戦闘Session速度保持契約.md)は初期化・読取・順序を説明し、実付与は[取得済み予約による一回速度強化](GDScript予約付き速度強化契約.md)、期限経過は[ラウンド終端の一回経過](GDScript速度強化ラウンド終端契約.md)へ接続しました。

状態付きラウンド開始の成功結果は `ok/plan/session/stop` です。`plan` は純粋契約の `scope:status_turn_order/initial/order/speeds` を含みます。Sessionは補正前の `stats.speed` を書き換えず、計算済み速度を次ラウンドへ再乗算しません。状態なしの従来 `start` は基礎順序APIと元の結果形式を維持し、元から存在する最低速度1も維持します。

Sessionは計画が全て成功した後だけroundを増やし、orderを独立コピーし、cursorを0へ戻します。Sessionはラウンド途中の状態付与・治療でorderを再整列せず、次の開始時だけ最新状態を反映します。同速は呼出元の明示順を維持します。Sessionは死亡・逃走者をorderから除外しますが、全参加者の状態と実効速度の対応は省略しません。片側の生存者がいなければ、正常計画後にstoppedへ進み、物理防御倍率を解除します。stoppedは勝敗や報酬の確定ではありません。

Sessionは未開始を `not_initialized`、進行中・offered/claimed予約保持中・停止後を `round_not_available` で拒否します。Sessionは開始可能な段階の不正明示順や計画拒否でもround/cursor/order/pending・資源・状態・物理防御倍率を変更しません。開発者は不正入力を修正して再試行してください。進行中の場合は現在ラウンドを公開の行動APIで完了してから次ラウンドを開始してください。

`application/battle_session_application.gd` の `start_with_statuses` は、保存レコードの再構築・状態保持・各行動の設定・状態補正済み初回ラウンドが全て成功した後だけ候補Sessionを公開します。Applicationの `begin_round` も同じ所有Sessionへ委譲します。準備結果 `preparation` の順序は状態を適用する前の準備情報で、実際の初回順序は返却 `session.order` を読んでください。Applicationの従来 `start` は状態未設定と基礎順序を維持します。Applicationは予約のclaim/finishを公開せず、開発者は公開の行動解決APIを使用してください。

開発者は次の集中検証と性能検査を、後述のPython/Godot設定後に実行してください。

```powershell
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_status_session_round.py tests/test_gdscript_session_status.py tests/test_gdscript_session_status_application.py tests/test_gdscript_status_physical_action.py tests/test_gdscript_battle_session.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_battle_session.py --with-statuses
```

状態付きSessionの集中検証は初回の実Python順序比較、付与/治療後の次回再計算、途中順序固定、補正の非累積、同IDの陣営分離、八体/空陣営/死亡/逃走、拒否時の全状態保持とApplicationの全成功後公開を確認します。性能区分 `--with-statuses` は同IDの八体とネスト付き状態・重複出血を使い、next→claim→0ダメージ/0MP→finishを反復します。性能検査は正常な状態補正ラウンド開始を八段階ごとに含め、標準20000段階・7サンプル・2000段階事前実行で一段階中央値2000us以内を要求します。性能検査は固定入力・最終順序/round/cursor・数値資源/状態・反復条件・原本保持を独立期待値へ照合し、高速な拒否や欠落結果を成功にしません。開始構築・I/O・AI・描画は計測外で、この段階の中央値をラウンド開始単独の時間とは扱いません。Godot未設定・診断・不一致・性能超過の扱いと実GUI/export/CIの未検証境界は、本書の検証方法に従います。

## 検証方法と証拠の限界

開発者はリポジトリルートで、使えるPythonとGodotを指定して次を実行してください。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotの実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_status_turn_order.py tests/test_gdscript_status_turn_order_performance.py tests/test_gdscript_turn_order.py tests/test_gdscript_status_stats.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_turn_order.py
```

比較テストは、実Pythonの `Combatant.speed` と `run_round` の速度ソートを使います。参照戦闘のshuffleだけを明示順に置き換え、行動・勝敗・継続効果・一時倍率期限の処理は停止します。この比較は戦闘一巡やAI/画面の動作確認ではありません。専用要求と個体/AI/items/party/stateの保存ダミーについて、Godot起動前後のbyte不変も確認します。実セーブは使用しません。

専用性能検査は、同IDの両陣営各四体、四状態、出血重複、倍率1.5/0と同速を持つ固定入力を使用します。毎回全員の補正と安定整列を実行し、固定入力・正常順序・全速度・原本保持を独立した期待値へ照合します。標準は20000回・7サンプル・2000回事前実行で、一計画中央値3000us以内を要求します。起動/I/O・Session・行動・AI・描画・保存は計測しません。

Godot未指定によるskipまたはCLI終了コード2は未検証です。解析/実行診断・値不一致・性能上限超過は失敗です。開発者は失敗原因を解消して再検証してください。実GUI操作・配布export・リモートCIは、この純粋計算の検証とは別の証拠です。
