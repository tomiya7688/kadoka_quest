# {
#   責務: [turn_preparation: Read-only record reconstruction -> pure base round plan. No action, inference or writes.]
#   フィールド: [builder: 構築処理（RefCounted）]
# }
extends RefCounted
## Read-only record reconstruction -> pure base round plan. No action, inference or writes.

const Builder = preload("res://application/combatant_builder.gd")
const Order = preload("res://engine/turn_order.gd")
var builder: RefCounted


# {
#   責務: [_init: ターン・preparationが利用する初期状態と依存を設定する]
#   処理: [1: ターン・preparationが利用する初期状態と依存を設定する]
#   引数: [repository: データ取得先（RefCounted）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _init(repository: RefCounted) -> void:
	builder = Builder.new(repository)


# {
#   責務: [prepare: ターン・preparationを準備する]
#   処理: [1: ターン・preparationを準備する]
#   引数: [
#     allies: 味方（Variant）
#     enemies: 敵（Variant）
#     shuffle_order: 並べ替え・順序（Variant）
#   ]
#   戻り値: [result: ターン・preparationを準備するための結果（Dictionary）]
# }
func prepare(allies: Variant, enemies: Variant, shuffle_order: Variant) -> Dictionary:
	var teams: Dictionary = {}
	var snapshots: Dictionary = {}
	for side in ["allies", "enemies"]:
		var built: Dictionary = builder.build_team(allies if side == "allies" else enemies)
		if not built["ok"]:
			return {"ok": false, "reason": "team_reconstruction_failed", "side": side, "detail": built}
		teams[side] = built["members"]
		snapshots[side] = _snapshots(built["members"])
	var planned := Order.plan(snapshots["allies"], snapshots["enemies"], shuffle_order)
	if not planned["ok"]:
		return planned
	return {"ok": true, "teams": teams, "plan": planned, "scope": "base_turn_preparation"}


# {
#   責務: [_snapshots: ターン・preparationのsnapshotsを求める]
#   処理: [1: ターン・preparationのsnapshotsを求める]
#   引数: [members: 個体一覧（Array）]
#   戻り値: [result: ターン・preparationのsnapshotsを求めるための結果（Array）]
# }
func _snapshots(members: Array) -> Array:
	var snapshots: Array = []
	for member: Dictionary in members:
		snapshots.append(member["snapshot"])
	return snapshots
