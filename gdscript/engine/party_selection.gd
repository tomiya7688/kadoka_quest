extends RefCounted
## Four-slot draft and selection rules. No files, UI or individual mutation.

var members: Array = []
var original: Array = []


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


func is_dirty() -> bool:
	return members != original
