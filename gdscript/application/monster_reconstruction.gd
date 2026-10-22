# {
#   責務: [monster_reconstruction: Coordinate base reconstruction, read-only modifier documents and pure calculation per scan.]
#   フィールド: [
#     repository: 正規の＋選択/装備カタログを読み取る取得先（RefCounted）
#     base_service: 保存個体のレベル別基礎能力と習得スキルを再構築する依存（RefCounted）
#     plus_documents: この再構築処理の存続中に種族ID別で共用する＋選択定義（Dictionary）
#     equipment_document: この再構築処理の存続中に共用する装備カタログの読込結果（Dictionary）
#   ]
# }
extends RefCounted
## Coordinate base reconstruction, read-only modifier documents and pure calculation per scan.

const BaseService = preload("res://application/monster_progression.gd")
const Modifiers = preload("res://engine/monster_modifiers.gd")
var repository: RefCounted
var base_service: RefCounted
var plus_documents: Dictionary = {}
var equipment_document: Dictionary = {}


# {
#   責務: [_init: 正規データの取得先を保持し、基礎能力値と習得スキルを再構築する依存を設定します]
#   処理: [1: 正規データの取得先を保持し、基礎能力値と習得スキルを再構築する依存を設定します]
#   引数: [content: 正規種族・装備定義の読込先（RefCounted）]
#   戻り値: [result: なし（void）。基礎再構築と正規補正定義の取得先を設定します]
# }
func _init(content: RefCounted) -> void:
	repository = content
	base_service = BaseService.new(content)


# {
#   責務: [rebuild: 基礎能力値と習得スキルの再構築結果へ、＋選択・許可装備の補正結果を加えて返します]
#   処理: [1: 基礎能力値と習得スキルの再構築結果へ、＋選択・許可装備の補正結果を加えて返します]
#   引数: [monster: 種族ID・レベル・＋選択・装備IDを含む保存個体（Dictionary）]
#   戻り値: [result: レベル別能力値・習得IDとmodifiersの補正結果、または再構築を拒否した理由（Dictionary）]
# }
func rebuild(monster: Dictionary) -> Dictionary:
	var base: Dictionary = base_service.rebuild(monster)
	if not base["ok"]:
		return base
	base["modifiers"] = _rebuild_modifiers(base, monster)
	return base


# {
#   責務: [_rebuild_modifiers: ＋と装備の定義を構築処理内で共用し、能力値・習得ID・許可装備の純粋計算へ委譲します]
#   処理: [1: ＋と装備の定義を構築処理内で共用し、能力値・習得ID・許可装備の純粋計算へ委譲します]
#   引数: [
#     base: 基礎能力statsと習得skill_idsを持つレベル別再構築結果（Dictionary）
#     monster: 種族ID・レベル・＋選択・装備IDを含む保存個体（Dictionary）
#   ]
#   戻り値: [result: 補正後能力値・習得ID・許可装備・警告、または補正失敗（Dictionary）]
# }
func _rebuild_modifiers(base: Dictionary, monster: Dictionary) -> Dictionary:
	var species: String = monster["species_id"]
	if not plus_documents.has(species):
		plus_documents[species] = repository.load_plus(species)
	var plus: Dictionary = plus_documents[species]
	if not plus["ok"]:
		return plus.duplicate(true)
	if equipment_document.is_empty():
		equipment_document = repository.load_equipment()
	if not equipment_document["ok"]:
		return equipment_document.duplicate(true)
	return Modifiers.apply(base, plus["value"], equipment_document["value"], monster)
