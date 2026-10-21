# GDScriptで参加者別速度をSessionに保持する契約

## 背景・目的と責務

状態付き戦闘Sessionは、速度所有者を接続する前は全参加者の倍率1で行動順を計算していました。Session速度保持の目的は、一体の[速度強化所有者](GDScript一時速度強化保持契約.md)を参加者別に所有し、数値資源と分離して読み、ラウンドの開始時に所有倍率を使うことです。

engine/battle_speed_state.gdは、各陣営最大四体の速度所有者とside/id索引を保持します。集合は初期倍率の検証を個体所有者へ委譲し、速度補正式や整列を実装しません。engine/battle_session.gdは全開始候補の成功後に速度集合を保持し、最新状態と所有倍率を[状態補正行動順](GDScript状態補正行動順契約.md)へ渡します。Applicationは開始・読取をSessionへ委譲し、全行動設定と初回計画の成功後だけ候補Sessionを公開します。

本書は初期倍率の保持・読取・行動順への接続を説明します。Sessionは速度の直接上書きAPIを公開せず、実付与は[取得済み予約による一回速度強化](GDScript予約付き速度強化契約.md)へ接続しました。スキル期間の正規化/抽選、終端での一回経過、ピオラの実行、AI・戦闘画面は未接続です。個体所有者の期間経過テストはSession終端の検証ではありません。

## 開発者の呼び出し方法

開発者は、engine/battle_session.gdの新規Sessionへ次の開始APIを呼んでください。これは内部契約であり、ゲーム画面に新しい操作は追加しません。

```gdscript
var multipliers = {"allies": {"same": 2.0}, "enemies": {"same": 0.75}}
var started = session.start_with_statuses(allies, enemies, initial_statuses, multipliers)
if started["ok"]:
    var planned = session.begin_round(shuffle_order)
```

allies/enemiesは従来と同じ満HP/MP・未逃走の六キー数値snapshot列、initial_statusesは空状態も全参加者について明示したside/id別状態辞書です。shuffle_orderは生存者全員を一回ずつ含む明示順です。開発者は開始/計画のokを確認してから読取結果を使ってください。

末尾のinitial_speed_multipliersは省略またはnullなら全員1です。明示した辞書はallies/enemiesだけを持ち、各陣営の全参加者IDに過不足なく一致する必要があります。空陣営には空辞書を指定してください。明示辞書の欠落個体を1へ補完しません。別陣営の同IDは別の所有者です。

各初期倍率は0以上9007199254740991以下の有限int/floatです。bool、数値文字列、null、配列、辞書、Object、非有限値は倍率として拒否します。各所有者の初期remaining_turnsは0、baseline_multiplierは初期speed_multiplierと同じです。初期倍率辞書に期間や外部snapshotを渡して期間付き強化を復元する機能はありません。

application/battle_session_application.gdの専用入口は、既存四引数の末尾へ同じ任意倍率を追加したstart_with_statuses(allies, enemies, shuffle_order, initial_statuses, initial_speed_multipliers)です。Applicationは保存レコードを再構築し、倍率の検証をSessionへ委譲します。Applicationのpreparation内の順序は補正前の準備情報です。実際の初回順序はsession.orderを読んでください。

## 独立読取と原子的な開始

Session.speeds()とApplication.speeds()は次の形式を返します。倍率の全体読取は、HP/MPや状態一覧を含まない独立した通常データです。

```json
{
  "teams": {
    "allies": {"same": {"speed_multiplier": 2.0, "remaining_turns": 0, "baseline_multiplier": 2.0}},
    "enemies": {"same": {"speed_multiplier": 0.75, "remaining_turns": 0, "baseline_multiplier": 0.75}}
  },
  "scope": "battle_speed_only"
}
```

Session.speed(key)とApplication.speed(key)は、side/idだけのキーに対してok=true/snapshotを返し、snapshotは一体の三キー速度辞書です。集合のread(key)も同じ個別読取形式です。集合のsnapshot()は全体読取、multipliers()は行動順へ渡すside/id別の現在倍率だけです。所有者オブジェクトは外部へ返しません。入力や全体/個別読取結果を後から編集しても、所有倍率・状態一覧・数値資源は変わりません。

