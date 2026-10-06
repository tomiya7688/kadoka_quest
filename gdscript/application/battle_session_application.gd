extends RefCounted
## Read-only fresh-battle preparation and Session initialization only; no action or persistence.

const Preparation = preload("res://application/turn_preparation.gd")
const Session = preload("res://engine/battle_session.gd")
var _preparation: RefCounted
var _session: RefCounted = Session.new()


func _init(repository: RefCounted) -> void:
	_preparation = Preparation.new(repository)


func start(allies: Variant, enemies: Variant, shuffle_order: Variant) -> Dictionary:
	if _session.snapshot()["phase"] != "not_started":
		return {"ok": false, "reason": "already_initialized"}
	var prepared: Dictionary = _preparation.prepare(allies, enemies, shuffle_order)
	if not prepared["ok"]:
		return prepared
	var candidate = Session.new()
	var started: Dictionary = candidate.start(_snapshots(prepared["teams"]["allies"]), _snapshots(prepared["teams"]["enemies"]))
	if not started["ok"]:
		return started
	var planned: Dictionary = candidate.begin_round(shuffle_order)
	if not planned["ok"]:
		return planned
	_session = candidate
	return {"ok": true, "preparation": prepared, "session": snapshot()}


func snapshot() -> Dictionary:
	return _session.snapshot()


func _snapshots(members: Array) -> Array:
	var snapshots: Array = []
	for member: Dictionary in members:
		snapshots.append(member["snapshot"])
	return snapshots
