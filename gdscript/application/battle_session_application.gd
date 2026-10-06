extends RefCounted
## Route read-only battle preparation and explicit actions; no calculations, AI or persistence.

const Preparation = preload("res://application/turn_preparation.gd")
const Session = preload("res://engine/battle_session.gd")
const Attack = preload("res://engine/normal_attack_action.gd")
var _preparation: RefCounted
var _repository: RefCounted
var _session: RefCounted = Session.new()
var _attack: RefCounted


func _init(repository: RefCounted) -> void:
	_repository = repository
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
	var skills: Dictionary = _repository.load_skills()
	if not skills["ok"]:
		return skills
	var attack = Attack.new(candidate)
	var configured: Dictionary = attack.start(prepared["teams"], skills["value"])
	if not configured["ok"]:
		return configured
	var planned: Dictionary = candidate.begin_round(shuffle_order)
	if not planned["ok"]:
		return planned
	_session = candidate
	_attack = attack
	return {"ok": true, "preparation": prepared, "session": snapshot()}


func begin_round(shuffle_order: Variant) -> Dictionary:
	return _session.begin_round(shuffle_order)


func next_actor() -> Dictionary:
	return _session.next_actor()


func resolve_normal_attack(request: Variant) -> Dictionary:
	return {"ok": false, "reason": "not_initialized"} if _attack == null else _attack.resolve(request)


func snapshot() -> Dictionary:
	return _session.snapshot()


func _snapshots(members: Array) -> Array:
	var snapshots: Array = []
	for member: Dictionary in members:
		snapshots.append(member["snapshot"])
	return snapshots
