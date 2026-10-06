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


func snapshot() -> Dictionary:
	return {"phase": _phase, "round": _round, "cursor": _cursor, "order": _order.duplicate(true),
		"pending": null if _pending.is_empty() else _pending.duplicate(true),
		"teams": _snapshots(), "scope": "base_battle_cursor"}


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


func claim(ticket: Variant) -> Dictionary:
	var checked := _check_ticket(ticket)
	if not checked["ok"]:
		return checked
	if _pending["stage"] != "offered":
		return _failure("already_claimed")
	var eligibility := _check(ticket["actor"])
	if not eligibility["can_act"]:
		_pending.clear()
		_cursor += 1
		_update_phase()
		return {"ok": true, "can_execute": false, "reason": eligibility["reason"], "session": snapshot()}
	_pending["stage"] = "claimed"
	return {"ok": true, "can_execute": true, "ticket": ticket.duplicate(true), "eligibility": eligibility}


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


func take_damage(key: Variant, amount: Variant) -> Dictionary:
	var checked := _resolve(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].take_damage(amount)


func mp_cost(key: Variant, cost: Variant) -> Dictionary:
	var checked := _resolve(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].mp_cost(cost)


func pay_mp(key: Variant, cost: Variant) -> Dictionary:
	var checked := _resolve(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].pay_mp(cost)


func flee(key: Variant) -> Dictionary:
	var checked := _resolve(key)
	return checked if not checked["ok"] else _by_id[key["side"]][key["id"]].flee()


func _resolve(key: Variant) -> Dictionary:
	if _phase == "not_started":
		return _failure("not_initialized")
	if not Order.valid_key(key):
		return _failure("invalid_actor_key")
	if not _by_id[key["side"]].has(key["id"]):
		return _failure("actor_missing")
	return {"ok": true}


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


func _check(key: Dictionary) -> Dictionary:
	var teams := _snapshots()
	return Order.check_actor(key, teams["allies"], teams["enemies"])


func _snapshots() -> Dictionary:
	var teams := {"allies": [], "enemies": []}
	for side in Order.SIDES:
		for state: RefCounted in _teams[side]:
			teams[side].append(state.snapshot())
	return teams


func _both_sides_alive() -> bool:
	for side in Order.SIDES:
		var living := false
		for state: RefCounted in _teams[side]:
			living = living or state.alive()
		if not living:
			return false
	return true


func _update_phase() -> void:
	if not _both_sides_alive():
		_phase = "stopped"
	elif _cursor == _order.size():
		_phase = "round_finished"


func _failure(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
