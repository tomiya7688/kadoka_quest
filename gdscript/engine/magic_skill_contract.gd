# {
#   責務: [magic_skill_contract: MPを消費する単体魔法の定義を検証し、HPとMPの変化を状態更新なしで予測します]
#   フィールド: []
# }
extends RefCounted

const Numbers = preload("res://engine/stat_numbers.gd")
const MagicNumbers = preload("res://engine/magic_numbers.gd")
const DEFINITION_FIELDS := ["id", "display_name", "description", "kind", "power", "element", "mp_cost"]
const QUOTE_FIELDS := ["magic", "target_hp", "target_max_hp", "current_mp", "target_resistances",
	"guard", "variance", "fixed_bonus_damage"]


# {
#   責務: [prepare: スキル一覧から指定IDの一意な単体魔法定義を検証して返します]
#   処理: [
#     1: 一覧の形式とIDを検証します
#     2: 指定IDの欠落や重複を拒否します
#     3: 選択した定義を検証します
#   ]
#   引数: [
#     document: schema_version=1とskills配列を持つスキル一覧（Variant）
#     skill_id: 一覧から選択するスキルID（Variant）
#   ]
#   戻り値: [result: ok=trueと独立したskill辞書、またはok=falseと拒否理由reason（Dictionary）]
# }
static func prepare(document: Variant, skill_id: Variant) -> Dictionary:
	# 一覧からの一意な選択だけを共用し、通常魔法の対応効果は引き続きここで限定する。
	var selected := select_definition(document, skill_id)
	if not selected["ok"]:
		return selected
	return _validate_definition(selected["skill"])


# {
#   責務: [select_definition: 一覧から指定IDの定義を一意に選び、原本から独立した辞書を返します]
#   処理: [
#     1: 一覧形式と選択IDを検証します
#     2: 指定IDの欠落と重複を拒否します
#     3: 選択した定義をコピーします
#   ]
#   引数: [
#     document: schema_version=1とskills配列を持つスキル一覧（Variant）
#     skill_id: 選択する空でない文字列ID（Variant）
#   ]
#   戻り値: [result: ok=trueと独立したskill、または理由付き拒否。効果の対応可否は呼出元で検証します（Dictionary）]
# }
static func select_definition(document: Variant, skill_id: Variant) -> Dictionary:
	# 未選択の定義や一覧の原本を修正せず、指定したIDだけを検索する。
	if not document is Dictionary or not document.get("skills") is Array:
		return _reject("invalid_skill_document")
	var version: Variant = document.get("schema_version")
	if not (version is int or version is float) or version != 1:
		return _reject("invalid_skill_document")
	if not skill_id is String or skill_id.is_empty():
		return _reject("invalid_skill_id")
	# 重複定義のうち一つを暗黙に採用しないよう、件数も保持する。
	var selected: Array = []
	for definition: Variant in document["skills"]:
		if definition is Dictionary and definition.get("id") is String and definition["id"] == skill_id:
			selected.append(definition)
	if selected.size() != 1:
		return _reject("skill_definition_missing_or_duplicate")
	return {"ok": true, "skill": selected[0].duplicate(true)}


# {
#   責務: [quote_damage: 単体魔法のHP変化と支払い後MPを、入力資源を変更せず予測します]
#   処理: [
#     1: 定義と要求を検証します
#     2: MP不足を拒否します
#     3: 属性耐性を含む数値結果へ残MP予測を加えます
#   ]
#   引数: [
#     definition: kind=magicと正のmp_costを持つ、追加効果のないスキル定義（Variant）
#     request: 魔力・対象の現在HPと最大HP・現在MP・耐性辞書・明示した揺らぎを持つ数値要求（Variant）
#   ]
#   戻り値: [result: ok=trueとHP/MP予測、またはok=falseとreason。実MP支払いとHP更新は行いません（Dictionary）]
# }
static func quote_damage(definition: Variant, request: Variant) -> Dictionary:
	# prepareを省略した呼出しにも、同じ対応範囲の検証を適用する。
	var validated := _validate_definition(definition)
	if not validated["ok"]:
		return validated
	var checked := _validate_quote(request)
	if not checked["ok"]:
		return checked
	var skill: Dictionary = validated["skill"]
	if checked["current_mp"] < skill["mp_cost"]:
		return _reject("insufficient_mp")
	# 装備JSON・AI・Sessionは渡さず、必要な数値と耐性だけを計算へ投影する。
	var numbers := {"magic": request.get("magic"), "target_hp": request.get("target_hp"),
		"target_max_hp": request.get("target_max_hp"), "target_resistances": request.get("target_resistances", {}),
		"guard": request.get("guard", 1.0), "variance": request.get("variance"),
		"fixed_bonus_damage": request.get("fixed_bonus_damage", 0), "power": skill["power"], "element": skill["element"]}
	var result := MagicNumbers.predict(numbers)
	if not result["ok"]:
		return result
	# 残MPは予測値のみ。無効や吸収でも、魔法を使用する場合のMP消費量を示す。
	result.merge({"scope": "magic_skill_quote", "skill_id": skill["id"], "mp_cost": skill["mp_cost"],
		"remaining_mp": checked["current_mp"] - skill["mp_cost"]}, true)
	return result


