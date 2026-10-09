# {
#   責務: [combatant_state: 戦闘個体一体の現在HP/MPと生死・逃走状態を所有し、保存・行動順・AI判断は担当しません]
#   フィールド: [
#     _identity: 戦闘個体のid・species_id・name（Dictionary）
#     _stats: 最大HP/MPを含む戦闘用の6能力値（Dictionary）
#     _hp: 戦闘個体の現在HP（int）
#     _mp: 戦闘個体の現在MP（int）
#     _fled: 戦闘個体が逃走済みかどうか（bool）
#     _initialized: 戦闘個体の初期資源を設定済みかどうか（bool）
#   ]
# }
extends RefCounted
## combatant_stateは戦闘個体一体の数値資源を保持し、保存・行動順・AI判断は行いません。

const Records = preload("res://engine/monster_record_contract.gd")
const MAX_EXACT_INTEGER := 9007199254740991
const STAT_KEYS := ["hp", "mp", "attack", "defense", "magic", "speed"]
var _identity: Dictionary = {}
var _stats: Dictionary = {}
var _hp := 0
var _mp := 0
var _fled := false
var _initialized := false


# {
#   責務: [start: 個体情報と基礎能力値を検証し、未開始の戦闘個体を最大HP・MPで一度だけ初期化します]
#   処理: [1: 個体情報と基礎能力値を検証し、未開始の戦闘個体を最大HP・MPで一度だけ初期化します]
#   引数: [
#     identity: 初期化する戦闘個体のid・species_id・name（Variant）
#     stats: 初期化する戦闘個体の最大HP/MPを含む6能力値（Variant）
#   ]
#   戻り値: [result: 初期化の成功と独立した状態、またはok=falseと拒否理由（Dictionary）]
# }
func start(identity: Variant, stats: Variant) -> Dictionary:
	if _initialized:
		return _failure("already_initialized")
	var checked := _validate_initial(identity, stats)
	if not checked["ok"]:
		return checked
	_identity = {"id": identity["id"], "species_id": identity["species_id"], "name": identity["name"]}
	for key in STAT_KEYS:
		_stats[key] = int(stats[key])
	_hp = _stats["hp"]
	_mp = _stats["mp"]
	_initialized = true
	return {"ok": true, "snapshot": snapshot()}


# {
#   責務: [snapshot: combatant_state.gdの戦闘個体が所有する個体情報・能力値・現在HPとMP・逃走と生存状態を読み取り用に返します]
#   処理: [1: 初期化済みなら個体情報と能力値を複製し、未初期化なら空辞書を返します]
#   引数: []
#   戻り値: [result: identity・stats・hp・mp・fled・aliveを持つ内部状態と独立した辞書、または未初期化の空辞書（Dictionary）]
# }
func snapshot() -> Dictionary:
	if not _initialized:
		return {}
	return {"identity": _identity.duplicate(true), "stats": _stats.duplicate(true),
		"hp": _hp, "mp": _mp, "fled": _fled, "alive": alive()}


# {
#   責務: [alive: 戦闘個体が初期化済み・HP正・未逃走のすべてを満たすか返します]
#   処理: [1: 戦闘個体が初期化済み・HP正・未逃走のすべてを満たすか返します]
#   引数: []
#   戻り値: [result: 初期化済み・HP正・未逃走ならtrue、それ以外false（bool）]
# }
func alive() -> bool:
	return _initialized and _hp > 0 and not _fled


# {
#   責務: [take_damage: 非負整数のダメージを現在HPまで適用し、実ダメージと残HPを返します]
#   処理: [1: 非負整数のダメージを現在HPまで適用し、実ダメージと残HPを返します]
#   引数: [amount: 非負整数の要求ダメージ量（Variant）]
#   戻り値: [result: 要求量requested・実ダメージdealt・現在HPと生存判定、または理由付き拒否（Dictionary）]
# }
func take_damage(amount: Variant) -> Dictionary:
	if not _initialized:
		return _failure("not_initialized")
	if not _nonnegative_integer(amount):
		return _failure("invalid_damage")
	var previous := _hp
	var dealt := mini(_hp, int(amount))
	_hp -= dealt
	return {"ok": true, "requested": int(amount), "previous_hp": previous,
		"dealt": dealt, "hp": _hp, "alive": alive()}