速度集合は全員成功するまで個体所有者を公開しません。Sessionは数値資源・状態・速度の全てが成功するまで開始段階や所有参照を切り替えません。Applicationは初回計画まで失敗した場合も公開Sessionを未開始のまま保持します。開発者は不正な初期条件を修正して再試行してください。成功後の二重初期化はalready_initializedで拒否します。

集合は参加者辞書の形式不正をinvalid_speed_participants、倍率の外側辞書/陣営形式不正をinvalid_initial_speed_multipliers、全ID集合不一致をspeed_context_mismatch、個体倍率不正をinvalid_speed_multiplierで拒否します。個体に対応する不正ではside/idも返します。数値参加者や状態の不正は既存契約の理由を保持します。

未開始/従来開始の全速度読取は空辞書です。個別読取は未開始ならnot_initialized、従来開始済みならspeed_not_configured、不正side/idならinvalid_actor_key、不在個体ならactor_missingで拒否します。従来startは状態・速度所有者を構築せず、基礎順序と返却形式を維持します。

## ラウンド境界と互換性

状態付きSessionはラウンド開始時に全参加者の最新状態と現在倍率を読みます。実効速度の乗算順・最後の整数化・下限1・精度上限は共用の純粋契約へ委譲します。例えば補正前速度11・出血・倍率2の味方は速度19、補正前速度10・状態なし・倍率0.75の敵は速度7になります。

個体倍率として妥当でも、基礎速度との途中積が精度上限を超える場合はbegin_roundが拒否します。Sessionは不正な計画でround/order/cursor/pending・速度・状態・資源・防御を変更しません。Applicationの初回計画が拒否された場合は候補Sessionも公開しません。

Sessionは途中の状態付与/治療で現在の行動順を変えず、次のラウンドでだけ最新状態から再計算します。Sessionは補正前stats.speedを書き換えず、計算済み速度を再乗算しません。死亡・逃走者を行動順から除いても、速度所有者や全員の実効速度辞書は保持します。ラウンド終端・stopped・防御解除は、今回の速度倍率や残り期間を変更しません。

Session七キーと数値参加者六キーのsnapshot、保存JSON/schema、Pythonゲーム処理、白黒GUIは変更しません。速度集合は最大八体だけを走査し、保有モンスター全件を探索しません。現在倍率は所有者から毎ラウンド読み、実効速度をキャッシュしません。

## 開発者の検証手順と証拠の限界

開発者は使えるPythonとGodotを設定し、リポジトリルートで次を実行してください。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotの実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_session_speed.py tests/test_gdscript_status_session_round.py tests/test_gdscript_speed_state.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_battle_session.py --with-speeds
```

集中テストは実PythonのCombatant.speedと安定順序へ比較し、三ラウンドの非累積、同ID陣営分離、八体/空陣営/死亡/逃走、初期化失敗後の再試行、不正/native倍率、コピー編集後の保持、Applicationの全成功後公開を確認します。専用要求と個体/AI/items/party/stateの保存ダミーはGodot起動前後でバイト不変を照合し、実セーブを使いません。

性能区分--with-speedsは状態付き開始を含み、味方四体に倍率2・敵四体に倍率0.75と、重複出血/ネスト付き状態を設定します。標準20000段階・7サンプル・2000段階事前実行で、八段階ごとの正常ラウンド開始を含むnext→claim→0ダメージ/0MP→finishの一段階中央値2000us以内を要求します。固定入力・最終順序/round/cursor・資源/状態/所有速度・反復条件・原本保持を独立期待値へ照合し、高速な拒否や倍率未保持を合格にしません。初期構築、起動/I/O、AI、描画、保存は計測外です。

Godot未設定のskip/終了コード2は未検証です。解析/実行診断、値不一致、性能超過は失敗です。開発者は原因を修正して再検証してください。ヘッドレス比較の成功を実GUI、配布export、リモートCIの成功とは扱いません。
