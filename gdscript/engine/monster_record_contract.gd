extends RefCounted
## Plain individual/default-AI documents. No persistence, rendering or battle inference.


static func safe_id(value: String) -> bool:
	if value.is_empty() or value != value.strip_edges() or value in [".", ".."] or value.ends_with("."):
		return false
	for index in value.length():
		if value.unicode_at(index) < 32 or value[index] in "\\/:*?\"<>|":
			return false
	var device := value.get_slice(".", 0).to_upper()
	return device not in ["CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6",
		"COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"]


static func default_ai(profile: String = "normal", tactic: String = "balanced") -> Dictionary:
	var biases := {
		"normal": {}, "support": {"heal": 0.2, "buff": 0.15},
		"trickster": {"drain_mp": 0.2, "evade": 0.15}, "dice": {"random": 0.25},
		"maru": {"field": 0.4, "random": 0.3}, "kadoka": {"field": 0.25, "defend": 0.1},
	}
	return {
		"schema_version": 1, "profile": profile,
		"tactic": tactic if tactic in ["balanced", "aggressive", "careful", "variety"] else "balanced",
		"weights": {"damage": 0.5, "survival": 0.5, "support": 0.5, "mp_care": 0.5},
		"kind_preferences": biases.get(profile, {}).duplicate(true),
		"action_preferences": {}, "context_preferences": {}, "context_actions": {}, "battles": 0, "actions": 0,
	}


static func create_record(id: String, species: Dictionary, name: String = "", level: int = 1, source: String = "starter") -> Dictionary:
	return {
		"monster": {
			"schema_version": 1, "id": id, "species_id": species["id"],
			"name": name if not name.is_empty() else species["display_name"],
			"level": clampi(level, 1, 100), "experience": 0, "plus_choices": [],
			"equipment_id": null, "source": source,
		},
		"ai": default_ai(str(species.get("ai_profile", "normal"))),
	}


static func validate_record(monster: Dictionary, ai: Dictionary, folder_id: String) -> Dictionary:
	if not _version(monster.get("schema_version", 1)) or not _version(ai.get("schema_version", 1)):
		return {"ok": false, "message": "未対応の個体/AI形式"}
	if not monster.get("id") is String or not safe_id(monster["id"]) or monster["id"] != folder_id:
		return {"ok": false, "message": "個体IDとフォルダ名が一致しません"}
	if not monster.get("species_id") is String or not monster.get("name") is String or monster["name"].is_empty():
		return {"ok": false, "message": "種族ID/個体名が不正です"}
	var level: Variant = monster.get("level", 1)
	if not _integer(level) or float(level) < 1 or float(level) > 100:
		return {"ok": false, "message": "レベルは1〜100の整数です"}
	var choices: Variant = monster.get("plus_choices", [])
	if not choices is Array:
		return {"ok": false, "message": "＋選択は配列です"}
	for choice in choices:
		if not choice is String:
			return {"ok": false, "message": "＋選択IDは文字列です"}
	return {"ok": true}


static func _integer(value: Variant) -> bool:
	return (value is int or value is float) and is_finite(float(value)) and float(value) == floorf(float(value))


static func _version(value: Variant) -> bool:
	return _integer(value) and float(value) == 1


static func party_entries(state: Dictionary, records: Dictionary) -> Array:
	var entries: Array = []
	var ids: Variant = state.get("current_party", [])
	if not ids is Array:
		return entries
	for id in ids.slice(0, 4):
		entries.append({"id": id, "record": records.get(id) if id is String else null})
	return entries
