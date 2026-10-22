# {
#   責務: [status_physical_skill_contract: MP付き単体物理の数値と、非致死ダメージ後の状態一件付与を既存契約で純粋予測します]
#   フィールド: []
# }
extends RefCounted

const Physical = preload("res://engine/physical_skill_contract.gd")
const Status = preload("res://engine/status_apply_contract.gd")
const Effects = preload("res://engine/status_effect_contract.gd")
const STATUS_FIELDS := ["status_effects", "status_resistance_level", "status_roll"]


# {
#   責務: [prepare: 一覧から指定IDの付与付き物理定義を一意に選び、物理と状態の検証を共用します]
#   処理: [
#     1: 選択候補だけから状態キーを除いた浅い投影を物理の一覧検証へ渡します
#     2: 一意な状態定義を検証した後だけ、独立した物理/状態定義を返します
#   ]
#   引数: [
#     document: schema_version=1とskills配列を持つ正規/MOD一覧（Variant）
#     skill_id: 一意に選択するスキルID（Variant）
#   ]
#   戻り値: [result: 正規化した独立skill、または部分結果のない拒否（Dictionary）]
# }
static func prepare(document: Variant, skill_id: Variant) -> Dictionary:
	# 状態ネストを型検証前に深く複製せず、未知効果を含む他のキーは捨てません。
	if not document is Dictionary or not document.get("skills") is Array:
		return _reject("invalid_skill_document")
	var projected: Dictionary = document.duplicate()
	var entries: Array = document["skills"].duplicate()
	var selected: Array = []
	for index in entries.size():
		var entry: Variant = entries[index]
		if skill_id is String and entry is Dictionary and entry.get("id") is String and entry["id"] == skill_id:
			selected.append(entry)
			entries[index] = _physical_definition(entry)
	projected["skills"] = entries
	var checked := Physical.prepare(projected, skill_id)
	if not checked["ok"]:
		return checked
	# 一意性・物理型を共用処理で確認した後だけ、必須の付与定義を検証/コピーします。
	if not selected[0].has("status_effect"):
		return _reject("status_effect_required")
	var effect: Variant = selected[0]["status_effect"]
	var status := Status.prepare_application({"effect": effect, "status_effects": []})
	if not status["ok"]:
		return status
	checked["skill"]["status_effect"] = effect.duplicate(true)
	return checked


# {
#   責務: [prepare_quote: 明示した物理乱数からダメージ/MPと付与判定値の要否を、実状態変更なしで返します]
#   処理: [1: 状態rollを許可しない準備入口で共用予測処理へ委譲します]
#   引数: [
#     definition: status_effect辞書を必須にしたMP付きphysical定義（Variant）
#     request: 物理数値とstatus_effects/任意status_resistance_level。status_rollは拒否します（Variant）
#   ]
#   戻り値: [result: status_physical_skill_preparation区分のphysical/status/status_eligible、または拒否（Dictionary）]
# }
static func prepare_quote(definition: Variant, request: Variant) -> Dictionary:
	# 付与乱数を生成せず、物理結果が非致死のときだけ判定要否を準備します。
	return _quote(definition, request, false)


# {
#   責務: [quote_damage: 物理ダメージ後も対象が生存する場合だけ、明示判定値による一件付与を予測します]
#   処理: [1: status_rollを許可する予測入口で共用予測処理へ委譲します]
#   引数: [
#     definition: 準備済みまたは同形式の付与付きphysical定義（Variant）
#     request: 物理数値とstatus_effects/任意status_resistance_level/status_roll（Variant）
#   ]
#   戻り値: [result: status_physical_skill_quote区分の独立physical/status/status_eligible、または拒否（Dictionary）]
# }
static func quote_damage(definition: Variant, request: Variant) -> Dictionary:
	# 予測をHP/MP/状態の実更新や予約取得の許可として扱いません。
	return _quote(definition, request, true)


