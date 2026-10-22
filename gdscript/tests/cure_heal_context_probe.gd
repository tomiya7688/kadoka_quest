# {
#   責務: [cure_heal_context_probe: 共用起動入口から回復準備・定義選択・初期状態一致・独立コピー・性能を観測します]
#   フィールド: []
# }
extends RefCounted
const Context = preload("res://engine/cure_heal_skill_context.gd")
const Healing = preload("res://engine/heal_skill_context.gd")
const Repository = preload("res://data/content_repository.gd")
const Builder = preload("res://application/combatant_builder.gd")


# {
#   責務: [run: 治療付き回復のケース観測または準備済み索引の選択性能を返します]
#   処理: [1: performance=trueなら計測、その他は各ケースを独立して観測します]
#   引数: [payload: 専用ケース配列または計測条件（Dictionary）]
#   戻り値: [result: ケース結果または性能結果（Dictionary）]
# }
static func run(payload: Dictionary) -> Dictionary:
	if payload.get("performance", false):
		return _measure(payload)
	var results: Array = []
	for request: Dictionary in payload.get("cases", []):
		results.append(_run_case(request))
	return {"results": results}


# {
#   責務: [_run_case: 開始情報・初期状態・定義選択と、入力/選択結果のネスト独立性を観測します]
#   処理: [
#     1: コピー入力を準備し、任意の再構築や非JSON状態注入を専用ケース内で行います
#     2: 準備/選択を実行し、コピー入力と選択結果を編集して準備結果の不変を確認します
#   ]
#   引数: [request: teams/skillsまたはrecords/project_root、初期状態、選択列と任意special（Dictionary）]
#   戻り値: [result: 準備・選択観測と原本保持/独立性（Dictionary）]
# }
static func _run_case(request: Dictionary) -> Dictionary:
	var before := JSON.stringify(request)
	var copied := request.duplicate(true)
	if copied.has("records"):
		var rebuilt := _rebuild(copied)
		if not rebuilt["ok"]:
			return {"prepared": rebuilt, "input_preserved": before == JSON.stringify(request)}
		copied["teams"] = rebuilt["teams"]
		copied["skills"] = rebuilt["skills"]
	# 非JSON状態はGodot内の専用コピーでだけ作り、要求ファイルへ保存しません。
	var cyclic: Dictionary = {}
	if copied.has("special"):
		var special: Dictionary = copied["special"]
		var value: Variant = NAN if special["value"] == "nan" else INF
		if special["value"] == "object":
			value = RefCounted.new()
		if special["value"] == "cycle":
			cyclic["self"] = cyclic
			value = cyclic
		copied["initial_statuses"][special["side"]][special["id"]][0]["metadata"] = value
	var prepared := Context.prepare(copied.get("teams"), copied.get("skills"), copied.get("initial_statuses"))
	cyclic.clear()
	if not prepared["ok"]:
		return {"prepared": prepared, "input_preserved": before == JSON.stringify(request)}
	var original := prepared.duplicate(true)
	var selections: Array = []
	for selection: Dictionary in copied.get("selections", []):
		selections.append(_select(prepared["context"], selection))
	_mutate_input(copied)
	return {"prepared": original, "selections": selections, "source_independent": prepared == original,
		"input_preserved": before == JSON.stringify(request)}


# {
#   責務: [_rebuild: 専用個体レコードから正規JSONのLv別習得・許可装備を既存Builderで再構築します]
#   処理: [1: 読取専用リポジトリとBuilderへ委譲し、両陣営の開始情報と正規スキル一覧を返します]
#   引数: [request: recordsの両陣営とdata/を含むプロジェクト基準project_rootを持つ専用要求（Dictionary）]
#   戻り値: [result: 再構築済みteams/skills、または最初の拒否結果（Dictionary）]
# }
static func _rebuild(request: Dictionary) -> Dictionary:
	# 個体/AIを保存せず、既存の再構築処理と正規dataの読み取りだけを使用します。
	var repository = Repository.new(request["project_root"])
	var builder = Builder.new(repository)
	var teams: Dictionary = {}
	for side in ["allies", "enemies"]:
		var built: Dictionary = builder.build_team(request["records"][side])
		if not built["ok"]:
			return built
		teams[side] = built["members"]
	var skills: Dictionary = repository.load_skills()
	return skills if not skills["ok"] else {"ok": true, "teams": teams, "skills": skills["value"]}


