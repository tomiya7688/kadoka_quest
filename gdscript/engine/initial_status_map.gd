# {
#   責務: [initial_status_map: 数値参加者と明示初期状態を照合し、各状態配列を検証/独立コピーします。実状態は保持しません]
#   フィールド: []
# }
extends RefCounted
const Order = preload("res://engine/turn_order.gd")
const Effects = preload("res://engine/status_effect_contract.gd")


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


# {
#   責務: [prepare: 全参加者に一致する初期状態を検証し、治療/付与の準備へ同じ独立一覧を返します]
#   処理: [
#     1: 数値参加者と明示状態のside/id集合の一致を確認します
#     2: 各状態配列の型/JSON互換性を共用検査し、順序と拡張情報を保って複製します
#   ]
#   引数: [
#     snapshots: 検証済み両陣営の数値snapshot列（Variant）
#     initial_statuses: 全参加者の状態配列を明示したside/id辞書（Variant）
#   ]
#   戻り値: [result: 独立initial_statuses、またはreasonと必要なside/idを持つ拒否（Dictionary）]
# }
static func prepare(snapshots: Variant, initial_statuses: Variant) -> Dictionary:
	# 治療候補や付与確率を計算せず、初期一覧をそのまま保持できるかだけを確認します。
	var matched := validate(snapshots, initial_statuses)
	if not matched["ok"]:
		return matched
	var result := {"allies": {}, "enemies": {}}
	for side in Order.SIDES:
		# 複数の不正一覧があっても、治療準備と同じ参加者順で最初の拒否対象を返します。
		for member: Dictionary in snapshots[side]:
			var id: String = member["identity"]["id"]
			var effects: Variant = initial_statuses[side][id]
			if not Effects.valid_effects(effects):
				return {"ok": false, "reason": "invalid_status_effects", "side": side, "id": id}
			result[side][id] = effects.duplicate(true)
	return {"ok": true, "initial_statuses": result}
