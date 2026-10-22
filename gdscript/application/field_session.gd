# {
#   責務: [field_session: In-memory exploration state; clock advances only while the field is active.]
#   フィールド: [
#     rules: rules
#     fixed_mobs: fixed・モブ一覧
#     clock_ms: clock・ミリ秒
#     despawned_fixed_mobs: despawned・fixed・モブ一覧（Array）
#     world: マップ状態（Dictionary）
#     visible_characters: visible・characters（Array）
#     x: X座標
#     y: Y座標
#     direction: direction
#   ]
# }
extends RefCounted
## In-memory exploration state; clock advances only while the field is active.

const FieldRules = preload("res://engine/field_engine.gd")
const FixedMobs = preload("res://engine/fixed_mob_controller.gd")
const RandomSource = preload("res://engine/field_random.gd")
var rules = FieldRules.new()
var fixed_mobs = FixedMobs.new(rules, RandomSource.new())
var clock_ms := 0.0
var despawned_fixed_mobs: Array = []
var world: Dictionary = {}
var visible_characters: Array = []
var x := 0
var y := 0
var direction := "front"


# {
#   責務: [enter_map: フィールド・セッションのenter・マップを求める]
#   処理: [1: フィールド・セッションのenter・マップを求める]
#   引数: [
#     map_data: マップ・データ（Dictionary）
#     blocks: ブロック定義（Dictionary）
#     entry: 項目（Dictionary）
#   ]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func enter_map(map_data: Dictionary, blocks: Dictionary, entry: Dictionary = {}) -> void:
	world = map_data
	rules.set_world(world, blocks)
	x = clampi(int(entry.get("x", world["start"]["x"])), 0, int(world["width"]) - 1)
	y = clampi(int(entry.get("y", world["start"]["y"])), 0, int(world["height"]) - 1)
	fixed_mobs.reset(world, blocks, despawned_fixed_mobs, [x, y], int(clock_ms))
	visible_characters = fixed_mobs.npcs


# {
#   責務: [advance: フィールド・セッションのadvanceを求める]
#   処理: [1: フィールド・セッションのadvanceを求める]
#   引数: [delta: 経過時間（float）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func advance(delta: float) -> void:
	clock_ms += maxf(0.0, delta) * 1000.0
	fixed_mobs.update([x, y], int(clock_ms))


# {
#   責務: [character_snapshot: フィールド・セッションのキャラクター・独立した状態の写しを求める]
#   処理: [1: フィールド・セッションのキャラクター・独立した状態の写しを求める]
#   引数: []
#   戻り値: [result: フィールド・セッションのキャラクター・独立した状態の写しを求めるための結果（Array）]
# }
func character_snapshot() -> Array:
	return fixed_mobs.snapshot(int(clock_ms))


# {
#   責務: [move_player: 主人公を移動する]
#   処理: [1: 主人公を移動する]
#   引数: [
#     dx: 横方向の移動量（int）
#     dy: 縦方向の移動量（int）
#   ]
#   戻り値: [result: 主人公を移動するための結果（Dictionary）]
# }
func move_player(dx: int, dy: int) -> Dictionary:
	var result: Dictionary = rules.resolve_player_move(x, y, dx, dy, direction, visible_characters, [])
	direction = result["direction"]
	if result["kind"] == "moved":
		x = result["x"]
		y = result["y"]
		result["event"] = rules.step_transition_at(x, y)
	return result


# {
#   責務: [interact: フィールド・セッションのinteractを求める]
#   処理: [1: フィールド・セッションのinteractを求める]
#   引数: []
#   戻り値: [result: フィールド・セッションのinteractを求めるための結果（Dictionary）]
# }
func interact() -> Dictionary:
	var front: Array = rules.front_position(x, y, direction)
	var npc: Dictionary = fixed_mobs.find_at(int(front[0]), int(front[1]))
	if not npc.is_empty():
		return fixed_mobs.talk(npc, direction)
	return {"kind": "event", "event": interaction_event()}


# {
#   責務: [interaction_event: フィールド・セッションのinteraction・イベントを求める]
#   処理: [1: フィールド・セッションのinteraction・イベントを求める]
#   引数: []
#   戻り値: [result: フィールド・セッションのinteraction・イベントを求めるための結果（Dictionary）]
# }
func interaction_event() -> Dictionary:
	var front: Array = rules.front_position(x, y, direction)
	for event: Dictionary in world.get("events", []):
		if (int(event["x"]) == int(front[0]) and int(event["y"]) == int(front[1])) \
			or (int(event["x"]) == x and int(event["y"]) == y):
			if event.get("type") != "transition" or event.get("activation", "step") == "interact":
				return event
	return {}
