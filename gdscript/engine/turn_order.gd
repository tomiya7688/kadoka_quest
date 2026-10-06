# {
#   責務: [turn_order: Pure base-speed ordering and latest-resource eligibility. No turns executed here.]
#   フィールド: []
# }
extends RefCounted
## Pure base-speed ordering and latest-resource eligibility. No turns executed here.

const State = preload("res://engine/combatant_state.gd")
const Records = preload("res://engine/monster_record_contract.gd")
const SIDES := ["allies", "enemies"]
const SNAPSHOT_KEYS := ["identity", "stats", "hp", "mp", "fled", "alive"]
const IDENTITY_KEYS := ["id", "species_id", "name"]
const ACTIVE_TEAM_LIMIT := 4


# {
#   責務: [participants: ターン・順序のparticipantsを求める]
#   処理: [1: ターン・順序のparticipantsを求める]
#   引数: [
#     allies: 味方（Variant）
#     enemies: 敵（Variant）
#   ]
#   戻り値: [result: ターン・順序のparticipantsを求めるための結果（Dictionary）]
# }
static func participants(allies: Variant, enemies: Variant) -> Dictionary:
	var prepared := _prepare(allies, enemies)
	if not prepared["ok"]:
		return prepared
	return {"ok": true, "members": _keys(prepared)}


# {
#   責務: [valid_key: ターン・順序のvalid・キーを求める]
#   処理: [1: ターン・順序のvalid・キーを求める]
#   引数: [key: キー（Variant）]
#   戻り値: [result: ターン・順序のvalid・キーを求めるための結果（bool）]
# }
static func valid_key(key: Variant) -> bool:
	return _valid_key(key)


# {
#   責務: [plan: ターン・順序を計画する]
#   処理: [1: ターン・順序を計画する]
#   引数: [
#     allies: 味方（Variant）
#     enemies: 敵（Variant）
#     shuffle_order: 並べ替え・順序（Variant）
#   ]
#   戻り値: [result: ターン・順序を計画するための結果（Dictionary）]
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
#   責務: [check_actor: 行動個体を検査する]
#   処理: [1: 行動個体を検査する]
#   引数: [
#     key: キー（Variant）
#     allies: 味方（Variant）
#     enemies: 敵（Variant）
#   ]
#   戻り値: [result: 行動個体を検査するための結果（Dictionary）]
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
	var reason := "no_living_foes" if foes.is_empty() else ("ready" if actor["alive"] else "actor_not_alive")
	return {"ok": true, "can_act": reason == "ready", "stop": foes.is_empty(), "reason": reason,
		"actor": key.duplicate(true), "friends": friends["living"].duplicate(true), "foes": foes.duplicate(true)}


# {
#   責務: [_prepare: ターン・順序を準備する]
#   処理: [1: ターン・順序を準備する]
#   引数: [
#     allies: 味方（Variant）
#     enemies: 敵（Variant）
#   ]
#   戻り値: [result: ターン・順序を準備するための結果（Dictionary）]
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
#   責務: [_keys: ターン・順序のキー一覧を求める]
#   処理: [1: ターン・順序のキー一覧を求める]
#   引数: [prepared: prepared（Dictionary）]
#   戻り値: [result: ターン・順序のキー一覧を求めるための結果（Array）]
# }
static func _keys(prepared: Dictionary) -> Array:
	var keys: Array = []
	for side in SIDES:
		for member: Dictionary in prepared["teams"][side]["living"]:
			keys.append({"side": side, "id": member["identity"]["id"]})
	return keys


# {
#   責務: [_valid_key: ターン・順序のvalid・キーを求める]
#   処理: [1: ターン・順序のvalid・キーを求める]
#   引数: [key: キー（Variant）]
#   戻り値: [result: ターン・順序のvalid・キーを求めるための結果（bool）]
# }
static func _valid_key(key: Variant) -> bool:
	return key is Dictionary and _exact_keys(key, ["side", "id"]) \
		and key.get("side") is String and key["side"] in SIDES \
		and key.get("id") is String and Records.safe_id(key["id"])


# {
#   責務: [_exact_keys: ターン・順序のexact・キー一覧を求める]
#   処理: [1: ターン・順序のexact・キー一覧を求める]
#   引数: [
#     value: 値（Dictionary）
#     expected: expected（Array）
#   ]
#   戻り値: [result: ターン・順序のexact・キー一覧を求めるための結果（bool）]
# }
static func _exact_keys(value: Dictionary, expected: Array) -> bool:
	if value.size() != expected.size():
		return false
	for key in value:
		if key not in expected:
			return false
	return true