# {
#   責務: [_validate_definition: 単体魔法の対応フィールドと数値を検証し、原本から独立した定義を返します]
#   処理: [
#     1: 未対応効果と不正な文字列を拒否します
#     2: MPと威力を検証します
#     3: 既定値を独立コピーへ加えます
#   ]
#   引数: [definition: 選択または直接指定したスキル定義（Variant）]
#   戻り値: [result: 検証済みskill、または理由付き拒否（Dictionary）]
# }
static func _validate_definition(definition: Variant) -> Dictionary:
	# 状態異常や全体攻撃等は、空やfalseでも未対応として拒否する。
	if not definition is Dictionary:
		return _reject("invalid_skill_definition")
	for field: Variant in definition:
		if field not in DEFINITION_FIELDS:
			return _reject("unsupported_magic_skill")
	if not definition.get("id") is String or definition["id"].is_empty() or definition["id"] in ["attack", "defend"]:
		return _reject("invalid_skill_id")
	if not definition.get("kind") is String or definition["kind"] != "magic":
		return _reject("unsupported_magic_skill")
	if not definition.get("display_name") is String or definition["display_name"].is_empty():
		return _reject("invalid_skill_text")
	if definition.has("description") and not definition["description"] is String:
		return _reject("invalid_skill_text")
	var element: Variant = definition.get("element", "physical")
	if not element is String or element.is_empty():
		return _reject("invalid_skill_element")
	# Python正本と同じくMPを0方向へ切り捨て、属性省略時はphysicalを使う。
	var cost := Numbers.integer_value(definition.get("mp_cost"))
	var power := Numbers.float_value(definition.get("power", 1.0))
	if not cost["ok"] or cost["value"] <= 0 or not power["ok"]:
		return _reject("invalid_magic_skill_numbers")
	var skill: Dictionary = definition.duplicate(true)
	skill.merge({"mp_cost": cost["value"], "power": power["value"], "element": element}, true)
	return {"ok": true, "skill": skill}


# {
#   責務: [_validate_quote: 未対応の要求キーと不正な現在MPを拒否します]
#   処理: [
#     1: 数値要求の対応キーを確認します
#     2: 現在MPが非負の正規整数か検証します
#   ]
#   引数: [request: 単体魔法の数値予測要求（Variant）]
#   戻り値: [result: 検証済みcurrent_mp、または理由付き拒否（Dictionary）]
# }
static func _validate_quote(request: Variant) -> Dictionary:
	# 回避・反撃・攻撃倍率等を無視した成功結果は返さない。
	if not request is Dictionary:
		return _reject("invalid_quote_request")
	for field: Variant in request:
		if field not in QUOTE_FIELDS:
			return _reject("unsupported_quote_field")
	var mp: Variant = request.get("current_mp")
	var checked := Numbers.integer_value(mp)
	if not (mp is int or mp is float) or not checked["ok"] or checked["value"] < 0 or checked["value"] != mp:
		return _reject("invalid_current_mp")
	return {"ok": true, "current_mp": checked["value"]}


# {
#   責務: [_reject: 呼出元が失敗を判別できる、理由付きの拒否結果を作ります]
#   処理: [1: 成功フラグをfalseにし拒否理由を保持します]
#   引数: [reason: スキル検証またはMP検証で失敗した理由（String）]
#   戻り値: [result: ok=falseとreasonを持つ辞書（Dictionary）]
# }
static func _reject(reason: String) -> Dictionary:
	# 未対応定義やMP不足を、成立した予測に置き換えない。
	return {"ok": false, "reason": reason}
