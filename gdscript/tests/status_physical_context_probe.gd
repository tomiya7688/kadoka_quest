# {
#   責務: [status_physical_context_probe: 付与付き物理の準備/選択と耐性再構築・独立性・千定義での選択性能を観測します]
#   フィールド: []
# }
extends RefCounted
const Context = preload("res://engine/status_physical_skill_context.gd")
const Physical = preload("res://engine/physical_skill_context.gd")
const Resistance = preload("res://engine/status_resistance.gd")
const Shared = preload("res://tests/cure_heal_context_probe.gd")
const Copies = preload("res://tests/session_status_probe.gd")


# {
#   責務: [run: 準備ケース/状態耐性ケースまたは固定した千定義の選択性能を観測します]
#   処理: [1: performanceなら反復測定し、その他は独立したケースごとの純粋契約を観測します]
#   引数: [payload: 専用ケース一覧またはiterations/samples/warmup（Dictionary）]
#   戻り値: [result: ケース結果または準備済み索引からの選択性能（Dictionary）]
# }
static func run(payload: Dictionary) -> Dictionary:
	# 起動と要求JSONのI/Oは共用プローブへ任せ、このスクリプトは観測だけを担当します。
	if payload.get("performance", false):
		return _measure(payload)
	var results: Array = []
	for request: Dictionary in payload.get("cases", []):
		results.append(_case(request))
	var traits: Array = []
	for species in payload.get("species", []):
		traits.append(Resistance.prepare(species))
	return {"results": results, "resistances": traits}


# {
#   責務: [_case: 専用入力の再構築/不正値注入後に準備と選択を観測し、原本と返却ネストの独立性を照合します]
#   処理: [
#     1: 任意レコードを共用Builderへ渡し、native不正値は専用コピー内だけへ注入します
#     2: 準備/選択後に注入を戻し、入力と返却値を編集して共有がないことを確認します
#   ]
#   引数: [request: teams/skills/initial_statuses・任意records/project_root・selections・任意specialの専用ケース（Dictionary）]
#   戻り値: [result: 準備/選択結果と入力保持・コピー独立性（Dictionary）]
# }
static func _case(request: Dictionary) -> Dictionary:
	var before := JSON.stringify(request)
	var copied := request.duplicate(true)
	if copied.has("records"):
		var rebuilt := Shared._rebuild(copied)
		if not rebuilt["ok"]:
			return {"prepared": rebuilt, "input_preserved": before == JSON.stringify(request)}
		copied["teams"] = rebuilt["teams"]
		if not copied.has("skills"):
			copied["skills"] = rebuilt["skills"]
	var source_before := JSON.stringify(copied)
	var holder: Variant
	var field: Variant
	var prior: Variant
	var had := false
	var cyclic: Dictionary = {}
	# 非JSON入力は共有data/実セーブへ書かず、観測後に循環と元フィールドを戻します。
	if copied.has("special"):
		var special: Dictionary = copied["special"]
		var path: Array = special["path"]
		holder = copied
		for index in path.size() - 1:
			holder = holder[path[index]]
		field = path[-1]
		had = holder.has(field)
		prior = holder.get(field)
		var value: Variant = NAN
		match special["value"]:
			"inf": value = INF
			"object": value = RefCounted.new()
			"non_string_key": value = {1: "invalid"}
			"cycle":
				cyclic["self"] = cyclic
				value = cyclic
		holder[field] = value
	var prepared := Context.prepare(copied.get("teams"), copied.get("skills"), copied.get("initial_statuses"))
	cyclic.clear()
	if copied.has("special"):
		if had:
			holder[field] = prior
		else:
			holder.erase(field)
	var input_preserved: bool = before == JSON.stringify(request) and source_before == JSON.stringify(copied)
	if not prepared["ok"]:
		return {"prepared": prepared, "input_preserved": input_preserved}
	var original := prepared.duplicate(true)
	var selections: Array = []
	for selection: Dictionary in copied.get("selections", []):
		selections.append(_select(prepared["context"], selection))
	# 入力側の状態/耐性/装備を編集しても、成功した準備結果へ伝播しないことを確認します。
	for side in ["allies", "enemies"]:
		for member in copied["teams"][side]:
			member["status_resistances"].clear()
	Shared._mutate_input(copied)
	return {"prepared": original, "selections": selections, "input_preserved": input_preserved,
		"source_independent": prepared == original}


