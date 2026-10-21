# {
#   責務: [battle_session: 戦闘個体の資源・行動予約・物理防御と、専用開始時の状態/速度所有者を保持します。攻撃計算や勝敗判定は行いません]
#   フィールド: [
#     _teams: allies/enemies別に保持する戦闘個体の資源所有者列（Dictionary）
#     _by_id: 陣営sideと個体idから資源所有者を検索する索引（Dictionary）
#     _phase: 戦闘開始前・ラウンド進行中・終端を表す段階（String）
#     _round: 戦闘開始後のラウンド番号（int）
#     _cursor: 確定した行動順内の現在位置（int）
#     _order: 現在ラウンドで固定したside+idの行動順（Array）
#     _pending: 現在提示中または取得済みの行動予約（Dictionary）
#     _guards: side+id別の物理防御倍率。資源snapshotとは別に保持する（Dictionary）
#     _statuses: 専用開始でだけ保持するbattle_status_state。従来開始と未開始ではnullです（RefCounted）
#     _speeds: 専用開始でだけ保持する参加者別の速度所有者集合（RefCounted）
#     _status_updates: 取得済み予約の治療/付与を種類別一回に制限する内部所有者（RefCounted）
#     _speed_update: 取得済み予約の速度付与を一回に制限する内部所有者（RefCounted）
#   ]
# }
extends RefCounted
## 数値資源・予約・状態・速度を分離保持し、取得済み予約の一件治療/付与を状態所有者へ委譲します。回復/攻撃計算と勝敗は担当しません。

const State = preload("res://engine/combatant_state.gd")
const Eligibility = preload("res://engine/actor_eligibility_projection.gd")
const Order = preload("res://engine/turn_order.gd")
const StatusOrder = preload("res://engine/status_turn_order.gd")
const StatNumbers = preload("res://engine/stat_numbers.gd")
const Statuses = preload("res://engine/battle_status_state.gd")
const Speeds = preload("res://engine/battle_speed_state.gd")
const SpeedUpdate = preload("res://engine/claimed_speed_update.gd")
const StatusUpdates = preload("res://engine/claimed_status_updates.gd")
var _teams: Dictionary = {"allies": [], "enemies": []}
var _by_id: Dictionary = {"allies": {}, "enemies": {}}
var _phase := "not_started"
var _round := 0
var _cursor := 0
var _order: Array = []
var _pending: Dictionary = {}
var _guards: Dictionary = {"allies": {}, "enemies": {}}
var _statuses: RefCounted
var _speeds: RefCounted
var _status_updates: RefCounted
var _speed_update: RefCounted


# {
#   責務: [start: 従来入口で満資源参加者と防御倍率を一度設定します。状態所有者は構築しません]
#   処理: [
#     1: 参加者と開始資源を検証し、内部へ公開していない資源所有者を構築します
#     2: 全員成功後に資源所有者を保持し、物理防御倍率を1としてラウンド開始待ちへ進みます
#   ]
#   引数: [
#     allies: 味方参加者の六キー数値snapshot列。各個体は満HP/MP・未逃走です（Variant）
#     enemies: 敵参加者の六キー数値snapshot列。各個体は満HP/MP・未逃走です（Variant）
#   ]
#   戻り値: [result: 初期化の成功と独立した状態、またはok=falseと拒否理由（Dictionary）]
# }
func start(allies: Variant, enemies: Variant) -> Dictionary:
	var prepared := _prepare_start(allies, enemies)
	return prepared if not prepared["ok"] else _commit_start(prepared, null, null)


# {
#   責務: [start_with_statuses: 数値資源・明示状態・初期速度倍率が全て成功した場合だけ新規戦闘を開始します]
#   処理: [1: 数値資源・状態・速度の所有者を未公開で構築し、全て成功した場合だけSessionへ保持します]
#   引数: [
#     allies: 満HP/MP・未逃走の味方数値snapshot列（Variant）
#     enemies: 満HP/MP・未逃走の敵数値snapshot列（Variant）
#     initial_statuses: 全参加者のside/idに一致する明示初期状態。省略や暗黙空配列補完は行いません（Variant）
#     initial_speed_multipliers: 全参加者のside/id別初期倍率。省略/nullは全員1、明示辞書の欠落は拒否します（Variant）
#   ]
#   戻り値: [result: 従来形式の独立した数値session、または未開始を保持した拒否（Dictionary）]
# }
func start_with_statuses(allies: Variant, enemies: Variant, initial_statuses: Variant, initial_speed_multipliers: Variant = null) -> Dictionary:
	var prepared := _prepare_start(allies, enemies)
	if not prepared["ok"]:
		return prepared
	var statuses = Statuses.new()
	var initialized: Dictionary = statuses.start({"allies": allies, "enemies": enemies}, initial_statuses)
	if not initialized["ok"]:
		return initialized
	var speeds = Speeds.new()
	var speed_started: Dictionary = speeds.start({"allies": allies, "enemies": enemies}, initial_speed_multipliers)
	if not speed_started["ok"]:
		return speed_started
	return _commit_start(prepared, statuses, speeds)


