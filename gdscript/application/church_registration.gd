# {
#   責務: [church_registration: Register only a checkpoint using validated content and guarded existing state I/O.]
#   フィールド: [persistence: persistence（RefCounted）]
# }
extends RefCounted
## Register only a checkpoint using validated content and guarded existing state I/O.
const Contract = preload("res://engine/revive_point_contract.gd")
var persistence: RefCounted


# {
#   責務: [_init: 教会・registrationが利用する初期状態と依存を設定する]
#   処理: [1: 教会・registrationが利用する初期状態と依存を設定する]
#   引数: [field_persistence: フィールド・persistence（RefCounted）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _init(field_persistence: RefCounted) -> void:
	persistence = field_persistence


# {
#   責務: [register: 教会・registrationを登録する]
#   処理: [1: 教会・registrationを登録する]
#   引数: [revive: 復活（Variant）]
#   戻り値: [result: 教会・registrationを登録するための結果（Dictionary）]
# }
func register(revive: Variant) -> Dictionary:
	return commit(begin(revive))


# {
#   責務: [begin: 教会・registrationを開始する]
#   処理: [1: 教会・registrationを開始する]
#   引数: [revive: 復活（Variant）]
#   戻り値: [result: 教会・registrationを開始するための結果（Dictionary）]
# }
func begin(revive: Variant) -> Dictionary:
	var valid := Contract.validate_point(revive)
	if not valid["ok"]:
		return valid
	var loaded: Dictionary = persistence.load_position()
	if not loaded["ok"]:
		if loaded.get("error") == "not_found":
			loaded["message"] = "セーブがありません。先にF5で保存してから教会を調べてください。"
		return loaded
	loaded["point"] = valid["point"]
	return loaded


# {
#   責務: [commit: 教会・registrationのcommitを求める]
#   処理: [1: 教会・registrationのcommitを求める]
#   引数: [request: 要求（Dictionary）]
#   戻り値: [result: 教会・registrationのcommitを求めるための結果（Dictionary）]
# }
func commit(request: Dictionary) -> Dictionary:
	if not request.get("ok", false):
		return _failure(request, false)
	var current: Dictionary = persistence.load_position()
	if not current["ok"]:
		return _failure(current, false)
	if current["digest"] != request["digest"]:
		return _failure({"error": "changed", "message": "セーブが外部で変更されました。教会を調べ直してください。"}, false)
	var point: Dictionary = request["point"]
	var world: Dictionary = persistence.repository.load_map(point["map_id"])
	if world.is_empty():
		return _failure({"error": "invalid_map", "message": persistence.repository.last_error}, false)
	var valid := Contract.validate_location(point, world, persistence.blocks)
	if not valid["ok"]:
		return _failure(valid, false)
	var plan := Contract.plan(current["value"], point)
	if plan["changed"]:
		var written: Dictionary = persistence.store.save_profile(persistence.profile_name, plan["state"], request["digest"], {})
		if not written["ok"]:
			return _failure(written, false)
	var final: Dictionary = persistence.load_position()
	if not final["ok"]:
		return _failure(final, plan["changed"])
	if final["value"] != plan["state"]:
		return _failure({"error": "changed", "message": "保存後のstateが期待した内容と一致しません。読み込み直してください。"}, plan["changed"])
	return {"ok": true, "saved": plan["changed"], "point": point.duplicate(true),
		"message": ("復活地点を登録しました: " if plan["changed"] else "登録済みの復活地点です: ") + point["name"]
			+ " [未移植: HP回復・敗北復活]"}


# {
#   責務: [_failure: 教会・registrationのfailureを求める]
#   処理: [1: 教会・registrationのfailureを求める]
#   引数: [
#     reason: 理由（Dictionary）
#     saved: saved（bool）
#   ]
#   戻り値: [result: 教会・registrationのfailureを求めるための結果（Dictionary）]
# }
static func _failure(reason: Dictionary, saved: bool) -> Dictionary:
	return {"ok": false, "saved": saved, "error": reason.get("error", "registration_failed"),
		"message": "復活地点の登録失敗: " + str(reason.get("message", "理由不明"))
			+ (" 書込後の確認に失敗しました。以前の保存へ巻き戻していません。" if saved else "")}
