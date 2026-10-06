# {
#   責務: [run_modifiers_probe: Real contracts and scan-local services over test-owned content, never actual user saves.]
#   フィールド: []
# }
extends SceneTree
## Real contracts and scan-local services over test-owned content, never actual user saves.

const Base = preload("res://engine/monster_progression.gd")
const Modifiers = preload("res://engine/monster_modifiers.gd")
const Numbers = preload("res://engine/stat_numbers.gd")
const Repository = preload("res://data/content_repository.gd")
const Reconstruction = preload("res://application/monster_reconstruction.gd")

# {
#   責務: [CountingRepository: counting・データ取得先の状態と振る舞いを担当する]
#   フィールド: [
#     bundle: bundle（Dictionary）
#     counts: counts
#   ]
# }
class CountingRepository:
	extends RefCounted
	var bundle: Dictionary
	var counts := {"base": 0, "plus": 0, "equipment": 0}
	# {
	#   責務: [load_progression: progressionを読み込む]
	#   処理: [1: progressionを読み込む]
	#   引数: [_id: 識別子（String）]
	#   戻り値: [result: progressionを読み込むための結果（Dictionary）]
	# }
	func load_progression(_id: String) -> Dictionary:
		counts["base"] += 1
		return {"ok": true, "stats": bundle["stats"], "skills": bundle["skills"]}
	# {
	#   責務: [load_plus: ＋選択を読み込む]
	#   処理: [1: ＋選択を読み込む]
	#   引数: [_id: 識別子（String）]
	#   戻り値: [result: ＋選択を読み込むための結果（Dictionary）]
	# }
	func load_plus(_id: String) -> Dictionary:
		counts["plus"] += 1
		return {"ok": true, "value": bundle["plus"]}
	# {
	#   責務: [load_equipment: 装備を読み込む]
	#   処理: [1: 装備を読み込む]
	#   引数: []
	#   戻り値: [result: 装備を読み込むための結果（Dictionary）]
	# }
	func load_equipment() -> Dictionary:
		counts["equipment"] += 1
		return {"ok": true, "value": bundle["equipment"]}


# {
#   責務: [_initialize: run・modifiers・probeのエントリ処理を実行する]
#   処理: [1: run・modifiers・probeのエントリ処理を実行する]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _initialize() -> void:
	var request: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(OS.get_cmdline_user_args()[0]))
	var results: Array = []
	var preserved: Array = []
	for parameters: Dictionary in request.get("cases", []):
		var template: Dictionary = request.get("templates", {}).get(parameters.get("template"), parameters)
		var before := template.duplicate(true)
		var base: Dictionary = parameters.get("base", Base.rebuild(template.get("stats"), template.get("skills"),
			parameters.get("level", 1)))
		var original_base := base.duplicate(true)
		var equipment: Variant = parameters.get("equipment", request.get("equipment", {"equipment": []}))
		var equipment_before: Variant = equipment.duplicate(true) if equipment is Dictionary or equipment is Array else equipment
		var monster: Dictionary = parameters.get("monster", {"species_id": parameters.get("template", "slime")})
		var monster_before := monster.duplicate(true)
		var result := Modifiers.apply(base, template.get("plus", {}), equipment, monster)
		results.append(result.duplicate(true))
		if result["ok"] and parameters.get("mutate_result", false):
			result["stats"]["attack"] = -999
			result["skill_ids"].append("mutation")
			result["equipment"]["modified"] = true
		preserved.append(template == before and base == original_base and equipment == equipment_before and monster == monster_before)
	var rounds: Array = []
	for value in request.get("rounds", []):
		rounds.append(Numbers.rounded_integer(float(value)))
	for value: String in request.get("special_rounds", []):
		rounds.append(Numbers.rounded_integer(INF if value == "inf" else NAN))
	var repository = Repository.new(OS.get_environment("KADOKA_CONTENT_ROOT"))
	var plus_documents: Array = []
	for id: String in request.get("load_plus", []):
		plus_documents.append(repository.load_plus(id))
	var equipment_document := repository.load_equipment() if request.get("load_equipment", false) else {}
	var counter_result: Dictionary = {}
	if request.has("count_bundle"):
		var counter = CountingRepository.new()
		counter.bundle = request["count_bundle"]
		var counted = Reconstruction.new(counter)
		for monster: Dictionary in request["count_monsters"]:
			counted.rebuild(monster)
		counter_result["one_scan"] = counter.counts.duplicate()
		Reconstruction.new(counter).rebuild(request["count_monsters"][0])
		counter_result["next_scan"] = counter.counts.duplicate()
	var service = Reconstruction.new(repository)
	var joined: Array = []
	for monster: Dictionary in request.get("monsters", []):
		joined.append(service.rebuild(monster))
	if not request.get("updates", []).is_empty():
		# Explicit fixture writes. Refuse the source checkout's canonical content root.
		var canonical := ProjectSettings.globalize_path("res://").trim_suffix("/").get_base_dir().simplify_path()
		assert(repository.root.to_lower() != canonical.to_lower())
		for update: Dictionary in request["updates"]:
			var relative := "data/equipment/equipment.json"
			if update["kind"] == "plus":
				assert(Repository.valid_id(update["species_id"]))
				relative = "data/species/" + update["species_id"] + "/plus.json"
			else:
				assert(update["kind"] == "equipment")
			var file := FileAccess.open(repository.root.path_join(relative), FileAccess.WRITE)
			file.store_string(JSON.stringify(update["value"]))
			file.close()
	var cached: Array = []
	var refreshed: Array = []
	var next_service = Reconstruction.new(repository)
	for monster: Dictionary in request.get("monsters", []):
		cached.append(service.rebuild(monster))
		refreshed.append(next_service.rebuild(monster))
	print("KADOKA_MODIFIERS_RESULT=" + Marshalls.utf8_to_base64(JSON.stringify({
		"results": results, "input_preserved": preserved, "rounds": rounds,
		"plus_documents": plus_documents, "equipment_document": equipment_document, "counts": counter_result,
		"joined": joined, "cached": cached, "refreshed": refreshed,
	})))
	quit(0)
