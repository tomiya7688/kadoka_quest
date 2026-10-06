# {
#   責務: [attack_numbers: 通常攻撃と物理スキルが共用する明示乱数のダメージ計算。状態更新とI/Oは行わない]
#   フィールド: []
# }
extends RefCounted
## Definition-specific callers share physical numbers without changing a skill's identity.

const Numbers = preload("res://engine/stat_numbers.gd")
const NORMAL_ATTACK_CRITICAL_CHANCE := 1.0 / 16.0
const VARIANCE_MIN := 0.92
const VARIANCE_MAX := 1.08
const DAMAGE_KINDS := ["physical", "magic", "drain_mp"]


# {
#   責務: [normal_attack: 明示乱数で通常攻撃の物理ダメージと実HP減少を計算する]
#   処理: [
#     1: 通常攻撃専用のID・kindと装備数値投影を検証する
#     2: 共通物理計算へ委譲し、通常攻撃のscopeを維持する
#   ]
#   引数: [request: 要求（Variant）]
#   戻り値: [result: 通常攻撃数値または理由付き拒否。状態や乱数源を所有しない]
# }
static func normal_attack(request: Variant) -> Dictionary:
	# 通常攻撃専用の入口を維持し、他のスキルをattackとして受け入れない。
	if not request is Dictionary:
		return _failure("通常攻撃の入力はオブジェクトです")
	if request.get("kind", "physical") != "physical" or request.get("skill_id", "attack") != "attack":
		return _failure("通常攻撃attackのphysical数値以外は未移植です")
	# 通常攻撃用の装備投影を検証してから、スキルIDを持たない共通数値処理へ委譲する。
	var equipment := _equipment_effect(request.get("equipment", {}))
	if not equipment["ok"]:
		return equipment
	var result := physical_damage(request, equipment)
	if result["ok"]:
		result["scope"] = "normal_attack_numbers"
	return result


# {
#   責務: [physical_damage: 定義検証済みの呼出元へ共通の物理ダメージ数値を返す]
#   処理: [
#     1: 能力値・倍率・乱数と投影済みの装備数値を検証する
#     2: 会心・防御・装備追加をPythonと同じ順序で計算する
#     3: 共通の最終ダメージ処理へ委譲する
#   ]
#   引数: [
#     request: 攻撃・防御・現在HP・明示乱数・倍率（Dictionary）
#     equipment: power_multiplierとfixed_bonus_damageだけの数値投影（Dictionary）
#   ]
#   戻り値: [result: ダメージ・実HP減少の予測と会心情報、または理由付き拒否（Dictionary）]
# }
static func physical_damage(request: Dictionary, equipment: Dictionary) -> Dictionary:
	# 値の変換規則は通常攻撃と物理スキルで共用し、演算前に有限性を確認する。
	var attack := Numbers.integer_value(request.get("attack"))
	var defense := Numbers.integer_value(request.get("defense"))
	var multiplier := Numbers.float_value(request.get("attack_multiplier", 1.0))
	var power := Numbers.float_value(request.get("power", 1.0))
	var critical_multiplier := Numbers.float_value(request.get("critical_multiplier", 1.0))
	var roll := Numbers.float_value(request.get("critical_roll"))
	if not attack["ok"] or not defense["ok"] or not multiplier["ok"] or not power["ok"] or not critical_multiplier["ok"]:
		return _failure("攻撃/防御/倍率が不正です")
	if not roll["ok"] or roll["value"] < 0.0 or roll["value"] >= 1.0:
		return _failure("会心乱数は0以上1未満です")
	var equipment_power := Numbers.float_value(equipment.get("power_multiplier", 1.0))
	var equipment_bonus := Numbers.integer_value(equipment.get("fixed_bonus_damage", 0))
	if not equipment_power["ok"] or not equipment_bonus["ok"]:
		return _failure("装備の威力倍率/固定追加値が不正です")
	# 攻撃倍率の切捨ては威力と掛ける前に行い、Pythonの演算順を保つ。
	var effective_attack := Numbers.integer_value(attack["value"] * multiplier["value"])
	var effective_power := Numbers.float_value(power["value"] * equipment_power["value"])
	if not effective_attack["ok"] or not effective_power["ok"]:
		return _failure("攻撃/威力の演算が精度範囲外です")
	# Python uses min(1, chance * multiplier), not a lower clamp.
	var chance := minf(1.0, NORMAL_ATTACK_CRITICAL_CHANCE * critical_multiplier["value"])
	var critical: bool = roll["value"] < chance
	var raw: float = effective_attack["value"] * effective_power["value"]
	if not critical:
		raw -= maxi(0, defense["value"]) * 0.42
	# 固定追加は基礎値の切捨て後に適用し、その後でguardと揺らぎを適用する。
	var truncated := Numbers.integer_value(raw)
	if not truncated["ok"]:
		return _failure("基礎ダメージの演算が精度範囲外です")
	var with_bonus := Numbers.integer_value(truncated["value"] + equipment_bonus["value"])
	if not with_bonus["ok"]:
		return _failure("追加ダメージの演算が精度範囲外です")
	var result := finish_damage({"kind": "physical", "damage": with_bonus["value"],
		"guard": request.get("guard", 1.0), "variance": request.get("variance"), "target_hp": request.get("target_hp")})
	if not result["ok"]:
		return result
	result.merge({"scope": "physical_damage_numbers", "critical": critical, "critical_chance": chance,
		"effective_attack": effective_attack["value"], "effective_power": effective_power["value"]}, true)
	return result