# {
#   責務: [_prepare_start: 新規開始の数値参加者を検証し、Sessionへ未公開の資源所有者を構築します]
#   処理: [1: 未開始・参加者・満HP/MPを確認し、全員の資源所有者とID索引をローカルに構築します]
#   引数: [
#     allies: 味方の六キー数値snapshot列（Variant）
#     enemies: 敵の六キー数値snapshot列（Variant）
#   ]
#   戻り値: [result: 内部コミット用の資源所有者/索引。公開APIや層外へ渡しません。または拒否（Dictionary）]
# }
func _prepare_start(allies: Variant, enemies: Variant) -> Dictionary:
	if _phase != "not_started":
		return _failure("already_initialized")
	var checked := Order.participants(allies, enemies)
	if not checked["ok"]:
		return checked
	var teams := {"allies": [], "enemies": []}
	var by_id := {"allies": {}, "enemies": {}}
	for side in Order.SIDES:
		var members: Array = allies if side == "allies" else enemies
		for index in members.size():
			var member: Dictionary = members[index]
			if member["hp"] != member["stats"]["hp"] or member["mp"] != member["stats"]["mp"] or member["fled"]:
				return {"ok": false, "reason": "fresh_start_required", "side": side, "index": index}
			var state = State.new()
			var initialized: Dictionary = state.start(member["identity"], member["stats"])
			if not initialized["ok"]:
				return initialized
			teams[side].append(state)
			by_id[side][member["identity"]["id"]] = state
	return {"ok": true, "teams": teams, "by_id": by_id}


# {
#   責務: [_commit_start: 全成功した開始候補だけをSessionへ保持し、初期防御倍率と開始段階を設定します]
#   処理: [1: 数値/状態/速度所有者を保持し、全物理防御倍率を1にしてラウンド開始待ちへ進みます]
#   引数: [
#     prepared: _prepare_startが作った内部専用の資源所有者/索引（Dictionary）
#     statuses: 初期化済み状態所有者、または従来開始を示すnull（RefCounted）
#     speeds: 初期化済み速度所有者集合、または従来開始を示すnull（RefCounted）
#   ]
#   戻り値: [result: ok=trueと従来の数値sessionコピー。内部所有者を返しません（Dictionary）]
# }
func _commit_start(prepared: Dictionary, statuses: RefCounted, speeds: RefCounted) -> Dictionary:
	_teams = prepared["teams"]
	_by_id = prepared["by_id"]
	_statuses = statuses
	_speeds = speeds
	# 全成功した開始候補にだけ、独立した種類別の一回判定記録を構築します。
	_status_updates = StatusUpdates.new(_by_id, statuses)
	_speed_update = SpeedUpdate.new(_by_id, speeds)
	for side in Order.SIDES:
		for id: String in _by_id[side]:
			_guards[side][id] = 1.0
	_phase = "between_rounds"
	return {"ok": true, "session": snapshot()}


# {
#   責務: [statuses: 専用開始で保持する全状態一覧を、数値資源とは別の独立コピーで返します]
#   処理: [1: 状態所有者がなければ空辞書、専用開始済みなら所有者の読取コピーを返します]
#   引数: []
#   戻り値: [result: teamsのside/id別状態配列とscope=battle_status_only、または未設定の空辞書（Dictionary）]
# }
func statuses() -> Dictionary:
	return {} if _statuses == null else _statuses.snapshot()

# {
#   責務: [speeds: 専用開始で保持する全参加者の速度状態を、数値資源とは別の独立コピーで返します]
#   処理: [1: 速度所有者がなければ空辞書、専用開始済みなら所有者集合のコピーを返します]
#   引数: []
#   戻り値: [result: side/id別teamsとscope=battle_speed_only、または未設定の空辞書（Dictionary）]
# }
func speeds() -> Dictionary:
	return {} if _speeds == null else _speeds.snapshot()


