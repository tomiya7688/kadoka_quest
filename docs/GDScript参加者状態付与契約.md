# GDScriptの参加者状態集合から一件付与を委譲する契約

## 背景・目的・対応範囲

個体状態所有者combatant_status_stateは、最新一覧への一件付与を実装済みです。戦闘参加者の状態集合battle_status_stateは、allies/enemiesの陣営と個体IDで対象所有者を選び、付与準備・予測・実更新を委譲します。状態集合は付与確率・耐性倍率・状態ID・重複の規則を再実装しません。

本契約は、対象一体だけの状態更新を行うための内部APIです。状態集合はHP/MP・生死・逃走・行動予約・スキル習得・種族/装備からの耐性再構築・AI・保存・乱数生成を扱いません。戦闘Sessionの予約への付与接続は[独立した低水準入口](GDScript予約付き状態付与契約.md)で実装しました。付与付き攻撃行動は未接続です。状態集合の付与成功を、一回のスキル行動の完了として扱わないでください。

## 開発者の実行方法と具体例

開発者は、Godotの検証用スクリプトの関数内で次の独立した例を実行してください。例の状態集合は、味方/敵に同じID「same」を持つ二体で開始します。例の付与対象は敵側だけです。

```gdscript
var Roster = preload("res://engine/battle_status_state.gd")
var stats = {"hp": 30, "mp": 7, "attack": 10, "defense": 10, "magic": 10, "speed": 10}
var member = {"identity": {"id": "same", "species_id": "slime", "name": "比較個体"},
    "stats": stats, "hp": 30, "mp": 7, "fled": false, "alive": true}
var snapshots = {"allies": [member.duplicate(true)], "enemies": [member.duplicate(true)]}
var initial = {"allies": {"same": []}, "enemies": {"same": []}}
var roster = Roster.new()
assert(roster.start(snapshots, initial)["ok"])
var target = {"side": "enemies", "id": "same"}
var request = {"effect": {"id": "bleeding", "display_name": "出血", "chance": 0.4},
    "resistance_level": "weak", "roll": 0.49}
var preparation = request.duplicate()
preparation.erase("roll")
assert(roster.prepare_application(target, preparation)["roll_required"])
assert(roster.quote_application(target, request)["applied"])
assert(roster.read(target)["snapshot"]["status_effects"].is_empty())
assert(roster.apply(target, request)["applied"])
assert(roster.read({"side": "allies", "id": "same"})["snapshot"]["status_effects"].is_empty())
assert(roster.read(target)["snapshot"]["status_effects"].size() == 1)
assert(not roster.apply(target, preparation)["applied"])
```

状態集合は基礎確率0.4をweak耐性で0.5へ補正する個体側の結果を受けます。roll0.49が0.5未満なので、実付与は敵sameの一覧へ出血一件を追加します。予測だけでは敵sameの一覧を変更しません。味方sameは空のままです。同IDの二回目付与は判定値なしで付与なしとなり、出血を重ねません。

## 開始・対象指定・委譲の手順

