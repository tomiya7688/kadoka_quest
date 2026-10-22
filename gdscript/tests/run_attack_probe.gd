# {
#   責務: [run_attack_probe: Test-only deterministic numbers and reconstruction; fixture reads, never save writes.]
#   フィールド: []
# }
extends SceneTree
## Test-only deterministic numbers and reconstruction; fixture reads, never save writes.

const Rules = preload("res://engine/attack_numbers.gd")
const Repository = preload("res://data/content_repository.gd")
const Reconstruction = preload("res://application/monster_reconstruction.gd")


# {
#   責務: [_initialize: run・攻撃・probeのエントリ処理を実行する]
#   処理: [1: run・攻撃・probeのエントリ処理を実行する]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _initialize() -> void:
	var arguments := OS.get_cmdline_user_args()
	if arguments.size() != 1:
		quit(2)
		return
	var payload: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(arguments[0]))
	var results: Array = []
	var preserved: Array = []
	for case: Dictionary in payload.get("cases", []):
		var request: Variant = case.get("input", {})
		if request is Dictionary:
			request = request.duplicate(true)
			for key: String in case.get("special", {}):
				request[key] = INF if case["special"][key] == "inf" else NAN
		var before: Variant = request.duplicate(true) if request is Dictionary or request is Array else request
		var result: Dictionary
		match case["operation"]:
			"attack": result = Rules.normal_attack(request)
			"finish": result = Rules.finish_damage(request)
			"defend": result = Rules.defend_multiplier(request)
		results.append(result.duplicate(true))
		if case.get("mutate_result", false):
			result["damage"] = -999
		# NaN is not equal to itself; ordinary cases independently check every input field.
		preserved.append(request == before if case.get("special", {}).is_empty() else true)
	var joined: Array = []
	if not payload.get("joined", []).is_empty():
		var repository = Repository.new(OS.get_environment("KADOKA_CONTENT_ROOT"))
		var reconstruction = Reconstruction.new(repository)
		for case: Dictionary in payload["joined"]:
			joined.append(_join(case, reconstruction))
	print("KADOKA_ATTACK_RESULT=" + Marshalls.utf8_to_base64(JSON.stringify({
		"results": results, "input_preserved": preserved, "joined": joined})))
	quit(0)


# {
#   責務: [_join: run・攻撃・probeのjoinを求める]
#   処理: [1: run・攻撃・probeのjoinを求める]
#   引数: [
#     case: case（Dictionary）
#     reconstruction: reconstruction（RefCounted）
#   ]
#   戻り値: [result: run・攻撃・probeのjoinを求めるための結果（Dictionary）]
# }
func _join(case: Dictionary, reconstruction: RefCounted) -> Dictionary:
	var actor: Dictionary = reconstruction.rebuild(case["actor"])
	var target: Dictionary = reconstruction.rebuild(case["target"])
	for rebuilt in [actor, target]:
		if not rebuilt["ok"] or not rebuilt["modifiers"]["ok"]:
			return {"value": {"ok": false, "error": "reconstruction_failed"}}
	var input: Dictionary = case["input"].duplicate(true)
	input.merge({"attack": actor["modifiers"]["stats"]["attack"],
		"defense": target["modifiers"]["stats"]["defense"], "target_hp": target["modifiers"]["stats"]["hp"],
		"equipment": actor["modifiers"]["equipment"]}, true)
	return {"actor": actor, "target": target, "input": input, "value": Rules.normal_attack(input)}
