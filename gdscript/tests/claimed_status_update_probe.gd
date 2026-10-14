# {
#   責務: [claimed_status_update_probe: 検証用の状態更新要求をSessionへ渡し、不正なnative値はコピーだけへ注入します]
#   フィールド: []
# }
extends RefCounted


# {
#   責務: [invoke: 現在または指定予約と対象/要求をSessionの治療/付与入口へ渡します]
#   処理: [1: 非有限/Object/循環/非文字列キーを任意コピーへ注入し、呼出後に専用循環を解きます]
#   引数: [
#     session: ケース専用のSession（RefCounted）
#     ticket: 現在または明示指定の行動票（Variant）
#     step: operation/actor/requestと任意specialの注入先/項目/値（Dictionary）
#   ]
#   戻り値: [result: Sessionの実治療/付与結果。入力や実セーブは変更しません（Dictionary）]
# }
static func invoke(session: RefCounted, ticket: Variant, step: Dictionary) -> Dictionary:
	# 製品入力の範囲外の値は専用コピーだけへ作り、要求JSON自体は保持します。
	var target: Variant = step.get("actor")
	var request: Variant = step.get("request")
	var cycle: Dictionary = {}
	if step.has("special"):
		ticket = ticket.duplicate(true) if ticket is Dictionary else ticket
		target = target.duplicate(true) if target is Dictionary else target
		request = request.duplicate(true) if request is Dictionary else request
		var special: Dictionary = step["special"]
		var value: Variant = NAN
		match special["value"]:
			"inf": value = INF
			"object": value = RefCounted.new()
			"non_string_key": value = {1: "invalid"}
			"cycle":
				cycle["self"] = cycle
				value = cycle
		match special.get("target", "request"):
			"ticket": ticket[special["field"]] = value
			"actor": target[special["field"]] = value
			"effect": request["effect"][special["field"]] = value
			_: request[special["field"]] = value
	# 同期APIの結果だけを返し、専用の循環参照は呼出後に解いて保持を残しません。
	var result: Dictionary = session.apply_status_cure(ticket, target, request) if step["operation"] == "apply_cure" else session.apply_status_application(ticket, target, request)
	cycle.clear()
	return result