# {
#   責務: [_select: 通常/付与付きの専用入口を観測し、選択返却値の編集が準備contextへ伝わらないか確認します]
#   処理: [1: 指定入口を呼び、返却ネストの編集後に元contextと再選択結果を照合します]
#   引数: [
#     context: 成功した準備の独立した個体/定義索引（Dictionary）
#     request: actor/skill_idと任意normal_physical/context_override（Dictionary）
#   ]
#   戻り値: [result: 選択結果とcontext保持/返却独立性（Dictionary）]
# }
static func _select(context: Dictionary, request: Dictionary) -> Dictionary:
	var before := context.duplicate(true)
	var source: Variant = request.get("context_override", context)
	var result: Dictionary
	if request.get("normal_physical", false):
		result = Physical.select(source, request.get("actor"), request.get("skill_id"))
	else:
		result = Context.select(source, request.get("actor"), request.get("skill_id"))
	var original := result.duplicate(true)
	Copies._mutate(result)
	var repeated: Dictionary = Physical.select(source, request.get("actor"), request.get("skill_id")) if request.get("normal_physical", false) else Context.select(source, request.get("actor"), request.get("skill_id"))
	return {"result": original, "independent": before == context and original == repeated}


# {
#   責務: [_measure: 八体/千定義を一度準備し、状態付与付き物理の成功選択だけを反復測定します]
#   処理: [1: 初期化とI/Oを計測外にし、実選択・初期状態/耐性・原本保持と中央値を返します]
#   引数: [payload: iterations/samples/warmupの反復条件（Dictionary）]
#   戻り値: [result: 一選択の中央値・固定期待値照合用の準備要素・実選択・保持確認（Dictionary）]
# }
static func _measure(payload: Dictionary) -> Dictionary:
	var source := _inputs()
	var teams: Dictionary = source["teams"]
	var statuses: Dictionary = source["statuses"]
	var skills: Dictionary = source["skills"]
	var before := JSON.stringify([teams, skills, statuses])
	var prepared := Context.prepare(teams, skills, statuses)
	if not prepared["ok"]:
		return prepared
	var actor := {"side": "allies", "id": "member_0"}
	var context: Dictionary = prepared["context"]
	var prepared_before := JSON.stringify(prepared)
	var iterations := maxi(1, int(payload.get("iterations", 20000)))
	var samples := maxi(1, int(payload.get("samples", 7)))
	var warmup := maxi(0, int(payload.get("warmup", 2000)))
	# 千件を毎回走査せず索引だけを使い、正常な付与定義と装備補正の選択を測定します。
	for index in warmup:
		Context.select(context, actor, "mod_status_hit")
	var timings: Array = []
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			Context.select(context, actor, "mod_status_hit")
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
	timings.sort()
	return {"microseconds": timings[timings.size() / 2], "iterations": iterations, "samples": samples, "warmup": warmup,
		"actors": prepared["snapshots"]["allies"].size() + prepared["snapshots"]["enemies"].size(),
		"definitions": context["definitions"].size(), "selected": Context.select(context, actor, "mod_status_hit"),
		"member": context["members"]["allies"]["member_0"].duplicate(true),
		"initial_statuses": prepared["initial_statuses"]["enemies"]["member_0"].duplicate(true),
		"snapshot": prepared["snapshots"]["allies"][0].duplicate(true),
		"prepared_preserved": prepared_before == JSON.stringify(prepared),
		"input_preserved": before == JSON.stringify([teams, skills, statuses])}


# {
#   責務: [_inputs: 選択/非消費検査の性能確認へ、八体/千定義・ネスト状態/耐性/装備の共用固定入力を作ります]
#   処理: [1: 独立した両陣営・状態辞書と一件の対応定義を含む千件一覧を返します]
#   引数: []
#   戻り値: [result: teams/statuses/skillsだけを持つ独立した計測入力（Dictionary）]
# }
static func _inputs() -> Dictionary:
	var teams := {"allies": [], "enemies": []}
	var statuses := {"allies": {}, "enemies": {}}
	for side in ["allies", "enemies"]:
		for index in 4:
			var id := "member_" + str(index)
			var stats := {"hp": 100, "mp": 100, "attack": 10, "defense": 10, "magic": 10, "speed": 10}
			teams[side].append({"snapshot": {"identity": {"id": id, "species_id": "slime", "name": id},
				"stats": stats, "hp": 100, "mp": 100, "fled": false, "alive": true}, "skill_ids": ["mod_status_hit"],
				"equipment": {"allowed_species_ids": ["slime"], "fixed_bonus_damage": 3,
					"skill_modifiers": {"mod_status_hit": {"power_multiplier": 2}}}, "status_resistances": {"bleeding": "weak"}})
			statuses[side][id] = ["poison", {"id": "mod", "metadata": {"deck": [1, true]}}]
	var skills := {"schema_version": 1, "skills": []}
	for index in 999:
		skills["skills"].append({"id": "other_" + str(index), "kind": "mod_unknown"})
	var definition := {"id": "mod_status_hit", "display_name": "計測用付与打撃", "kind": "physical", "mp_cost": 3,
		"status_effect": {"id": "bleeding", "chance": 0.4, "metadata": {"deck": [1, {"kept": true}]}}}
	skills["skills"].append(definition)
	return {"teams": teams, "statuses": statuses, "skills": skills}
