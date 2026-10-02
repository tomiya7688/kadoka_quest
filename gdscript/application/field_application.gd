extends Control
## Composition/coordinator: data -> session -> renderer. Source-only prototype.

const Repository = preload("res://data/content_repository.gd")
const Session = preload("res://application/field_session.gd")
const Keyboard = preload("res://ui/field_input.gd")
const Images = preload("res://ui/content_images.gd")
const FieldView = preload("res://ui/field_view.gd")

var repository: RefCounted
var session = Session.new()
var keyboard = Keyboard.new()
var images: RefCounted
var blocks: Dictionary = {}
var view: Control
var title: Label
var status: Label


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
	status.text = "GDScript試作：矢印 / WASDで移動・長押し、Enter / Space / Eで調べる。セーブ・戦闘は未移植です。"
	add_child(status)


func open_map(map_id: String, entry: Dictionary = {}) -> bool:
	var world: Dictionary = repository.load_map(map_id)
	if world.is_empty():
		status.text = repository.last_error
		return false
	session.enter_map(world, blocks, entry)
	for mob: Dictionary in session.visible_characters:
		var species_id := str(mob["species_id"])
		images.species[species_id] = repository.load_species(species_id)
	_refresh_view()
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
	if event is InputEventKey and event.pressed and not event.echo \
		and event.physical_keycode in [KEY_ENTER, KEY_SPACE, KEY_E] and not session.world.is_empty():
		_handle_event(session.interaction_event())
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
	title.text = "%s  (%d, %d) — GDScript試作 / 保存なし" % [session.world.get("display_name", ""), session.x, session.y]
	view.show_snapshot({
		"map": session.world, "blocks": blocks, "characters": session.visible_characters,
		"player": {"species_id": "hero", "x": session.x, "y": session.y, "direction": session.direction},
	}, images)
