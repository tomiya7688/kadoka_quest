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
#   責務: [_initialize: 専用JSONの行動順/生存検査と正規個体の読取専用準備を実行し、観測結果を出力します]
#   処理: [1: ケースごとの入力保持/返却値独立性を観測し、Base64のJSONとして標準出力へ返します]
#   引数: []
#   戻り値: [result: なし（void）。引数不足は終了コード2、正常観測は終了コード0です]
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
#   責務: [_execute: 参加者列挙・基礎順序計画・最新生存検査の指定操作を純粋契約へ委譲します]
#   処理: [1: operationに対応するOrderの公開関数を呼び、未対応操作は理由付きで拒否します]
#   引数: [
#     operation: participants/plan/checkのいずれかの専用操作名（String）
#     request: 対応する両陣営数値snapshotと任意の明示順/行動者キー（Dictionary）
#   ]
#   戻り値: [result: 純粋契約の観測値、またはunknown_probe_operationの拒否（Dictionary）]
# }
func _execute(operation: String, request: Dictionary) -> Dictionary:
	match operation:
		"participants": return Order.participants(request.get("allies"), request.get("enemies"))
		"plan": return Order.plan(request.get("allies"), request.get("enemies"), request.get("shuffle_order"))
		"check": return Order.check_actor(request.get("actor"), request.get("allies"), request.get("enemies"))
	return {"ok": false, "reason": "unknown_probe_operation"}


# {
#   責務: [_mutate: 正常な観測結果の識別キー/数値を編集し、再実行結果と原入力の参照独立性を検査可能にします]
#   処理: [1: 存在するキー列・生存者一覧・行動者の返却値だけを専用の変更値へ置き換えます]
#   引数: [value: 独立性を検査する純粋契約の結果辞書（Dictionary）]
#   戻り値: [result: なし（void）。valueだけを変更し、失敗結果は保持します]
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
