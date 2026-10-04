extends RefCounted
## Normal-attack and physical-only guard numbers. Explicit random inputs; no battle state or I/O.

const Numbers = preload("res://engine/stat_numbers.gd")
const NORMAL_ATTACK_CRITICAL_CHANCE := 1.0 / 16.0
const VARIANCE_MIN := 0.92
const VARIANCE_MAX := 1.08
const DAMAGE_KINDS := ["physical", "magic", "drain_mp"]


static func normal_attack(request: Variant) -> Dictionary:
	if not request is Dictionary:
		return _failure("通常攻撃の入力はオブジェクトです")
	if request.get("kind", "physical") != "physical" or request.get("skill_id", "attack") != "attack":
		return _failure("通常攻撃attackのphysical数値以外は未移植です")
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
	var equipment := _equipment_effect(request.get("equipment", {}))
	if not equipment["ok"]:
		return equipment
	var effective_attack := Numbers.integer_value(attack["value"] * multiplier["value"])
	var effective_power := Numbers.float_value(power["value"] * equipment["power_multiplier"])
	if not effective_attack["ok"] or not effective_power["ok"]:
		return _failure("攻撃/威力の演算が精度範囲外です")
	# Python uses min(1, chance * multiplier), not a lower clamp.
	var chance := minf(1.0, NORMAL_ATTACK_CRITICAL_CHANCE * critical_multiplier["value"])
	var critical: bool = roll["value"] < chance
	var raw: float = effective_attack["value"] * effective_power["value"]
	if not critical:
		raw -= maxi(0, defense["value"]) * 0.42
	var truncated := Numbers.integer_value(raw)
	if not truncated["ok"]:
		return _failure("基礎ダメージの演算が精度範囲外です")
	var with_bonus := Numbers.integer_value(truncated["value"] + equipment["fixed_bonus_damage"])
	if not with_bonus["ok"]:
		return _failure("追加ダメージの演算が精度範囲外です")
	var result := finish_damage({"kind": "physical", "damage": with_bonus["value"],
		"guard": request.get("guard", 1.0), "variance": request.get("variance"), "target_hp": request.get("target_hp")})
	if not result["ok"]:
		return result
	result.merge({"scope": "normal_attack_numbers", "critical": critical, "critical_chance": chance,
		"effective_attack": effective_attack["value"], "effective_power": effective_power["value"]}, true)
	return result


static func defend_multiplier(definition: Variant = {}) -> Dictionary:
	if not definition is Dictionary or definition.get("kind", "defend") != "defend":
		return _failure("防御倍率にはdefend定義が必要です")
	var value := Numbers.float_value(definition.get("damage_multiplier", 0.5))
	if not value["ok"]:
		return _failure("防御倍率が不正です")
	return {"ok": true, "guard": value["value"], "scope": "defend_multiplier_only"}


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


static func _equipment_effect(definition: Variant) -> Dictionary:
	if definition == null:
		definition = {}
	if not definition is Dictionary:
		return _failure("装備の数値効果はオブジェクトです")
	var modifiers: Variant = definition.get("skill_modifiers", {})
	if not modifiers is Dictionary or not modifiers.get("attack", {}) is Dictionary:
		return _failure("装備のattack威力補正が不正です")
	var power := Numbers.float_value(modifiers.get("attack", {}).get("power_multiplier", 1.0))
	var bonus := Numbers.integer_value(definition.get("fixed_bonus_damage", 0))
	if not power["ok"] or not bonus["ok"]:
		return _failure("装備のattack威力倍率/固定追加値が不正です")
	return {"ok": true, "power_multiplier": power["value"], "fixed_bonus_damage": bonus["value"]}


static func _failure(message: String) -> Dictionary:
	return {"ok": false, "error": "invalid_attack_numbers", "message": message}
