# {
#   責務: [run_battle_session_probe: Developer-only isolated session protocol probe and amortized cursor-stage microbenchmark.]
#   フィールド: []
# }
extends SceneTree
## Developer-only isolated session protocol probe and amortized cursor-stage microbenchmark.

const Session = preload("res://engine/battle_session.gd")
const Application = preload("res://application/battle_session_application.gd")
const Repository = preload("res://data/content_repository.gd")
const Order = preload("res://engine/turn_order.gd")


# {
#   責務: [_initialize: run・戦闘・セッション・probeのエントリ処理を実行する]
#   処理: [1: run・戦闘・セッション・probeのエントリ処理を実行する]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _initialize() -> void:
	var arguments := OS.get_cmdline_user_args()
	if arguments.size() != 1:
		quit(2)
		return
	var payload: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(arguments[0]))
	var result := {"cases": [], "joined": []}
	if payload.get("performance", false):
		result = _performance(payload)
	else:
		for case: Dictionary in payload.get("cases", []):
			result["cases"].append(_case(case))
		for case: Dictionary in payload.get("joined", []):
			result["joined"].append(_joined(case))
	print("KADOKA_SESSION_RESULT=" + Marshalls.utf8_to_base64(JSON.stringify(result)))
	quit(0)


# {
#   責務: [_case: run・戦闘・セッション・probeのcaseを求める]
#   処理: [1: run・戦闘・セッション・probeのcaseを求める]
#   引数: [case: case（Dictionary）]
#   戻り値: [result: run・戦闘・セッション・probeのcaseを求めるための結果（Dictionary）]
# }
func _case(case: Dictionary) -> Dictionary:
	var session = Session.new()
	var input: Dictionary = case["input"].duplicate(true)
	for special: Dictionary in case.get("special", []):
		var current: Variant = input
		var path: Array = special["path"]
		for index in path.size() - 1:
			current = current[int(path[index])] if current is Array else current[path[index]]
		current[path.back()] = INF if special["value"] == "inf" else NAN
	var before := input.duplicate(true)
	var initialized: Dictionary = session.start(input.get("allies"), input.get("enemies")) if case.get("start", true) else {}
	var copied_initial := initialized.duplicate(true)
	if case.get("mutate_initial", false):
		_mutate(initialized)
	var observations: Array = []
	for action: Dictionary in case.get("actions", []):
		var value := _execute(session, action, input)
		var copied := value.duplicate(true)
		if action.get("mutate_result", false):
			_mutate(value)
		observations.append({"value": copied, "session": session.snapshot()})
	return {"initialized": copied_initial, "observations": observations, "session": session.snapshot(),
		"input_preserved": input == before if case.get("special", []).is_empty() else true}


# {
#   責務: [_execute: run・戦闘・セッション・probeを実行する]
#   処理: [1: run・戦闘・セッション・probeを実行する]
#   引数: [
#     session: セッション（RefCounted）
#     action: action（Dictionary）
#     input: 入力（Dictionary）
#   ]
#   戻り値: [result: run・戦闘・セッション・probeを実行するための結果（Dictionary）]
# }
func _execute(session: RefCounted, action: Dictionary, input: Dictionary) -> Dictionary:
	var value: Variant = action.get("value")
	if action.has("special"):
		value = INF if action["special"] == "inf" else NAN
	var pending: Variant = session.snapshot()["pending"]
	var ticket: Variant = action.get("ticket", pending["ticket"] if pending is Dictionary else null)
	match action["kind"]:
		"start": return session.start(action.get("allies", input.get("allies")), action.get("enemies", input.get("enemies")))
		"begin": return session.begin_round(action.get("order", input.get("shuffle_order")))
		"next": return session.next_actor()
		"claim": return session.claim(ticket)
		"finish": return session.finish(ticket)
		"damage": return session.take_damage(action.get("actor"), value)
		"cost": return session.mp_cost(action.get("actor"), value)
		"pay": return session.pay_mp(action.get("actor"), value)
		"flee": return session.flee(action.get("actor"))
		"snapshot": return session.snapshot()
		"drain": return _drain(session, action.get("effects", []))
		"input_mutation":
			input["allies"][0]["identity"]["name"] = "edited caller"
			input["allies"][0]["stats"]["hp"] = 999
			input["shuffle_order"].reverse()
			return {"ok": true}
	return {"ok": false, "reason": "unknown_probe_operation"}


