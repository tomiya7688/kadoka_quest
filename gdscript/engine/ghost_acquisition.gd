# {
#   責務: [ghost_acquisition: Pure missing-species/flag plan. Never edits existing individuals, party or position.]
#   フィールド: []
# }
extends RefCounted
## Pure missing-species/flag plan. Never edits existing individuals, party or position.
const SPECIES := ["maru", "kadoka"]


# {
#   責務: [plan: おばけ・acquisitionを計画する]
#   処理: [1: おばけ・acquisitionを計画する]
#   引数: [
#     state: 状態（Dictionary）
#     records: 個体レコード一覧（Dictionary）
#   ]
#   戻り値: [result: おばけ・acquisitionを計画するための結果（Dictionary）]
# }
static func plan(state: Dictionary, records: Dictionary) -> Dictionary:
	if not state.get("flags", {}) is Dictionary:
		return {"ok": false, "error": "invalid_flags", "message": "flagsが辞書ではありません。修復後に入力し直してください。"}
	var updated := state.duplicate(true)
	updated["flags"] = updated.get("flags", {}).duplicate(true)
	updated["flags"]["ghost_entrance_open"] = true
	return {"ok": true, "state": updated, "missing": missing_species(records)}


# {
#   責務: [missing_species: おばけ・acquisitionのmissing・種族を求める]
#   処理: [1: おばけ・acquisitionのmissing・種族を求める]
#   引数: [records: 個体レコード一覧（Dictionary）]
#   戻り値: [result: おばけ・acquisitionのmissing・種族を求めるための結果（Array）]
# }
static func missing_species(records: Dictionary) -> Array:
	var owned: Dictionary = {}
	for record: Dictionary in records.values():
		owned[record["monster"]["species_id"]] = true
	var missing: Array = []
	for species: String in SPECIES:
		if not owned.has(species):
			missing.append(species)
	return missing


# {
#   責務: [validate_species: 種族を妥当性を検査する]
#   処理: [1: 種族を妥当性を検査する]
#   引数: [
#     species: 種族（Dictionary）
#     id: 識別子（String）
#   ]
#   戻り値: [result: 種族を妥当性を検査するための結果（Dictionary）]
# }
static func validate_species(species: Dictionary, id: String) -> Dictionary:
	var version: Variant = species.get("schema_version", 1)
	if not (version is int or version is float) or float(version) != 1 or species.get("id") != id \
		or not species.get("display_name") is String or str(species["display_name"]).is_empty() \
		or not species.get("ai_profile", "normal") is String:
		return {"ok": false, "error": "invalid_species", "message": "取得種族の定義が不正です: " + id}
	return {"ok": true}
