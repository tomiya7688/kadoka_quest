# {
#   責務: [run_normal_attack_probe: Developer-only pure/joined action probe and eight-actor action microbenchmark.]
#   フィールド: []
# }
extends SceneTree
## Developer-only pure/joined action probe and eight-actor action microbenchmark.

const Session = preload("res://engine/battle_session.gd")
const Attack = preload("res://engine/normal_attack_action.gd")
const Defend = preload("res://engine/basic_defend_action.gd")
const Physical = preload("res://engine/physical_skill_action.gd")
const Magic = preload("res://engine/magic_skill_action.gd")
const Resistance = preload("res://engine/elemental_resistance.gd")
const Numbers = preload("res://engine/attack_numbers.gd")
const Application = preload("res://application/battle_session_application.gd")
const Repository = preload("res://data/content_repository.gd")
const Order = preload("res://engine/turn_order.gd")


# {
#   責務: [_initialize: 専用JSONの操作列または開発計測を実行し、結果をbase64付き標準出力で返して終了します]
#   処理: [1: 専用JSONの操作列または開発計測を実行し、結果をbase64付き標準出力で返して終了します]
#   引数: []
#   戻り値: [result: なし（void）。専用結果を標準出力へ返し、プローブを終了します]
# }
func _initialize() -> void:
	var arguments := OS.get_cmdline_user_args()
	if arguments.size() != 1:
		quit(2)
		return
	var payload: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(arguments[0]))
	var result := {"cases": [], "joined": []}
	if payload.get("performance", false):
		result = _performance(payload)
	else:
		for case: Dictionary in payload.get("cases", []):
			result["cases"].append(_case(case, false))
		for case: Dictionary in payload.get("joined", []):
			result["joined"].append(_case(case, true))
	print("KADOKA_NORMAL_ACTION_RESULT=" + Marshalls.utf8_to_base64(JSON.stringify(result)))
	quit(0)


