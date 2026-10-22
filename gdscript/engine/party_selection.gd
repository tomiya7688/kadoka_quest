# {
#   責務: [party_selection: Four-slot draft and selection rules. No files, UI or individual mutation.]
#   フィールド: [
#     members: 個体一覧（Array）
#     original: original（Array）
#   ]
# }
extends RefCounted
## Four-slot draft and selection rules. No files, UI or individual mutation.

var members: Array = []
var original: Array = []


# {
#   責務: [start: パーティ・選択状態を開始する]
#   処理: [1: パーティ・選択状態を開始する]
#   引数: [value: 値（Variant）]
#   戻り値: [result: パーティ・選択状態を開始するための結果（Dictionary）]
# }
func start(value: Variant) -> Dictionary:
	if not value is Array or value.size() > 4:
		return {"ok": false, "message": "current_partyは最大4枠の配列にしてください。自動切捨てはしません。"}
	for id in value:
		if id != null and (not id is String or id.is_empty()):
			return {"ok": false, "message": "パーティ枠には個体IDまたはnullを指定してください。"}
	members = value.duplicate(true)
	while members.size() < 4:
		members.append(null)
	original = members.duplicate(true)
	return {"ok": true}


# {
#   責務: [assign: パーティ・選択状態のassignを求める]
#   処理: [1: パーティ・選択状態のassignを求める]
#   引数: [
#     slot: 編成枠（int）
#     id: 識別子（Variant）
#     records: 個体レコード一覧（Dictionary）
#   ]
#   戻り値: [result: パーティ・選択状態のassignを求めるための結果（Dictionary）]
# }
func assign(slot: int, id: Variant, records: Dictionary) -> Dictionary:
	if slot < 0 or slot >= members.size():
		return {"ok": false, "message": "編集するパーティ枠を選択してください。"}
	if id != null:
		if not id is String or not records.has(id):
			return {"ok": false, "message": "読込可能な保有個体を選択してください。"}
		var previous := members.find(id)
		if previous != -1 and previous != slot:
			return {"ok": false, "message": "同じ個体は複数枠へ入れられません。先に元の枠から外してください。"}
	members[slot] = id
	return {"ok": true}


# {
#   責務: [validate: パーティ・選択状態を妥当性を検査する]
#   処理: [1: パーティ・選択状態を妥当性を検査する]
#   引数: [records: 個体レコード一覧（Dictionary）]
#   戻り値: [result: パーティ・選択状態を妥当性を検査するための結果（Dictionary）]
# }
func validate(records: Dictionary) -> Dictionary:
	var seen: Dictionary = {}
	for id in members:
		if id == null:
			continue
		if not records.has(id):
			return {"ok": false, "message": "読込できない個体を枠から外してください: " + str(id)}
		if seen.has(id):
			return {"ok": false, "message": "重複した個体を枠から外してください: " + str(id)}
		seen[id] = true
	return {"ok": true}


# {
#   責務: [is_dirty: dirtyを該当するか判定する]
#   処理: [1: dirtyを該当するか判定する]
#   引数: []
#   戻り値: [result: dirtyを該当するか判定するための結果（bool）]
# }
func is_dirty() -> bool:
	return members != original


# {
#   責務: [replace_members: パーティ・選択状態のreplace・個体一覧を求める]
#   処理: [1: パーティ・選択状態のreplace・個体一覧を求める]
#   引数: [
#     value: 値（Array）
#     records: 個体レコード一覧（Dictionary）
#   ]
#   戻り値: [result: パーティ・選択状態のreplace・個体一覧を求めるための結果（Dictionary）]
# }
func replace_members(value: Array, records: Dictionary) -> Dictionary:
	var candidate = get_script().new()
	var valid: Dictionary = candidate.start(value)
	if not valid["ok"]:
		return valid
	valid = candidate.validate(records)
	if valid["ok"]:
		members = candidate.members.duplicate(true)
	return valid