# {
#   責務: [mp_cost: 消費量を検証し、現在MPで支払えるか資源更新なしで返します]
#   処理: [1: 消費量を検証し、現在MPで支払えるか資源更新なしで返します]
#   引数: [cost: 戦闘個体の現在MPから支払う、非負整数の消費要求量（Variant）]
#   戻り値: [result: 要求消費量cost・支払い可否affordable・現在mp、または理由付き拒否（Dictionary）]
# }
func mp_cost(cost: Variant) -> Dictionary:
	if not _initialized:
		return _failure("not_initialized")
	if not _nonnegative_integer(cost):
		return _failure("invalid_mp_cost")
	return {"ok": true, "cost": int(cost), "affordable": int(cost) <= _mp, "mp": _mp}


# {
#   責務: [heal: 非負整数の回復量を現在HPへ加え、最大HPで止めます]
#   処理: [1: 初期化と回復量を確認し、最大HPとの差分まで回復して実回復量を返します]
#   引数: [amount: 安全な範囲の非負整数として扱える回復要求量（Variant）]
#   戻り値: [result: 要求量requested・実回復量healed・現在hp、または理由付き拒否（Dictionary）]
# }
func heal(amount: Variant) -> Dictionary:
	# 数値資源だけを更新する。逃走状態は解除せず、教会復活や勝敗判定も行わない。
	if not _initialized:
		return _failure("not_initialized")
	if not _nonnegative_integer(amount):
		return _failure("invalid_healing")
	var previous := _hp
	var healed := mini(_stats["hp"] - _hp, int(amount))
	_hp += healed
	return {"ok": true, "requested": int(amount), "previous_hp": previous,
		"healed": healed, "hp": _hp, "alive": alive()}


# {
#   責務: [pay_mp: 支払える非負整数の消費量だけMPから引き、不足時はMPを保持します]
#   処理: [1: 支払える非負整数の消費量だけMPから引き、不足時はMPを保持します]
#   引数: [cost: 戦闘個体の現在MPから支払う、非負整数の消費要求量（Variant）]
#   戻り値: [result: 実消費量spent・現在mp、または資源を保持した不足や不正入力の拒否（Dictionary）]
# }
func pay_mp(cost: Variant) -> Dictionary:
	var checked := mp_cost(cost)
	if not checked["ok"]:
		return checked
	if not checked["affordable"]:
		return {"ok": false, "reason": "insufficient_mp", "cost": int(cost),
			"affordable": false, "spent": 0, "mp": _mp}
	_mp -= int(cost)
	return {"ok": true, "cost": int(cost), "affordable": true, "spent": int(cost), "mp": _mp}


# {
#   責務: [restore_mp: 非負整数のMP回復量を最大MPまで適用し、HPと逃走状態を変更しません]
#   処理: [
#     1: 初期化と回復量の正規整数形式を確認します
#     2: 最大MPまでの空き量で回復を制限し、実回復量と残MPを返します
#   ]
#   引数: [amount: 精度上限以内の非負整数のMP回復要求量（Variant）]
#   戻り値: [result: requested・previous_mp・restored・現在mp・alive、または資源を保持した拒否（Dictionary）]
# }
func restore_mp(amount: Variant) -> Dictionary:
	# 数値資源だけを更新します。HP0の復活や逃走解除、行動の許可は行いません。
	if not _initialized:
		return _failure("not_initialized")
	if not _nonnegative_integer(amount):
		return _failure("invalid_mp_recovery")
	var previous := _mp
	# 精度上限近傍でも、回復要求量との加算前に最大MPまでの空き量で制限します。
	var restored := mini(_stats["mp"] - _mp, int(amount))
	_mp += restored
	return {"ok": true, "requested": int(amount), "previous_mp": previous,
		"restored": restored, "mp": _mp, "alive": alive()}


# {
#   責務: [flee: HPとMPを保持したまま戦闘個体を逃走済みにし、生存判定から除外します]
#   処理: [1: HPとMPを保持したまま戦闘個体を逃走済みにし、生存判定から除外します]
#   引数: []
#   戻り値: [result: 逃走更新の結果・現在HP/MP・生存判定、または未初期化の拒否（Dictionary）]
# }
func flee() -> Dictionary:
	if not _initialized:
		return _failure("not_initialized")
	var changed := not _fled
	_fled = true
	return {"ok": true, "changed": changed, "alive": alive(), "hp": _hp, "mp": _mp}


