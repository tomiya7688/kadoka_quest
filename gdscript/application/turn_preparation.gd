extends RefCounted
## Read-only record reconstruction -> pure base round plan. No action, inference or writes.

const Builder = preload("res://application/combatant_builder.gd")
const Order = preload("res://engine/turn_order.gd")
var builder: RefCounted


func _init(repository: RefCounted) -> void:
	builder = Builder.new(repository)


func prepare(allies: Variant, enemies: Variant, shuffle_order: Variant) -> Dictionary:
	var teams: Dictionary = {}
	var snapshots: Dictionary = {}
	for side in ["allies", "enemies"]:
		var built: Dictionary = builder.build_team(allies if side == "allies" else enemies)
		if not built["ok"]:
			return {"ok": false, "reason": "team_reconstruction_failed", "side": side, "detail": built}
		teams[side] = built["members"]
		snapshots[side] = _snapshots(built["members"])
	var planned := Order.plan(snapshots["allies"], snapshots["enemies"], shuffle_order)
	if not planned["ok"]:
		return planned
	return {"ok": true, "teams": teams, "plan": planned, "scope": "base_turn_preparation"}


func _snapshots(members: Array) -> Array:
	var snapshots: Array = []
	for member: Dictionary in members:
		snapshots.append(member["snapshot"])
	return snapshots