# {
#   責務: [_case: 専用開始情報でSessionと必要な行動処理を構築し、明示操作後の資源・防御倍率・入力保持を観測します]
#   処理: [
#     1: 独立Sessionまたは読取専用データを使うapplicationと、指定された物理・魔法行動処理を初期化する
#     2: 明示操作と入力/出力コピー編集試験を進める
#     3: 実セーブに触れず資源・guard・入力保持の結果を返す
#   ]
#   引数: [
#     case: 専用開始情報と明示操作列（Dictionary）
#     joined: trueならapplication経由、falseなら純粋Sessionで実行する設定（bool）
#   ]
#   戻り値: [result: 初期化結果・操作別観測・最終Session・防御倍率・入力保持判定（Dictionary）]
# }
func _case(case: Dictionary, joined: bool) -> Dictionary:
	var input: Dictionary = case["input"].duplicate(true)
	for special: String in case.get("definition_special", {}):
		for entry: Dictionary in input.get("skills", {}).get("skills", []):
			if entry.get("id") == case.get("special_skill_id", "defend"):
				entry[special] = INF if case["definition_special"][special] == "inf" else NAN
	var before := input.duplicate(true)
	var session: RefCounted
	var attack: RefCounted
	var defend: RefCounted
	var physical: RefCounted
	var magic: RefCounted
	var self_magic: RefCounted
	var initialized: Dictionary
	if joined:
		session = Application.new(Repository.new(OS.get_environment("KADOKA_CONTENT_ROOT")))
		initialized = session.start(input.get("allies"), input.get("enemies"), input.get("shuffle_order"))
	else:
		session = Session.new()
		initialized = session.start(input.get("allies"), input.get("enemies")) if case.get("start_session", true) else {"ok": true}
		attack = Attack.new(session)
		if case.get("basic_defend", false):
			defend = Defend.new(session)
		# 行動種別ごとに要求された処理だけを設定し、すべて同じSessionの資源を更新する。
		if case.get("physical_skill", false):
			physical = Physical.new(session)
		if case.get("magic_skill", false):
			magic = Magic.new(session)
		if case.get("self_damage_magic", false):
			self_magic = Magic.new(session, true)
		var teams := {"allies": [], "enemies": []}
		for side in Order.SIDES:
			for member: Dictionary in input.get(side, []):
				teams[side].append({"snapshot": member,
					"skill_ids": input.get("learned", {}).get(side, {}).get(member["identity"]["id"], []),
					"equipment": input.get("equipment", {}).get(side, {}).get(member["identity"]["id"], {}),
					"resistances": input.get("resistances", {}).get(side, {}).get(member["identity"]["id"], {})})
		if initialized["ok"]:
			initialized = attack.start(case.get("context", teams), input.get("skills", {"schema_version": 1, "skills": [{"id": "attack", "kind": "physical"}]}))
		if initialized["ok"] and case.get("basic_defend", false):
			initialized = defend.start(input.get("skills", {"schema_version": 1, "skills": [{"id": "defend", "kind": "defend"}]}))
		if initialized["ok"] and case.get("physical_skill", false):
			initialized = physical.start(case.get("physical_context", teams), input.get("skills"))
		if initialized["ok"] and case.get("magic_skill", false):
			initialized = magic.start(case.get("magic_context", teams), input.get("skills"))
		if initialized["ok"] and case.get("self_damage_magic", false):
			initialized = self_magic.start(case.get("magic_context", teams), input.get("skills"))
		if initialized["ok"]:
			initialized = session.begin_round(input["shuffle_order"])
	var initial := initialized.duplicate(true)
	if case.get("mutate_initial", false):
		_mutate(initialized)
	var observations: Array = []
	var last_ticket: Variant = null
	for action: Dictionary in case.get("actions", []):
		var pending: Variant = session.snapshot()["pending"]
		if pending is Dictionary:
			last_ticket = pending["ticket"].duplicate(true)
		var value := _execute(session, attack, action, input, last_ticket, joined, defend, physical, magic, self_magic)
		var copied := value.duplicate(true)
		if action.get("mutate_result", false):
			_mutate(value)
		if action.get("mutate_effects", false):
			var edited: Dictionary = session.effects()
			for side in Order.SIDES:
				for id: String in edited["teams"][side]:
					edited["teams"][side][id] = 999.0
		observations.append({"value": copied, "session": session.snapshot(), "effects": session.effects()})
	return {"initialized": initial, "observations": observations, "session": session.snapshot(),
		"effects": session.effects(), "input_preserved": input == before}