# {
#   責務: [speed: 専用開始した指定参加者の速度倍率・残り期間・復元先を独立コピーで返します]
#   処理: [1: 未開始/未設定を拒否し、参加者キーの検証と読取を速度所有者集合へ委譲します]
#   引数: [key: 読み取る参加者のside/idだけの辞書（Variant）]
#   戻り値: [result: ok=true/snapshot、または未開始/未設定/不正参加者の拒否（Dictionary）]
# }
func speed(key: Variant) -> Dictionary:
	if _phase == "not_started":
		return _failure("not_initialized")
	if _speeds == null:
		return _failure("speed_not_configured")
	return _speeds.read(key)




# {
#   責務: [status: 専用開始した戦闘の指定参加者について状態一覧の独立コピーを取得します]
#   処理: [1: Sessionの開始と状態設定を確認し、side/idの検証と読み取りを状態所有者へ委譲します]
#   引数: [key: 読み取る参加者のallies/enemiesを示すsideと個体id（Variant）]
#   戻り値: [result: ok=trueと個体状態snapshot、または未開始/未設定/不正参加者の拒否（Dictionary）]
# }
func status(key: Variant) -> Dictionary:
	if _phase == "not_started":
		return _failure("not_initialized")
	if _statuses == null:
		return _failure("status_not_configured")
	return _statuses.read(key)


# {
#   責務: [apply_status_cure: 現在取得済み予約の生存する同陣営対象へ、一予約一回だけ状態治療を委譲します]
#   処理: [
#     1: 現在行動票・取得段階・状態設定・対象と行動可否を確認します
#     2: 状態所有者が最新一覧で判定し、成功した呼出しだけを予約単位で使用済みにします
#   ]
#   引数: [
#     ticket: 現在のround/slot/actorに一致する取得済み行動票（Variant）
#     target: 同陣営の生存対象を指定するside/id（Variant）
#     request: cure_chanceと任意rollだけを持つ治療条件（Variant）
#   ]
#   戻り値: [result: 実治療の独立結果、または状態を変更しない理由付き拒否（Dictionary）]
# }
func apply_status_cure(ticket: Variant, target: Variant, request: Variant) -> Dictionary:
	# Sessionだけが現在の予約を照合し、対象/一覧更新と再判定防止は専用所有者へ委譲します。
	var checked := _check_claimed_update_ticket(ticket)
	if not checked["ok"]:
		return checked
	return _status_updates.cure(_pending["ticket"], target, request,
		_by_id[ticket["actor"]["side"]][ticket["actor"]["id"]].alive() and _both_sides_alive())


# {
#   責務: [apply_status_application: 現在取得済み予約で、生存対象への状態一件付与を一回だけ判定します]
#   処理: [1: 現在の取得済み予約と最新行動可否を確認し、対象/実付与/種類別再判定防止を専用所有者へ委譲します]
#   引数: [
#     ticket: 現在のround/slot/actorに一致する取得済み行動票（Variant）
#     target: 味方/敵/本人を含む生存対象のside/id。スキル対象制限は上位行動で確認してください（Variant）
#     request: effectと任意resistance_level/rollだけの付与条件。外部一覧/予測は拒否します（Variant）
#   ]
#   戻り値: [result: combatant_status_applyの独立結果、または資源/状態/予約を保持した拒否（Dictionary）]
# }
func apply_status_application(ticket: Variant, target: Variant, request: Variant) -> Dictionary:
	# HPMP・防御倍率・予約段階を変更せず、付与の一回判定だけを最新所有一覧へ接続します。
	var checked := _check_claimed_update_ticket(ticket)
	if not checked["ok"]:
		return checked
	return _status_updates.apply(_pending["ticket"], target, request,
		_by_id[ticket["actor"]["side"]][ticket["actor"]["id"]].alive() and _both_sides_alive())


# {
#   責務: [apply_speed_multiplier: 現在取得済みの予約から、生存対象の速度強化を一回だけ委譲します]
#   処理: [1: 現在予約と取得段階を照合し、最新生存・対象検査・速度更新と一回記録を専用所有者へ渡します]
#   引数: [
#     ticket: 現在round/slot/actorに一致する取得済み行動票（Variant）
#     target: 生存する味方/敵/本人のside/id。スキル対象制限は上位行動の責務です（Variant）
#     request: 必須multiplierと任意durationだけの倍率/期間選択済み要求（Variant）
#   ]
#   戻り値: [result: combatant_speed_applyの独立結果、または速度/資源/予約を保持した拒否（Dictionary）]
# }
func apply_speed_multiplier(ticket: Variant, target: Variant, request: Variant) -> Dictionary:
	# この低水準APIはclaim/finishやMP支払いを代用せず、速度の更新だけを担当へ委譲します。
	var checked := _check_claimed_update_ticket(ticket)
	if not checked["ok"]:
		return checked
	return _speed_update.apply(_pending["ticket"], target, request,
		_by_id[ticket["actor"]["side"]][ticket["actor"]["id"]].alive() and _both_sides_alive())


