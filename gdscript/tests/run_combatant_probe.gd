extends SceneTree
## Developer-only isolated-fixture probe. Battle state never writes any content/save.

const State = preload("res://engine/combatant_state.gd")
const Builder = preload("res://application/combatant_builder.gd")
const Repository = preload("res://data/content_repository.gd")
const Numbers = preload("res://engine/attack_numbers.gd")


func _initialize() -> void:
	var arguments := OS.get_cmdline_user_args()
	if arguments.size() != 1:
		quit(2)
		return
	var payload: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(arguments[0]))
	var result: Dictionary
	if payload.get("performance", false):
		result = _performance(payload)
	else:
		var builder = Builder.new(Repository.new(OS.get_environment("KADOKA_CONTENT_ROOT")))
		result = {"cases": [], "records": [], "teams": [], "joined": []}
		for case: Dictionary in payload.get("cases", []):
			result["cases"].append(_case(case))
		for record: Variant in payload.get("records", []):
			var before: Variant = _copy(record)
			result["records"].append({"value": builder.build(record), "preserved": record == before})
		for team: Variant in payload.get("teams", []):
			var before: Variant = _copy(team)
			result["teams"].append({"value": builder.build_team(team), "preserved": team == before})
		for case: Dictionary in payload.get("joined", []):
			result["joined"].append(_join(case, builder))
	print("KADOKA_COMBATANT_RESULT=" + Marshalls.utf8_to_base64(JSON.stringify(result)))
	quit(0)


func _case(case: Dictionary) -> Dictionary:
	var case_before := case.duplicate(true)
	var states: Array = [State.new(), State.new()]
	var identity: Variant = _copy(case.get("identity"))
	var stats: Variant = _copy(case.get("stats"))
	for key: String in case.get("special_stats", {}):
		stats[key] = INF if case["special_stats"][key] == "inf" else NAN
	var before: Variant = _copy([identity, stats])
	var initialized: Dictionary = states[0].start(identity, stats) if case.get("start", true) else {"ok": true}
	var observations: Array = []
	for action: Dictionary in case.get("actions", []):
		var state: RefCounted = states[int(action.get("actor", 0))]
		var value: Variant = action.get("value")
		if action.has("special"):
			value = INF if action["special"] == "inf" else NAN
		var answer: Dictionary = {}
		match action["kind"]:
			"damage": answer = state.take_damage(value)
			"cost": answer = state.mp_cost(value)
			"pay": answer = state.pay_mp(value)
			"flee": answer = state.flee()
			"start": answer = state.start(action.get("identity", identity), action.get("stats", stats))
			"initial_result_mutation":
				initialized["snapshot"]["stats"]["hp"] = 999
				initialized["snapshot"]["identity"]["name"] = "changed result"
			"snapshot_mutation":
				var detached: Dictionary = state.snapshot()
				if not detached.is_empty():
					detached["stats"]["hp"] = 999
					detached["identity"]["name"] = "changed"
					detached["hp"] = 999
			"input_mutation":
				identity["name"] = "changed input"
				stats["hp"] = 999
			"living", "living_mutation":
				var snapshots: Array = []
				for member: RefCounted in states:
					if not member.snapshot().is_empty():
						snapshots.append(member.snapshot())
				answer = State.living(action.get("members", snapshots))
				if action["kind"] == "living_mutation" and answer["ok"] and not answer["members"].is_empty():
					answer["members"][0]["stats"]["hp"] = 999
					answer["members"][0]["identity"]["name"] = "changed living"
		observations.append({"value": answer, "snapshots": [states[0].snapshot(), states[1].snapshot()]})
	return {"initialized": initialized, "observations": observations,
		"case_preserved": case == case_before,
		"input_preserved": [identity, stats] == before if case.get("special_stats", {}).is_empty() else true}


func _join(case: Dictionary, builder: RefCounted) -> Dictionary:
	var before := case.duplicate(true)
	var actor: Dictionary = builder.build(case["actor"])
	var target: Dictionary = builder.build(case["target"])
	if not actor["ok"] or not target["ok"]:
		return {"ok": false, "reason": "build_failed", "actor": actor, "target": target}
	var state = State.new()
	state.start(target["snapshot"]["identity"], target["snapshot"]["stats"])
	var steps: Array = []
	for parameters: Dictionary in case["attacks"]:
		var request := parameters.duplicate(true)
		request.merge({"attack": actor["snapshot"]["stats"]["attack"],
			"defense": target["snapshot"]["stats"]["defense"], "target_hp": state.snapshot()["hp"],
			"equipment": actor["equipment"]}, true)
		var numbers := Numbers.normal_attack(request)
		var applied: Dictionary = state.take_damage(numbers["damage"]) if numbers["ok"] else {}
		steps.append({"numbers": numbers, "applied": applied, "snapshot": state.snapshot()})
	return {"ok": true, "actor": actor, "target": target, "steps": steps, "preserved": case == before}


func _performance(payload: Dictionary) -> Dictionary:
	var iterations := int(payload.get("iterations", 20000))
	var samples := int(payload.get("samples", 7))
	var warmup := int(payload.get("warmup", 2000))
	for index in warmup:
		_cycle()
	var timings: Array = []
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			_cycle()
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
	timings.sort()
	return {"microseconds": timings[timings.size() / 2], "iterations": iterations,
		"samples": samples, "warmup": warmup, "actors": 8}


func _cycle() -> void:
	var snapshots: Array = []
	for index in 8:
		var state = State.new()
		state.start({"id": str(index), "species_id": "slime", "name": "test"},
			{"hp": 100, "mp": 20, "attack": 10, "defense": 10, "magic": 10, "speed": 10})
		state.take_damage(10)
		state.pay_mp(5)
		if index == 7:
			state.flee()
		snapshots.append(state.snapshot())
	State.living(snapshots)


func _copy(value: Variant) -> Variant:
	return value.duplicate(true) if value is Dictionary or value is Array else value
