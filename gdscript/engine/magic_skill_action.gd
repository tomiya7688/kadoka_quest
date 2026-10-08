# {
#   責務: [magic_skill_action: 最新予約と資源を検証し、単体魔法のMP消費・HP効果・専用追加効果を一度だけ適用します]
#   フィールド: [
#     _session: 戦闘資源と行動予約を所有するSession（RefCounted）
#     _context: 開始時の習得・装備・耐性・定義の独立情報（Dictionary）
#     _self_damage: trueなら自傷付き単体魔法だけを受け付ける、構築時固定の区分（bool）
#     _drain_mp: trueなら吸MP付き単体魔法だけを受け付ける、構築時固定の区分（bool）
#     _quote: 区分に対応した非破壊の魔法予測処理（GDScript）
#     _scope: 構築時の魔法区分を示す実適用結果の範囲名（String）
#   ]
# }
extends RefCounted
const Context = preload("res://engine/magic_skill_context.gd")
const Quote = preload("res://engine/magic_skill_contract.gd")
const SelfDamageQuote = preload("res://engine/self_damage_magic_contract.gd")
const DrainMpQuote = preload("res://engine/drain_mp_skill_contract.gd")
const Order = preload("res://engine/turn_order.gd")
const Numbers = preload("res://engine/stat_numbers.gd")
const REQUEST_FIELDS := ["ticket", "target", "skill_id", "variance"]
var _session: RefCounted
var _context: Dictionary = {}
var _self_damage: bool
var _drain_mp: bool
var _quote: GDScript
var _scope := "explicit_magic_skill_only"

# {
#   責務: [_init: HP・MP・行動予約の更新先Sessionと、通常/自傷/吸MPの魔法区分を固定します]
#   処理: [
#     1: 資源を複製せず、更新先のSession参照を設定します
#     2: 構築時の魔法区分に対応する純粋予測処理を選択します
#   ]
#   引数: [
#     session: 戦闘資源と行動予約の所有者（RefCounted）
#     self_damage: trueなら自傷専用。falseなら自傷を扱わず、drain_mp=falseの場合は通常魔法専用です（bool）
#     drain_mp: trueなら吸MP専用。self_damageとの同時指定はstartで拒否します（bool）
#   ]
#   戻り値: [result: なし（void）]
# }
func _init(session: RefCounted, self_damage: bool = false, drain_mp: bool = false) -> void:
	_session = session
	# 行動要求で区分を変更させず、定義検証と数値予測に同じ区分を使う。
	_self_damage = self_damage
	_drain_mp = drain_mp
	_quote = Quote
	if self_damage:
		_quote = SelfDamageQuote
		_scope = "explicit_self_damage_magic_only"
	elif drain_mp:
		_quote = DrainMpQuote
		_scope = "explicit_drain_mp_magic_only"

# {
#   責務: [start: 新鮮なSessionと一致する魔法用の開始情報を一度だけ設定します]
#   処理: [1: 初期化時点・開始情報・資源の一致を確認して独立情報を保持します]
#   引数: [
#     teams: 戦闘資源・習得・許可装備・耐性を持つ両陣営（Variant）
#     skills: 正規スキル一覧（Variant）
#   ]
#   戻り値: [result: 設定成功または理由付き拒否（Dictionary）]
# }
func start(teams: Variant, skills: Variant) -> Dictionary:
	# 自傷と吸MPの複合効果は今回の予測契約に含まれず、片方だけ実行する設定を拒否します。
	if _self_damage and _drain_mp:
		return _reject("invalid_magic_mode")
	# 消費済み資源や開始後の定義差替えは受け付けない。
	if not _context.is_empty():
		return _reject("already_initialized")
	if _session.snapshot()["phase"] != "between_rounds":
		return _reject("session_not_fresh")
	var checked := Context.prepare(teams, skills)
	if not checked["ok"]:
		return checked
	if checked["snapshots"] != _session.snapshot()["teams"]:
		return _reject("magic_context_mismatch")
	_context = checked["context"]
	return {"ok": true, "scope": _scope}