# {
#   責務: [_check_claimed_update_ticket: 治療/状態付与/速度付与に共通の現在予約と取得済み段階を確認します]
#   処理: [1: 既存の行動票検査が成功した後だけ、claimed段階を要求します]
#   引数: [ticket: 状態または速度の更新を要求する現在の行動予約識別子（Variant）]
#   戻り値: [result: ok=true、または未開始/不正/古い/未取得の予約を示す非破壊的拒否（Dictionary）]
# }
func _check_claimed_update_ticket(ticket: Variant) -> Dictionary:
	# 照合成功後の一回記録には_pendingの整数票を使い、JSONのfloat票との辞書比較差による再送を防ぎます。
	# 提示中の行動票を状態/速度の更新権として扱わず、取得/完了自体は既存APIへ任せます。
	var checked := _check_ticket(ticket)
	if not checked["ok"]:
		return checked
	return {"ok": true} if _pending["stage"] == "claimed" else _failure("pending_not_claimed")



# {
#   責務: [snapshot: 戦闘段階・ラウンド・行動順・予約・両陣営資源を内部状態と独立した辞書で返します]
#   処理: [1: 戦闘段階・ラウンド・行動順・予約・両陣営資源を内部状態と独立した辞書で返します]
#   引数: []
#   戻り値: [result: 内部状態から独立した戦闘段階・予約・参加者資源の辞書（Dictionary）]
# }
func snapshot() -> Dictionary:
	return {"phase": _phase, "round": _round, "cursor": _cursor, "order": _order.duplicate(true),
		"pending": null if _pending.is_empty() else _pending.duplicate(true),
		"teams": _snapshots(), "scope": "base_battle_cursor"}


# {
#   責務: [begin_round: 現在資源を保持し、状態付き開始では最新状態の補正速度、従来開始では基本速度でラウンド順序を固定します]
#   処理: [
#     1: 開始可能な戦闘段階を確認し、所有資源と最新状態による順序の計算を担当契約へ委譲します
#     2: 計画成功後だけラウンドとカーソルを更新し、敵なし停止時は防御解除と速度期間の終端処理へ委譲します
#   ]
#   引数: [shuffle_order: 陣営sideと個体idで表す全参加者の並べ替え候補列。敏捷性が同じ参加者の順を決めます（Variant）]
#   戻り値: [result: plan/session/stopまたは理由付き拒否。勝敗処理ではない]
# }
func begin_round(shuffle_order: Variant) -> Dictionary:
	# Sessionは進行中の順序や予約を上書きしないよう、計算前にラウンド開始可能性を確認します。
	if _phase == "not_started":
		return _failure("not_initialized")
	if _phase not in ["between_rounds", "round_finished"]:
		return _failure("round_not_available")
	var teams := _snapshots()
	var planned := _plan_round(teams, shuffle_order)
	if not planned["ok"]:
		return planned
	# Sessionは計画全体が成功するまでラウンド・順序・資源・状態を変更しません。
	_round += 1
	_order = planned["order"].duplicate(true)
	_cursor = 0
	_phase = "round_active"
	if not _both_sides_alive():
		_end_round("stopped")
	return {"ok": true, "plan": planned, "session": snapshot(), "stop": _phase == "stopped"}


# {
#   責務: [_plan_round: 所有状態の有無に応じて基礎順序または状態補正順序へ委譲し、Session自体を変更しません]
#   処理: [1: 従来開始は基礎順序へ渡し、状態付き開始は全員の最新状態と所有倍率を状態順序へ渡します]
#   引数: [
#     teams: Sessionが所有する現在HPMP・生死と補正前能力値の独立コピー（Dictionary）
#     shuffle_order: 生存者全員のside/idを一度ずつ含む同速時の明示順（Variant）
#   ]
#   戻り値: [result: 完全な順序計画または非変更の拒否。状態付き計画は全員の実効速度も返します（Dictionary）]
# }
func _plan_round(teams: Dictionary, shuffle_order: Variant) -> Dictionary:
	# 従来開始は最新状態を持たないため、最低速度1を含む元の基礎順序契約へ直接委譲します。
	if _statuses == null:
		return Order.plan(teams["allies"], teams["enemies"], shuffle_order)
	# ラウンド要求へ外部倍率を持ち込まず、開始時に独立保持した全参加者の現在倍率を読みます。
	var multipliers: Dictionary = _speeds.multipliers()
	return StatusOrder.plan({"allies": teams["allies"], "enemies": teams["enemies"],
		"statuses": _statuses.snapshot()["teams"], "speed_multipliers": multipliers, "shuffle_order": shuffle_order})


