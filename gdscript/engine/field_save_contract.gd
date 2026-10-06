# {
#   責務: [field_save_contract: Pure field save validation/serialization, preserving unrelated state keys.]
#   フィールド: []
# }
extends RefCounted
## Pure field save validation/serialization, preserving unrelated state keys.

const Rules = preload("res://engine/field_engine.gd")
const INITIAL_INVENTORY := {"orange": 3}
const DEFAULT_STATE := {
	"schema_version": 1, "map_id": "starting_town", "player": {"x": 18, "y": 14},
	"revive_point": {"map_id": "starting_town", "x": 18, "y": 11, "name": "はじまりの街の教会"},
	"current_party": [], "flags": {"story_complete": false, "ghost_entrance_open": false},
}


# {
#   責務: [validate_document: 文書を妥当性を検査する]
#   処理: [1: 文書を妥当性を検査する]
#   引数: [state: 状態（Dictionary）]
#   戻り値: [result: 文書を妥当性を検査するための結果（Dictionary）]
# }
static func validate_document(state: Dictionary) -> Dictionary:
	var version: Variant = state.get("schema_version", 1)
	if not _integer(version) or int(version) != 1:
		return {"ok": false, "error": "unsupported_schema", "message": "未対応のセーブ形式です。"}
	if not state.get("map_id") is String or str(state["map_id"]).is_empty() or not state.get("player") is Dictionary:
		return {"ok": false, "error": "invalid_position", "message": "マップ・座標データが不正です。"}
	var player: Dictionary = state["player"]
	if not _integer(player.get("x")) or not _integer(player.get("y")):
		return {"ok": false, "error": "invalid_position", "message": "座標は整数で指定してください。"}
	if player.get("direction", "front") not in Rules.DIRECTIONS:
		return {"ok": false, "error": "invalid_direction", "message": "向きのデータが不正です。"}
	return {"ok": true}


# {
#   責務: [_integer: フィールド・保存・契約のintegerを求める]
#   処理: [1: フィールド・保存・契約のintegerを求める]
#   引数: [value: 値（Variant）]
#   戻り値: [result: フィールド・保存・契約のintegerを求めるための結果（bool）]
# }
static func _integer(value: Variant) -> bool:
	return (value is int or value is float) and is_finite(float(value)) and float(value) == floorf(float(value))


# {
#   責務: [validate_location: セーブ座標が現在のマップと占有契約で復元可能か検証する]
#   処理: [
#     1: セーブ文書の形式を検証する
#     2: 移動量0で地形・イベント・明示された現在キャラの占有を照合する
#   ]
#   引数: [
#     state: セーブ状態
#     world: 対象マップの定義
#     blocks: ブロック定義
#     characters: 現在占有。初期NPC座標を現在占有とみなさない
#   ]
#   戻り値: [result: okまたはblocked_position等の理由付き拒否]
# }
static func validate_location(
	state: Dictionary, world: Dictionary, blocks: Dictionary, characters: Array = [],
) -> Dictionary:
	var document := validate_document(state)
	if not document["ok"]:
		return document
	var player: Dictionary = state["player"]
	# Source NPC spawn coordinates are not current occupancy. Loading reserves the
	# player first, then resets/relocates NPCs. Saving supplies live logical actors.
	var rules = Rules.new(world, blocks)
	var move: Dictionary = rules.resolve_player_move(
		int(player["x"]), int(player["y"]), 0, 0, str(player.get("direction", "front")), characters, [],
	)
	if move["kind"] != "moved":
		return {"ok": false, "error": "blocked_position", "message": "復元座標へ移動できません: " + move["reason"]}
	return {"ok": true}


# {
#   責務: [capture: フィールド・保存・契約のcaptureを求める]
#   処理: [1: フィールド・保存・契約のcaptureを求める]
#   引数: [
#     base: base（Dictionary）
#     map_id: マップ・識別子（String）
#     x: X座標（int）
#     y: Y座標（int）
#     direction: direction（String）
#   ]
#   戻り値: [result: フィールド・保存・契約のcaptureを求めるための結果（Dictionary）]
# }
static func capture(base: Dictionary, map_id: String, x: int, y: int, direction: String) -> Dictionary:
	var state := base.duplicate(true)
	state["map_id"] = map_id
	var player: Dictionary = state.get("player", {}).duplicate(true)
	player.merge({"x": x, "y": y, "direction": direction}, true)
	state["player"] = player
	return state