# {
#   責務: [defend_multiplier: 攻撃・numbersのdefend・multiplierを求める]
#   処理: [1: 攻撃・numbersのdefend・multiplierを求める]
#   引数: [definition: 定義（Variant）]
#   戻り値: [result: 攻撃・numbersのdefend・multiplierを求めるための結果（Dictionary）]
# }
static func defend_multiplier(definition: Variant = {}) -> Dictionary:
	# 基本防御の倍率だけを読み、特殊防御の行動実装を代用しない。
	if not definition is Dictionary or definition.get("kind", "defend") != "defend":
		return _failure("防御倍率にはdefend定義が必要です")
	var value := Numbers.float_value(definition.get("damage_multiplier", 0.5))
	if not value["ok"]:
		return _failure("防御倍率が不正です")
	return {"ok": true, "guard": value["value"], "scope": "defend_multiplier_only"}


# {
#   責務: [finish_damage: 物理限定guard・揺らぎ・最低1・残HP上限の数値契約を適用する]
#   処理: [
#     1: 入力kind・有限値・乱数範囲を検証する
#     2: physicalだけguardを適用し、最終ダメージと残HPを求める
#   ]
#   引数: [request: 要求（Variant）]
#   戻り値: [result: damage/dealt/remaining_hp/applied_guardまたは拒否結果。魔法や耐性の完全実装ではない]
# }
static func finish_damage(request: Variant) -> Dictionary:
	# Only the final positive-damage path; this does not implement magic, resistance or absorption.
	if not request is Dictionary or request.get("kind") not in DAMAGE_KINDS:
		return _failure("最終ダメージにはphysical/magic/drain_mpの数値入力が必要です")
	var damage := Numbers.integer_value(request.get("damage"))
	var guard := Numbers.float_value(request.get("guard", 1.0))
	var variance := Numbers.float_value(request.get("variance"))
	var hp := Numbers.integer_value(request.get("target_hp"))
	if not damage["ok"] or not guard["ok"] or not hp["ok"] or hp["value"] < 0:
		return _failure("ダメージ/防御倍率/現在HPが不正です")
	if not variance["ok"] or variance["value"] < VARIANCE_MIN or variance["value"] > VARIANCE_MAX:
		return _failure("ダメージ乱数は0.92以上1.08以下です")
	var applied_guard: float = guard["value"] if request["kind"] == "physical" else 1.0
	var adjusted := Numbers.integer_value(damage["value"] * applied_guard * variance["value"])
	if not adjusted["ok"]:
		return _failure("最終ダメージの演算が精度範囲外です")
	var final_damage := maxi(1, adjusted["value"])
	var remaining := maxi(0, hp["value"] - final_damage)
	return {"ok": true, "scope": "positive_damage_finalization", "raw_damage": damage["value"],
		"damage": final_damage, "dealt": hp["value"] - remaining, "remaining_hp": remaining,
		"applied_guard": applied_guard, "variance": variance["value"]}


# {
#   責務: [_equipment_effect: 攻撃・numbersの装備・効果を求める]
#   処理: [1: 攻撃・numbersの装備・効果を求める]
#   引数: [definition: 定義（Variant）]
#   戻り値: [result: 攻撃・numbersの装備・効果を求めるための結果（Dictionary）]
# }
static func _equipment_effect(definition: Variant) -> Dictionary:
	# 通常攻撃専用の投影。別スキルの補正をここから借用しない。
	if definition == null:
		definition = {}
	if not definition is Dictionary:
		return _failure("装備の数値効果はオブジェクトです")
	var modifiers: Variant = definition.get("skill_modifiers", {})
	if not modifiers is Dictionary or not modifiers.get("attack", {}) is Dictionary:
		return _failure("装備のattack威力補正が不正です")
	# 共通計算へは装備JSONを渡さず、必要な有限数値だけを渡す。
	var power := Numbers.float_value(modifiers.get("attack", {}).get("power_multiplier", 1.0))
	var bonus := Numbers.integer_value(definition.get("fixed_bonus_damage", 0))
	if not power["ok"] or not bonus["ok"]:
		return _failure("装備のattack威力倍率/固定追加値が不正です")
	return {"ok": true, "power_multiplier": power["value"], "fixed_bonus_damage": bonus["value"]}


# {
#   責務: [_failure: 攻撃・numbersのfailureを求める]
#   処理: [1: 攻撃・numbersのfailureを求める]
#   引数: [message: message（String）]
#   戻り値: [result: 攻撃・numbersのfailureを求めるための結果（Dictionary）]
# }
static func _failure(message: String) -> Dictionary:
	return {"ok": false, "error": "invalid_attack_numbers", "message": message}
