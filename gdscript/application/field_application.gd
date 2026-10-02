extends Control
## Composition/coordinator: data -> session -> renderer. Source-only prototype.

const Repository = preload("res://data/content_repository.gd")
const Session = preload("res://application/field_session.gd")
const Keyboard = preload("res://ui/field_input.gd")
const Images = preload("res://ui/content_images.gd")
const FieldView = preload("res://ui/field_view.gd")
const SaveStore = preload("res://data/field_save_store.gd")
const Persistence = preload("res://application/field_persistence.gd")

var repository: RefCounted
var session = Session.new()
var keyboard = Keyboard.new()
var images: RefCounted
var blocks: Dictionary = {}
var view: Control
var title: Label
var status: Label
var persistence: RefCounted
var profile_name := "default"


func _ready() -> void:
	var content_root := OS.get_environment("KADOKA_CONTENT_ROOT")
	if content_root.is_empty():
		content_root = ProjectSettings.globalize_path("res://").trim_suffix("/").get_base_dir()
	repository = Repository.new(content_root)
	images = Images.new(content_root)
	_create_ui()
	blocks = repository.load_blocks()
	if blocks.is_empty():
		status.text = repository.last_error
		set_process(false)
		return
	images.species["hero"] = repository.load_species("hero")
	open_map("starting_town")
	_setup_persistence()


func _create_ui() -> void:
	title = Label.new()
	title.position = Vector2(16, 10)
	add_child(title)
	view = FieldView.new()
	view.position = Vector2(16, 52)
	view.size = Vector2(928, 416)
	view.clip_contents = true
	view.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	add_child(view)
	status = Label.new()
	status.position = Vector2(16, 478)
	status.size = Vector2(928, 54)
	status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	status.text = "矢印 / WASD：移動　Enter / Space / E：調べる　F5：保存　F9：読込（戦闘は未移植）"
	add_child(status)


func open_map(map_id: String, entry: Dictionary = {}) -> bool:
	var world: Dictionary = repository.load_map(map_id)
	if world.is_empty():
		status.text = repository.last_error
		return false
	_enter_world(world, entry)
	return true


func _enter_world(world: Dictionary, entry: Dictionary) -> void:
	session.enter_map(world, blocks, entry)
	session.direction = str(entry.get("direction", session.direction))
	for mob: Dictionary in session.visible_characters:
		var species_id := str(mob["species_id"])
		images.species[species_id] = repository.load_species(species_id)
	_refresh_view()


func _setup_persistence() -> void:
	var save_root := OS.get_environment("KADOKA_GDSCRIPT_SAVE_ROOT")
	if save_root.is_empty():
		save_root = "user://savedata"
	var configured_name := OS.get_environment("KADOKA_GDSCRIPT_SAVE_NAME")
	if not configured_name.is_empty():
		profile_name = configured_name
	persistence = Persistence.new(repository, SaveStore.new(save_root), blocks, profile_name)
	load_saved_position(true)
	_refresh_view()


func save_current_position() -> bool:
	if persistence == null or session.world.is_empty():
		return false
	var result: Dictionary = persistence.save_position(session)
	status.text = "保存しました: " + profile_name if result["ok"] else "保存失敗: " + str(result["message"])
	return result["ok"]


func load_saved_position(silent_missing: bool = false) -> bool:
	var result: Dictionary = persistence.load_position()
	if not result["ok"]:
		if not silent_missing or result["error"] != "not_found":
			status.text = "読込失敗: " + str(result["message"])
		return false
	var entry: Dictionary = result["value"]["player"].duplicate()
	entry["direction"] = entry.get("direction", "front")
	_enter_world(result["world"], entry)
	status.text = "読み込みました: " + profile_name
	return true


func _process(delta: float) -> void:
	if session.world.is_empty():
		return
	var step: Vector2i = keyboard.movement_step(delta)
	if step != Vector2i.ZERO:
		var result: Dictionary = session.move_player(step.x, step.y)
		if result["kind"] == "moved" and result.get("event") != null:
			_handle_event(result["event"])
		_refresh_view()


func _unhandled_key_input(event: InputEvent) -> void:
	if not event is InputEventKey or not event.pressed or event.echo or session.world.is_empty():
		return
	match event.physical_keycode:
		KEY_F5:
			save_current_position()
		KEY_F9:
			load_saved_position()
		KEY_ENTER, KEY_SPACE, KEY_E:
			_handle_event(session.interaction_event())
		_:
			return
	get_viewport().set_input_as_handled()


func _handle_event(event: Dictionary) -> void:
	if event.is_empty():
		status.text = "目の前に調べるものはありません。"
		return
	if event.get("type") == "transition":
		var target: Dictionary = event.get("target", {})
		if open_map(str(target.get("map_id", "")), target):
			status.text = str(event.get("text", "マップを移動しました。"))
	elif event.get("type") == "message":
		status.text = str(event.get("text", ""))
	else:
		status.text = "[未移植: %s] %s" % [event.get("type", "event"), event.get("text", "")]


func _refresh_view() -> void:
	title.text = "%s  (%d, %d) — GDScript / %s" % [session.world.get("display_name", ""), session.x, session.y, profile_name]
	view.show_snapshot({
		"map": session.world, "blocks": blocks, "characters": session.visible_characters,
		"player": {"species_id": "hero", "x": session.x, "y": session.y, "direction": session.direction},
	}, images)
