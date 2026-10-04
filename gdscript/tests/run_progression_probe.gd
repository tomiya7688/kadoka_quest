extends SceneTree
## Real engine contracts and read-only repository calls; fixture roots only.

const Progression = preload("res://engine/monster_progression.gd")
const Repository = preload("res://data/content_repository.gd")
const Service = preload("res://application/monster_progression.gd")

class CountingRepository:
	extends RefCounted
	var calls := 0
	var bundle: Dictionary
	func load_progression(_id: String) -> Dictionary:
		calls += 1
		return bundle


func _initialize() -> void:
	var request: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(OS.get_cmdline_user_args()[0]))
	var results: Array = []
	var preserved: Array = []
	for parameters: Dictionary in request.get("cases", []):
		var template: Dictionary = request.get("templates", {}).get(parameters.get("template"), parameters)
		var before := template.duplicate(true)
		var stats: Variant = template.get("stats")
		var level: Variant = parameters.get("level", 1)
		if parameters.get("nonfinite") == "level_inf":
			level = INF
		elif parameters.get("nonfinite") in ["stat_inf", "stat_nan"]:
			stats = stats.duplicate(true)
			stats["levels"]["1"]["attack"] = INF if parameters["nonfinite"] == "stat_inf" else NAN
		var result := Progression.rebuild(stats, template.get("skills"), level)
		results.append(result.duplicate(true))
		if result["ok"] and parameters.get("mutate_result", false):
			result["stats"]["attack"] = -999
			result["skill_ids"].append("mutation")
		preserved.append(template == before)
	var repository = Repository.new(OS.get_environment("KADOKA_CONTENT_ROOT"))
	var bundles: Array = []
	for id: String in request.get("load_ids", []):
		bundles.append(repository.load_progression(id))
	var joins: Array = []
	var reads := 0
	var next_scan_reads := 0
	if request.has("join_bundle"):
		var counter = CountingRepository.new()
		counter.bundle = request["join_bundle"]
		var service = Service.new(counter)
		for monster: Dictionary in request.get("join_monsters", []):
			joins.append(service.rebuild(monster))
		reads = counter.calls
		# A new snapshot gets a new service: no stale cross-scan cache.
		Service.new(counter).rebuild(request["join_monsters"][0])
		next_scan_reads = counter.calls
	print("KADOKA_PROGRESSION_RESULT=" + Marshalls.utf8_to_base64(JSON.stringify({
		"results": results, "input_preserved": preserved, "bundles": bundles, "joins": joins, "reads": reads,
		"next_scan_reads": next_scan_reads,
	})))
	quit(0)
