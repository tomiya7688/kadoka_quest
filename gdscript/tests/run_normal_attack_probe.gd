# {
#   責務: [run_normal_attack_probe: Developer-only pure/joined action probe and eight-actor action microbenchmark.]
#   フィールド: []
# }
extends SceneTree
## Developer-only pure/joined action probe and eight-actor action microbenchmark.

const Session = preload("res://engine/battle_session.gd")
const Attack = preload("res://engine/normal_attack_action.gd")
const Application = preload("res://application/battle_session_application.gd")
const Repository = preload("res://data/content_repository.gd")
const Order = preload("res://engine/turn_order.gd")


# {
#   責務: [_initialize: run・normal・攻撃・probeのエントリ処理を実行する]
#   処理: [1: run・normal・攻撃・probeのエントリ処理を実行する]
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
			result["cases"].append(_case(case, false))
		for case: Dictionary in payload.get("joined", []):
			result["joined"].append(_case(case, true))
	print("KADOKA_NORMAL_ACTION_RESULT=" + Marshalls.utf8_to_base64(JSON.stringify(result)))
	quit(0)


# {
#   責務: [_case: run・normal・攻撃・probeのcaseを求める]
#   処理: [1: run・normal・攻撃・probeのcaseを求める]
#   引数: [
#     case: case（Dictionary）
#     joined: joined（bool）
#   ]
#   戻り値: [result: run・normal・攻撃・probeのcaseを求めるための結果（Dictionary）]
# }
func _case(case: Dictionary, joined: bool) -> Dictionary:
	var input: Dictionary = case["input"].duplicate(true)
	var before := input.duplicate(true)
	var session: RefCounted
	var attack: RefCounted
	var initialized: Dictionary
	if joined:
		session = Application.new(Repository.new(OS.get_environment("KADOKA_CONTENT_ROOT")))
		initialized = session.start(input.get("allies"), input.get("enemies"), input.get("shuffle_order"))
	else:
		session = Session.new()
		initialized = session.start(input.get("allies"), input.get("enemies")) if case.get("start_session", true) else {"ok": true}
		attack = Attack.new(session)
		var teams := {"allies": [], "enemies": []}
		for side in Order.SIDES:
			for member: Dictionary in input.get(side, []):
				teams[side].append({"snapshot": member, "equipment": input.get("equipment", {}).get(side, {}).get(member["identity"]["id"], {})})
		if initialized["ok"]:
			initialized = attack.start(case.get("context", teams), input.get("skills", {"schema_version": 1, "skills": [{"id": "attack", "kind": "physical"}]}))
		if initialized["ok"]:
			initialized = session.begin_round(input["shuffle_order"])
	var initial := initialized.duplicate(true)
	if case.get("mutate_initial", false):
		_mutate(initialized)
	var observations: Array = []
	var last_ticket: Variant = null
	for action: Dictionary in case.get("actions", []):
		var pending: Variant = session.snapshot()["pending"]
		if pending is Dictionary:
			last_ticket = pending["ticket"].duplicate(true)
		var value := _execute(session, attack, action, input, last_ticket, joined)
		var copied := value.duplicate(true)
		if action.get("mutate_result", false):
			_mutate(value)
		observations.append({"value": copied, "session": session.snapshot()})
	return {"initialized": initial, "observations": observations, "session": session.snapshot(), "input_preserved": input == before}