# {
#   責務: [_execute: 専用テストの明示操作をSession・行動処理・純粋耐性計算へ委譲します]
#   処理: [1: 専用テストの明示操作をSession・行動処理・純粋耐性計算へ委譲します]
#   引数: [
#     session: 操作先の戦闘資源・行動予約を持つSessionまたはapplication（RefCounted）
#     attack: 純粋Sessionに対する通常攻撃の行動処理。application試験ではnull（RefCounted）
#     action: 種別と操作別引数を持つ専用要求（Dictionary）
#     input: 開始時の両陣営・明示順・習得・装備・耐性の専用コピー（Dictionary）
#     ticket: 行動権チケット（Variant）
#     joined: trueならapplication経由、falseなら純粋Sessionで実行する設定（bool）
#     defend: テスト対象の基本防御Action。旧通常攻撃ケースではnull（RefCounted）
#     physical: MP付き物理Action。通常ケースではnull（RefCounted）
#     magic: MP付き単体魔法Action。通常ケースではnull（RefCounted）
#     self_magic: 自傷付き単体魔法Action。自傷魔法以外の試験ではnull（RefCounted）
#   ]
#   戻り値: [result: 操作を委譲した担当モジュールの結果または不明操作の拒否（Dictionary）]
# }
func _execute(session: RefCounted, attack: RefCounted, action: Dictionary, input: Dictionary, ticket: Variant,
	joined: bool, defend: RefCounted, physical: RefCounted, magic: RefCounted, self_magic: RefCounted) -> Dictionary:
	match action["kind"]:
		"next": return session.next_actor()
		"begin": return session.begin_round(action.get("order", input["shuffle_order"]))
		"attack":
			var request: Variant = action.get("request", {"ticket": ticket, "target": action.get("target"),
				"skill_id": "attack", "critical_roll": 0.5, "variance": 1.0})
			if request is Dictionary:
				request = request.duplicate(true)
				request.merge(action.get("overrides", {}), true)
				for special: String in action.get("special", {}):
					request[special] = INF if action["special"][special] == "inf" else NAN
			return session.resolve_normal_attack(request) if joined else attack.resolve(request)
		"claim": return session.claim(ticket)
		"finish": return session.finish(action.get("ticket", ticket))
		"defend":
			var request: Variant = action.get("request", {"ticket": ticket, "skill_id": "defend"})
			if request is Dictionary:
				request = request.duplicate(true)
				request.merge(action.get("overrides", {}), true)
			return session.resolve_basic_defend(request) if joined else defend.resolve(request)
		"configure_defend": return defend.start(null)
		"physical":
			# 通常攻撃へIDを偽装せず、別Actionで正規IDの補正・MPを検証する。
			var request: Variant = action.get("request", {"ticket": ticket, "target": action.get("target"),
				"skill_id": action.get("skill_id", "body_bash"), "critical_roll": 0.5, "variance": 1.0})
			if request is Dictionary:
				request = request.duplicate(true)
				request.merge(action.get("overrides", {}), true)
				for special: String in action.get("special", {}):
					request[special] = INF if action["special"][special] == "inf" else NAN
			return session.resolve_physical_skill(request) if joined else physical.resolve(request)
		"configure_physical": return physical.start(null, null)
		"magic", "self_magic":
			# 魔法は会心値を持たず、耐性・MP・威力の上書きも受け付けない。
			var request: Variant = action.get("request", {"ticket": ticket, "target": action.get("target"),
				"skill_id": action.get("skill_id", "metal_burst" if action["kind"] == "self_magic" else "weaken"), "variance": 1.0})
			if request is Dictionary:
				request = request.duplicate(true)
				request.merge(action.get("overrides", {}), true)
				for special: String in action.get("special", {}):
					request[special] = INF if action["special"][special] == "inf" else NAN
			if action["kind"] == "self_magic":
				return session.resolve_self_damage_magic_skill(request) if joined else self_magic.resolve(request)
			return session.resolve_magic_skill(request) if joined else magic.resolve(request)
		"configure_magic": return magic.start(null, null)
		"configure_self_magic": return self_magic.start(null, null)
		"resistance": return Resistance.prepare(action.get("species"), action.get("equipment"))
		"heal":
			var amount: Variant = action.get("amount")
			if action.has("special"):
				amount = INF if action["special"] == "inf" else NAN
			return session.heal(action.get("actor"), amount)
		"apply_defend":
			var guard: Variant = action.get("guard", 0.5)
			if action.has("special"):
				guard = INF if action["special"] == "inf" else NAN
			return session.apply_defend(action.get("ticket", ticket), guard)
		"guard": return session.guard(action.get("actor"))
		"final_numbers":
			var current: Dictionary = session.guard(action["target"])
			return Numbers.finish_damage({"kind": action["damage_kind"], "damage": action["damage"],
				"guard": current["guard"], "variance": 1.0, "target_hp": 1000})
		"mp": return session.pay_mp(action["actor"], action["cost"])
		"configure": return attack.start(null, null)
		"damage": return session.take_damage(action["actor"], action["amount"])
		"flee": return session.flee(action["actor"])
		"input_mutation":
			_mutate(input)
			return {"ok": true}
	return {"ok": false, "reason": "unknown_probe_operation"}


# {
#   責務: [_mutate: 入力や返却値のコピー内の数値・ID・習得・耐性を編集し、所有者から独立しているか試します]
#   処理: [1: 入力や返却値のコピー内の数値・ID・習得・耐性を編集し、所有者から独立しているか試します]
#   引数: [value: 所有者から独立しているか検査する入力または結果のコピー（Variant）]
#   戻り値: [result: なし（void）。検証対象コピー内の数値・ID・習得・耐性を編集します]
# }
func _mutate(value: Variant) -> void:
	if value is Array:
		for entry: Variant in value:
			_mutate(entry)
	elif value is Dictionary:
		for entry: Variant in value.values():
			_mutate(entry)
		for key in ["hp", "mp", "round", "slot", "cursor", "speed", "attack", "power", "fixed_bonus_damage",
			"power_multiplier", "damage_multiplier", "applied_guard", "self_damage_ratio", "self_damage", "self_dealt", "remaining_actor_hp"]:
			if value.has(key):
				value[key] = 999
		if value.has("id"):
			value["id"] = "edited output"
		# 開始後に渡した習得情報を編集しても、Actionの独立コピーは変更されない。
		if value.has("skill_ids"):
			value["skill_ids"].clear()
		# 開始時耐性の独立コピーを確認するため、コピー内の属性値も編集する。
		for element in ["mental", "fire", "ice", "metal"]:
			if value.get(element) is String:
				value[element] = "immune"


