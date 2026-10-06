extends RefCounted
## Battle-only numeric state. No persistence, turn policy or AI inference.

const Records = preload("res://engine/monster_record_contract.gd")
const MAX_EXACT_INTEGER := 9007199254740991
const STAT_KEYS := ["hp", "mp", "attack", "defense", "magic", "speed"]
var _identity: Dictionary = {}
var _stats: Dictionary = {}
var _hp := 0
var _mp := 0
var _fled := false
var _initialized := false


func start(identity: Variant, stats: Variant) -> Dictionary:
	if _initialized:
		return _failure("already_initialized")
	var checked := _validate_initial(identity, stats)
	if not checked["ok"]:
		return checked
	_identity = {"id": identity["id"], "species_id": identity["species_id"], "name": identity["name"]}
	for key in STAT_KEYS:
		_stats[key] = int(stats[key])
	_hp = _stats["hp"]
	_mp = _stats["mp"]
	_initialized = true
	return {"ok": true, "snapshot": snapshot()}


func snapshot() -> Dictionary:
	if not _initialized:
		return {}
	return {"identity": _identity.duplicate(true), "stats": _stats.duplicate(true),
		"hp": _hp, "mp": _mp, "fled": _fled, "alive": alive()}


func alive() -> bool:
	return _initialized and _hp > 0 and not _fled


func take_damage(amount: Variant) -> Dictionary:
	if not _initialized:
		return _failure("not_initialized")
	if not _nonnegative_integer(amount):
		return _failure("invalid_damage")
	var previous := _hp
	var dealt := mini(_hp, int(amount))
	_hp -= dealt
	return {"ok": true, "requested": int(amount), "previous_hp": previous,
		"dealt": dealt, "hp": _hp, "alive": alive()}


func mp_cost(cost: Variant) -> Dictionary:
	if not _initialized:
		return _failure("not_initialized")
	if not _nonnegative_integer(cost):
		return _failure("invalid_mp_cost")
	return {"ok": true, "cost": int(cost), "affordable": int(cost) <= _mp, "mp": _mp}


func pay_mp(cost: Variant) -> Dictionary:
	var checked := mp_cost(cost)
	if not checked["ok"]:
		return checked
	if not checked["affordable"]:
		return {"ok": false, "reason": "insufficient_mp", "cost": int(cost),
			"affordable": false, "spent": 0, "mp": _mp}
	_mp -= int(cost)
	return {"ok": true, "cost": int(cost), "affordable": true, "spent": int(cost), "mp": _mp}


func flee() -> Dictionary:
	if not _initialized:
		return _failure("not_initialized")
	var changed := not _fled
	_fled = true
	return {"ok": true, "changed": changed, "alive": alive(), "hp": _hp, "mp": _mp}


static func living(snapshots: Variant) -> Dictionary:
	if not snapshots is Array:
		return _failure("invalid_members")
	var members: Array = []
	var ids: Dictionary = {}
	for index in snapshots.size():
		var member: Variant = snapshots[index]
		var checked := _validate_snapshot(member)
		if not checked["ok"]:
			checked["index"] = index
			return checked
		var id: String = member["identity"]["id"]
		if ids.has(id):
			return {"ok": false, "reason": "duplicate_member", "index": index}
		ids[id] = true
		if member["alive"]:
			members.append(member.duplicate(true))
	return {"ok": true, "members": members}


static func _validate_snapshot(value: Variant) -> Dictionary:
	if not value is Dictionary:
		return _failure("invalid_snapshot")
	var initial := _validate_initial(value.get("identity"), value.get("stats"))
	if not initial["ok"]:
		return initial
	if not _nonnegative_integer(value.get("hp")) or not _nonnegative_integer(value.get("mp")):
		return _failure("invalid_runtime_resources")
	if value["hp"] > value["stats"]["hp"] or value["mp"] > value["stats"]["mp"]:
		return _failure("resources_exceed_maximum")
	if not value.get("fled") is bool or not value.get("alive") is bool:
		return _failure("invalid_alive_flags")
	if value["alive"] != (value["hp"] > 0 and not value["fled"]):
		return _failure("inconsistent_alive")
	return {"ok": true}


static func _validate_initial(identity: Variant, stats: Variant) -> Dictionary:
	if not identity is Dictionary:
		return _failure("invalid_identity")
	for key in ["id", "species_id", "name"]:
		if not identity.get(key) is String or identity[key].is_empty():
			return _failure("invalid_identity_" + key)
	if not Records.safe_id(identity["id"]) or not Records.safe_id(identity["species_id"]):
		return _failure("unsafe_identity")
	if not stats is Dictionary:
		return _failure("invalid_stats")
	for key in STAT_KEYS:
		if not _nonnegative_integer(stats.get(key)):
			return _failure("invalid_stat_" + key)
	if stats["hp"] == 0:
		return _failure("invalid_max_hp")
	return {"ok": true}


static func _nonnegative_integer(value: Variant) -> bool:
	return (value is int or value is float) and is_finite(float(value)) \
		and float(value) >= 0 and float(value) <= MAX_EXACT_INTEGER and float(value) == floorf(float(value))


static func _failure(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