# {
#   責務: [resolve: 単体魔法のMP消費・敵HP効果・区分専用のHP代償またはMP移転・予約完了を同期実行します]
#   処理: [
#     1: 最新状態と要求を資源更新なしで検証します
#     2: 予約を一度だけ取得し、行動不可なら資源を消費せず取り消します
#     3: MP消費・敵HP効果・区分専用のHP代償またはMP移転の順に担当資源処理を呼び、予約を完了します
#   ]
#   引数: [request: ticket・敵target・skill_id・varianceの4キーを持つ要求（Variant）]
#   戻り値: [result: 実行結果とSessionコピー、または理由付き拒否（Dictionary）]
# }
func resolve(request: Variant) -> Dictionary:
	# 不正要求やMP不足は予約取得前に返し、同じ予約で別行動を選択できるようにする。
	var checked := _validate(request)
	if not checked["ok"]:
		return checked
	# 検証からfinishまでawaitやcallbackを挟まず、途中の外部更新を許さない。
	var claimed: Dictionary = _session.claim(request["ticket"])
	if not claimed["ok"]:
		return claimed
	if not claimed["can_execute"]:
		return {"ok": true, "executed": false, "reason": claimed["reason"], "session": claimed["session"]}
	var numbers: Dictionary = checked["numbers"]
	# 敵の効果より先に支払い、無効・満タン吸収でもMP消費を省略しない。
	var paid: Dictionary = _session.pay_mp(request["ticket"]["actor"], numbers["mp_cost"])
	if not paid["ok"]:
		return _reject("action_payment_failed")
	var applied: Dictionary
	# 吸収は負のダメージとして渡さず、Sessionの最大HPで止まる回復へ委譲する。
	if numbers["resistance_kind"] == "absorb":
		applied = _session.heal(request["target"], numbers["recovery"])
	else:
		applied = _session.take_damage(request["target"], numbers["damage"])
	if not applied["ok"]:
		return _reject("action_application_failed")
	# 敵を倒した場合や敵が無効・吸収の場合も、終了判定の前に術者の実減少だけを支払う。
	if _self_damage:
		var cost: Dictionary = _session.take_damage(request["ticket"]["actor"], numbers["self_dealt"])
		if not cost["ok"]:
			return _reject("action_self_damage_failed")
	# 最後の敵を倒してもMP移転を省略せず、終了処理より前に担当資源処理へ委譲します。
	var transfer: Dictionary = {}
	if _drain_mp:
		transfer = _apply_drain_mp(request["ticket"]["actor"], request["target"], numbers)
		if not transfer["ok"]:
			return transfer
	var finished: Dictionary = _session.finish(request["ticket"])
	if not finished["ok"]:
		return _reject("action_finish_failed")
	var result := {"ok": true, "executed": true, "scope": _scope,
		"ticket": request["ticket"].duplicate(true), "target": request["target"].duplicate(true),
		"numbers": numbers, "spent_mp": paid["spent"], "session": finished["session"]}
	if _drain_mp:
		result.merge(transfer, true)
	return result

# {
#   責務: [_apply_drain_mp: 予測済みの敵MP喪失と術者の最大MPまでの回復を、同じSessionへ順に適用します]
#   処理: [
#     1: 敵の喪失予測量をSessionのMP減算へ渡します
#     2: 敵が失った実MP量を術者のMP回復へ渡し、実回復量を別に返します
#   ]
#   引数: [
#     actor: 行動予約を取得済みの術者のsideとid（Dictionary）
#     target: HP効果後には死亡している場合もある敵のsideとid（Dictionary）
#     numbers: 最新資源から検証済みの吸MP予測（Dictionary）
#   ]
#   戻り値: [result: 実喪失drained_mp・実回復recovered_mp、または内部適用の失敗（Dictionary）]
# }
func _apply_drain_mp(actor: Dictionary, target: Dictionary, numbers: Dictionary) -> Dictionary:
	# 無効/吸収耐性や敵MP0では、不要な資源操作を行いません。
	if numbers["drained_mp"] == 0:
		return {"ok": true, "drained_mp": 0, "recovered_mp": 0}
	# pay_mpは数値減算であり、死亡対象への行動許可ではありません。対象の生存はclaim前に検証済みです。
	var drained: Dictionary = _session.pay_mp(target, numbers["drained_mp"])
	if not drained["ok"]:
		return _reject("action_drain_mp_failed")
	# 回復の上限は資源所有者が守り、術者が回復できないMPを敵へ戻しません。
	var recovered: Dictionary = _session.restore_mp(actor, drained["spent"])
	if not recovered["ok"]:
		return _reject("action_mp_recovery_failed")
	return {"ok": true, "drained_mp": drained["spent"], "recovered_mp": recovered["restored"]}

