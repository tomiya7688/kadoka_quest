# {
#   責務: [cure_heal_skill_contract: HP回復と状態異常一件の治療を既存契約で予測し、実資源・元定義・元一覧を変更しません]
#   フィールド: []
# }
extends RefCounted

const Numbers = preload("res://engine/stat_numbers.gd")
const MagicContract = preload("res://engine/magic_skill_contract.gd")
const HealContract = preload("res://engine/heal_skill_contract.gd")
const CureContract = preload("res://engine/status_cure_contract.gd")


# {
#   責務: [prepare: スキル一覧から指定IDの治療付きHP回復定義を選び、対応範囲と数値を検証します]
#   処理: [1: 共用の一覧選択で形式・IDの一意性を確認し、治療付き回復の定義検証へ委譲します]
#   引数: [
#     document: schema_version=1とskills配列を持つ一覧（Variant）
#     skill_id: 選択する空でない文字列ID（Variant）
#   ]
#   戻り値: [result: ok=trueと独立したskill、または理由付き拒否（Dictionary）]
# }
static func prepare(document: Variant, skill_id: Variant) -> Dictionary:
	var selected := MagicContract.select_definition(document, skill_id)
	if not selected["ok"]:
		return selected
	return _validate_definition(selected["skill"])


# {
#   責務: [quote_heal: 指定対象のHP回復・一件の治療と術者の消費後MPを、明示判定値だけで予測します]
#   処理: [
#     1: 定義と許可要求キーを検証し、HP/MP計算とMP不足拒否を既存回復契約へ委譲します
#     2: 既存治療契約で状態と判定値を検証し、両方が成功した場合だけ統合予測を返します
#   ]
#   引数: [
#     definition: kind=heal・正のmp_cost・有限status_cure_chanceを持つ定義（Variant）
#     request: current_mp・target_hp・target_max_hp・status_effectsと任意のrollだけを持つ辞書（Variant）
#   ]
#   戻り値: [result: 独立したHP/MP・治療予測、または理由付き拒否。乱数生成・実更新・復活許可は行いません（Dictionary）]
# }
static func quote_heal(definition: Variant, request: Variant) -> Dictionary:
	# 不正な治療情報でもHPだけの部分成功を返さず、実更新側が誤適用する余地を残しません。
	var validated := _validate_definition(definition)
	if not validated["ok"]:
		return validated
	if not request is Dictionary:
		return _reject("invalid_quote_request")
	for field in request:
		if field not in ["current_mp", "target_hp", "target_max_hp", "status_effects", "roll"]:
			return _reject("unsupported_cure_heal_request")
	var skill: Dictionary = validated["skill"]
	var healing := HealContract.quote_heal(_heal_definition(skill), {
		"current_mp": request.get("current_mp"), "target_hp": request.get("target_hp"),
		"target_max_hp": request.get("target_max_hp")})
	if not healing["ok"]:
		return healing
	# MP不足を先に拒否します。候補があれば確率0/1でもrollが必要です。
	var curing := CureContract.quote_cure({"status_effects": request.get("status_effects"),
		"cure_chance": skill["status_cure_chance"], "roll": request.get("roll")})
	if not curing["ok"]:
		return curing
	healing["scope"] = "cure_heal_skill_quote"
	for field in ["cured", "cured_name", "candidate_index", "roll_required", "cure_chance", "remaining_status_effects"]:
		healing[field] = curing[field]
	return healing


# {
#   責務: [_validate_definition: 治療確率を必須検証し、未知効果を捨てずに拒否して既存HP回復検証へ委譲します]
#   処理: [
#     1: 対応キーと有限治療確率を確認します
#     2: 検証済み治療確率だけを除いたコピーでHP回復定義を検証し、独立定義へ戻します
#   ]
#   引数: [definition: 選択または直接指定した治療付き回復定義（Variant）]
#   戻り値: [result: 正規化した独立skill、または理由付き拒否（Dictionary）]
# }
static func _validate_definition(definition: Variant) -> Dictionary:
	if not definition is Dictionary:
		return _reject("invalid_skill_definition")
	# 値がfalse・0・空の未知効果も、対応したように捨てません。
	for field in definition:
		if field not in ["id", "display_name", "description", "kind", "heal_ratio", "mp_cost", "status_cure_chance"]:
			return _reject("unsupported_cure_heal_skill")
	var chance := Numbers.float_value(definition.get("status_cure_chance"))
	if not chance["ok"]:
		return _reject("invalid_cure_chance")
	var checked := HealContract.validate_definition(_heal_definition(definition))
	if not checked["ok"]:
		return checked
	checked["skill"]["status_cure_chance"] = chance["value"]
	return checked


# {
#   責務: [_heal_definition: 検証済み治療キーだけを除いた一時辞書を、既存HP回復の型検証へ渡します]
#   処理: [1: 辞書の外側だけを複製し、status_cure_chanceだけを除いて返します]
#   引数: [definition: 未知キー拒否と治療確率検証を通過した定義（Dictionary）]
#   戻り値: [result: 原本のキーを変更しない一時辞書。値の型検証後に既存回復契約が深くコピーします（Dictionary）]
# }
static func _heal_definition(definition: Dictionary) -> Dictionary:
	# 不正なネスト値を型検証前に再帰コピーせず、検証済みのスカラー定義だけを独立保持します。
	var copied := definition.duplicate()
	copied.erase("status_cure_chance")
	return copied


# {
#   責務: [_reject: 治療付き回復の拒否を成功結果と区別できる理由付き辞書へ変換します]
#   処理: [1: ok=falseと具体的な拒否理由を返します]
#   引数: [reason: 定義または要求を拒否した理由（String）]
#   戻り値: [result: ok=falseとreasonの辞書（Dictionary）]
# }
static func _reject(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
