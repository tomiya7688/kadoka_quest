# GDScriptの状態付与付き物理スキルの開始・非消費検査

## 背景・目的と今回の範囲

[純粋な実行準備](GDScript状態付与付き物理準備契約.md)の返却contextは編集可能な通常データで、現在の戦闘予約やMPを保証しません。status_physical_skill_preflightは開始情報を非公開の独立コピーで保持し、提示中の予約・習得/許可装備・敵対象・最新資源/状態を消費せず確認します。

本契約は検査入口です。検査の成功は攻撃の実行許可や完了ではありません。検査はclaim/finish、HP/MP変更、状態付与/治療、ダメージ計算、乱数生成、AI、画面、保存を実行しません。実消費・出血補正済みダメージ・一件付与は、検査を共用する別の[専用行動](GDScript状態付与付き物理行動契約.md)へ接続しました。速度補正済み行動順、行動阻害、ターン末効果は未接続です。数値個体snapshot六キー、Session七キー、正規JSON/保存schemaは維持します。

## 開発者の開始方法

純粋engineを検証する開発者は、初期状態を明示したSession.start_with_statusesで数値参加者を開始し、Preflight.new(session).start(teams, skills, initial_statuses)へ[準備契約](GDScript状態付与付き物理準備契約.md)と同じ入力を渡してください。

startは未設定かつ初回ラウンド前（phase=between_rounds、round=0）だけを許可します。startは共用Context.prepareへ資源/習得/許可装備・状態耐性・全員の初期状態の検証とコピーを委譲します。startは準備した数値/初期状態とSessionの所有正本が一致する場合だけ非公開contextを設定し、ok=true/scope=status_physical_preflight_onlyを返します。startの失敗はSessionと検査の保持情報を変更せず、正しい入力で再試行できます。

保存レコードから検証する開発者は、Application.start_with_statuses(allies, enemies, shuffle_order, initial_statuses)を使ってください。Applicationは再構築した参加者と正規スキルから、候補Session・既存行動・治療付き回復・付与付き物理検査を構築します。Applicationは全設定と初回ラウンドが成功した後だけ使用する参照を一度に切り替えます。Applicationの従来startは付与付き物理検査を設定しません。

本契約は内部APIです。ゲーム画面へ新しい操作は追加しません。開発者は初期化後にSession/Application.next_actorで予約を提示し、次の検査を呼んでください。

## 検査要求と最新値の読取

純粋engineの入口はPreflight.inspect(request)、Applicationの入口はinspect_status_physical_skill(request)です。開発者は次の三キーだけを渡してください。

```json
{
  "ticket": {"round": 1, "slot": 0, "actor": {"side": "allies", "id": "same"}},
  "target": {"side": "enemies", "id": "same"},
  "skill_id": "mod_status_hit"
}
```

検査は現在offeredのround/slot/actorをSession.inspect_ticketで照合します。検査は開始時コピーの習得とID索引から、付与定義を必須にした単体physicalと選択IDの装備補正を共用選択します。検査は未知/重複/未習得ID、通常物理、未対応の選択効果/装備補正を拒否します。通常物理行動は引き続き付与定義を拒否します。

付与付き物理の非消費検査は、指定対象が行動者とは異なる陣営の参加者であることを確認します。行動者が最新生存/逃走/敵存在の条件で行動可能なら、検査は指定敵の生存と最新MPの支払可否も確認します。死亡/逃走した行動者や生存敵なしでは、検査はMP不足へ理由を置き換えず、eligibility.can_act=falseを返します。検査は行動不能を発見しても予約を取り消しません。開発者はcan_act=falseの検査を実行可能と解釈しないでください。

成功結果はok/scope、独立ticket/eligibility、skill/equipment、actor_resources/target_resources、actor_status/target_status、target_status_resistances、target_guard、stats_scopeを持ちます。actor_status/target_statusはstatus_effects一キーの個体状態snapshotです。target_status_resistancesは開始時に保持した対象種族の状態耐性で、属性耐性や装備の属性段階とは別です。

