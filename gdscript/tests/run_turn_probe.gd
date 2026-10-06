# {
#   責務: [run_turn_probe: Developer-only pure turn contracts and isolated read-only record preparation.]
#   フィールド: []
# }
extends SceneTree
## Developer-only pure turn contracts and isolated read-only record preparation.

const Order = preload("res://engine/turn_order.gd")
const Preparation = preload("res://application/turn_preparation.gd")
const Repository = preload("res://data/content_repository.gd")


# {
#   責務: [_initialize: run・ターン・probeのエントリ処理を実行する]
#   処理: [1: run・ターン・probeのエントリ処理を実行する]
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
	for case: Dictionary in payload.get("cases", []):
		var request: Dictionary = case["input"].duplicate(true)
		for special: Dictionary in case.get("special", []):
			var current: Variant = request
			var path: Array = special["path"]
			for index in path.size() - 1:
				current = current[int(path[index])] if current is Array else current[path[index]]
			current[path.back()] = INF if special["value"] == "inf" else NAN
		var before := request.duplicate(true)
		var value := _execute(case["operation"], request)
		var copied := value.duplicate(true)
		if case.get("mutate_result", false):
			_mutate(value)
		result["cases"].append({"value": copied, "again": _execute(case["operation"], request),
			"input_preserved": request == before if case.get("special", []).is_empty() else true})
	var preparation = Preparation.new(Repository.new(OS.get_environment("KADOKA_CONTENT_ROOT")))
	for case: Dictionary in payload.get("joined", []):
		var before := case.duplicate(true)
		var value: Dictionary = preparation.prepare(case.get("allies"), case.get("enemies"), case.get("shuffle_order"))
		var copied := value.duplicate(true)
		if case.get("mutate_result", false) and value["ok"] and not value["teams"]["allies"].is_empty():
			value["teams"]["allies"][0]["snapshot"]["stats"]["speed"] = 999
			value["teams"]["allies"][0]["equipment"]["private"] = "edited output"
		result["joined"].append({"value": copied,
			"again": preparation.prepare(case.get("allies"), case.get("enemies"), case.get("shuffle_order")),
			"input_preserved": case == before})
	print("KADOKA_TURN_RESULT=" + Marshalls.utf8_to_base64(JSON.stringify(result)))
	quit(0)


# {
#   責務: [_execute: run・ターン・probeを実行する]
#   処理: [1: run・ターン・probeを実行する]
#   引数: [
#     operation: operation（String）
#     request: 要求（Dictionary）
#   ]
#   戻り値: [result: run・ターン・probeを実行するための結果（Dictionary）]
# }
func _execute(operation: String, request: Dictionary) -> Dictionary:
	match operation:
		"participants": return Order.participants(request.get("allies"), request.get("enemies"))
		"plan": return Order.plan(request.get("allies"), request.get("enemies"), request.get("shuffle_order"))
		"check": return Order.check_actor(request.get("actor"), request.get("allies"), request.get("enemies"))
	return {"ok": false, "reason": "unknown_probe_operation"}


# {
#   責務: [_mutate: run・ターン・probeのmutateを求める]
#   処理: [1: run・ターン・probeのmutateを求める]
#   引数: [value: 値（Dictionary）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _mutate(value: Dictionary) -> void:
	if not value["ok"]:
		return
	for key in ["members", "order", "initial"]:
		if value.has(key) and not value[key].is_empty():
			value[key][0]["id"] = "edited output"
	for key in ["friends", "foes"]:
		if value.has(key) and not value[key].is_empty():
			value[key][0]["identity"]["name"] = "edited output"
			value[key][0]["stats"]["speed"] = 999
	if value.has("actor"):
		value["actor"]["id"] = "edited output"
