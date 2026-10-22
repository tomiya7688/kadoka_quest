# {
#   責務: [turn_preparation: 両陣営の保存個体を戦闘用に再構築し、指定の並べ替え候補列を使う行動順計画を返します]
#   フィールド: [builder: 保存個体から能力値・戦闘資源・習得スキルを構築するcombatant_builder.gdの構築処理（RefCounted）]
# }
extends RefCounted
## turn_preparation.gdの準備処理は戦闘参加者と行動順を準備し、行動実行・AI選択・保存書き込みを行いません。

const Builder = preload("res://application/combatant_builder.gd")
const Order = preload("res://engine/turn_order.gd")
var builder: RefCounted


# {
#   責務: [_init: 参加個体の再構築に使うデータ取得先をcombatant_builder.gdの構築処理へ渡します]
#   処理: [1: 指定リポジトリを使うcombatant_builder.gdの構築処理を生成し、戦闘参加者の準備に使用します]
#   引数: [repository: 正規の種族・装備などのJSON定義を取得するリポジトリ（RefCounted）]
#   戻り値: [result: なし（void）。参加個体の構築処理を設定し、戦闘行動は実行しません]
# }
func _init(repository: RefCounted) -> void:
	builder = Builder.new(repository)


# {
#   責務: [prepare: 味方と敵の戦闘参加者を再構築し、敏捷性に基づく行動順を計画します]
#   処理: [1: 両陣営の個体構築をcombatant_builder.gdの構築処理へ、行動順計画をturn_order.gdの行動順計算へ委譲し、最初の失敗時点で拒否結果を返します]
#   引数: [
#     allies: 戦闘へ参加させる味方の保存個体レコード列（Variant）
#     enemies: 戦闘へ参加させる敵の個体レコード列（Variant）
#     shuffle_order: 陣営sideと個体idで表す全参加者の並べ替え候補列。敏捷性が同じ参加者の順を決めます（Variant）
#   ]
#   戻り値: [result: 成功時は再構築済み参加者teamsと行動順plan、失敗時は理由reasonと該当陣営や詳細を持つ結果（Dictionary）]
# }
func prepare(allies: Variant, enemies: Variant, shuffle_order: Variant) -> Dictionary:
	# 戦闘準備処理は、両陣営の個体構築が成功してから行動順を計画し、個体構築に失敗した場合は該当陣営を呼び出し元へ伝えます。
	var teams: Dictionary = {}
	var snapshots: Dictionary = {}
	for side in ["allies", "enemies"]:
		var built: Dictionary = builder.build_team(allies if side == "allies" else enemies)
		if not built["ok"]:
			return {"ok": false, "reason": "team_reconstruction_failed", "side": side, "detail": built}
		teams[side] = built["members"]
		snapshots[side] = _snapshots(built["members"])
	# 戦闘準備処理は、行動順の計算へ戦闘資源だけを渡し、装備や学習状態の所有をturn_order.gdの行動順計算へ持ち込みません。
	var planned := Order.plan(snapshots["allies"], snapshots["enemies"], shuffle_order)
	if not planned["ok"]:
		return planned
	return {"ok": true, "teams": teams, "plan": planned, "scope": "base_turn_preparation"}


# {
#   責務: [_snapshots: 構築済みの戦闘参加者から、行動順計算へ渡す戦闘資源辞書だけを順に取り出します]
#   処理: [1: 各参加者のsnapshotを列へ追加し、装備と習得スキルの情報を行動順計算の入力へ混在させません]
#   引数: [members: combatant_builder.gdの構築処理が返した戦闘資源snapshot・装備・習得スキルなどを持つ参加者列（Array）]
#   戻り値: [result: 入力の参加者順を保ったsnapshotの参照列。辞書自体はここでは複製しません（Array）]
# }
func _snapshots(members: Array) -> Array:
	var snapshots: Array = []
	for member: Dictionary in members:
		snapshots.append(member["snapshot"])
	return snapshots
