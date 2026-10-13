# GDScriptでSessionに初期状態を分離保持する契約

例えばSessionは、味方と敵に同じ個体ID「same」がいても、味方の毒と敵の空状態を別々に保持します。開発者が読取結果の毒を消しても、Session内の毒は変わりません。数値資源snapshotには状態一覧を追加しません。

この契約の目的は、[治療付き回復準備](GDScript治療付き回復準備契約.md)が返す編集可能な初期状態を、戦闘中の所有状態へ移すことです。本書は保持/読取を説明します。[治療付き回復行動](GDScript治療付き回復行動契約.md)からの取得済み予約一回の治療とApplicationの専用開始も接続しました。AI・戦闘画面は未接続です。

## 開発者が使う入口と具体例

開発者は、engine/battle_session.gdの新規Sessionにstart_with_statuses(allies, enemies, initial_statuses)を一度呼んでください。両陣営には従来と同じ六キーの数値snapshot列を渡します。各陣営は最大四体、陣営内IDは一意、開始時は満HP/MP・未逃走です。状態なしも空配列として全参加者について明示してください。

開発者は、次の例をGodotの検証用スクリプトの関数内に置いて実行してください。関数名や呼び出し方法は既存の検証スクリプトに合わせます。この例は関数本体だけを示し、数値参加者と初期状態を用意して開始成功・陣営の分離・読取結果編集後の保持をassertで確認します。

```gdscript
var Session = preload("res://engine/battle_session.gd")
var stats = {"hp": 30, "mp": 7, "attack": 10, "defense": 10, "magic": 10, "speed": 10}
var ally = {"identity": {"id": "same", "species_id": "slime", "name": "味方"},
    "stats": stats, "hp": 30, "mp": 7, "fled": false, "alive": true}
var enemy = ally.duplicate(true)
enemy["identity"]["name"] = "敵"
var initial = {"allies": {"same": [{"id": "poison", "metadata": {"deck": [1, 2]}}]},
    "enemies": {"same": []}}
var session = Session.new()
var started = session.start_with_statuses([ally], [enemy], initial)
assert(started["ok"])
var copied = session.status({"side": "allies", "id": "same"})
copied["snapshot"]["status_effects"].clear()
assert(session.statuses()["teams"] == initial)
assert(session.status({"side": "enemies", "id": "same"})["snapshot"]["status_effects"].is_empty())
```

[回復準備契約](GDScript治療付き回復準備契約.md)を使う場合、開発者はその成功結果のsnapshots.allies、snapshots.enemies、initial_statusesを専用開始へ渡してください。準備しただけではSessionに登録されません。開始後に準備結果や入力原本を編集してもSession内の状態は変わりません。

## 所有と原子的な開始

Sessionは数値参加者を従来の順序/資源契約で検証し、未公開の資源所有者を構築します。initial_status_mapは両陣営とID集合を照合する共用部品です。状態辞書はallies/enemiesだけを持ち、各陣営の全参加者IDと厳密に一致する必要があります。欠落・余分なID・余分な外側キーを拒否し、空状態を補完しません。両陣営が空ならinitial_statusesは{"allies": {}, "enemies": {}}です。

battle_status_stateは参加者ごとに[個体状態所有者](GDScript戦闘状態一覧契約.md)を構築し、一覧の内容検証とコピーを委譲します。文字列/辞書の順序、重複状態、未知MOD ID、JSON互換の拡張情報を保持します。非有限値・Object・循環・深さや整数精度の超過・認識キーの型不正は共用状態契約に従って拒否します。状態IDの存在は、その付与/継続効果を実装したことを意味しません。

数値と全員の状態が成功した場合だけ、Sessionは両方を保持し、物理防御倍率1・between_roundsに進みます。一体でも失敗すれば数値参加者・防御倍率・状態・開始段階は未開始のままです。開発者は不正入力を修正して同じ未開始Sessionで再試行できます。開始後の従来/専用入口による上書きはalready_initializedとして拒否します。

## 返却形式と保持期間

開始成功は従来と同じ{"ok": true, "session": 数値snapshot}です。Session.snapshot()はphase/round/cursor/order/pending/teams/scopeの七キー、参加者はidentity/stats/hp/mp/fled/aliveの六キーを維持します。状態を数値snapshotへ混ぜません。

Session.statuses()は{"teams": {"allies": {"個体ID": 状態配列}, "enemies": {...}}, "scope": "battle_status_only"}を返します。Session.status(key)は、side/idだけの参加者キーに対して{"ok": true, "snapshot": {"status_effects": 状態配列}}を返します。全体/個別とも、ネストまで独立した編集可能な通常データです。状態所有者そのものや一覧上書きAPIは公開しません。更新は上記行動契約のapply_status_cureで現在取得済み予約一回に制限します。

状態はラウンドの開始/終了・予約提示/取得/完了・HP/MP操作・死亡・逃走・stopped後も保持します。物理防御倍率の終端解除は状態を解除しません。毒の継続ダメージ、眠りによる行動取消、残存ターン経過や戦闘後保存は実行しません。既存の通常HP回復行動はHP/MPだけを更新し、状態を治療しません。

従来Session.start(allies, enemies)は状態所有者を構築しません。未開始または従来開始のstatuses()は空辞書です。個別status()は未開始ならnot_initialized、従来開始済みならstatus_not_configuredを返します。専用開始後の不正side/id形式はinvalid_actor_key、不明IDはactor_missingです。Applicationは従来開始を維持し、明示状態付きstart_with_statusesだけが状態と治療付き行動を設定します。

## 検証方法と完了の確認

開発者はリポジトリルートで、使えるGodotとPythonを指定して次を実行してください。実セーブではなく、共用起動fixtureの専用要求と個体/AI/items/party/stateの保存ダミーを使い、byte不変を確認します。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotの実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_session_status.py tests/test_gdscript_battle_session.py tests/test_gdscript_combatant_status.py tests/test_gdscript_cure_heal_context.py tests/test_gdscript_heal_action.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_cure.py --session-status
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_battle_session.py
```

テストは厳密ID一致、同IDの陣営分離、ネスト/順序/重複/未知MOD情報、空状態/空陣営、原本/返却値独立性、不正開始後の未開始保持と再試行、再開始拒否、ラウンド/死亡/逃走/防御解除後の状態保持、準備→専用開始と通常回復の互換性を確認します。Godotの解析/実行診断がない実結果と要求/保存ダミーのbyte保持が成功条件です。

--session-statusは各反復で新規八体Sessionの明示状態付き開始→一体読取→全体読取→数値snapshot読取を測ります。各個体は解除不可・ネスト付き毒・眠りの三件を持ちます。標準20000回・7サンプル・2000回事前実行で中央値3000us以内、固定八体の満数値資源、全初期状態、個別読取と原本保持がすべて一致した場合だけ成功します。従来カーソル性能は開始構築を計測外に置いた別区分です。

Godot未指定のskip/終了コード2は未検証です。開発者はGodotを指定して再実行してください。解析/実行診断・期待値不一致・時間超過は失敗です。起動/I/O・HP/MPと治療の統合行動・状態付与/継続効果・AI・描画/FPS・実GUI・配布export・リモートCIはこの状態保持計測/検証の証拠に含めません。正規data/assets・保存JSON/schemaは変更しません。

[コードの入口](CODEMAP.md) / [形式仕様](FORMATS.md) / [数値Session契約](GDScript戦闘Session契約.md) / [移行単位](ワークフロー/GDScript移行実装単位.md)
