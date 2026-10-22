# {
#   責務: [physical_skill_contract: MP付き単体物理スキルの定義検証と資源・ダメージの予測。状態更新・I/O・AIは行わない]
#   フィールド: []
# }
extends RefCounted

const Numbers = preload("res://engine/stat_numbers.gd")
const AttackNumbers = preload("res://engine/attack_numbers.gd")
const DEFINITION_FIELDS := ["id", "display_name", "description", "kind", "power", "mp_cost", "critical_multiplier"]
const QUOTE_FIELDS := ["attack", "defense", "target_hp", "current_mp", "attack_multiplier",
	"guard", "critical_roll", "variance", "power_multiplier", "fixed_bonus_damage"]


# {
#   責務: [prepare: 正規スキル一覧から要求IDの一意なMP付き物理定義を取り出す]
#   処理: [
#     1: スキル一覧のschema_version=1と空でない文字列の要求IDを確認します
#     2: 要求IDに一致する定義を集め、欠落や二件以上の重複を拒否します
#     3: 一意に選んだ定義の対応キー・数値を検証し、独立したコピーを返します
#   ]
#   引数: [
#     document: 正規skills JSONに相当する入力（Variant）
#     skill_id: 取得するスキルID（Variant）
#   ]
#   戻り値: [result: 独立したskill辞書、またはok=falseとreason（Dictionary）]
# }
static func prepare(document: Variant, skill_id: Variant) -> Dictionary:
	# カタログ全体を書き換えず、呼出元が指定した定義だけを対象にする。
	if not document is Dictionary or not document.get("skills") is Array:
		return _reject("invalid_skill_document")
	var version: Variant = document.get("schema_version")
	if not (version is int or version is float) or version != 1:
		return _reject("invalid_skill_document")
	if not skill_id is String or skill_id.is_empty():
		return _reject("invalid_skill_id")
	# 同じIDの複数定義から勝手に選ばず、一意性を確認する。
	var selected: Array = []
	for definition: Variant in document["skills"]:
		if definition is Dictionary and definition.get("id") is String and definition["id"] == skill_id:
			selected.append(definition)
	if selected.size() != 1:
		return _reject("skill_definition_missing_or_duplicate")
	return _validate_definition(selected[0])


# {
#   責務: [quote_damage: MP不足を判定し、資源を変更せず物理スキルの結果を予測する]
#   処理: [
#     1: スキル定義と予測要求を検証する
#     2: MP不足なら数値計算前に拒否する
#     3: 共通物理計算の結果へ残MPの予測を付ける
#   ]
#   引数: [
#     definition: prepareのskill、または同じ形式の定義（Variant）
#     request: 能力値・現在MP/HP・明示乱数・装備数値投影（Variant）
#   ]
#   戻り値: [result: ダメージと残MPの予測、または理由付き拒否（Dictionary）。実資源は更新しない]
# }
static func quote_damage(definition: Variant, request: Variant) -> Dictionary:
	# prepareを通さない呼出しでも、未対応効果を黙って無視しない。
	var validated := _validate_definition(definition)
	if not validated["ok"]:
		return validated
	var checked := _validate_quote(request)
	if not checked["ok"]:
		return checked
	var skill: Dictionary = validated["skill"]
	if checked["current_mp"] < skill["mp_cost"]:
		return _reject("insufficient_mp")
	# スキルIDをattackへ置き換えず、検証済み威力だけを共通計算へ渡す。
	var numbers: Dictionary = request.duplicate(true)
	numbers.merge({"power": skill["power"], "critical_multiplier": skill["critical_multiplier"]}, true)
	var equipment := {"power_multiplier": request.get("power_multiplier", 1.0),
		"fixed_bonus_damage": request.get("fixed_bonus_damage", 0)}
	var result := AttackNumbers.physical_damage(numbers, equipment)
	if not result["ok"]:
		return _reject("invalid_physical_numbers", result.get("message", ""))
	# remaining_mpは予測値であり、SessionのMP消費や行動権取得を代用しない。
	result.merge({"scope": "physical_skill_quote", "skill_id": skill["id"], "mp_cost": skill["mp_cost"],
		"remaining_mp": checked["current_mp"] - skill["mp_cost"]}, true)
	return result