# {
#   責務: [next_actor: 死亡/逃走者を飛ばし、次の行動候補をoffered段階で提示します。提示だけでは実行権を与えません]
#   処理: [
#     1: pendingがあれば同じコピーを返し新しい行動権を与えない
#     2: 最新生存を確認して候補を予約し、敵なし/末尾なら防御解除と速度期間の終端処理へ委譲します
#   ]
#   引数: []
#   戻り値: [result: offered/pending/終端結果。取得だけではcan_execute=false（Dictionary）]
# }
func next_actor() -> Dictionary:
	if _phase == "not_started":
		return _failure("not_initialized")
	if _phase != "round_active":
		return {"ok": true, "status": _phase, "can_execute": false}
	if not _pending.is_empty():
		return {"ok": true, "status": "pending", "pending": _pending.duplicate(true), "can_execute": false}
	var skipped: Array = []
	while _cursor < _order.size():
		var checked := _check(_order[_cursor])
		if checked["stop"]:
			_end_round("stopped")
			return {"ok": true, "status": _phase, "reason": checked["reason"], "skipped": skipped, "can_execute": false}
		if not checked["can_act"]:
			skipped.append(_order[_cursor].duplicate(true))
			_cursor += 1
			continue
		_pending = {"ticket": {"round": _round, "slot": _cursor, "actor": _order[_cursor].duplicate(true)},
			"stage": "offered"}
		return {"ok": true, "status": "offered", "pending": _pending.duplicate(true),
			"eligibility": checked, "skipped": skipped, "can_execute": false}
	_end_round("round_finished" if _both_sides_alive() else "stopped")
	return {"ok": true, "status": _phase, "skipped": skipped, "can_execute": false}


# {
#   責務: [inspect_ticket: 提示中の行動票と最新生存条件を照合します。取得・資源変更・順序消費は行いません]
#   処理: [
#     1: 現在のround/slot/actorとの一致を検証する
#     2: 既claimedを拒否し、最新の死亡・逃走・敵生存を照合する
#   ]
#   引数: [ticket: 現在ラウンドround・行動順位置slot・side/idのactorを持つ行動票（Variant）]
#   戻り値: [result: eligibilityまたは拒否理由。行動権は取得しない]
# }
func inspect_ticket(ticket: Variant) -> Dictionary:
	# Read-only validation, never a permission to execute or consume the cursor.
	var checked := _check_ticket(ticket)
	if not checked["ok"]:
		return checked
	if _pending["stage"] != "offered":
		return _failure("already_claimed")
	return {"ok": true, "eligibility": _check(ticket["actor"])}


# {
#   責務: [claim: 提示中の行動票を最新状態と照合し、一回だけ取得します。実行不能なら候補を取り消します]
#   処理: [
#     1: inspect_ticketで現在の行動候補を確認する
#     2: 実行不能なら候補を取消しcursorを進める
#     3: 実行可能ならclaimedへ変更する。HP/MPや攻撃計算は変更しない
#   ]
#   引数: [ticket: 提示中のround/slot/actorと一致する一回取得用の行動票（Variant）]
#   戻り値: [result: can_execute/ticketまたは拒否理由]
# }
func claim(ticket: Variant) -> Dictionary:
	var checked := inspect_ticket(ticket)
	if not checked["ok"]:
		return checked
	var eligibility: Dictionary = checked["eligibility"]
	if not eligibility["can_act"]:
		_pending.clear()
		_cursor += 1
		_update_phase()
		return {"ok": true, "can_execute": false, "reason": eligibility["reason"], "session": snapshot()}
	_pending["stage"] = "claimed"
	return {"ok": true, "can_execute": true, "ticket": ticket.duplicate(true), "eligibility": eligibility}