# {
#   責務: [living: 戦闘資源の列を検証し、HPが正で未逃走の個体だけを独立コピーで返します]
#   処理: [1: 戦闘資源の列を検証し、HPが正で未逃走の個体だけを独立コピーで返します]
#   引数: [snapshots: identity・stats・hp・mp・fled・aliveを持つ戦闘個体の資源列（Variant）]
#   戻り値: [result: 生存個体の独立コピー列members、または拒否理由と失敗位置index（Dictionary）]
# }
static func living(snapshots: Variant) -> Dictionary:
	if not snapshots is Array:
		return _failure("invalid_members")
	var members: Array = []
	var ids: Dictionary = {}
	for index in snapshots.size():
		var member: Variant = snapshots[index]
		var checked := _validate_snapshot(member)
		if not checked["ok"]:
			checked["index"] = index
			return checked
		var id: String = member["identity"]["id"]
		if ids.has(id):
			return {"ok": false, "reason": "duplicate_member", "index": index}
		ids[id] = true
		if member["alive"]:
			members.append(member.duplicate(true))
	return {"ok": true, "members": members}


# {
#   責務: [_validate_snapshot: 資源6キーの構造・HP/MP上限・生存フラグの整合性を検証します]
#   処理: [1: 資源6キーの構造・HP/MP上限・生存フラグの整合性を検証します]
#   引数: [value: 構造と現在資源を確認する戦闘個体snapshot（Variant）]
#   戻り値: [result: 形式検証の成功ok、または戦闘資源の不正を示すreason（Dictionary）]
# }
static func _validate_snapshot(value: Variant) -> Dictionary:
	if not value is Dictionary:
		return _failure("invalid_snapshot")
	var initial := _validate_initial(value.get("identity"), value.get("stats"))
	if not initial["ok"]:
		return initial
	if not _nonnegative_integer(value.get("hp")) or not _nonnegative_integer(value.get("mp")):
		return _failure("invalid_runtime_resources")
	if value["hp"] > value["stats"]["hp"] or value["mp"] > value["stats"]["mp"]:
		return _failure("resources_exceed_maximum")
	if not value.get("fled") is bool or not value.get("alive") is bool:
		return _failure("invalid_alive_flags")
	if value["alive"] != (value["hp"] > 0 and not value["fled"]):
		return _failure("inconsistent_alive")
	return {"ok": true}


# {
#   責務: [_validate_initial: 安全な個体IDと非負整数の6能力値を検証し、最大HPが正であることを確認します]
#   処理: [1: 安全な個体IDと非負整数の6能力値を検証し、最大HPが正であることを確認します]
#   引数: [
#     identity: 空でないid・species_id・nameを持つ戦闘個体情報（Variant）
#     stats: 非負整数の6能力値を持ち、最大HPは正とする戦闘用能力値（Variant）
#   ]
#   戻り値: [result: 初期情報の検証成功ok、または不正ID・能力値を示すreason（Dictionary）]
# }
static func _validate_initial(identity: Variant, stats: Variant) -> Dictionary:
	if not identity is Dictionary:
		return _failure("invalid_identity")
	for key in ["id", "species_id", "name"]:
		if not identity.get(key) is String or identity[key].is_empty():
			return _failure("invalid_identity_" + key)
	if not Records.safe_id(identity["id"]) or not Records.safe_id(identity["species_id"]):
		return _failure("unsafe_identity")
	if not stats is Dictionary:
		return _failure("invalid_stats")
	for key in STAT_KEYS:
		if not _nonnegative_integer(stats.get(key)):
			return _failure("invalid_stat_" + key)
	if stats["hp"] == 0:
		return _failure("invalid_max_hp")
	return {"ok": true}


# {
#   責務: [_nonnegative_integer: 値が有限で精度上限以内の非負整数値か確認し、boolや数値文字列を拒否します]
#   処理: [1: 値が有限で精度上限以内の非負整数値か確認し、boolや数値文字列を拒否します]
#   引数: [value: 正規整数の形式と有限性・精度範囲を確認する候補値（Variant）]
#   戻り値: [result: 有限で精度上限以内の非負整数値ならtrue、bool・文字列・不正値ならfalse（bool）]
# }
static func _nonnegative_integer(value: Variant) -> bool:
	return (value is int or value is float) and is_finite(float(value)) \
		and float(value) >= 0 and float(value) <= MAX_EXACT_INTEGER and float(value) == floorf(float(value))


# {
#   責務: [_failure: 戦闘資源を変更せず、ok=falseと指定した拒否理由を返します]
#   処理: [1: 戦闘資源を変更せず、ok=falseと指定した拒否理由を返します]
#   引数: [reason: 初期化・資源形式・数値操作を拒否した理由（String）]
#   戻り値: [result: ok=falseと指定した拒否理由reasonを持つ辞書（Dictionary）]
# }
static func _failure(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