# {
#   責務: [_drain: run・戦闘・セッション・probeのdrainを求める]
#   処理: [1: run・戦闘・セッション・probeのdrainを求める]
#   引数: [
#     session: セッション（RefCounted）
#     effects: effects（Array）
#   ]
#   戻り値: [result: run・戦闘・セッション・probeのdrainを求めるための結果（Dictionary）]
# }
func _drain(session: RefCounted, effects: Array) -> Dictionary:
	var entries: Array = []
	for index in 8:
		var offered: Dictionary = session.next_actor()
		if offered.get("status") != "offered":
			break
		var ticket: Dictionary = offered["pending"]["ticket"]
		var claimed: Dictionary = session.claim(ticket)
		if not claimed.get("can_execute", false):
			continue
		var applied: Array = []
		for effect: Dictionary in effects:
			if effect["after"] == ticket["actor"]:
				applied.append(_execute(session, effect, {}))
		var finished: Dictionary = session.finish(ticket)
		assert(finished["ok"])
		entries.append({"actor": ticket["actor"], "eligibility": claimed["eligibility"], "applied": applied})
	return {"entries": entries, "session": session.snapshot()}


# {
#   責務: [_joined: run・戦闘・セッション・probeのjoinedを求める]
#   処理: [1: run・戦闘・セッション・probeのjoinedを求める]
#   引数: [case: case（Dictionary）]
#   戻り値: [result: run・戦闘・セッション・probeのjoinedを求めるための結果（Dictionary）]
# }
func _joined(case: Dictionary) -> Dictionary:
	var before := case.duplicate(true)
	var application = Application.new(Repository.new(OS.get_environment("KADOKA_CONTENT_ROOT")))
	var value: Dictionary = application.start(case.get("allies"), case.get("enemies"), case.get("shuffle_order"))
	var copied := value.duplicate(true)
	_mutate(value)
	var status: Dictionary = application.snapshot()
	_mutate(status)
	return {"value": copied, "session": application.snapshot(),
		"again": application.start(case.get("allies"), case.get("enemies"), case.get("shuffle_order")),
		"preserved": case == before}


# {
#   責務: [_mutate: run・戦闘・セッション・probeのmutateを求める]
#   処理: [1: run・戦闘・セッション・probeのmutateを求める]
#   引数: [value: 値（Variant）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _mutate(value: Variant) -> void:
	if value is Array:
		for entry: Variant in value:
			_mutate(entry)
	elif value is Dictionary:
		for entry: Variant in value.values():
			_mutate(entry)
		for key in ["hp", "mp", "round", "slot", "cursor", "speed"]:
			if value.has(key):
				value[key] = 999
		if value.has("id"):
			value["id"] = "edited output"


# {
#   責務: [_performance: run・戦闘・セッション・probeのperformanceを求める]
#   処理: [1: run・戦闘・セッション・probeのperformanceを求める]
#   引数: [payload: 要求データ（Dictionary）]
#   戻り値: [result: run・戦闘・セッション・probeのperformanceを求めるための結果（Dictionary）]
# }
func _performance(payload: Dictionary) -> Dictionary:
	var input := _benchmark_input()
	var session = Session.new()
	session.start(input["allies"], input["enemies"])
	var iterations := int(payload.get("iterations", 20000))
	var samples := int(payload.get("samples", 7))
	var warmup := int(payload.get("warmup", 2000))
	for index in warmup:
		_stage(session, input["shuffle_order"])
	var timings: Array = []
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			_stage(session, input["shuffle_order"])
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
	timings.sort()
	return {"microseconds": timings[timings.size() / 2], "iterations": iterations, "samples": samples,
		"warmup": warmup, "actors": 8}


# {
#   責務: [_stage: run・戦闘・セッション・probeのstageを求める]
#   処理: [1: run・戦闘・セッション・probeのstageを求める]
#   引数: [
#     session: セッション（RefCounted）
#     shuffle_order: 並べ替え・順序（Array）
#   ]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _stage(session: RefCounted, shuffle_order: Array) -> void:
	if session.snapshot()["phase"] != "round_active":
		session.begin_round(shuffle_order)
	var offered: Dictionary = session.next_actor()
	var ticket: Dictionary = offered["pending"]["ticket"]
	var claimed: Dictionary = session.claim(ticket)
	assert(claimed["can_execute"])
	session.take_damage(ticket["actor"], 0)
	session.pay_mp(ticket["actor"], 0)
	session.finish(ticket)


# {
#   責務: [_benchmark_input: run・戦闘・セッション・probeのbenchmark・入力を求める]
#   処理: [1: run・戦闘・セッション・probeのbenchmark・入力を求める]
#   引数: []
#   戻り値: [result: run・戦闘・セッション・probeのbenchmark・入力を求めるための結果（Dictionary）]
# }
func _benchmark_input() -> Dictionary:
	var teams := {"allies": [], "enemies": []}
	for side in Order.SIDES:
		for index in 4:
			teams[side].append({"identity": {"id": str(index), "species_id": "slime", "name": "test"},
				"stats": {"hp": 100, "mp": 20, "attack": 10, "defense": 10, "magic": 10, "speed": index % 3 + 1},
				"hp": 100, "mp": 20, "fled": false, "alive": true})
	teams["shuffle_order"] = Order.participants(teams["allies"], teams["enemies"])["members"]
	return teams