# {
#   責務: [_validate: 最新予約・習得・敵対象・現在MPとHPを確認し、魔法の適用結果を予測します]
#   処理: [
#     1: 厳密な要求と最新offered予約を検証します
#     2: 習得済み定義・敵対象・揺らぎを確認します
#     3: 行動可能な場合だけ最新資源で魔法結果を予測します
#   ]
#   引数: [request: 明示された魔法行動要求（Variant）]
#   戻り値: [result: 予測numbersまたは理由付き拒否（Dictionary）]
# }
func _validate(request: Variant) -> Dictionary:
	# 会心値・威力・MP・耐性・guardの要求側上書きを拒否する。
	if _context.is_empty():
		return _reject("not_initialized")
	if not request is Dictionary or request.size() != REQUEST_FIELDS.size():
		return _reject("invalid_magic_request")
	for field in REQUEST_FIELDS:
		if not request.has(field):
			return _reject("invalid_magic_request")
	if not Order.valid_key(request["target"]):
		return _reject("invalid_target_key")
	var inspected: Dictionary = _session.inspect_ticket(request["ticket"])
	if not inspected["ok"]:
		return inspected
	var actor: Dictionary = request["ticket"]["actor"]
	var target: Dictionary = request["target"]
	var selected := Context.select(_context, actor, request["skill_id"], _self_damage, _drain_mp)
	if not selected["ok"]:
		return selected
	if actor["side"] == target["side"]:
		return _reject("target_not_enemy")
	var teams: Dictionary = _session.snapshot()["teams"]
	var defender := _member(teams[target["side"]], target["id"])
	if defender.is_empty():
		return _reject("target_missing")
	var variance := Numbers.float_value(request["variance"])
	if not variance["ok"] or variance["value"] < 0.92 or variance["value"] > 1.08:
		return _reject("invalid_variance")
	# 死亡・逃走・敵なしはMP不足に置き換えず、Sessionの予約取消へ渡す。
	if not inspected["eligibility"]["can_act"]:
		return {"ok": true}
	if not defender["alive"]:
		return _reject("target_not_alive")
	var attacker := _member(teams[actor["side"]], actor["id"])
	# guardを渡さないため、基本ぼうぎょは魔法を軽減しない。対象は最新HPで計算する。
	var forecast := {"magic": attacker["stats"]["magic"],
		"target_hp": defender["hp"], "target_max_hp": defender["stats"]["hp"], "current_mp": attacker["mp"],
		"target_resistances": _context["members"][target["side"]][target["id"]]["resistances"],
		"variance": request["variance"], "fixed_bonus_damage": selected["fixed_bonus_damage"]}
	# HP代償は要求値ではなく、予約検証後の術者の現在HP・最大HPから予測する。
	if _self_damage:
		forecast["actor_hp"] = attacker["hp"]
		forecast["actor_max_hp"] = attacker["stats"]["hp"]
	# 吸MPの上限と敵の残MPは要求から受け取らず、予約検証後の最新Sessionから取得します。
	if _drain_mp:
		forecast["actor_max_mp"] = attacker["stats"]["mp"]
		forecast["target_mp"] = defender["mp"]
	var numbers: Dictionary = _quote.quote_damage(selected["skill"], forecast)
	return numbers if not numbers["ok"] else {"ok": true, "numbers": numbers}

# {
#   責務: [_member: 最大4体の参加チームから指定IDの最新戦闘資源を取り出します]
#   処理: [1: 参加個体のIDを照合し、一致した資源または空辞書を返します]
#   引数: [
#     team: 最新snapshotの参加チーム（Array）
#     id: 検索する個体ID（String）
#   ]
#   戻り値: [result: 一致した個体の資源または空辞書（Dictionary）]
# }
func _member(team: Array, id: String) -> Dictionary:
	for member: Dictionary in team:
		if member["identity"]["id"] == id:
			return member
	return {}

# {
#   責務: [_reject: 魔法行動の失敗理由を共通の辞書形式で返します]
#   処理: [1: ok=falseと呼出元が指定した理由を返します]
#   引数: [reason: 要求・開始情報・適用手順の拒否理由（String）]
#   戻り値: [result: 理由付き拒否結果（Dictionary）]
# }
func _reject(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