# {
#   責務: [finish: 取得済みの現在行動票を一回だけ完了し、末尾/敵なしなら物理防御解除と速度期間の経過へ委譲します]
#   処理: [
#     1: 同じticketがclaimedであることを確認する
#     2: pendingを消費しcursorを進め終端判定へ委譲する
#   ]
#   引数: [ticket: 取得済みの現在round/slot/actorに一致する完了用行動票（Variant）]
#   戻り値: [result: 更新後sessionまたは非破壊的拒否。戦闘の勝敗確定ではない（Dictionary）]
# }
func finish(ticket: Variant) -> Dictionary:
	var checked := _check_ticket(ticket)
	if not checked["ok"]:
		return checked
	if _pending["stage"] != "claimed":
		return _failure("pending_not_claimed")
	_pending.clear()
	_cursor += 1
	_update_phase()
	return {"ok": true, "session": snapshot()}


# {
#   責務: [take_damage: 指定したside/idの参加個体へダメージ適用を委譲し、実ダメージと現在HPを返します]
#   処理: [1: 指定したside/idの参加個体へダメージ適用を委譲し、実ダメージと現在HPを返します]
#   引数: [
#     key: sideとidで指定する戦闘参加個体（Variant）
#     amount: 非負整数の要求ダメージ量（Variant）
#   ]
#   戻り値: [result: 要求量・実ダメージ・現在HP、または理由付き拒否（Dictionary）]
# }
func take_damage(key: Variant, amount: Variant) -> Dictionary:
	var checked := _resolve(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].take_damage(amount)


# {
#   責務: [heal: 指定参加個体のHP回復を資源所有者へ委譲します]
#   処理: [1: 初期化とside/idを検証し、combatant_state.gdへ最大HPで止まる回復を依頼します]
#   引数: [
#     key: 回復対象を指定するsideとid（Variant）
#     amount: 非負整数の回復要求量（Variant）
#   ]
#   戻り値: [result: 個体の実回復量と現在HP、または理由付き拒否（Dictionary）]
# }
func heal(key: Variant, amount: Variant) -> Dictionary:
	# 予約・逃走・勝敗を変更せず、HPの数値更新だけを担当個体へ委譲する。
	var checked := _resolve(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].heal(amount)


# {
#   責務: [effects: 全参加者の物理防御倍率を、数値資源/状態一覧と別の独立コピーで返します]
#   処理: [1: 両陣営のside+id倍率を複製する]
#   引数: []
#   戻り値: [result: side/id別の倍率teamsとscope=basic_guard_onlyの独立辞書（Dictionary）]
# }
func effects() -> Dictionary:
	return {"teams": _guards.duplicate(true), "scope": "basic_guard_only"}


# {
#   責務: [guard: 指定参加者についてSessionが保持する現在の物理防御倍率を読み取ります]
#   処理: [1: side+idを検証し所有倍率を返す]
#   引数: [key: 対象のside+id（Variant）]
#   戻り値: [result: ok/guardまたはreason付き失敗（Dictionary）]
# }
func guard(key: Variant) -> Dictionary:
	var checked := _resolve(key)
	return checked if not checked["ok"] else {"ok": true, "guard": _guards[key["side"]][key["id"]]}


# {
#   責務: [apply_defend: 現在の行動票を取得済みで生存する行動者本人の物理防御倍率だけを更新します]
#   処理: [
#     1: ticketの一致とclaimedおよび有限倍率を検証する
#     2: 最新行動可否を確認し本人の倍率だけを変更する
#   ]
#   引数: [
#     ticket: 単一行動権のticket（Variant）
#     multiplier: 正規defend定義から検証済みの倍率（Variant）
#   ]
#   戻り値: [result: ok/guardまたは非破壊的な失敗（Dictionary）]
# }
func apply_defend(ticket: Variant, multiplier: Variant) -> Dictionary:
	var checked := _check_ticket(ticket)
	if not checked["ok"]:
		return checked
	if _pending["stage"] != "claimed":
		return _failure("pending_not_claimed")
	var value := StatNumbers.float_value(multiplier)
	if not value["ok"]:
		return _failure("invalid_guard")
	if not _check(ticket["actor"])["can_act"]:
		return _failure("actor_cannot_defend")
	var actor: Dictionary = ticket["actor"]
	_guards[actor["side"]][actor["id"]] = value["value"]
	return {"ok": true, "guard": value["value"]}


