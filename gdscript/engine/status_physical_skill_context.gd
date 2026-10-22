# {
#   責務: [status_physical_skill_context: 付与付き物理の開始資源・習得/許可装備・明示初期状態・状態耐性を独立した実行準備へまとめます]
#   フィールド: []
# }
extends RefCounted
const Physical = preload("res://engine/physical_skill_context.gd")
const InitialMap = preload("res://engine/initial_status_map.gd")
const Resistance = preload("res://engine/status_resistance.gd")
const Effects = preload("res://engine/status_effect_contract.gd")
const Order = preload("res://engine/turn_order.gd")


# {
#   責務: [prepare: 全参加者の開始資源・習得/装備・初期状態・状態耐性が成功した場合だけ、独立した準備情報を返します]
#   処理: [
#     1: コピー前にteams/skillsのJSON互換性を確認し、共用の資源/習得/装備/索引検証へ委譲します
#     2: 全参加者に一致する初期状態と個体別状態耐性を検証し、部分成功なしで返します
#   ]
#   引数: [
#     teams: 満HP/MPのsnapshot・skill_ids・equipment・明示status_resistancesを持つ両陣営（Variant）
#     skills: schema_version=1とskills配列を持つ正規/MOD一覧（Variant）
#     initial_statuses: 全参加者の状態配列をside/idごとに明示した辞書（Variant）
#   ]
#   戻り値: [result: 独立snapshots/context/initial_statuses、または理由付き拒否。Session保持ではありません（Dictionary）]
# }
static func prepare(teams: Variant, skills: Variant, initial_statuses: Variant) -> Dictionary:
	# 共用開始処理の深いコピーへObject/循環/過深を渡さず、純粋なJSON由来の開始情報に限定します。
	if not Effects.valid_json_value(teams) or not Effects.valid_json_value(skills):
		return {"ok": false, "reason": "invalid_status_physical_payload"}
	var prepared := Physical.prepare(teams, skills)
	if not prepared["ok"]:
		return prepared
	# 状態の一致/検証は治療付き回復と共用し、初期状態を暗黙の空配列へ置き換えません。
	var statuses := InitialMap.prepare(prepared["snapshots"], initial_statuses)
	if not statuses["ok"]:
		return statuses
	for side in Order.SIDES:
		for member: Dictionary in teams[side]:
			var traits := Resistance.validate(member.get("status_resistances"))
			if not traits["ok"]:
				return traits
			var id: String = member["snapshot"]["identity"]["id"]
			prepared["context"]["members"][side][id]["status_resistances"] = traits["status_resistances"]
	prepared["initial_statuses"] = statuses["initial_statuses"]
	return prepared


# {
#   責務: [select: 準備済み参加者の習得/許可装備から、状態定義を必須にした単体物理スキルを選びます]
#   処理: [1: 物理の共用選択へ専用入口で委譲し、検証済み定義と装備補正だけを返します]
#   引数: [
#     context: prepareで取得した個体別の習得/装備/状態耐性とID別定義索引（Variant）
#     actor: 選択する参加者のsideとidだけを持つ辞書（Variant）
#     skill_id: 習得済み付与付きphysicalのID（Variant）
#   ]
#   戻り値: [result: 独立skillとpower_multiplier/fixed_bonus_damage、または非破壊的な拒否（Dictionary）]
# }
static func select(context: Variant, actor: Variant, skill_id: Variant) -> Dictionary:
	# 要求から定義契約や実行モードを選ばせず、付与付き物理の専用検証だけを使います。
	return Physical.select_status_physical(context, actor, skill_id)
