# {
#   責務: [turn_order: Pure base-speed ordering and latest-resource eligibility. No turns executed here.]
#   フィールド: []
# }
extends RefCounted
## Pure base-speed ordering and latest-resource eligibility. No turns executed here.

const Eligibility = preload("res://engine/actor_eligibility_projection.gd")
const State = preload("res://engine/combatant_state.gd")
const Records = preload("res://engine/monster_record_contract.gd")
const SIDES := ["allies", "enemies"]
const SNAPSHOT_KEYS := ["identity", "stats", "hp", "mp", "fled", "alive"]
const IDENTITY_KEYS := ["id", "species_id", "name"]
const ACTIVE_TEAM_LIMIT := 4


# {
#   責務: [participants: 両陣営の厳密数値参加者を検証し、生存者のside/id列を返します]
#   処理: [1: 各陣営最大四体と六キー資源を共用検証し、生存者の識別キーを作ります]
#   引数: [
#     allies: 味方の六キー数値snapshot列（Variant）
#     enemies: 敵の六キー数値snapshot列（Variant）
#   ]
#   戻り値: [result: ok=trueと生存者members、または最初の形式/資源拒否（Dictionary）]
# }
static func participants(allies: Variant, enemies: Variant) -> Dictionary:
	var prepared := _prepare(allies, enemies)
	if not prepared["ok"]:
		return prepared
	return {"ok": true, "members": _keys(prepared)}


# {
#   責務: [valid_key: side/idだけを持つ参加者キーの形式を確認します]
#   処理: [1: allies/enemiesのsideと空でない文字列idを厳密に検証します]
#   引数: [key: 存在検索前に形式を確認する候補キー（Variant）]
#   戻り値: [valid: 形式が正しければtrue。参加者の存在や生存は保証しません（bool）]
# }
static func valid_key(key: Variant) -> bool:
	return _valid_key(key)


# {
#   責務: [plan: 生存参加者の明示順を検証し、基本速度で安定した行動順を固定します]
#   処理: [1: 生存者だけの一意なshuffle_orderを確認し、同速では指定順を保ちます]
#   引数: [
#     allies: 最新の味方数値snapshot列（Variant）
#     enemies: 最新の敵数値snapshot列（Variant）
#     shuffle_order: 生存者全員のside/idを一度ずつ持つ明示順（Variant）
#   ]
#   戻り値: [result: 生存者initialと速度順orderの独立キー列、または不正順序の拒否（Dictionary）]
# }
static func plan(allies: Variant, enemies: Variant, shuffle_order: Variant) -> Dictionary:
	var prepared := _prepare(allies, enemies)
	if not prepared["ok"]:
		return prepared
	var initial := _keys(prepared)
	if not shuffle_order is Array or shuffle_order.size() != initial.size():
		return {"ok": false, "reason": "invalid_shuffle_size"}
	var seen: Array = []
	var ordered: Array = []
	for index in shuffle_order.size():
		var key: Variant = shuffle_order[index]
		if not _valid_key(key) or key not in initial:
			return {"ok": false, "reason": "unknown_shuffle_actor", "index": index}
		if key in seen:
			return {"ok": false, "reason": "duplicate_shuffle_actor", "index": index}
		seen.append(key)
		var actor: Dictionary = prepared["teams"][key["side"]]["by_id"][key["id"]]
		# Python Combatant.speed floors unmodified speed to one. Stable insertion keeps ties.
		var speed := maxi(1, int(actor["stats"]["speed"]))
		var position := ordered.size()
		while position > 0 and ordered[position - 1]["speed"] < speed:
			position -= 1
		ordered.insert(position, {"key": key.duplicate(true), "speed": speed})
	var order: Array = []
	for entry: Dictionary in ordered:
		order.append(entry["key"])
	return {"ok": true, "initial": initial, "order": order, "scope": "base_turn_order"}


