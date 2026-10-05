extends RefCounted
## Coordinate validated missing-only acquisition and a guarded flag save, never render.
const Policy = preload("res://engine/ghost_acquisition.gd")
const Records = preload("res://engine/monster_record_contract.gd")
const MonsterStore = preload("res://data/monster_store.gd")
const Reconstruction = preload("res://application/monster_reconstruction.gd")
var persistence: RefCounted


func _init(field_persistence: RefCounted) -> void:
	persistence = field_persistence


func begin() -> Dictionary:
	var loaded: Dictionary = persistence.load_position()
	if not loaded["ok"] and loaded.get("error") == "not_found":
		loaded["message"] = "セーブがありません。先にF5で保存してから、あいことばを入力し直してください。"
	return loaded


func acquire(request: Dictionary) -> Dictionary:
	var created: Array = []
	if not request.get("ok", false):
		return _failure(request, created, false, "begin")
	var current := _unchanged(request)
	if not current["ok"]:
		return _failure(current, created, false, "validate")
	var owned := _read_owned(current["value"])
	if not owned["ok"]:
		return _failure(owned, created, false, "validate")
	var plan := Policy.plan(current["value"], owned["records"])
	if not plan["ok"]:
		return _failure(plan, created, false, "validate")
	var prepared := _prepare_records(plan["missing"])
	if not prepared["ok"]:
		return _failure(prepared, created, false, "definitions")
	var profile: Dictionary = persistence.store.resolve_profile(persistence.profile_name)
	if not profile["ok"]:
		return _failure(profile, created, false, "validate")
	var store := _monster_store(profile["path"])
	for record: Dictionary in prepared["records"]:
		current = _unchanged(request)
		if not current["ok"]:
			return _failure(current, created, false, "create")
		owned = _read_owned(current["value"])
		if not owned["ok"]:
			return _failure(owned, created, false, "create")
		if record["monster"]["species_id"] not in Policy.missing_species(owned["records"]):
			continue  # A newly imported individual also counts; never rewrite its AI.
		var result: Dictionary = store.create_new(record)
		if not result["ok"]:
			return _failure(result, created, false, "create")
		created.append({"id": result["id"], "name": record["monster"]["name"], "species_id": record["monster"]["species_id"]})
	return _commit_flag(request, plan["state"], created)


func _prepare_records(missing: Array) -> Dictionary:
	var records: Array = []
	var reconstruction = Reconstruction.new(persistence.repository)
	for id: String in missing:
		var species: Dictionary = persistence.repository.load_species(id)
		var valid := Policy.validate_species(species, id)
		if not valid["ok"]:
			return valid
		var record := Records.create_record("monster_" + Crypto.new().generate_random_bytes(6).hex_encode(), species,
			"", 1, "ghost_home_password")
		var rebuilt: Dictionary = reconstruction.rebuild(record["monster"])
		if not rebuilt["ok"]:
			return rebuilt
		if not rebuilt["modifiers"]["ok"]:
			return rebuilt["modifiers"]
		records.append(record)
	return {"ok": true, "records": records}


func _commit_flag(request: Dictionary, state: Dictionary, created: Array) -> Dictionary:
	var current := _unchanged(request)
	if not current["ok"]:
		return _failure(current, created, false, "save")
	var verified := _verify_owned(current["value"])
	if not verified["ok"]:
		return _failure(verified, created, false, "save")
	var saved := false
	if state != request["value"]:
		var written: Dictionary = persistence.store.save_profile(persistence.profile_name, state, request["digest"], {})
		if not written["ok"]:
			return _failure(written, created, false, "save")
		saved = true
	var final: Dictionary = persistence.load_position()
	if not final["ok"]:
		return _failure(final, created, saved, "verify")
	if final["value"] != state:
		return _failure({"error": "changed", "message": "保存後のstateが変化しています。読み込み直してください。"}, created, saved, "verify")
	verified = _verify_owned(final["value"])
	if not verified["ok"]:
		return _failure(verified, created, saved, "verify")
	var names: PackedStringArray = []
	for record: Dictionary in created:
		names.append(record["name"])
	return {"ok": true, "complete": true, "created": created, "flag_saved": saved, "partial": false,
		"message": "へいわなすみか。" + (" 牧場に " + "・".join(names) + " が増えました。" if not names.is_empty() else " 2匹とも既にいます。")}


func _unchanged(request: Dictionary) -> Dictionary:
	var current: Dictionary = persistence.load_position()
	if current["ok"] and current["digest"] != request["digest"]:
		return {"ok": false, "error": "changed", "message": "セーブが外部で変更されました。あいことばを入力し直してください。"}
	return current


func _read_owned(state: Dictionary) -> Dictionary:
	var result: Dictionary = persistence.roster.read_snapshot(state)
	if result["ok"] and not result["warnings"].is_empty():
		return {"ok": false, "error": "invalid_owned", "message": "既存個体/定義に問題があります: " + str(result["warnings"][0])}
	return result


func _verify_owned(state: Dictionary) -> Dictionary:
	var result := _read_owned(state)
	if result["ok"] and not Policy.missing_species(result["records"]).is_empty():
		return {"ok": false, "error": "incomplete", "message": "取得した2種族の所有を確認できません。"}
	return result


func _monster_store(path: String) -> RefCounted:
	return MonsterStore.new(path)


static func _failure(reason: Dictionary, created: Array, saved: bool, stage: String) -> Dictionary:
	var partial := not created.is_empty() or saved
	var message := "取得を完了できません: " + str(reason.get("message", "理由不明"))
	if partial:
		message += " 部分保存あり（追加個体%d体、フラグ保存%s）。削除せず保持しました。再入力で不足分だけ再試行します。" % [created.size(), str(saved)]
	return {"ok": false, "complete": false, "error": reason.get("error", "acquisition_failed"), "stage": stage,
		"created": created.duplicate(true), "flag_saved": saved, "partial": partial, "message": message}