# {
#   責務: [_select: 専用/通常HP回復の選択結果を編集し、準備contextとの共有がないか確認します]
#   処理: [1: 指定の選択入口を呼び、結果のskillを編集して元contextを再照合します]
#   引数: [
#     context: 検証済みの開始情報と定義索引（Dictionary）
#     request: actor・skill_idと任意normal_heal/context_overrideを持つ選択条件（Dictionary）
#   ]
#   戻り値: [result: 選択結果とcontext保持の観測（Dictionary）]
# }
static func _select(context: Dictionary, request: Dictionary) -> Dictionary:
	var before := context.duplicate(true)
	var source: Variant = request.get("context_override", context)
	var result: Dictionary
	if request.get("normal_heal", false):
		result = Healing.select(source, request.get("actor"), request.get("skill_id"))
	else:
		result = Context.select(source, request.get("actor"), request.get("skill_id"))
	var original := result.duplicate(true)
	if result.get("skill") is Dictionary:
		result["skill"]["id"] = "changed"
		result["skill"]["status_cure_chance"] = 99
	return {"result": original, "independent": before == context}


# {
#   責務: [_mutate_input: 開始情報・スキル配列・初期状態のネストを編集して準備結果との共有を検出します]
#   処理: [1: コピー入力の習得・snapshot・定義配列と各状態を変更します]
#   引数: [input: 元要求から独立した観測専用入力（Dictionary）]
#   戻り値: [result: なし（void）]
# }
static func _mutate_input(input: Dictionary) -> void:
	for side in ["allies", "enemies"]:
		for member: Dictionary in input["teams"][side]:
			member["skill_ids"].clear()
			member["snapshot"]["stats"]["hp"] = 1
			member["snapshot"]["identity"]["id"] = "changed"
			member["equipment"]["skill_modifiers"] = {"spirit_recover": {"changed": true}}
		for effects: Array in input["initial_statuses"][side].values():
			for effect in effects:
				if effect is Dictionary:
					effect["id"] = "changed"
					if effect.get("metadata") is Dictionary and effect["metadata"].get("deck") is Array:
						effect["metadata"]["deck"].clear()
			effects.append("changed")
	input["skills"]["skills"].clear()


# {
#   責務: [_measure: 八体の開始情報と千件定義を一度準備し、治療付き定義の選択だけの中央値を測ります]
#   処理: [1: 初期化を計測外へ分け、反復選択の中央値・実定義・準備/原本保持を返します]
#   引数: [payload: iterations・samples・warmupの反復条件（Dictionary）]
#   戻り値: [result: 選択時間と正規化定義・参加数・索引数・入力保持の観測（Dictionary）]
# }
static func _measure(payload: Dictionary) -> Dictionary:
	var teams := {"allies": [], "enemies": []}
	var statuses := {"allies": {}, "enemies": {}}
	for side in ["allies", "enemies"]:
		for index in 4:
			var id := "member_" + str(index)
			var stats := {"hp": 100, "mp": 100, "attack": 10, "defense": 10, "magic": 10, "speed": 10}
			teams[side].append({"snapshot": {"identity": {"id": id, "species_id": "hero", "name": id},
				"stats": stats, "hp": 100, "mp": 100, "fled": false, "alive": true},
				"skill_ids": ["spirit_recover"], "equipment": {}})
			statuses[side][id] = [{"id": "poison", "metadata": {"deck": [1, 2]}}]
	var skills := {"schema_version": 1, "skills": []}
	for index in 999:
		skills["skills"].append({"id": "other_" + str(index), "kind": "mod_unknown"})
	var definition := {"id": "spirit_recover", "display_name": "精霊回復", "kind": "heal", "mp_cost": 4,
		"heal_ratio": 0.03, "status_cure_chance": 0.03}
	skills["skills"].append(definition)
	var before := JSON.stringify([teams, skills, statuses])
	var prepared := Context.prepare(teams, skills, statuses)
	if not prepared["ok"]:
		return prepared
	var actor := {"side": "allies", "id": "member_0"}
	var context: Dictionary = prepared["context"]
	var context_before := JSON.stringify(prepared)
	var iterations := maxi(1, int(payload.get("iterations", 20000)))
	var samples := maxi(1, int(payload.get("samples", 7)))
	var warmup := maxi(0, int(payload.get("warmup", 2000)))
	# 大量のMOD定義は毎選択で走査せず、検証済みID索引を使用します。
	for index in warmup:
		Context.select(context, actor, "spirit_recover")
	var timings: Array = []
	for sample in samples:
		var started := Time.get_ticks_usec()
		for index in iterations:
			Context.select(context, actor, "spirit_recover")
		timings.append(float(Time.get_ticks_usec() - started) / iterations)
	timings.sort()
	return {"microseconds": timings[timings.size() / 2], "iterations": iterations, "samples": samples, "warmup": warmup,
		"selected": Context.select(context, actor, "spirit_recover"), "actors": 8, "definitions": context["definitions"].size(),
		"input_preserved": before == JSON.stringify([teams, skills, statuses]), "prepared_preserved": context_before == JSON.stringify(prepared)}