# {
#   責務: [mp_cost: 指定した戦闘個体が現在のMPで指定消費量を払えるか確認し、MP自体は変更しません]
#   処理: [1: 陣営と個体IDから戦闘個体を特定し、消費MPの妥当性と支払い可否の確認をcombatant_state.gdの戦闘個体へ委譲します]
#   引数: [
#     key: MPの支払い可否を調べる個体の陣営sideと個体idを含む辞書（Variant）
#     cost: 支払えるか確認する消費MP。combatant_state.gdの戦闘個体が非負整数として検証します（Variant）
#   ]
#   戻り値: [result: 妥当な入力なら消費量cost・支払い可否affordable・現在mp、不正なら拒否理由reasonを含む結果（Dictionary）]
# }
func mp_cost(key: Variant, cost: Variant) -> Dictionary:
	var checked := _resolve(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].mp_cost(cost)


# {
#   責務: [pay_mp: 指定したside/idの参加個体へMP支払いを委譲し、不正や不足時は資源を保持します]
#   処理: [1: 指定したside/idの参加個体へMP支払いを委譲し、不正や不足時は資源を保持します]
#   引数: [
#     key: sideとidで指定する戦闘参加個体（Variant）
#     cost: 指定個体が支払う非負整数のMP量（Variant）
#   ]
#   戻り値: [result: 実消費量spent・現在mp、または資源を保持した不足や不正入力の拒否（Dictionary）]
# }
func pay_mp(key: Variant, cost: Variant) -> Dictionary:
	var checked := _resolve(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].pay_mp(cost)


# {
#   責務: [restore_mp: 指定個体の最大MPまでの数値回復を資源所有者へ委譲し、予約やHPを変更しません]
#   処理: [1: 陣営と個体IDを検証し、combatant_state.gdへMP回復を委譲します]
#   引数: [
#     key: MPを回復する戦闘参加個体のsideとid（Variant）
#     amount: 精度上限以内の非負整数として検証するMP回復要求量（Variant）
#   ]
#   戻り値: [result: 実回復量restored・現在mp、または資源を保持した拒否（Dictionary）]
# }
func restore_mp(key: Variant, amount: Variant) -> Dictionary:
	# 数値回復は行動権を与えず、ラウンドや逃走・勝敗判定を変更しません。
	var checked := _resolve(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].restore_mp(amount)


# {
#   責務: [flee: 指定した参加個体をHPとMPを保持した逃走状態へ変更します]
#   処理: [1: 指定した参加個体をHPとMPを保持した逃走状態へ変更します]
#   引数: [key: sideとidで指定する戦闘参加個体（Variant）]
#   戻り値: [result: 逃走更新の結果・現在HP/MP・生存判定、または未初期化の拒否（Dictionary）]
# }
func flee(key: Variant) -> Dictionary:
	var checked := _resolve(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].flee()


# {
#   責務: [_resolve: Sessionの初期化とside/idの形式・存在を確認し、指定個体への資源操作を許可または拒否します]
#   処理: [1: Sessionの初期化とside/idの形式・存在を確認し、指定個体への資源操作を許可または拒否します]
#   引数: [key: sideとidで指定する戦闘参加個体（Variant）]
#   戻り値: [result: 指定個体の検証成功ok、または未初期化・不正キー・欠落個体のreason（Dictionary）]
# }
func _resolve(key: Variant) -> Dictionary:
	if _phase == "not_started":
		return _failure("not_initialized")
	if not Order.valid_key(key):
		return _failure("invalid_actor_key")
	if not _by_id[key["side"]].has(key["id"]):
		return _failure("actor_missing")
	return {"ok": true}


# {
#   責務: [_check_ticket: 現在の予約と指定ticketのラウンド・位置・行動者が厳密に一致するか検証します]
#   処理: [1: 現在の予約と指定ticketのラウンド・位置・行動者が厳密に一致するか検証します]
#   引数: [ticket: 行動権チケット（Variant）]
#   戻り値: [result: 予約一致の成功ok、または欠落・不正・不一致を示すreason（Dictionary）]
# }
func _check_ticket(ticket: Variant) -> Dictionary:
	if _phase == "not_started":
		return _failure("not_initialized")
	if not ticket is Dictionary or ticket.size() != 3 or not Order.valid_key(ticket.get("actor")):
		return _failure("invalid_ticket")
	for key in ["round", "slot"]:
		var value: Variant = ticket.get(key)
		if not (value is int or value is float) or not is_finite(float(value)) \
			or value < 0 or value > State.MAX_EXACT_INTEGER or float(value) != floorf(float(value)):
			return _failure("invalid_ticket")
	# JSON.parseの整数値floatと内部intは同じ予約番号として照合し、小数/真偽値は上の検証で拒否します。
	if _pending.is_empty() or int(ticket["round"]) != _pending["ticket"]["round"] \
		or int(ticket["slot"]) != _pending["ticket"]["slot"] or ticket["actor"] != _pending["ticket"]["actor"]:
		return _failure("ticket_not_pending")
	return {"ok": true}


