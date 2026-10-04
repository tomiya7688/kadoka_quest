extends RefCounted
## Clock/RNG-injected fixed-actor rules. No I/O, UI, scene, battle or acquisition effects.

const Rules = preload("res://engine/field_engine.gd")
const Dialogue = preload("res://engine/dialogue_deck.gd")
const OPPOSITE = {"left": "right", "right": "left", "back": "front", "front": "back"}
const STEPS = [[-1, 0], [1, 0], [0, -1], [0, 1]]
var field: RefCounted
var rng: RefCounted
var npcs: Array = []
var warnings: Array = []
var movements: Array = []
var dialogue_states: Array = []
var movement_duration_ms: int


func _init(rules: RefCounted, random_source: RefCounted, duration_ms: int = 180) -> void:
	field = rules
	rng = random_source
	movement_duration_ms = maxi(1, duration_ms)


func reset(world: Dictionary, blocks: Dictionary, despawned: Array, player: Array, now: int) -> void:
	field.set_world(world, blocks)
	npcs.clear()
	movements.clear()
	dialogue_states.clear()
	warnings.clear()
	for source: Dictionary in world.get("fixed_mobs", []):
		var key := "%s:%s" % [world.get("id", ""), source.get("id", "")]
		if not bool(source.get("enabled", true)) or (
			not bool(source.get("respawn_on_map_enter", true)) and key in despawned
		):
			continue
		var npc := source.duplicate(true)
		npc.merge({
			"id": "fixed_mob_%d" % (npcs.size() + 1), "name": str(source.get("species_id", "")),
			"direction": "front", "ai": "idle", "move_interval_ms": 900, "move_chance": 100,
		}, false)
		# Never place on an occupied, blocked or out-of-bounds cell, even in edited maps.
		if not _free(int(npc["x"]), int(npc["y"]), player, npcs):
			var position := _first_free(world, player)
			if position.is_empty():
				warnings.append("固定モブ %s: 空きマスがないため配置できません。" % npc["id"])
				continue
			npc["x"] = position[0]
			npc["y"] = position[1]
		npc["move_count"] = 0
		npc["next_move_tick"] = now + maxi(100, int(npc["move_interval_ms"]))
		npcs.append(npc)
		dialogue_states.append(Dialogue.create(source))
		movements.append({"start": Vector2(npc["x"], npc["y"]),
			"target": Vector2(npc["x"], npc["y"]), "time": now})


func find_at(x: int, y: int) -> Dictionary:
	for npc: Dictionary in npcs:
		if int(npc["x"]) == x and int(npc["y"]) == y:
			return npc
	return {}


func talk(npc: Dictionary, player_direction: String) -> Dictionary:
	var index := npcs.find(npc)
	if index < 0:
		return {"kind": "dialogue_error", "name": "固定モブ", "error": "not_present",
			"message": "対象の固定モブがいません。"}
	npc["direction"] = OPPOSITE.get(player_direction, "front")
	var result := {"kind": "dialogue", "npc_id": npc["id"], "name": npc["name"]}
	var interaction := str(npc.get("interaction", "talk"))
	if interaction != "talk":
		result.merge({"kind": "dialogue_error", "error": "unported_interaction",
			"message": "[未移植: %s] この固定モブの操作はまだ接続されていません。" % interaction}, true)
		return result  # Do not consume dialogue/RNG or pretend to start a battle.
	var line: Dictionary = Dialogue.next_line(dialogue_states[index], rng)
	result.merge(line, true)
	if not line["ok"]:
		result["kind"] = "dialogue_error"
	else:
		result["unported_despawn"] = bool(npc.get("despawn_after_interaction", npc.get("despawn_after_talk", false)))
	return result


func _free(x: int, y: int, player: Array, others: Array) -> bool:
	if x == int(player[0]) and y == int(player[1]):
		return false
	return field.resolve_player_move(x, y, 0, 0, "front", others, [])["kind"] == "moved"


func _first_free(world: Dictionary, player: Array) -> Array:
	for y in int(world["height"]):
		for x in int(world["width"]):
			if _free(x, y, player, npcs):
				return [x, y]
	return []


func faces_player(npc: Dictionary, player: Array) -> bool:
	var front: Array = field.front_position(int(npc["x"]), int(npc["y"]), str(npc["direction"]))
	return int(front[0]) == int(player[0]) and int(front[1]) == int(player[1])


func move(index: int, player: Array, now: int) -> bool:
	var npc: Dictionary = npcs[index]
	if npc["ai"] == "idle" or faces_player(npc, player):
		return false
	if rng.randrange(100) >= clampi(int(npc["move_chance"]), 0, 100):
		return false
	var steps: Array = []
	if npc["ai"] == "chase":
		if int(player[0]) != int(npc["x"]):
			steps.append([1 if int(player[0]) > int(npc["x"]) else -1, 0])
		if int(player[1]) != int(npc["y"]):
			steps.append([0, 1 if int(player[1]) > int(npc["y"]) else -1])
	var fallback := STEPS.duplicate(true)
	rng.shuffle(fallback)
	for step: Array in fallback:
		if step not in steps:
			steps.append(step)
	var others: Array = []
	for other: Dictionary in npcs:
		if not is_same(other, npc):
			others.append(other)
	for step: Array in steps:
		var x := int(npc["x"]) + int(step[0])
		var y := int(npc["y"]) + int(step[1])
		if not _free(x, y, player, others):
			continue
		var start := _position(index, now)
		# Logical destination is reserved immediately; interpolation is visual only.
		npc["x"] = x
		npc["y"] = y
		npc["direction"] = Rules.direction_for_step(int(step[0]), int(step[1]))
		npc["move_count"] += 1
		movements[index] = {"start": start, "target": Vector2(x, y), "time": now}
		return true
	return false


func update(player: Array, now: int) -> bool:
	var moved := false
	for index in npcs.size():
		var npc: Dictionary = npcs[index]
		if now < int(npc["next_move_tick"]):
			continue
		var actor_moved := move(index, player, now)
		moved = actor_moved or moved
		# One attempt per deadline, even idle/blocked/failed-roll; no catch-up burst.
		npc["next_move_tick"] = now + maxi(100, int(npc["move_interval_ms"]))
	return moved


func _position(index: int, now: int) -> Vector2:
	var movement: Dictionary = movements[index]
	var progress := clampf(float(now - int(movement["time"])) / movement_duration_ms, 0.0, 1.0)
	var eased := progress * progress * (3.0 - 2.0 * progress)
	return Vector2(movement["start"]).lerp(Vector2(movement["target"]), eased)


func snapshot(now: int) -> Array:
	var result: Array = []
	for index in npcs.size():
		var npc: Dictionary = npcs[index].duplicate(true)
		var position := _position(index, now)
		npc["display_x"] = position.x
		npc["display_y"] = position.y
		result.append(npc)
	return result
