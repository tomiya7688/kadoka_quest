# {
#   責務: [initial_status_map: 数値参加者と明示初期状態の陣営/個体IDを照合します。状態の内容検証や保持は行いません]
#   フィールド: []
# }
extends RefCounted
const Order = preload("res://engine/turn_order.gd")


# {
#   責務: [validate: 全参加者と初期状態のID集合が一致するか確認し、欠落/余分な個体を拒否します]
#   処理: [1: 数値参加者を順序契約で検証し、各陣営の状態辞書と全IDの厳密一致を確認します]
#   引数: [
#     snapshots: allies/enemiesだけを持つ六キー数値snapshot列の辞書（Variant）
#     initial_statuses: allies/enemiesだけを持ち、参加者IDをキーに初期状態を指定する辞書（Variant）
#   ]
#   戻り値: [result: 一致ならok=true、不正ならreasonと必要なside/id。状態内容を検証済みとはしません（Dictionary）]
# }
static func validate(snapshots: Variant, initial_statuses: Variant) -> Dictionary:
	# IDを読む前に数値参加者を検証し、不正型でGodotの実行診断を起こさないようにします。
	if not snapshots is Dictionary or snapshots.size() != 2:
		return {"ok": false, "reason": "invalid_status_participants"}
	var participants := Order.participants(snapshots.get("allies"), snapshots.get("enemies"))
	if not participants["ok"]:
		return participants
	if not initial_statuses is Dictionary or initial_statuses.size() != 2:
		return {"ok": false, "reason": "invalid_initial_statuses"}
	for side in Order.SIDES:
		var entries: Variant = initial_statuses.get(side)
		if not entries is Dictionary:
			return {"ok": false, "reason": "invalid_initial_statuses", "side": side}
		if entries.size() != snapshots[side].size():
			return {"ok": false, "reason": "status_context_mismatch", "side": side}
		for member: Dictionary in snapshots[side]:
			var id: String = member["identity"]["id"]
			if not entries.has(id):
				return {"ok": false, "reason": "status_context_mismatch", "side": side, "id": id}
	return {"ok": true}
