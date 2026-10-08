# {
#   責務: [drain_mp_skill_contract: 吸MP付き単体魔法の敵HP・敵MP・術者の残MPを、入力を変更せず予測します]
#   フィールド: []
# }
extends RefCounted

const Numbers = preload("res://engine/stat_numbers.gd")
const MagicContract = preload("res://engine/magic_skill_contract.gd")


# {
#   責務: [prepare: 一覧から指定IDの一意な吸MPスキルを選び、対応効果と数値を検証します]
#   処理: [
#     1: 共用の一覧選択でIDの欠落・重複を拒否します
#     2: 吸MP定義を検証して原本と独立した定義を返します
#   ]
#   引数: [
#     document: schema_version=1とskills配列を持つスキル一覧（Variant）
#     skill_id: 使用する空でない文字列ID（Variant）
#   ]
#   戻り値: [result: ok=trueと独立したskill、または理由付き拒否（Dictionary）]
# }
static func prepare(document: Variant, skill_id: Variant) -> Dictionary:
	# 一覧の選択だけを共用し、通常魔法へ吸MPの対応範囲を広げない。
	var selected := MagicContract.select_definition(document, skill_id)
	if not selected["ok"]:
		return selected
	return _validate_definition(selected["skill"])


# {
#   責務: [quote_damage: 吸MP魔法の対象HP効果と、MP消費後の吸収・回復・残MPを予測します]
#   処理: [
#     1: 定義と両者のMP資源を検証します
#     2: 通常魔法の契約で敵HPとMP消費後の資源を予測します
#     3: 敵MP喪失と術者MP回復を別々に予測して結果へ加えます
#   ]
#   引数: [
#     definition: kind=drain_mpと正のmp_costを持つ単体スキル定義。mp_power省略時は0.12（Variant）
#     request: 通常魔法の数値要求にactor_max_mpとtarget_mpを加えた辞書（Variant）
#   ]
#   戻り値: [result: ok=trueとHP/MP予測、または理由付き拒否。実資源は変更しません（Dictionary）]
# }
static func quote_damage(definition: Variant, request: Variant) -> Dictionary:
	# prepareを省略しても、不正な定義や資源を補修して成功扱いしない。
	var validated := _validate_definition(definition)
	if not validated["ok"]:
		return validated
	var resources := _validate_resources(request)
	if not resources["ok"]:
		return resources
	# 対応する吸MPキーだけを分離し、未知キーは通常魔法の厳密な検証へ残す。
	var skill: Dictionary = validated["skill"].duplicate(true)
	skill.erase("mp_power")
	skill["kind"] = "magic"
	var magic_request: Dictionary = request.duplicate(true)
	magic_request.erase("actor_max_mp")
	magic_request.erase("target_mp")
	var result := MagicContract.quote_damage(skill, magic_request)
	if not result["ok"]:
		return result
	var transfer := _predict_transfer(validated["skill"], request, resources, result)
	if not transfer["ok"]:
		return transfer
	# remaining_mpは支払い後ではなく吸収後。支払い直後の値も別名で保持する。
	result.merge(transfer, true)
	result["scope"] = "drain_mp_skill_quote"
	return result


# {
#   責務: [_validate_definition: 吸MP区分と有限mp_powerを検証し、その他の魔法効果の検証を共用します]
#   処理: [
#     1: kind=drain_mpと有限mp_powerを確認します
#     2: 既知の区分と吸MPキーだけを分離して通常魔法の定義検証へ渡します
#     3: 独立定義へ吸MP区分と正規化したmp_powerを戻します
#   ]
#   引数: [definition: 選択または直接指定した吸MP付き定義（Variant）]
#   戻り値: [result: 独立した検証済みskill、または理由付き拒否（Dictionary）]
# }
static func _validate_definition(definition: Variant) -> Dictionary:
	# kindを検証せず書き換えると、未対応の効果を通常魔法として成功させてしまう。
	if not definition is Dictionary:
		return _reject("invalid_skill_definition")
	if not definition.get("kind") is String or definition["kind"] != "drain_mp":
		return _reject("unsupported_drain_mp_skill")
	var power := Numbers.float_value(definition.get("mp_power", 0.12))
	if not power["ok"]:
		return _reject("invalid_drain_mp_power")
	var base_definition: Dictionary = definition.duplicate(true)
	base_definition.erase("mp_power")
	base_definition["kind"] = "magic"
	var validated := MagicContract.prepare({"schema_version": 1, "skills": [base_definition]}, base_definition.get("id"))
	if not validated["ok"]:
		return validated
	# 未対応効果を捨てずに検証した後で、吸MPとして使う独立定義だけを作る。
	validated["skill"].merge({"kind": "drain_mp", "mp_power": power["value"]}, true)
	return validated


