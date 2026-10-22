# {
#   責務: [revive_point_contract: Pure checkpoint validation and a one-key state plan; never heal or teleport.]
#   フィールド: []
# }
extends RefCounted
## Pure checkpoint validation and a one-key state plan; never heal or teleport.
const Rules = preload("res://engine/field_engine.gd")


# {
#   責務: [validate_point: 地点を妥当性を検査する]
#   処理: [1: 地点を妥当性を検査する]
#   引数: [value: 値（Variant）]
#   戻り値: [result: 地点を妥当性を検査するための結果（Dictionary）]
# }
static func validate_point(value: Variant) -> Dictionary:
	if not value is Dictionary or not value.get("map_id") is String or str(value["map_id"]).is_empty() \
		or not value.get("name") is String or str(value["name"]).strip_edges().is_empty():
		return _invalid("reviveのmap_id/nameは空でない文字列が必要です。")
	if not _integer(value.get("x")) or not _integer(value.get("y")):
		return _invalid("reviveのx/yは整数で指定してください。")
	return {"ok": true, "point": value.duplicate(true)}


# {
#   責務: [validate_location: locationを妥当性を検査する]
#   処理: [1: locationを妥当性を検査する]
#   引数: [
#     point: 地点（Dictionary）
#     world: マップ状態（Dictionary）
#     blocks: ブロック定義（Dictionary）
#   ]
#   戻り値: [result: locationを妥当性を検査するための結果（Dictionary）]
# }
static func validate_location(point: Dictionary, world: Dictionary, blocks: Dictionary) -> Dictionary:
	if world.get("id") != point["map_id"]:
		return _invalid("復活先マップのidが一致しません。")
	for event: Variant in world.get("events", []):
		if not event is Dictionary or not _integer(event.get("x")) or not _integer(event.get("y")):
			return _invalid("復活先マップのイベント座標が不正です。")
	var x := int(point["x"])
	var y := int(point["y"])
	if x < 0 or y < 0 or x >= int(world["width"]) or y >= int(world["height"]):
		return _invalid("復活先の座標がマップ範囲外です。")
	var tile: Variant = world["tiles"][y][x]
	if not tile is String or not blocks.get(tile) is Dictionary \
		or not blocks[tile].get("player_walkable") is bool:
		return _invalid("復活先のブロック定義が不正です。")
	var move: Dictionary = Rules.new(world, blocks).resolve_player_move(x, y, 0, 0, "front", [], [])
	if move["kind"] != "moved":
		return _invalid("復活先へ移動できません: " + move["reason"])
	return {"ok": true}


# {
#   責務: [plan: 復活・地点・契約を計画する]
#   処理: [1: 復活・地点・契約を計画する]
#   引数: [
#     state: 状態（Dictionary）
#     point: 地点（Dictionary）
#   ]
#   戻り値: [result: 復活・地点・契約を計画するための結果（Dictionary）]
# }
static func plan(state: Dictionary, point: Dictionary) -> Dictionary:
	var updated := state.duplicate(true)
	updated["revive_point"] = point.duplicate(true)
	return {"ok": true, "state": updated, "changed": updated != state}


# {
#   責務: [_integer: 復活・地点・契約のintegerを求める]
#   処理: [1: 復活・地点・契約のintegerを求める]
#   引数: [value: 値（Variant）]
#   戻り値: [result: 復活・地点・契約のintegerを求めるための結果（bool）]
# }
static func _integer(value: Variant) -> bool:
	return (value is int or value is float) and is_finite(float(value)) and float(value) == floorf(float(value))


# {
#   責務: [_invalid: 復活・地点・契約のinvalidを求める]
#   処理: [1: 復活・地点・契約のinvalidを求める]
#   引数: [message: message（String）]
#   戻り値: [result: 復活・地点・契約のinvalidを求めるための結果（Dictionary）]
# }
static func _invalid(message: String) -> Dictionary:
	return {"ok": false, "error": "invalid_revive", "message": message}