開発者は、状態集合のstart(snapshots, initial_statuses)へ[明示初期状態の形式](GDScript戦闘Session状態保持契約.md#所有と原子的な開始)を渡してください。状態集合は全員の初期化が成功した場合だけ所有者を保持します。不正初期状態では未開始を保持し、正しい入力で再試行できます。開始後の再初期化はalready_initializedで拒否します。空の両陣営も明示した空辞書/配列で開始できます。

状態集合は付与要求に対し、初期化済みか、keyがside/idだけを持つ正しい参加者キーか、指定参加者が存在するかを順に検査します。key.sideはalliesまたはenemies、key.idは空でない文字列です。状態集合は陣営とIDを一緒に索引へ使い、同じIDの別陣営を同一人物として扱いません。参加者の存在検査は生存/行動権の検査ではありません。

| 状態集合のAPI | 条件・結果・状態変更 |
| --- | --- |
| prepare_application(key, request) | 状態集合は対象個体の最新一覧から、独立候補/一覧・補正後確率・roll_requiredを返します。prepare_applicationはeffectと任意resistance_levelだけを受け、状態を変更しません。 |
| quote_application(key, request) | 状態集合は対象個体の最新一覧で一件付与を予測し、scope:status_apply_quoteを返します。quote_applicationはeffectと任意resistance_level/rollだけを受け、状態を変更しません。 |
| apply(key, request) | 状態集合は対象個体のapplyへ委譲し、scope:combatant_status_applyの独立結果を返します。成立した候補一件だけを対象の末尾へ追加し、他の参加者を変更しません。 |

状態集合の付与条件は[個体状態所有者の契約](GDScript戦闘状態一覧契約.md#最新一覧への一件付与)と[純粋付与契約](GDScript状態付与予測契約.md)を共用します。状態集合は入力原本・返却結果・読取値の編集を、保持する一覧へ伝播させません。外部status_effects・古いresulting_status_effects・予測結果・候補位置を更新命令に持ち込めません。未知要求キーはfalse/0/空でも拒否します。

状態集合のapplyは、呼び出した時点の最新一覧で同IDを再検査します。同IDが既に存在する場合は一覧を置換/延長せず、判定値を要求しません。対象のcure(key, request)で状態を除いた後は、applyで同IDを再付与できます。異なるIDを別の呼び出しで付与することは、一行動につき一回の予約制限とは異なります。

状態集合は内部の_by_id索引と個体所有者を返しません。snapshot()はteamsとscope:battle_status_only、read(key)はokとstatus_effectsだけのsnapshotを独立コピーで返します。新しい付与入口は全体/個別の読取形式、従来cure、六キー数値参加者、Sessionの七キーsnapshot、保存JSON/schemaを変更しません。陣営/IDの対象検索は辞書索引で行い、全参加者を再走査しません。付与規則の一覧検査/コピーは対象個体の所有者へ委譲します。

## 拒否・不成立と開発者の対応

状態集合は未開始ならnot_initialized、不正side/idキーならinvalid_actor_key、正しいキーでも対象が存在しなければactor_missingを返します。開発者は、開始成功・キー形式・参加者IDと陣営を確認してください。空の状態集合へ付与を要求した場合もactor_missingになります。

対象検査が成功すると、状態集合は個体側の要求拒否をそのまま返します。辞書以外はinvalid_status_apply_request、未知要求はunsupported_status_apply_request、型/定義/確率/耐性/rollは純粋付与契約のreasonになります。拒否結果はok:falseとreasonだけで、全参加者の状態を変更しません。状態集合は不正入力を自動補修しません。

操作の成功ok:trueと実付与の成立applied:trueは別です。IDなし・同ID存在・基礎確率0以下・無効耐性・判定不成立は、正常な付与なしで一覧を保持します。判定不要でも指定済み不正rollを拒否します。未知MOD状態IDとJSON互換拡張情報は保持しますが、継続時間・出血ダメージ・能力値低下・行動不能は実行しません。

## 検証方法と完了確認

開発者はリポジトリルートで使えるPythonとGodotを指定し、次を実行してください。実セーブは使いません。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotの実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_roster_status_application.py tests/test_gdscript_owned_status_application.py tests/test_gdscript_session_status.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_cure.py --roster-status-apply
```

専用テストは、両陣営の同ID・八体の各対象への付与/重複/治療/再付与・準備/予測非変更・不正初期化後の再試行・空集合・不正対象/要求/非JSON値・原本/返却ネストの独立性を実Godotで観測します。専用テストは、対象の付与結果を学習なしの実Python _try_apply_statusと比較し、要求と五種類の保存ダミーのbyte不変を共用fixtureで検査します。

性能検査は各反復で両陣営同IDの八体を新規開始し、enemies/member_2だけへの準備→予測→対象読取→出血一件実追加→判定値なしの重複→個別/全体読取を測ります。標準20000回・7サンプル・2000回事前実行で一サイクル中央値3000us以内、対象一体の三件→四件、他七体の三件保持、固定入力と実観測の一致がすべて成功条件です。起動/I/O・HPMP・Session予約/攻撃・AI・描画・保存は測りません。

Godot未指定のスキップ/性能終了コード2は未検証です。開発者はGodotを指定して再実行してください。解析/実行診断・期待値不一致・時間超過は失敗です。付与のSession予約・攻撃行動・耐性再構築・継続効果・AI・実GUI・配布export・リモートCIは本単位では未検証です。

[コード入口](CODEMAP.md) / [個体状態契約](GDScript戦闘状態一覧契約.md) / [Session状態保持](GDScript戦闘Session状態保持契約.md) / [移行単位](ワークフロー/GDScript移行実装単位.md)
