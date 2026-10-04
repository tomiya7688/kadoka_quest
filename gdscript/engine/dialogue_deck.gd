extends RefCounted
## Pure per-actor dialogue cards. Inject shuffle; never save or render this state.


static func create(source: Dictionary) -> Dictionary:
	if not source.has("dialogue"):
		return _failure("missing_deck", "会話デッキが設定されていません。")
	var definition: Variant = source["dialogue"]
	if not definition is Array:
		return _failure("invalid_deck", "会話デッキは文字列の配列で指定してください。")
	var cards: Array = []
	for value: Variant in definition:
		if not value is String:
			return _failure("invalid_card", "会話デッキに文字列以外の台詞があります。")
		var line := _trim(value)
		if not line.is_empty():
			cards.append(line)
	if cards.is_empty():
		return _failure("empty_deck", "会話デッキに空でない台詞がありません。")
	return {"ok": true, "cards": cards, "remaining": [], "last": null}


static func next_line(state: Dictionary, rng: RefCounted) -> Dictionary:
	if not state["ok"]:
		return state.duplicate(true)
	var remaining: Array = state["remaining"]
	if remaining.is_empty():
		remaining.append_array(state["cards"])
		rng.shuffle(remaining)
		if remaining.size() > 1 and remaining[-1] == state["last"]:
			var saved: Variant = remaining[0]
			remaining[0] = remaining[-1]
			remaining[-1] = saved
	var line: String = remaining.pop_back()
	state["last"] = line
	return {"ok": true, "line": line}


static func _failure(reason: String, message: String) -> Dictionary:
	return {"ok": false, "error": reason, "message": message}


static func _trim(value: String) -> String:
	# Match Python str.strip(), including full-width/Unicode whitespace in MODs.
	var first := 0
	var last := value.length()
	while first < last and _space(value.unicode_at(first)):
		first += 1
	while last > first and _space(value.unicode_at(last - 1)):
		last -= 1
	return value.substr(first, last - first)


static func _space(point: int) -> bool:
	return (9 <= point and point <= 13) or (28 <= point and point <= 32) \
		or (8192 <= point and point <= 8202) or point in [133, 160, 5760, 8232, 8233, 8239, 8287, 12288]
