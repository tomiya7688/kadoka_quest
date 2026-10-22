# {
#   責務: [physical_skill_context: 開始時の戦闘資源・習得・許可装備を検証し、指定物理スキルの定義と装備補正を選びます]
#   フィールド: []
# }
extends RefCounted
const Quote = preload("res://engine/physical_skill_contract.gd")
const StatusQuote = preload("res://engine/status_physical_skill_contract.gd")
const Order = preload("res://engine/turn_order.gd")
const State = preload("res://engine/combatant_state.gd")
const Numbers = preload("res://engine/stat_numbers.gd")
const EQUIPMENT_FIELDS := ["id", "display_name", "description", "category", "allowed_species_ids",
	"stat_multipliers", "resistance_steps", "skill_modifiers", "fixed_bonus_damage"]


# {
#   責務: [prepare: 満HP/MPの戦闘個体と習得・許可装備・スキル一覧の独立コピーを作ります]
#   処理: [
#     1: 両陣営とスキル一覧を検証し、重複検出可能なID別索引を作ります
#     2: 参加個体の資源・習得・装備を検証し、Session比較用のsnapshotと選択用contextを返します
#   ]
#   引数: [
#     teams: snapshot・skill_ids・equipmentを持つ再構築済みのallies/enemies（Variant）
#     skills: schema_version=1とskills配列を持つスキル一覧（Variant）
#   ]
#   戻り値: [result: 正規化資源snapshotsと独立した個体情報/定義索引context、または理由付き拒否（Dictionary）]
# }
static func prepare(teams: Variant, skills: Variant) -> Dictionary:
	# 未対応定義は削除せず、選択時に個別の対応範囲を確認する。
	if not skills is Dictionary or not skills.get("skills") is Array:
		return _reject("invalid_skill_document")
	var version: Variant = skills.get("schema_version")
	if not (version is int or version is float) or version != 1:
		return _reject("invalid_skill_document")
	if not teams is Dictionary or teams.size() != 2 or not teams.get("allies") is Array or not teams.get("enemies") is Array:
		return _reject("invalid_physical_context")
	# 保有MODスキル数に比例する検索を毎行動に繰り返さず、重複はそのまま検出可能に保持する。
	var definitions := _definition_index(skills["skills"])
	var snapshots := {"allies": [], "enemies": []}
	var members := {"allies": {}, "enemies": {}}
	for side in Order.SIDES:
		for member: Variant in teams[side]:
			var checked := _prepare_member(member)
			if not checked["ok"]:
				return checked
			snapshots[side].append(checked["snapshot"])
			members[side][checked["snapshot"]["identity"]["id"]] = checked["member"]
	# 各個体は_prepare_member内のOrder.participantsで厳密検証済みです。集合に残る上限/重複だけを確認します。
	for side in Order.SIDES:
		if snapshots[side].size() > Order.ACTIVE_TEAM_LIMIT or members[side].size() != snapshots[side].size():
			# 不正集合の理由/side/detailは公開の順序契約へ委譲し、従来の拒否形式と優先順を保ちます。
			return Order.participants(snapshots["allies"], snapshots["enemies"])
	return {"ok": true, "snapshots": snapshots, "context": {"members": members, "definitions": definitions}}


# {
#   責務: [_definition_index: 文字列IDを持つ定義だけを独立コピーし、重複も保持するID別候補索引を作ります]
#   処理: [1: 索引対象の定義列を一度だけ深く複製し、新規のID別候補配列へ振り分けます]
#   引数: [entries: スキル文書の定義列。文字列IDのない要素は従来どおり選択対象にしません（Array）]
#   戻り値: [result: 原本と参照を共有しないID別の定義候補配列。未知効果や重複定義も削除しません（Dictionary）]
# }
static func _definition_index(entries: Array) -> Dictionary:
	# ID別配列を構築してから丸ごと複製すると、千件の空でない候補配列も二重に生成します。
	var candidates: Array = []
	for definition: Variant in entries:
		if definition is Dictionary and definition.get("id") is String:
			candidates.append(definition)
	var definitions: Dictionary = {}
	for definition: Dictionary in candidates.duplicate(true):
		var id: String = definition["id"]
		if not definitions.has(id):
			definitions[id] = []
		definitions[id].append(definition)
	return definitions