# {
#   責務: [_validate_definition: 単体物理の対応範囲と有限数値を確認し、独立した定義へ正規化する]
#   処理: [
#     1: 名前・kind・未対応フィールドを検証する
#     2: Python互換の威力・会心倍率・MP整数を検証する
#     3: 副作用のない定義の写しを返す
#   ]
#   引数: [definition: 正の消費MPを持つ単体physicalのスキル定義（Variant）]
#   戻り値: [result: 正規化した独立skill、または不正/未対応を示す理由付き拒否（Dictionary）]
# }
static func _validate_definition(definition: Variant) -> Dictionary:
	# 未対応効果はfalseや空でも拒否し、通常攻撃と基本防御の入口を分ける。
	if not definition is Dictionary:
		return _reject("invalid_skill_definition")
	for field: Variant in definition:
		if field not in DEFINITION_FIELDS:
			return _reject("unsupported_physical_skill")
	if not definition.get("id") is String or definition["id"].is_empty() or definition["id"] in ["attack", "defend"]:
		return _reject("invalid_skill_id")
	if not definition.get("kind") is String or definition["kind"] != "physical":
		return _reject("unsupported_physical_skill")
	for field in ["display_name", "description"]:
		if definition.has(field) and not definition[field] is String:
			return _reject("invalid_skill_text")
	if not definition.has("display_name") or definition["display_name"].is_empty():
		return _reject("invalid_skill_text")
	# mp_costはPythonのintと同じ0方向切捨て。負値とゼロはこのMP付き単位の対象外。
	var cost := Numbers.integer_value(definition.get("mp_cost"))
	var power := Numbers.float_value(definition.get("power", 1.0))
	var critical := Numbers.float_value(definition.get("critical_multiplier", 1.0))
	if not cost["ok"] or cost["value"] <= 0 or not power["ok"] or not critical["ok"]:
		return _reject("invalid_physical_skill_numbers")
	var skill: Dictionary = definition.duplicate(true)
	skill.merge({"power": power["value"], "critical_multiplier": critical["value"], "mp_cost": cost["value"]}, true)
	return {"ok": true, "skill": skill}


# {
#   責務: [_validate_quote: 予測要求の未知キーと現在MPの正規整数を検証する]
#   処理: [1: 未対応の入力と不正なMPを拒否する]
#   引数: [request: 現在HPMP・能力値・物理乱数・装備数値を持つダメージ予測要求（Variant）]
#   戻り値: [result: 検証済み整数current_mp、または未知キー/不正MPを示す拒否（Dictionary）]
# }
static func _validate_quote(request: Variant) -> Dictionary:
	# 学習済みAI・装備JSON・状態効果をこの数値要求に混在させない。
	if not request is Dictionary:
		return _reject("invalid_quote_request")
	for field: Variant in request:
		if field not in QUOTE_FIELDS:
			return _reject("unsupported_quote_field")
	# 現在MPはStateの正規整数と同じ扱いにし、小数を切り捨てて不足を隠さない。
	var mp: Variant = request.get("current_mp")
	var checked := Numbers.integer_value(mp)
	if not (mp is int or mp is float) or not checked["ok"] or checked["value"] < 0 or checked["value"] != mp:
		return _reject("invalid_current_mp")
	return {"ok": true, "current_mp": checked["value"]}


# {
#   責務: [_reject: 物理定義/数値予測の失敗を、JSON互換の理由付き辞書として返します]
#   処理: [1: ok=falseとreason、数値検査から渡された補足messageを返します]
#   引数: [
#     reason: 呼出元が判別する拒否理由（String）
#     message: 数値検査の補足（String）
#   ]
#   戻り値: [result: ok=falseの辞書（Dictionary）]
# }
static func _reject(reason: String, message: String = "") -> Dictionary:
	# 未対応効果とMP不足を呼出元が区別できるよう、拒否理由を保持する。
	return {"ok": false, "reason": reason, "message": message}