# {
#   責務: [_check: 所有資源の最新生存を投影契約へ渡し、指定行動者の生存・逃走・敵の有無を確認します]
#   処理: [1: 検証済み所有者から最新生存者だけを読み、共用の投影契約で行動可否を組み立てます]
#   引数: [key: 実行可否を調べる行動者の陣営sideと個体id（Dictionary）]
#   戻り値: [result: 行動者の実行可否can_act・友軍friends・敵foes・停止判定stop（Dictionary）]
# }
func _check(key: Dictionary) -> Dictionary:
	# キーは検証済みの行動順/予約に由来し、資源所有者の全更新APIは開始時の不変条件を維持します。
	# 最新生存を毎回読み、公開コピーの再検証や死者の不要コピーを繰り返しません。
	var side: String = key["side"]
	var other := "enemies" if side == "allies" else "allies"
	return Eligibility.from_resources(key, _by_id[side][key["id"]].alive(), _teams[side], _teams[other])


# {
#   責務: [_snapshots: 各資源所有者から最新コピーを取得し、両陣営の参加者列を持つ辞書を返します]
#   処理: [1: 初期参加順を保って最新資源をalliesとenemiesの列へ追加します]
#   引数: []
#   戻り値: [result: alliesとenemiesをキーとする最新資源コピー列の辞書（Dictionary）]
# }
func _snapshots() -> Dictionary:
	var teams := {"allies": [], "enemies": []}
	for side in Order.SIDES:
		for state: RefCounted in _teams[side]:
			teams[side].append(state.snapshot())
	return teams


# {
#   責務: [_both_sides_alive: 両陣営それぞれにHPが正で未逃走の参加個体がいるか確認します]
#   処理: [1: 両陣営それぞれにHPが正で未逃走の参加個体がいるか確認します]
#   引数: []
#   戻り値: [result: 両陣営に生存・未逃走の参加個体がいる場合true、それ以外false（bool）]
# }
func _both_sides_alive() -> bool:
	for side in Order.SIDES:
		var living := false
		for state: RefCounted in _teams[side]:
			living = living or state.alive()
		if not living:
			return false
	return true


# {
#   責務: [_update_phase: 最新生存とカーソルを確認し、戦闘停止またはラウンド終端へ段階を更新します]
#   処理: [1: 最新生存とカーソルを確認し、戦闘停止またはラウンド終端へ段階を更新します]
#   引数: []
#   戻り値: [result: なし（void）。最新生存とカーソルに応じて戦闘段階を更新します]
# }
func _update_phase() -> void:
	if not _both_sides_alive():
		_end_round("stopped")
	elif _cursor == _order.size():
		_end_round("round_finished")


# {
#   責務: [_end_round: 進行中のラウンドを一度だけ閉じ、全員の速度期間経過と防御解除を行います]
#   処理: [
#     1: round_activeから指定終端段階へ切り替え、同じラウンドの再経過を防ぎます
#     2: 速度集合へ全員の一回経過を委譲し、全個体の物理防御倍率を1へ戻します
#   ]
#   引数: [phase: round_finishedまたはstopped（String）]
#   戻り値: [result: なし（void）。HP/MP・状態一覧・固定順を保持し、速度期間と物理防御倍率だけを更新します]
# }
func _end_round(phase: String) -> void:
	# 末尾・途中停止・取消が同じ終端へ集まっても、終了済みラウンドを二回進めません。
	if _phase != "round_active":
		return
	_phase = phase
	if _speeds != null:
		_speeds.elapse_round()
	# 生死や逃走で所有者を取り除かず、全参加者のラウンド限定防御を解除します。
	for side in Order.SIDES:
		for id: String in _guards[side]:
			_guards[side][id] = 1.0


# {
#   責務: [_failure: Sessionを変更せず、ok=falseと指定した拒否理由を返します]
#   処理: [1: Sessionを変更せず、ok=falseと指定した拒否理由を返します]
#   引数: [reason: Sessionの開始・予約・資源操作を拒否した具体的理由（String）]
#   戻り値: [result: ok=falseと指定した拒否理由reasonを持つ辞書（Dictionary）]
# }
func _failure(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
