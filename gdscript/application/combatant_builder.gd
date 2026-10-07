# {
#   責務: [combatant_builder: 保存個体のレベル・＋選択・装備から戦闘用能力値と習得スキルを再構築し、HPとMPを最大値で初期化した状態を返します]
#   フィールド: [
#     reconstruction: 正規JSONから能力値・装備・習得を再構築する処理（RefCounted）
#     _repository: 正規種族定義を取得するリポジトリ（RefCounted）
#     _species_documents: この構築処理の存続中だけ共用する種族定義の読込結果（Dictionary）
#   ]
# }
extends RefCounted
## combatant_builder.gdの構築処理は保存個体から独立した戦闘状態を作り、元の個体レコードとAIへ書き戻しません。

const Records = preload("res://engine/monster_record_contract.gd")
const Reconstruction = preload("res://application/monster_reconstruction.gd")
const State = preload("res://engine/combatant_state.gd")
const Resistance = preload("res://engine/elemental_resistance.gd")
const ACTIVE_TEAM_LIMIT := 4
var reconstruction: RefCounted
var _repository: RefCounted
var _species_documents: Dictionary = {}


# {
#   責務: [_init: 戦闘個体の再構築に使うデータ取得先をmonster_reconstruction.gdの再構築処理へ渡します]
#   処理: [1: 指定リポジトリから正規種族・装備定義を読むmonster_reconstruction.gdの再構築処理を生成します]
#   引数: [repository: 正規の種族・装備などのJSON定義を取得するリポジトリ（RefCounted）]
#   戻り値: [result: なし（void）。個体の再構築処理を設定し、個体データはまだ取得しません]
# }
func _init(repository: RefCounted) -> void:
	_repository = repository
	reconstruction = Reconstruction.new(repository)


# {
#   責務: [build: 保存個体とAIの形式を確認し、正規データから再構築した戦闘資源・習得スキル・装備を返します]
#   処理: [
#     1: 個体レコードのmonsterとaiを検証し、正規JSONから能力値・習得スキル・装備を再構築します
#     2: combatant_state.gdの戦闘個体でHPとMPを最大値へ初期化し、戦闘資源と独立した習得スキルID・許可装備を返します
#   ]
#   引数: [record: 保存個体monsterと学習状態aiを含む個体レコード（Variant）]
#   戻り値: [result: 成功時は資源snapshot・習得ID skill_ids・許可装備equipment・属性耐性resistances・警告warnings、失敗時は理由reason（Dictionary）]
# }
func build(record: Variant) -> Dictionary:
	# combatant_builder.gdの構築処理は保存個体とAIの形式を検証し、不正なレコードを自動補修して戦闘へ持ち込みません。
	if not record is Dictionary or not record.get("monster") is Dictionary or not record.get("ai") is Dictionary:
		return {"ok": false, "reason": "invalid_record"}
	var monster: Dictionary = record["monster"]
	var checked := Records.validate_record(monster, record["ai"], str(monster.get("id", "")))
	if not checked["ok"]:
		return {"ok": false, "reason": "invalid_record", "detail": checked}
	# 戦闘個体の構築処理は、保存個体のレベル・＋選択・装備から正規JSONで能力値を再構築し、保存個体やAIへ書き戻しません。
	var rebuilt: Dictionary = reconstruction.rebuild(monster)
	if not rebuilt["ok"]:
		return {"ok": false, "reason": "reconstruction_failed", "detail": rebuilt.duplicate(true)}
	var modified: Dictionary = rebuilt["modifiers"]
	if not modified["ok"]:
		return {"ok": false, "reason": "modifiers_failed", "detail": modified.duplicate(true)}
	# 属性耐性は種族定義と許可済み装備から作り、資源6キーや保存レコードへ混ぜない。
	var traits := _resistances(monster["species_id"], modified["equipment"])
	if not traits["ok"]:
		return {"ok": false, "reason": "resistance_reconstruction_failed", "detail": traits}
	# 戦闘個体の構築処理は、新規combatant_state.gdの戦闘個体で戦闘用HPとMPを最大値へ初期化し、保存レコードと戦闘中の資源を分離します。
	var state = State.new()
	var initialized: Dictionary = state.start(monster, modified["stats"])
	if not initialized["ok"]:
		return initialized
	# 戦闘個体の構築処理は、習得スキルIDを戦闘資源のidentity・stats・hp・mp・fled・aliveと別に複製し、行動開始時の設定として渡します。
	return {"ok": true, "snapshot": state.snapshot(), "skill_ids": modified["skill_ids"].duplicate(true),
		"warnings": modified["warnings"].duplicate(true),
		"equipment": modified["equipment"].duplicate(true), "resistances": traits["resistances"],
		"scope": "combatant_resources_only"}


# {
#   責務: [_resistances: 正規種族を構築処理内で共用し、許可装備を含む属性耐性を返します]
#   処理: [
#     1: 未読込の種族定義を取得し、読込失敗とID不一致を拒否します
#     2: 属性耐性の段階計算を純粋engineへ委譲します
#   ]
#   引数: [
#     species_id: 再構築する正規種族ID（String）
#     equipment: 再構築済みの許可装備または空辞書（Dictionary）
#   ]
#   戻り値: [result: 独立したresistancesまたは理由付き拒否（Dictionary）]
# }
func _resistances(species_id: String, equipment: Dictionary) -> Dictionary:
	# 行動のたびにJSONを読み直さず、同じ戦闘準備では種族ごとに一度だけ取得する。
	if not _species_documents.has(species_id):
		var definition: Dictionary = _repository.load_species(species_id)
		_species_documents[species_id] = definition if definition.get("id") == species_id else {}
	var species: Dictionary = _species_documents[species_id]
	if species.is_empty():
		return {"ok": false, "reason": "invalid_species_definition"}
	return Resistance.prepare(species, equipment)


# {
#   責務: [build_team: 最大4体の個体レコードを戦闘参加者へ再構築し、同じ個体IDの重複を拒否します]
#   処理: [1: 個体数の上限と各個体の再構築結果を確認し、個体IDの重複がない場合に入力順の参加者列を返します]
#   引数: [records: 戦闘へ参加させるmonsterとaiを含む個体レコードの配列（Variant）]
#   戻り値: [result: 成功時は再構築済み参加者members、失敗時は拒否理由reasonと必要に応じて失敗位置indexを持つ辞書（Dictionary）]
# }
func build_team(records: Variant) -> Dictionary:
	# 戦闘チームの構築処理は、戦闘参加人数だけに上限を設け、保有モンスター数を制限しません。
	if not records is Array:
		return {"ok": false, "reason": "invalid_team"}
	if records.size() > ACTIVE_TEAM_LIMIT:
		return {"ok": false, "reason": "active_team_limit", "limit": ACTIVE_TEAM_LIMIT}
	var members: Array = []
	# 戦闘チームの構築処理は、一つの陣営へ同じ個体を重複登録せず、入力順を保った参加者列を作ります。
	var ids: Dictionary = {}
	for index in records.size():
		var built := build(records[index])
		if not built["ok"]:
			built["index"] = index
			return built
		var id: String = built["snapshot"]["identity"]["id"]
		if ids.has(id):
			return {"ok": false, "reason": "duplicate_member", "index": index}
		ids[id] = true
		members.append(built)
	return {"ok": true, "members": members}
