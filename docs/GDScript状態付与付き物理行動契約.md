# GDScriptの状態付与付き単体物理行動

## 背景・目的・範囲

純粋な物理/付与予測だけでは、戦闘のMP・HP・状態一覧・行動予約は更新されません。`status_physical_skill_action.gd` は、最新状態で再検証してから、予約取得→MP消費→物理ダメージ→生存対象への状態一件付与→予約完了を同期実行します。

本契約は開発者用の内部APIです。正のMPを消費する、状態効果付きの単体 `physical` だけを扱います。正規スキルには付与付き物理の定義がないため、比較テストは一時コピーのMOD定義を使います。正規JSON、保存schema、Pythonの戦闘規則、白黒GUIは変更しません。魔法の状態付与、全体攻撃、行動阻害、継続ダメージ、一時倍率の保持/期限、状態補正済み行動順、AI・戦闘画面への接続は本単位に含みません。

## 所有と開始方法

資源・状態一覧・予約の正本は `battle_session.gd` が所有します。専用Actionは同じSessionの[非消費検査](GDScript状態付与付き物理検査契約.md)を構築し、開始時の習得/許可装備・定義索引・状態耐性を共用します。ActionはHPMPや状態の別正本を持ちません。

純粋engineを使う開発者は、`Session.start_with_statuses` で数値参加者を開始した後、`Action.new(session).start(teams, skills, initial_statuses)` を呼んでください。入力は[準備契約](GDScript状態付与付き物理準備契約.md)と同じです。開始情報の設定は、初回ラウンド前かつ数値/初期状態がSessionと一致する場合に一度だけ成功します。失敗時はSessionと未設定のActionを保持し、修正後に再試行できます。成功後に `Session.begin_round` と `next_actor` で行動予約を提示してください。

保存レコードから始める開発者は `Application.start_with_statuses(allies, enemies, shuffle_order, initial_statuses)` を使ってください。Applicationは全候補の構築と初回ラウンドに成功した場合だけ参照を公開し、`resolve_status_physical_skill(request)` を専用Actionへ委譲します。Applicationの従来 `start` は専用Actionを設定せず、専用実行は `not_initialized` です。通常物理の `resolve_physical_skill` は付与定義を引き続き拒否します。

## 行動要求と実更新

開発者は、純粋engineの `Action.resolve` またはApplicationの `resolve_status_physical_skill` へ、次の五必須キーと任意の `status_roll` だけを渡してください。三キーの非消費 `inspect` 要求とは区別してください。

```json
{
  "ticket": {"round": 1, "slot": 0, "actor": {"side": "allies", "id": "same"}},
  "target": {"side": "enemies", "id": "same"},
  "skill_id": "mod_status_hit",
  "critical_roll": 0.5,
  "variance": 1.0,
  "status_roll": 0.49
}
```

`ticket` は現在提示中のround/slot/actorに厳密一致する行動予約識別子です。`target` は別陣営の生存参加者です。種族が同じ、または個体IDが両陣営で同じでも、side/idの組で対象を区別します。`skill_id` は開始時に習得済みで、定義が一意な対応スキルだけを選びます。装備は開始時の種族許可を検証し、選択IDの威力倍率と固定加算を使います。

Actionは予約取得前に、最新の生存/逃走/敵存在・MP・対象状態・物理防御倍率 `guard` を読み直します。対象の補正前防御力と最新状態を[状態能力値補正](GDScript状態能力値補正契約.md)へ渡し、出血0.9倍を一度だけ適用した実効防御力を物理計算へ使います。会心・装備補正・整数化・guard・ダメージ乱数は[物理/付与予測](GDScript状態付与付き物理予測契約.md)と共用します。補正結果を基礎statsへ書き戻さないため、次の攻撃で出血倍率を二重に掛けません。治療後の攻撃は最新の出血なし状態で計算します。

検証成功後のActionは、予約を一回取得して消費MPを払い、対象HPを減らします。実ダメージが正で対象HPも正の場合だけ、Sessionの最新状態一覧へ付与を依頼します。致死攻撃ではMP消費とHP減少だけを実施し、付与を呼びません。対象の状態耐性は開始時に保持した種族状態耐性から取得し、省略したIDはnormalです。属性耐性や装備の属性段階と混同しません。