# {
#   責務: [_performance: 専用の8体Sessionで通常攻撃1回の次行動取得から完了までを反復計測します]
#   処理: [1: 専用の8体Sessionで通常攻撃1回の次行動取得から完了までを反復計測します]
#   引数: [payload: 反復回数iterations・標本数samples・事前反復warmupの計測条件（Dictionary）]
#   戻り値: [result: 8体の通常攻撃1回あたりの中央値usと最終資源検証値（Dictionary）]
# }
func _performance(payload: Dictionary) -> Dictionary:
	var teams := {"allies": [], "enemies": []}
	var prepared := {"allies": [], "enemies": []}
	for side in Order.SIDES:
		for index in 4:
			var member := {"identity": {"id": str(index), "species_id": "slime", "name": "test"},
				"stats": {"hp": 1000000000, "mp": 20, "attack": 10, "defense": 10, "magic": 10, "speed": index % 3 + 1},
				"hp": 1000000000, "mp": 20, "fled": false, "alive": true}
			teams[side].append(member)
			prepared[side].append({"snapshot": member, "equipment": {"fixed_bonus_damage": 3}})
	var order: Array = Order.participants(teams["allies"], teams["enemies"])["members"]
	var session = Session.new()
	session.start(teams["allies"], teams["enemies"])
	var attack = Attack.new(session)
	var configured: Dictionary = attack.start(prepared, {"schema_version": 1, "skills": [{"id": "attack", "kind": "physical"}]})
	assert(configured["ok"])
	var iterations := int(payload.get("iterations", 20000))
	var samples := int(payload.get("samples", 7))
	var warmup := int(payload.get("warmup", 2000))
	for index in warmup:
		_stage(session, attack, order)
	var timings: Array = []
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			_stage(session, attack, order)
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
	timings.sort()
	var minimum_hp := 1000000000
	for team: Array in session.snapshot()["teams"].values():
		for member: Dictionary in team:
			minimum_hp = mini(minimum_hp, member["hp"])
	return {"microseconds": timings[timings.size() / 2], "iterations": iterations, "samples": samples,
		"warmup": warmup, "actors": 8, "minimum_hp": minimum_hp}


# {
#   責務: [_stage: 専用8体Sessionのラウンドを必要時だけ開始し、次の通常攻撃を実行してHP減少を確認します]
#   処理: [1: 専用8体Sessionのラウンドを必要時だけ開始し、次の通常攻撃を実行してHP減少を確認します]
#   引数: [
#     session: 専用8体のHP・MPと行動予約を保持する戦闘Session（RefCounted）
#     attack: 専用Sessionへ通常攻撃を適用する行動処理（RefCounted）
#     order: 陣営sideと個体idで表した8体の明示参加順（Array）
#   ]
#   戻り値: [result: なし（void）。次の通常攻撃を実行し、MP非消費とHP減少を確認します]
# }
func _stage(session: RefCounted, attack: RefCounted, order: Array) -> void:
	if session.snapshot()["phase"] != "round_active":
		session.begin_round(order)
	var offered: Dictionary = session.next_actor()
	var ticket: Dictionary = offered["pending"]["ticket"]
	var target := {"side": "enemies" if ticket["actor"]["side"] == "allies" else "allies", "id": "0"}
	var resolved: Dictionary = attack.resolve({"ticket": ticket, "target": target, "skill_id": "attack", "critical_roll": 0.5, "variance": 1.0})
	assert(resolved["executed"])
