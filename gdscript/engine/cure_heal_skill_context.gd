# {
#   責務: [cure_heal_skill_context: 治療付き回復の開始情報と参加者別の初期状態を検証し、実行に使う定義を選びます]
#   フィールド: []
# }
extends RefCounted
const Healing = preload("res://engine/heal_skill_context.gd")
const Curing = preload("res://engine/status_cure_contract.gd")
const Order = preload("res://engine/turn_order.gd")
const InitialMap = preload("res://engine/initial_status_map.gd")


# {
#   責務: [prepare: 開始資源・習得・許可装備と、全参加者に一致する初期状態一覧の独立コピーを作ります]
#   処理: [1: 共用開始情報検証と初期状態検証が両方成功した場合だけ、準備結果を返します]
#   引数: [
#     teams: 満HP/MPのsnapshot・skill_ids・許可装備equipmentを持つ両陣営（Variant）
#     skills: schema_version=1とskills配列を持つJSON由来の正規/互換MOD定義（Variant）
#     initial_statuses: allies/enemiesごとに全参加者idをキーとし、各状態配列を明示した辞書（Variant）
#   ]
#   戻り値: [result: 独立snapshots・context・initial_statuses、または部分成功のない拒否（Dictionary）]
# }
static func prepare(teams: Variant, skills: Variant, initial_statuses: Variant) -> Dictionary:
	# HP/MPや習得・装備の規則は再実装せず、HP回復と同じ開始情報検証を使います。
	var prepared := Healing.prepare(teams, skills)
	if not prepared["ok"]:
		return prepared
	var statuses := _initial_statuses(prepared["snapshots"], initial_statuses)
	if not statuses["ok"]:
		return statuses
	prepared["initial_statuses"] = statuses["initial_statuses"]
	return prepared


# {
#   責務: [select: 開始情報の参加者から習得済みの治療付き回復定義を独立して選びます]
#   処理: [1: 共用の回復選択へ治療付き専用入口で委譲し、状態やHP/MPを更新しません]
#   引数: [
#     context: prepareで取得した個体情報と定義索引（Variant）
#     actor: 選択する参加者のsideとid（Variant）
#     skill_id: 治療付き回復として選択するID（Variant）
#   ]
#   戻り値: [result: 独立した検証済みskill、または理由付き拒否（Dictionary）]
# }
static func select(context: Variant, actor: Variant, skill_id: Variant) -> Dictionary:
	return Healing.select_cure_heal(context, actor, skill_id)


# {
#   責務: [_initial_statuses: 数値snapshotの参加者と初期状態のside/idを一対一に照合し、状態配列を独立検証します]
#   処理: [
#     1: 両陣営の辞書と全参加者idの一致を確認し、欠落/余分な個体を拒否します
#     2: 各状態配列を純粋治療契約で検証し、参加者別の独立一覧を返します
#   ]
#   引数: [
#     snapshots: 共用開始検証を通過した両陣営の六キー数値snapshot列（Dictionary）
#     initial_statuses: 各参加者の初期状態配列を明示したside/id別辞書（Variant）
#   ]
#   戻り値: [result: 独立initial_statuses、またはreasonと必要なside/idを持つ拒否（Dictionary）]
# }
static func _initial_statuses(snapshots: Dictionary, initial_statuses: Variant) -> Dictionary:
	# 空状態を暗黙補完せず、敵も含むすべての参加者に明示した一覧を要求します。
	var matched := InitialMap.validate(snapshots, initial_statuses)
	if not matched["ok"]:
		return matched
	var result := {"allies": {}, "enemies": {}}
	for side in Order.SIDES:
		var entries: Dictionary = initial_statuses[side]
		for member: Dictionary in snapshots[side]:
			var id: String = member["identity"]["id"]
			# 未知MOD情報は保持しますが、付与/継続効果や治療成功をここで実行しません。
			var checked := Curing.select_candidate(entries[id])
			if not checked["ok"]:
				checked["side"] = side
				checked["id"] = id
				return checked
			result[side][id] = checked["effects"]
	return {"ok": true, "initial_statuses": result}
