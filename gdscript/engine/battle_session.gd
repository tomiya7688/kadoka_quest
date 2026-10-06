# {
#   責務: [battle_session: Own battle resources and a single-use round cursor. No action resolution or outcomes.]
#   フィールド: [
#     _teams: 両陣営（Dictionary）
#     _by_id: by・識別子（Dictionary）
#     _phase: 進行段階
#     _round: ラウンド
#     _cursor: カーソル
#     _order: 順序（Array）
#     _pending: 保留中の行動（Dictionary）
#   ]
# }
extends RefCounted
## Own battle resources and a single-use round cursor. No action resolution or outcomes.

const State = preload("res://engine/combatant_state.gd")
const Order = preload("res://engine/turn_order.gd")
var _teams: Dictionary = {"allies": [], "enemies": []}
var _by_id: Dictionary = {"allies": {}, "enemies": {}}
var _phase := "not_started"
var _round := 0
var _cursor := 0
var _order: Array = []
var _pending: Dictionary = {}


# {
#   責務: [start: 戦闘・セッションを開始する]
#   処理: [1: 戦闘・セッションを開始する]
#   引数: [
#     allies: 味方（Variant）
#     enemies: 敵（Variant）
#   ]
#   戻り値: [result: 戦闘・セッションを開始するための結果（Dictionary）]
# }
func start(allies: Variant, enemies: Variant) -> Dictionary:
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
	_teams = teams
	_by_id = by_id
	_phase = "between_rounds"
	return {"ok": true, "session": snapshot()}


# {
#   責務: [snapshot: 戦闘・セッションを状態を複製する]
#   処理: [1: 戦闘・セッションを状態を複製する]
#   引数: []
#   戻り値: [result: 戦闘・セッションを状態を複製するための結果（Dictionary）]
# }
func snapshot() -> Dictionary:
	return {"phase": _phase, "round": _round, "cursor": _cursor, "order": _order.duplicate(true),
		"pending": null if _pending.is_empty() else _pending.duplicate(true),
		"teams": _snapshots(), "scope": "base_battle_cursor"}


# {
#   責務: [begin_round: 資源を保持したまま明示shuffleに基づくラウンドの順序を固定する]
#   処理: [
#     1: 開始可能なphaseと参加者/順序の契約を検証する
#     2: 新しいroundとcursorを設定し、生存陣営に応じて進行段階を決める
#   ]
#   引数: [shuffle_order: 並べ替え・順序（Variant）]
#   戻り値: [result: plan/session/stopまたは理由付き拒否。勝敗処理ではない]
# }
func begin_round(shuffle_order: Variant) -> Dictionary:
	if _phase == "not_started":
		return _failure("not_initialized")
	if _phase not in ["between_rounds", "round_finished"]:
		return _failure("round_not_available")
	var teams := _snapshots()
	var planned := Order.plan(teams["allies"], teams["enemies"], shuffle_order)
	if not planned["ok"]:
		return planned
	_round += 1
	_order = planned["order"].duplicate(true)
	_cursor = 0
	_phase = "round_active" if _both_sides_alive() else "stopped"
	return {"ok": true, "plan": planned, "session": snapshot(), "stop": _phase == "stopped"}


# {
#   責務: [next_actor: 行動個体を次の値を求める]
#   処理: [1: 行動個体を次の値を求める]
#   引数: []
#   戻り値: [result: 行動個体を次の値を求めるための結果（Dictionary）]
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
			_phase = "stopped"
			return {"ok": true, "status": _phase, "reason": checked["reason"], "skipped": skipped, "can_execute": false}
		if not checked["can_act"]:
			skipped.append(_order[_cursor].duplicate(true))
			_cursor += 1
			continue
		_pending = {"ticket": {"round": _round, "slot": _cursor, "actor": _order[_cursor].duplicate(true)},
			"stage": "offered"}
		return {"ok": true, "status": "offered", "pending": _pending.duplicate(true),
			"eligibility": checked, "skipped": skipped, "can_execute": false}
	_phase = "round_finished" if _both_sides_alive() else "stopped"
	return {"ok": true, "status": _phase, "skipped": skipped, "can_execute": false}


