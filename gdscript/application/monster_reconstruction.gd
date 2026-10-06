# {
#   責務: [monster_reconstruction: Coordinate base reconstruction, read-only modifier documents and pure calculation per scan.]
#   フィールド: [
#     repository: データ取得先（RefCounted）
#     base_service: base・service（RefCounted）
#     plus_documents: ＋選択・文書一覧（Dictionary）
#     equipment_document: 装備・文書（Dictionary）
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
#   責務: [_init: モンスター・reconstructionが利用する初期状態と依存を設定する]
#   処理: [1: モンスター・reconstructionが利用する初期状態と依存を設定する]
#   引数: [content: content（RefCounted）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _init(content: RefCounted) -> void:
	repository = content
	base_service = BaseService.new(content)


# {
#   責務: [rebuild: モンスター・reconstructionのrebuildを求める]
#   処理: [1: モンスター・reconstructionのrebuildを求める]
#   引数: [monster: モンスター（Dictionary）]
#   戻り値: [result: モンスター・reconstructionのrebuildを求めるための結果（Dictionary）]
# }
func rebuild(monster: Dictionary) -> Dictionary:
	var base: Dictionary = base_service.rebuild(monster)
	if not base["ok"]:
		return base
	base["modifiers"] = _rebuild_modifiers(base, monster)
	return base


# {
#   責務: [_rebuild_modifiers: モンスター・reconstructionのrebuild・modifiersを求める]
#   処理: [1: モンスター・reconstructionのrebuild・modifiersを求める]
#   引数: [
#     base: base（Dictionary）
#     monster: モンスター（Dictionary）
#   ]
#   戻り値: [result: モンスター・reconstructionのrebuild・modifiersを求めるための結果（Dictionary）]
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