# {
#   責務: [_validate_resources: 術者の現在MP/最大MPと敵MPが非負の正規整数で整合するか確認します]
#   処理: [
#     1: 文字列・bool・小数部分・非有限値・整数精度超過を拒否します
#     2: 術者の現在MPが最大MPを超えていないか確認します
#   ]
#   引数: [request: current_mp・actor_max_mp・target_mpを持つ数値要求（Variant）]
#   戻り値: [result: 正規化したMP資源、または理由付き拒否（Dictionary）]
# }
static func _validate_resources(request: Variant) -> Dictionary:
	# MPの小数切捨てで不正資源を隠さない。最大MP0も資源値としては許可する。
	if not request is Dictionary:
		return _reject("invalid_quote_request")
	var resources := {"ok": true}
	for field in ["current_mp", "actor_max_mp", "target_mp"]:
		var value: Variant = request.get(field)
		var checked := Numbers.integer_value(value)
		if not (value is int or value is float) or not checked["ok"] or checked["value"] != value or checked["value"] < 0:
			return _reject("invalid_drain_mp_resources")
		resources[field] = checked["value"]
	if resources["current_mp"] > resources["actor_max_mp"]:
		return _reject("invalid_drain_mp_resources")
	return resources


# {
#   責務: [_predict_transfer: 耐性で吸MP可否を決め、敵のMP喪失と術者のMP回復を別々の上限で予測します]
#   処理: [
#     1: 無効・吸収耐性ならMP吸収を行わず、その他では魔力とmp_powerから上限を求めます
#     2: 敵MPを上限として奪い、MP消費後の術者最大MPまで回復します
#     3: 算出した吸MP上限量・実喪失・実回復・残資源を返します
#   ]
#   引数: [
#     skill: 検証済みの有限mp_powerを持つ吸MP定義（Dictionary）
#     request: 魔法予測で検証済みのmagicを持つ数値要求（Dictionary）
#     resources: 検証済みの術者最大MPと敵現在MP（Dictionary）
#     hp_quote: 敵HP効果・耐性・支払い後remaining_mpの通常魔法予測（Dictionary）
#   ]
#   戻り値: [result: MP吸収後の予測値、または演算精度超過による拒否（Dictionary）]
# }
static func _predict_transfer(skill: Dictionary, request: Dictionary, resources: Dictionary, hp_quote: Dictionary) -> Dictionary:
	# 敵のHP0・最低HPダメージ・揺らぎ・装備加算はMP吸収量を変更しない。
	var blocked: bool = hp_quote["resistance_kind"] in ["immune", "absorb"]
	var limit := 0
	if not blocked:
		var magic := Numbers.integer_value(request["magic"])
		var amount := Numbers.integer_value(magic["value"] * skill["mp_power"])
		if not amount["ok"]:
			return _reject("invalid_drain_mp_numbers")
		limit = maxi(1, amount["value"])
	var drained: int = mini(resources["target_mp"], limit)
	var paid_mp: int = hp_quote["remaining_mp"]
	# 精度超過する加算を先に行わず、最大MPまでの空き量で回復を制限する。
	var recovered: int = mini(drained, resources["actor_max_mp"] - paid_mp)
	return {"ok": true, "mp_power": skill["mp_power"], "mp_drain_blocked": blocked,
		"mp_drain_limit": limit, "drained_mp": drained, "recovered_mp": recovered,
		"remaining_target_mp": resources["target_mp"] - drained, "mp_after_payment": paid_mp,
		"remaining_mp": paid_mp + recovered}


# {
#   責務: [_reject: 吸MP定義・資源・精度の失敗を、成立した予測と区別できる結果へ変換します]
#   処理: [1: ok=falseと具体的な拒否理由を返します]
#   引数: [reason: 定義・資源・数値を拒否した理由（String）]
#   戻り値: [result: ok=falseとreasonの辞書（Dictionary）]
# }
static func _reject(reason: String) -> Dictionary:
	# 原本の補修や未対応効果の省略で、失敗を成功へ置き換えない。
	return {"ok": false, "reason": reason}