検査は資源/状態/guardを毎回Sessionから読み直します。stats_scope=before_status_modifiersは、返却statsが状態補正前であることを示します。検査はこのstatsを補正済み防御や最終ダメージへ変換しません。返却eligibilityは生存/逃走/敵存在の既存判定で、眠り等の行動阻害を実装済みとは扱いません。

検査は予約を取得せず、同じ提示予約で何度でも読み取れます。検査後にMP/HP/状態が変われば、次の検査は最新値を返します。返却値・開始入力・以前の検査結果を編集しても、Sessionや非公開contextは変わりません。開発者は過去の成功結果を、将来の実行時の再検証の代わりに使わないでください。

## 拒否条件と復旧

開始失敗はalready_initialized/session_not_fresh、数値不一致はstatus_physical_context_mismatch、状態未設定はstatus_not_configured、状態不一致はstatus_physical_status_mismatchです。純粋準備が拒否した場合は共用reasonを保持します。開発者は不正入力を修正し、まだ初回ラウンド前なら同じ未設定検査へ再試行してください。

検査の未設定はnot_initialized、三キー以外の要求はinvalid_status_physical_preflight_requestです。検査は未知キーの値がfalse/0/空でも拒否します。検査はcritical_roll/variance/status_roll、外部一覧/耐性/定義/装備、modeも受け付けません。最終行動要求や数値予測の入力と、本検査の三キー要求を混同しないでください。

予約の型/陣営ID/一致/取得段階の拒否理由はSessionの理由を保持します。不正対象はinvalid_target_key、味方はtarget_not_enemy、不在はtarget_missing、実行可能者の死亡対象はtarget_not_alive、MP不足はinsufficient_mpです。検査失敗は予約/資源/状態/guardを変更せず、開発者は同じ提示予約で要求を修正して再検査できます。取得済み/終了済み/古い予約は再利用できません。

## 検証と性能の実行方法

開発者はリポジトリルートで使えるPython/Godotを指定して、次を実行してください。テストは専用要求と五種類の保存ダミーを使い、正規JSONのbyte保持も確認します。Applicationの習得境界は、一時領域のdataコピーだけでbody_bashへ付与を追加し、スライムLv6/7を比較します。正規スキル定義へ付与を追加したものではありません。

```powershell
$env:KADOKA_GODOT_EXECUTABLE = '<Godotの実行ファイル>'
$env:PYTHONPATH = 'src'
& '<Pythonの実行ファイル>' -m pytest tests/test_gdscript_status_physical_preflight.py tests/test_gdscript_cure_heal_action.py tests/test_gdscript_physical_action.py -q
& '<Pythonの実行ファイル>' tools/performance-check/script/check_gdscript_status_physical.py --preflight
```

--preflightは八体/千定義を開始時だけ準備し、最新予約/資源/状態を読み取る成功検査を標準20000回・7サンプル・2000回事前実行で測ります。性能検査は中央値3000us以内、固定定義・装備倍率2/固定加算3・状態/耐性/満資源・提示予約の保持を独立した期待値へ照合します。高速拒否だけでは通過しません。起動/I/O・準備/索引作成・HPMP/状態実更新・予約取得・AI・描画・保存は測りません。

Godot未指定のskip/性能終了コード2は未検証です。開発者はGodotを指定して再実行してください。実Godotの解析/実行診断、結果不一致、時間超過は失敗です。本検査の性能測定は専用行動の実更新を含みません。AI・戦闘画面は未接続で、実GUI・配布export・全E2E・リモートCIは未検証です。

[純粋予測](GDScript状態付与付き物理予測契約.md) / [準備](GDScript状態付与付き物理準備契約.md) / [予約付き付与](GDScript予約付き状態付与契約.md) / [形式](FORMATS.md) / [CODEMAP](CODEMAP.md) / [移行単位](ワークフロー/GDScript移行実装単位.md)