# {
#   責務: [_execute: run・normal・攻撃・probeを実行する]
#   処理: [1: run・normal・攻撃・probeを実行する]
#   引数: [
#     session: セッション（RefCounted）
#     attack: 攻撃（RefCounted）
#     action: action（Dictionary）
#     input: 入力（Dictionary）
#     ticket: 行動権チケット（Variant）
#     joined: joined（bool）
#   ]
#   戻り値: [result: run・normal・攻撃・probeを実行するための結果（Dictionary）]
# }
func _execute(session: RefCounted, attack: RefCounted, action: Dictionary, input: Dictionary, ticket: Variant, joined: bool) -> Dictionary:
	match action["kind"]:
		"next": return session.next_actor()
		"begin": return session.begin_round(action.get("order", input["shuffle_order"]))
		"attack":
			var request: Variant = action.get("request", {"ticket": ticket, "target": action.get("target"),
				"skill_id": "attack", "critical_roll": 0.5, "variance": 1.0})
			if request is Dictionary:
				request = request.duplicate(true)
				request.merge(action.get("overrides", {}), true)
				for special: String in action.get("special", {}):
					request[special] = INF if action["special"][special] == "inf" else NAN
			return session.resolve_normal_attack(request) if joined else attack.resolve(request)
		"claim": return session.claim(ticket)
		"configure": return attack.start(null, null)
		"damage": return session.take_damage(action["actor"], action["amount"])
		"flee": return session.flee(action["actor"])
		"input_mutation":
			_mutate(input)
			return {"ok": true}
	return {"ok": false, "reason": "unknown_probe_operation"}


# {
#   責務: [_mutate: run・normal・攻撃・probeのmutateを求める]
#   処理: [1: run・normal・攻撃・probeのmutateを求める]
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
		for key in ["hp", "mp", "round", "slot", "cursor", "speed", "attack", "power", "fixed_bonus_damage", "power_multiplier"]:
			if value.has(key):
				value[key] = 999
		if value.has("id"):
			value["id"] = "edited output"


# {
#   責務: [_performance: run・normal・攻撃・probeのperformanceを求める]
#   処理: [1: run・normal・攻撃・probeのperformanceを求める]
#   引数: [payload: 要求データ（Dictionary）]
#   戻り値: [result: run・normal・攻撃・probeのperformanceを求めるための結果（Dictionary）]
# }
func _performance(payload: Dictionary) -> Dictionary:
	var teams := {"allies": [], "enemies": []}
	var prepared := {"allies": [], "enemies": []}
	for side in Order.SIDES:
		for index in 4:
			var member := {"identity": {"id": str(index), "species_id": "slime", "name": "test"},
				"stats": {"hp": 1000000000, "mp": 20, "attack": 10, "defense": 10, "magic": 10, "speed": index % 3 + 1},
				"hp": 1000000000, "mp": 20, "fled": false, "alive": true}
			teams[side].append(member)
			prepared[side].append({"snapshot": member, "equipment": {"fixed_bonus_damage": 3}})
	var order: Array = Order.participants(teams["allies"], teams["enemies"])["members"]
	var session = Session.new()
	session.start(teams["allies"], teams["enemies"])
	var attack = Attack.new(session)
	var configured: Dictionary = attack.start(prepared, {"schema_version": 1, "skills": [{"id": "attack", "kind": "physical"}]})
	assert(configured["ok"])
	var iterations := int(payload.get("iterations", 20000))
	var samples := int(payload.get("samples", 7))
	var warmup := int(payload.get("warmup", 2000))
	for index in warmup:
		_stage(session, attack, order)
	var timings: Array = []
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			_stage(session, attack, order)
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
	timings.sort()
	var minimum_hp := 1000000000
	for team: Array in session.snapshot()["teams"].values():
		for member: Dictionary in team:
			minimum_hp = mini(minimum_hp, member["hp"])
	return {"microseconds": timings[timings.size() / 2], "iterations": iterations, "samples": samples,
		"warmup": warmup, "actors": 8, "minimum_hp": minimum_hp}


# {
#   責務: [_stage: run・normal・攻撃・probeのstageを求める]
#   処理: [1: run・normal・攻撃・probeのstageを求める]
#   引数: [
#     session: セッション（RefCounted）
#     attack: 攻撃（RefCounted）
#     order: 順序（Array）
#   ]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _stage(session: RefCounted, attack: RefCounted, order: Array) -> void:
	if session.snapshot()["phase"] != "round_active":
		session.begin_round(order)
	var offered: Dictionary = session.next_actor()
	var ticket: Dictionary = offered["pending"]["ticket"]
	var target := {"side": "enemies" if ticket["actor"]["side"] == "allies" else "allies", "id": "0"}
	var resolved: Dictionary = attack.resolve({"ticket": ticket, "target": target, "skill_id": "attack", "critical_roll": 0.5, "variance": 1.0})
	assert(resolved["executed"])