# {
#   責務: [_quote: 物理と状態の検証が両方成功した場合だけ、非致死条件付きの統合結果を返します]
#   処理: [
#     1: 定義・要求キー・数値投影のJSON互換性を確認します
#     2: 物理契約でMP不足/ダメージを確認した後、状態契約へ準備/予測を委譲します
#   ]
#   引数: [
#     definition: 付与付きphysical定義（Variant）
#     request: 対象の最新一覧と独立した数値/判定条件（Variant）
#     allow_roll: 準備ではfalse、予測ではtrueに入口が固定する内部区分（bool）
#   ]
#   戻り値: [result: 独立した統合結果、または部分成功を返さない拒否（Dictionary）]
# }
static func _quote(definition: Variant, request: Variant, allow_roll: bool) -> Dictionary:
	if not definition is Dictionary:
		return _reject("invalid_skill_definition")
	var checked := prepare({"schema_version": 1, "skills": [definition]}, definition.get("id"))
	if not checked["ok"]:
		return checked
	if not request is Dictionary:
		return _reject("invalid_quote_request")
	for field in request:
		if field not in Physical.QUOTE_FIELDS and field not in STATUS_FIELDS:
			return _reject("unsupported_status_physical_request")
		if field == "status_roll" and not allow_roll:
			return _reject("unsupported_status_physical_request")
	var skill: Dictionary = checked["skill"]
	var numbers: Dictionary = {}
	for field in Physical.QUOTE_FIELDS:
		if request.has(field):
			numbers[field] = request[field]
	# 物理契約が複製する前に、Object/循環/過深の数値入力を共用JSON検査で拒否します。
	if not Effects.valid_effects([{"payload": numbers}]):
		return _reject("invalid_physical_payload")
	var physical := Physical.quote_damage(_physical_definition(skill), numbers)
	if not physical["ok"]:
		return physical
	# Pythonのdealt>0かつ攻撃後aliveに合わせ、致死/ダメージなしは成功率0の一時投影にします。
	var eligible: bool = physical["dealt"] > 0 and physical["remaining_hp"] > 0
	var effect: Dictionary = skill["status_effect"].duplicate()
	if not eligible:
		effect["chance"] = 0.0
	var status_request := {"effect": effect, "status_effects": request.get("status_effects"),
		"resistance_level": request.get("status_resistance_level", "normal")}
	if allow_roll and request.has("status_roll"):
		status_request["roll"] = request["status_roll"]
	var status: Dictionary = Status.quote_application(status_request) if allow_roll else Status.prepare_application(status_request)
	if not status["ok"]:
		return status
	if not eligible:
		status["outcome"] = "no_damage" if physical["dealt"] <= 0 else "target_defeated"
	return {"ok": true, "scope": "status_physical_skill_quote" if allow_roll else "status_physical_skill_preparation",
		"physical": physical, "status": status, "status_eligible": eligible}


# {
#   責務: [_physical_definition: 状態キーだけを除いた浅い定義投影を、既存物理検証へ渡します]
#   処理: [1: 外側だけを複製してstatus_effectだけを除き、未知キーと原本は保持します]
#   引数: [definition: 物理/状態の入力定義。ネスト検証前にも使う辞書（Dictionary）]
#   戻り値: [result: 状態ネストを再帰複製しない物理側の一時定義（Dictionary）]
# }
static func _physical_definition(definition: Dictionary) -> Dictionary:
	# 状態付与を通常の物理入口が受け入れたように見せず、専用入口だけで分離します。
	var copied: Dictionary = definition.duplicate()
	copied.erase("status_effect")
	return copied


# {
#   責務: [_reject: 付与付き物理予測を数値/状態の部分成功なしで拒否します]
#   処理: [1: ok=falseと具体的なreasonだけを返します]
#   引数: [reason: 定義/要求/数値投影の拒否理由（String）]
#   戻り値: [result: 非破壊的な拒否辞書（Dictionary）]
# }
static func _reject(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