# {
#   責務: [inspect_ticket: 現在のoffered ticketと最新実行可否を読み取り専用で確認する]
#   処理: [
#     1: 現在のround/slot/actorとの一致を検証する
#     2: 既claimedを拒否し、最新の死亡・逃走・敵生存を照合する
#   ]
#   引数: [ticket: 行動権チケット（Variant）]
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
#   責務: [claim: offered行動権を最新状態と照合し一度だけ取得する]
#   処理: [
#     1: inspect_ticketで現在の行動候補を確認する
#     2: 実行不能なら候補を取消しcursorを進める
#     3: 実行可能ならclaimedへ変更する。HP/MPや攻撃計算は変更しない
#   ]
#   引数: [ticket: 行動権チケット（Variant）]
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
#   責務: [finish: 戦闘・セッションを終了処理を行う]
#   処理: [1: 戦闘・セッションを終了処理を行う]
#   引数: [ticket: 行動権チケット（Variant）]
#   戻り値: [result: 戦闘・セッションを終了処理を行うための結果（Dictionary）]
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
#   責務: [take_damage: ダメージを反映する]
#   処理: [1: ダメージを反映する]
#   引数: [
#     key: キー（Variant）
#     amount: 量（Variant）
#   ]
#   戻り値: [result: ダメージを反映するための結果（Dictionary）]
# }
func take_damage(key: Variant, amount: Variant) -> Dictionary:
	var checked := _resolve(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].take_damage(amount)


# {
#   責務: [mp_cost: 戦闘・セッションのMP・消費量を求める]
#   処理: [1: 戦闘・セッションのMP・消費量を求める]
#   引数: [
#     key: キー（Variant）
#     cost: 消費量（Variant）
#   ]
#   戻り値: [result: 戦闘・セッションのMP・消費量を求めるための結果（Dictionary）]
# }
func mp_cost(key: Variant, cost: Variant) -> Dictionary:
	var checked := _resolve(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].mp_cost(cost)


# {
#   責務: [pay_mp: MPを支払う]
#   処理: [1: MPを支払う]
#   引数: [
#     key: キー（Variant）
#     cost: 消費量（Variant）
#   ]
#   戻り値: [result: MPを支払うための結果（Dictionary）]
# }
func pay_mp(key: Variant, cost: Variant) -> Dictionary:
	var checked := _resolve(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].pay_mp(cost)


# {
#   責務: [flee: 戦闘・セッションを逃走状態を設定する]
#   処理: [1: 戦闘・セッションを逃走状態を設定する]
#   引数: [key: キー（Variant）]
#   戻り値: [result: 戦闘・セッションを逃走状態を設定するための結果（Dictionary）]
# }
func flee(key: Variant) -> Dictionary:
	var checked := _resolve(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].flee()


# {
#   責務: [_resolve: 戦闘・セッションを解決する]
#   処理: [1: 戦闘・セッションを解決する]
#   引数: [key: キー（Variant）]
#   戻り値: [result: 戦闘・セッションを解決するための結果（Dictionary）]
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
#   責務: [_check_ticket: 行動権チケットを検査する]
#   処理: [1: 行動権チケットを検査する]
#   引数: [ticket: 行動権チケット（Variant）]
#   戻り値: [result: 行動権チケットを検査するための結果（Dictionary）]
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
	if _pending.is_empty() or ticket != _pending["ticket"]:
		return _failure("ticket_not_pending")
	return {"ok": true}


# {
#   責務: [_check: 戦闘・セッションを検査する]
#   処理: [1: 戦闘・セッションを検査する]
#   引数: [key: キー（Dictionary）]
#   戻り値: [result: 戦闘・セッションを検査するための結果（Dictionary）]
# }
func _check(key: Dictionary) -> Dictionary:
	var teams := _snapshots()
	return Order.check_actor(key, teams["allies"], teams["enemies"])


# {
#   責務: [_snapshots: 戦闘・セッションのsnapshotsを求める]
#   処理: [1: 戦闘・セッションのsnapshotsを求める]
#   引数: []
#   戻り値: [result: 戦闘・セッションのsnapshotsを求めるための結果（Dictionary）]
# }
func _snapshots() -> Dictionary:
	var teams := {"allies": [], "enemies": []}
	for side in Order.SIDES:
		for state: RefCounted in _teams[side]:
			teams[side].append(state.snapshot())
	return teams


# {
#   責務: [_both_sides_alive: 戦闘・セッションのboth・sides・aliveを求める]
#   処理: [1: 戦闘・セッションのboth・sides・aliveを求める]
#   引数: []
#   戻り値: [result: 戦闘・セッションのboth・sides・aliveを求めるための結果（bool）]
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
#   責務: [_update_phase: 進行段階を更新する]
#   処理: [1: 進行段階を更新する]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _update_phase() -> void:
	if not _both_sides_alive():
		_phase = "stopped"
	elif _cursor == _order.size():
		_phase = "round_finished"


# {
#   責務: [_failure: 戦闘・セッションのfailureを求める]
#   処理: [1: 戦闘・セッションのfailureを求める]
#   引数: [reason: 理由（String）]
#   戻り値: [result: 戦闘・セッションのfailureを求めるための結果（Dictionary）]
# }
func _failure(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
