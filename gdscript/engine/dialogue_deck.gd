# {
#   責務: [dialogue_deck: Pure per-actor dialogue cards. Inject shuffle; never save or render this state.]
#   フィールド: []
# }
extends RefCounted
## Pure per-actor dialogue cards. Inject shuffle; never save or render this state.


# {
#   責務: [create: 会話・deckを作成する]
#   処理: [1: 会話・deckを作成する]
#   引数: [source: 元データ（Dictionary）]
#   戻り値: [result: 会話・deckを作成するための結果（Dictionary）]
# }
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


# {
#   責務: [next_line: lineを次の値を求める]
#   処理: [1: lineを次の値を求める]
#   引数: [
#     state: 状態（Dictionary）
#     rng: 乱数供給元（RefCounted）
#   ]
#   戻り値: [result: lineを次の値を求めるための結果（Dictionary）]
# }
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


# {
#   責務: [_failure: 会話・deckのfailureを求める]
#   処理: [1: 会話・deckのfailureを求める]
#   引数: [
#     reason: 理由（String）
#     message: message（String）
#   ]
#   戻り値: [result: 会話・deckのfailureを求めるための結果（Dictionary）]
# }
static func _failure(reason: String, message: String) -> Dictionary:
	return {"ok": false, "error": reason, "message": message}


# {
#   責務: [_trim: 会話・deckのtrimを求める]
#   処理: [1: 会話・deckのtrimを求める]
#   引数: [value: 値（String）]
#   戻り値: [result: 会話・deckのtrimを求めるための結果（String）]
# }
static func _trim(value: String) -> String:
	# Match Python str.strip(), including full-width/Unicode whitespace in MODs.
	var first := 0
	var last := value.length()
	while first < last and _space(value.unicode_at(first)):
		first += 1
	while last > first and _space(value.unicode_at(last - 1)):
		last -= 1
	return value.substr(first, last - first)


# {
#   責務: [_space: 会話・deckのspaceを求める]
#   処理: [1: 会話・deckのspaceを求める]
#   引数: [point: 地点（int）]
#   戻り値: [result: 会話・deckのspaceを求めるための結果（bool）]
# }
static func _space(point: int) -> bool:
	return (9 <= point and point <= 13) or (28 <= point and point <= 32) \
		or (8192 <= point and point <= 8202) or point in [133, 160, 5760, 8232, 8233, 8239, 8287, 12288]