# {
#   責務: [_prepare_member: 参加個体の満HP/MP・習得ID・装備許可を検証し、独立した開始情報を作ります]
#   処理: [
#     1: snapshotの資源と習得IDを検証し、資源消費済みや逃走済みの個体を拒否します
#     2: 装備する種族の許可を検証し、Session比較用の整数snapshotを作ります
#   ]
#   引数: [member: 再構築済みのsnapshot・skill_ids・equipmentを持つ参加個体（Variant）]
#   戻り値: [result: 正規化snapshotと独立した習得/装備member、または理由付き拒否（Dictionary）]
# }
static func _prepare_member(member: Variant) -> Dictionary:
	# 習得情報は行動payloadでなく、開始時に受け取る再構築結果へ限定する。
	if not member is Dictionary or not member.get("snapshot") is Dictionary or not member.get("skill_ids") is Array:
		return _reject("invalid_physical_context")
	var snapshot: Dictionary = member["snapshot"]
	var validated := Order.participants([snapshot], [])
	if not validated["ok"]:
		return validated
	for id: Variant in member["skill_ids"]:
		if not id is String or id.is_empty():
			return _reject("invalid_learned_skills")
	if snapshot["hp"] != snapshot["stats"]["hp"] or snapshot["mp"] != snapshot["stats"]["mp"] or snapshot["fled"]:
		return _reject("fresh_physical_context_required")
	var equipment := _equipment(member.get("equipment"), snapshot["identity"]["species_id"])
	if not equipment["ok"]:
		return equipment
	# Order.participantsで六キー/資源/生存整合性を検証済みです。新規所有者を作って再検証せず、JSON整数値を正規化します。
	var normalized: Dictionary = snapshot.duplicate(true)
	for stat in State.STAT_KEYS:
		normalized["stats"][stat] = int(snapshot["stats"][stat])
	normalized["hp"] = int(snapshot["hp"])
	normalized["mp"] = int(snapshot["mp"])
	return {"ok": true, "snapshot": normalized, "member": {
		"skill_ids": member["skill_ids"].duplicate(true), "equipment": equipment["equipment"]}}


# {
#   責務: [_equipment: 空辞書を未装備として扱い、非空装備の種族許可と効果辞書の形式を確認します]
#   処理: [1: 未対応キー・不正許可リスト・種族不許可・不正なskill_modifiersを拒否します]
#   引数: [
#     definition: 再構築で選択した装備定義、または未装備の空辞書（Variant）
#     species: 装備する戦闘個体の種族ID（String）
#   ]
#   戻り値: [result: 独立したequipment、または理由付き拒否（Dictionary）]
# }
static func _equipment(definition: Variant, species: String) -> Dictionary:
	# 空辞書は再構築済みの未装備・不明ID・装備不可であり、補正を加えない。
	if not definition is Dictionary:
		return _reject("invalid_physical_equipment")
	if definition.is_empty():
		return {"ok": true, "equipment": {}}
	for field: Variant in definition:
		if field not in EQUIPMENT_FIELDS:
			return _reject("unsupported_physical_equipment")
	var allowed: Variant = definition.get("allowed_species_ids")
	if not allowed is Array:
		return _reject("invalid_equipment_permission")
	for id: Variant in allowed:
		if not id is String:
			return _reject("invalid_equipment_permission")
	if species not in allowed:
		return _reject("equipment_not_allowed")
	if not definition.get("skill_modifiers", {}) is Dictionary:
		return _reject("invalid_physical_equipment")
	return {"ok": true, "equipment": definition.duplicate(true)}


# {
#   責務: [select: 習得した通常のMP付き物理定義を選び、状態付与付き定義を引き続き拒否します]
#   処理: [1: 物理の共用習得/装備選択へ、付与に未対応の既存定義契約を渡します]
#   引数: [
#     context: prepareの個体別習得/許可装備と定義索引（Dictionary）
#     actor: 選択する参加者のsideとid（Dictionary）
#     skill_id: MP付き通常物理のスキルID（Variant）
#   ]
#   戻り値: [result: 独立skillと装備補正、または理由付き拒否（Dictionary）]
# }
static func select(context: Dictionary, actor: Dictionary, skill_id: Variant) -> Dictionary:
	# 従来の物理行動を付与付きとして暗黙に実行しないよう、入口の契約を固定します。
	return _select(context, actor, skill_id, Quote)


