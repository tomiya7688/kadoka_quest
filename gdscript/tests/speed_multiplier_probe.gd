# {
#   責務: [speed_multiplier_probe: 独立した八体の速度所有者へ専用操作列を渡し、拒否・非共有・入力保持を観測します]
#   フィールド: []
# }
extends RefCounted

const SpeedState = preload("res://engine/combatant_speed_state.gd")


# {
#   責務: [run: 専用ケースごとの速度強化操作と保持状態の観測を集めます]
#   処理: [1: ケース一覧を個別観測へ渡し、結果列を返します]
#   引数: [payload: casesに独立した操作ケース一覧を持つ専用辞書（Dictionary）]
#   戻り値: [result: ケースの観測を含むresults辞書（Dictionary）]
# }
static func run(payload: Dictionary) -> Dictionary:
	var results: Array = []
	for entry: Dictionary in payload.get("cases", []):
		results.append(_observe(entry))
	return {"results": results}


# {
#   責務: [_observe: 一ケースの八所有者を分離して操作し、他個体・返却値・元要求の非変更を確認します]
#   処理: [
#     1: 未開始の所有者を八体作り、指定個体の専用操作を順番に実行します
#     2: 返却snapshotを編集して所有状態の不変を確認し、拒否時と他個体の状態保持を記録します
#   ]
#   引数: [entry: operationsにmethod/任意owner/value/specialを持つ操作列を含む辞書（Dictionary）]
#   戻り値: [result: observations/input_preservedと全個体のfinal辞書（Dictionary）]
# }
static func _observe(entry: Dictionary) -> Dictionary:
	var original := JSON.stringify(entry)
	var owners: Array = []
	for _index in 8:
		owners.append(SpeedState.new())
	var observations: Array = []
	for operation: Dictionary in entry.get("operations", []):
		var index := int(operation.get("owner", 0))
		var before := _snapshots(owners)
		var result := _invoke(owners[index], operation)
		var after := _snapshots(owners)
		var saved := result.duplicate(true)
		# 呼出側が成功結果を編集しても、同じ所有者と他の七体へ変更が伝わらないことを確認します。
		if result.has("snapshot"):
			result["snapshot"]["speed_multiplier"] = -999
		var others_unchanged := true
		for other in 8:
			if other != index and before[other] != after[other]:
				others_unchanged = false
		observations.append({"result": saved, "snapshot": after[index],
			"result_independent": after == _snapshots(owners), "others_unchanged": others_unchanged,
			"rejection_preserved": saved.get("ok", true) or before == after})
	return {"observations": observations, "final": _snapshots(owners), "input_preserved": original == JSON.stringify(entry)}


# {
#   責務: [_invoke: JSONの専用操作を所有者APIへ渡し、非JSON値は検査用コピーだけへ注入します]
#   処理: [1: 任意のnative値を用意し、指定された開始・付与・経過・読取を一回だけ呼びます]
#   引数: [
#     owner: 操作対象一体の速度所有者（RefCounted）
#     operation: method/valueと任意specialを持つ専用操作辞書（Dictionary）
#   ]
#   戻り値: [result: 所有者APIの結果。未知テスト操作は理由付き拒否です（Dictionary）]
# }
static func _invoke(owner: RefCounted, operation: Dictionary) -> Dictionary:
	var value: Variant = operation.get("value")
	if value is Dictionary:
		value = value.duplicate(true)
	if operation.has("special"):
		var native: Variant = NAN
		match operation["special"]:
			"inf": native = INF
			"negative_inf": native = -INF
			"object": native = RefCounted.new()
			"vector": native = Vector2.ONE
		if value is Dictionary:
			value[operation.get("field", "multiplier")] = native
		else:
			value = native
	match operation["method"]:
		"start": return owner.start(value) if operation.has("value") or operation.has("special") else owner.start()
		"apply": return owner.apply_multiplier(value)
		"elapse": return owner.elapse_round()
		"snapshot": return {"ok": true, "snapshot": owner.snapshot()}
	return {"ok": false, "reason": "invalid_probe_operation"}


# {
#   責務: [_snapshots: 八体それぞれの速度強化を独立した読取結果へ投影します]
#   処理: [1: 各所有者のsnapshotだけを順番に収集します]
#   引数: [owners: 専用ケースの八速度所有者（Array）]
#   戻り値: [result: 各所有者の三キー辞書または未開始の空辞書の列（Array）]
# }
static func _snapshots(owners: Array) -> Array:
	var snapshots: Array = []
	for owner in owners:
		snapshots.append(owner.snapshot())
	return snapshots
