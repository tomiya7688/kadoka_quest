extends RefCounted
## Coordinate base reconstruction, read-only modifier documents and pure calculation per scan.

const BaseService = preload("res://application/monster_progression.gd")
const Modifiers = preload("res://engine/monster_modifiers.gd")
var repository: RefCounted
var base_service: RefCounted
var plus_documents: Dictionary = {}
var equipment_document: Dictionary = {}


func _init(content: RefCounted) -> void:
	repository = content
	base_service = BaseService.new(content)


func rebuild(monster: Dictionary) -> Dictionary:
	var base: Dictionary = base_service.rebuild(monster)
	if not base["ok"]:
		return base
	base["modifiers"] = _rebuild_modifiers(base, monster)
	return base


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