# {
#   責務: [check_actor: 最新資源から指定行動者の生存・逃走と生存敵の有無を確認します]
#   処理: [1: 参加者を検証し、指定行動者と同陣営/敵陣営の生存者を照合します]
#   引数: [
#     key: 行動者の厳密side/idキー（Variant）
#     allies: 最新の味方数値snapshot列（Variant）
#     enemies: 最新の敵数値snapshot列（Variant）
#   ]
#   戻り値: [result: can_act/stop/reasonと独立した生存者情報、または不正参加者の拒否（Dictionary）]
# }
static func check_actor(key: Variant, allies: Variant, enemies: Variant) -> Dictionary:
	if not _valid_key(key):
		return {"ok": false, "reason": "invalid_actor_key"}
	var prepared := _prepare(allies, enemies)
	if not prepared["ok"]:
		return prepared
	var friends: Dictionary = prepared["teams"][key["side"]]
	if not friends["by_id"].has(key["id"]):
		return {"ok": false, "reason": "actor_missing"}
	var other: String = "enemies" if key["side"] == "allies" else "allies"
	var foes: Array = prepared["teams"][other]["living"]
	var actor: Dictionary = friends["by_id"][key["id"]]
	# 生の参加者形式の厳密検査は維持し、検証後の行動可否の組立だけをSessionと共用します。
	return Eligibility.project(key, actor["alive"], friends["living"], foes)


# {
#   責務: [_prepare: 両陣営の参加上限と厳密な数値snapshotを検証し、生存者とID索引を独立構築します]
#   処理: [1: 最大四体/陣営と六キー資源を共用検証し、形式不正は部分結果なしで拒否します]
#   引数: [
#     allies: 味方の数値snapshot列（Variant）
#     enemies: 敵の数値snapshot列（Variant）
#   ]
#   戻り値: [result: 陣営別living/by_id、または不正陣営/参加者の拒否理由（Dictionary）]
# }
static func _prepare(allies: Variant, enemies: Variant) -> Dictionary:
	var teams: Dictionary = {}
	for side in SIDES:
		var members: Variant = allies if side == "allies" else enemies
		if not members is Array:
			return {"ok": false, "reason": "invalid_team", "side": side}
		if members.size() > ACTIVE_TEAM_LIMIT:
			return {"ok": false, "reason": "active_team_limit", "side": side, "limit": ACTIVE_TEAM_LIMIT}
		var living := State.living(members)
		if not living["ok"]:
			return {"ok": false, "reason": "invalid_team", "side": side, "detail": living}
		var by_id: Dictionary = {}
		for index in members.size():
			var member: Dictionary = members[index]
			if not _exact_keys(member, SNAPSHOT_KEYS) or not _exact_keys(member["identity"], IDENTITY_KEYS) \
				or not _exact_keys(member["stats"], State.STAT_KEYS):
				return {"ok": false, "reason": "unsupported_combatant_fields", "side": side, "index": index}
			by_id[member["identity"]["id"]] = member.duplicate(true)
		teams[side] = {"living": living["members"], "by_id": by_id}
	return {"ok": true, "teams": teams}


# {
#   責務: [_keys: 検証済み両陣営から生存参加者だけの独立識別キー列を作ります]
#   処理: [1: allies/enemies順にlivingのIDをside/id辞書へ取り出します]
#   引数: [prepared: _prepareが検証したteams/living/by_idを持つ内部結果（Dictionary）]
#   戻り値: [result: 生存参加者のside/id列。死亡/逃走者は含みません（Array）]
# }
static func _keys(prepared: Dictionary) -> Array:
	var keys: Array = []
	for side in SIDES:
		for member: Dictionary in prepared["teams"][side]["living"]:
			keys.append({"side": side, "id": member["identity"]["id"]})
	return keys


# {
#   責務: [_valid_key: 参加者指定がside/idだけを持ち、許可陣営と安全な文字列IDであるか確認します]
#   処理: [1: 厳密二キー辞書とallies/enemies・Records.safe_idに適合するIDを確認します]
#   引数: [key: 参加者の存在検索前に形式を調べる候補（Variant）]
#   戻り値: [valid: 形式が正しければtrue。存在/生存は検査しません（bool）]
# }
static func _valid_key(key: Variant) -> bool:
	return key is Dictionary and _exact_keys(key, ["side", "id"]) \
		and key.get("side") is String and key["side"] in SIDES \
		and key.get("id") is String and Records.safe_id(key["id"])


# {
#   責務: [_exact_keys: 入力辞書のキー集合が指定したキー一覧と一致するか確認します]
#   処理: [1: 辞書のキー数と所属を照合し、欠落/未知キーを拒否します]
#   引数: [
#     value: キー集合を確認する入力辞書（Dictionary）
#     expected: 許可する全キーの一覧（Array）
#   ]
#   戻り値: [matches: キーの欠落/未知がなければtrue（bool）]
# }
static func _exact_keys(value: Dictionary, expected: Array) -> bool:
	if value.size() != expected.size():
		return false
	for key in value:
		if key not in expected:
			return false
	return true
