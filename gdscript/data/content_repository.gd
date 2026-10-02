extends RefCounted
## Read-only access to the existing canonical data, never savedata/UserData.

var root: String
var last_error := ""


func _init(content_root: String) -> void:
	root = content_root.simplify_path()


func _read_dictionary(relative: String) -> Dictionary:
	last_error = ""
	var path := root.path_join(relative)
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		last_error = "Cannot read: " + path
		return {}
	var json := JSON.new()
	if json.parse(file.get_as_text()) != OK or not json.data is Dictionary:
		last_error = "Invalid JSON object: " + path
		return {}
	return json.data


static func valid_id(value: String) -> bool:
	if value.is_empty():
		return false
	for character in value:
		if not character in "abcdefghijklmnopqrstuvwxyz0123456789_-":
			return false
	return true


func load_blocks() -> Dictionary:
	var definitions := {}
	var folder := root.path_join("data/blocks")
	if not DirAccess.dir_exists_absolute(folder):
		last_error = "Missing blocks directory: " + folder
		return {}
	for filename in DirAccess.get_files_at(folder):
		if filename.ends_with(".json"):
			var block := _read_dictionary("data/blocks/" + filename)
			if block.is_empty() or not block.get("id") is String:
				if last_error.is_empty():
					last_error = "Missing block id: " + filename
				return {}
			definitions[block["id"]] = block
	return definitions


func load_map(map_id: String) -> Dictionary:
	if not valid_id(map_id):
		last_error = "Invalid map id: " + map_id
		return {}
	var world := _read_dictionary("data/maps/" + map_id + "/map.json")
	if world.is_empty():
		return {}
	if not world.get("tiles") is Array or int(world.get("width", 0)) <= 0 \
		or int(world.get("height", 0)) <= 0 or not world.get("start") is Dictionary:
		last_error = "Invalid map dimensions/start: " + map_id
		return {}
	if world["tiles"].size() != int(world["height"]):
		last_error = "Invalid map rows: " + map_id
		return {}
	for row in world["tiles"]:
		if not row is Array or row.size() != int(world["width"]):
			last_error = "Invalid map columns: " + map_id
			return {}
	world["events"] = world.get("events", []).duplicate(true)
	var folder := "data/maps/" + map_id + "/events"
	var filenames := PackedStringArray()
	if DirAccess.dir_exists_absolute(root.path_join(folder)):
		filenames = DirAccess.get_files_at(root.path_join(folder))
	filenames.sort()
	for filename in filenames:
		if not filename.ends_with(".json"):
			continue
		var extra := _read_dictionary(folder.path_join(filename))
		var embedded: Variant = extra.get("events")
		var values: Array = embedded if embedded is Array else [extra]
		for event in values:
			if event is Dictionary and event.get("id"):
				world["events"].append(event)
	last_error = ""
	return world


func load_species(species_id: String) -> Dictionary:
	if not valid_id(species_id):
		last_error = "Invalid species id: " + species_id
		return {}
	return _read_dictionary("data/species/" + species_id + "/species.json")