# {
#   責務: [select_status_physical: 付与定義を必須にした単体物理を、通常物理と共用の習得/装備検証で選びます]
#   処理: [1: 共用選択へ状態付与付き物理の専用定義契約を渡します]
#   引数: [
#     context: 開始時に独立コピーした個体別習得/許可装備とID索引（Variant）
#     actor: 選択する参加者のsideとidだけを持つ辞書（Variant）
#     skill_id: 選択を要求する付与付き物理ID（Variant）
#   ]
#   戻り値: [result: 独立skillと装備補正、または非破壊的な拒否（Dictionary）]
# }
static func select_status_physical(context: Variant, actor: Variant, skill_id: Variant) -> Dictionary:
	# 生の要求からスクリプトやmodeを渡さず、専用入口の定義検査だけを使用します。
	return _select(context, actor, skill_id, StatusQuote)


# {
#   責務: [_select: 開始時の習得と選択IDの許可装備補正を確認し、指定物理契約で一意な定義を選びます]
#   処理: [
#     1: 個体索引・参加者キー・習得を確認し、内部で固定した物理契約へ定義検証を委譲します
#     2: 選択IDの威力倍率と固定加算を検証し、他IDの装備効果を混ぜず返します
#   ]
#   引数: [
#     context: prepareの個体/定義索引。編集可能な通常データで、認証情報ではありません（Variant）
#     actor: 参加者を一意に示すside/id（Variant）
#     skill_id: 通常または付与付きの物理ID（Variant）
#     definition_contract: 公開入口が固定する物理専用定義契約（GDScript）
#   ]
#   戻り値: [result: 独立skillと装備補正、または部分成功なしの拒否（Dictionary）]
# }
static func _select(context: Variant, actor: Variant, skill_id: Variant, definition_contract: GDScript) -> Dictionary:
	# 不正な選択要求で辞書参照の実行診断を発生させず、準備データも変更しません。
	if not context is Dictionary or not context.get("members") is Dictionary or not context.get("definitions") is Dictionary:
		return _reject("invalid_physical_context")
	if not Order.valid_key(actor):
		return _reject("invalid_actor_key")
	var side: Variant = context["members"].get(actor["side"])
	if not side is Dictionary or not side.get(actor["id"]) is Dictionary:
		return _reject("actor_missing")
	var member: Dictionary = side[actor["id"]]
	if not member.get("skill_ids") is Array or not member.get("equipment") is Dictionary:
		return _reject("invalid_physical_context")
	# 未習得と通常攻撃への偽装を、行動権取得前に区別する。
	if not skill_id is String or skill_id.is_empty():
		return _reject("invalid_skill_id")
	if skill_id in ["attack", "defend"]:
		return _reject("unsupported_action")
	if skill_id not in member["skill_ids"]:
		return _reject("skill_not_learned")
	var selected: Dictionary = definition_contract.prepare({"schema_version": 1, "skills": context["definitions"].get(skill_id, [])}, skill_id)
	if not selected["ok"]:
		return selected
	# 他IDの補正を流用せず、選択IDの未知効果はfalseや空でも拒否する。
	var definition: Dictionary = member["equipment"]
	var modifier: Variant = definition.get("skill_modifiers", {}).get(skill_id, {})
	if not modifier is Dictionary:
		return _reject("invalid_physical_equipment")
	for field: Variant in modifier:
		if field != "power_multiplier":
			return _reject("unsupported_physical_equipment")
	var power := Numbers.float_value(modifier.get("power_multiplier", 1.0))
	var bonus := Numbers.integer_value(definition.get("fixed_bonus_damage", 0))
	if not power["ok"] or not bonus["ok"]:
		return _reject("invalid_physical_equipment")
	return {"ok": true, "skill": selected["skill"], "equipment": {
		"power_multiplier": power["value"], "fixed_bonus_damage": bonus["value"]}}


# {
#   責務: [_reject: 開始情報または物理スキル選択の失敗を、理由付き辞書へ変換します]
#   処理: [1: ok=falseと具体的な拒否理由を返します]
#   引数: [reason: 開始情報・習得・装備・選択定義を拒否した理由（String）]
#   戻り値: [result: ok=falseの辞書（Dictionary）]
# }
static func _reject(reason: String) -> Dictionary:
	# 初期化や選択の失敗を呼出側が理由で判別できるようにする。
	return {"ok": false, "reason": reason}