付与は同じIDを重ねません。重複・無効耐性・確率0では `status_roll` を省略できます。判定が必要な場合の `status_roll` は有限の0以上1未満です。指定した不正値は、致死・重複・無効でも予約取得前に拒否します。付与不成立でも、正常に実行した攻撃のMP・ダメージ・予約は消費します。

成功結果は `ok=true/executed=true/scope=explicit_status_physical_skill_only` と、独立したticket/target、numbers、spent_mp、dealt、applied_status、session、statusesを持ちます。numbersは物理と状態の純粋予測です。applied_statusはSessionの実付与結果で、致死など付与対象外なら空辞書です。数値個体snapshot六キー、Session七キー、状態の別保持を維持します。結果や以前の検査結果を編集しても、所有状態や開始情報は変わりません。

## 取消・拒否・内部失敗

死亡/逃走した行動者や生存敵なしは、MP不足で隠さずSessionの取消規則へ渡します。Actionは取消時にも要求形式・定義・対象の存在・指定済み乱数を検証します。正常取消は `ok=true/executed=false/reason/session` を返し、MP・HP・状態を追加更新しません。取消された予約は再利用できません。

未知キー、未習得/重複/未対応定義、不正な対象・乱数・装備、MP不足は予約取得前に拒否します。未知キーはfalse/0/空でも拒否します。Actionは外部の状態一覧・耐性・威力・装備・guard・実行modeを受け付けません。開始時入力のObject・循環・過深も拒否します。開発者は拒否理由に対応する入力を修正し、まだofferedの予約なら再試行してください。取得済み/完了済み/古い予約の再送は追加更新しません。

通常のSessionでは、実更新前の検証から完了までawaitや外部callbackを挟みません。ただし、予約取得後に内部所有者が予期せず更新を拒否した場合、本契約は取引全体の巻き戻しを保証しません。Actionは `ok=false/reason/action_consumed=true` を返し、理由は `action_payment_failed`、`action_application_failed`、`action_status_failed`、`action_finish_failed` のいずれかです。開発者は消費済み予約を再実行せず、当該戦闘を中断して内部失敗を調査してください。故障注入テストは各停止位置と部分更新範囲を明示的に検査します。

## 開発者の検証方法

開発者はリポジトリルートで使えるPython/Godotを指定し、次を順番に実行してください。重いテストと標準性能測定は同時実行しないでください。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotの実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_status_physical_action.py tests/test_gdscript_status_physical_action_edges.py tests/test_gdscript_status_physical_action_performance.py tests/test_gdscript_status_physical_preflight.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_physical_action.py
```

機能テストは実PythonのBattleEngineと実GodotのMP/HP/付与を比較し、出血による次回ダメージの変化、治療、guard、装備、Lv6/7の習得境界、取消・再送・途中失敗、返却/開始入力の独立性を検査します。テストは隔離した保存ダミーと一時データコピーを使い、正規JSONと実セーブを変更しません。

専用性能検査は八体・千定義を使い、八行動ごとの新規Session/Action/索引構築も含めて実攻撃を反復します。各行動は3MP消費・18ダメージ・出血付与と予約完了後の再送拒否を確認します。最終全八体のHP82/MP97と状態、固定原本・確認件数を独立した期待値へ照合し、高速拒否や重複判定だけでは通過しません。標準は20000回・7サンプル・2000回事前実行、一行動中央値3000us以内です。起動/I/O・AI・描画・保存は測りません。

Godot未指定のskipまたは終了コード2は未検証です。解析/実行診断、固定値不一致、性能超過は失敗です。内部APIの成功を実GUI、フィールド遭遇、配布export、全E2E、リモートCIの成功とは扱いません。

[非消費検査](GDScript状態付与付き物理検査契約.md) / [状態補正](GDScript状態能力値補正契約.md) / [形式](FORMATS.md) / [移行単位](ワークフロー/GDScript移行実装単位.md)
