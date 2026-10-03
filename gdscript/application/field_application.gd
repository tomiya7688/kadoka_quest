extends Control
## Composition/coordinator: data -> session -> renderer. Source-only prototype.

const Repository = preload("res://data/content_repository.gd")
const Session = preload("res://application/field_session.gd")
const Keyboard = preload("res://ui/field_input.gd")
const Images = preload("res://ui/content_images.gd")
const FieldView = preload("res://ui/field_view.gd")
const RosterView = preload("res://ui/roster_view.gd")
const PartyView = preload("res://ui/party_view.gd")
const PartyEditor = preload("res://application/party_editor.gd")
const PresetService = preload("res://application/party_presets.gd")
const PresetView = preload("res://ui/party_preset_view.gd")
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
var owned_snapshot: Dictionary = {"records": {}, "party": [], "warnings": []}
var roster_view: PanelContainer
var party_view: PanelContainer
var party_editor: RefCounted
var presets: RefCounted
var preset_view: PanelContainer


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
	status.text = "矢印 / WASD：移動　Enter / Space / E：調べる　F5：保存　F9：読込　F6：個体確認"
	add_child(status)
	roster_view = RosterView.new()
	roster_view.position = Vector2(48, 64)
	roster_view.size = Vector2(864, 396)
	add_child(roster_view)
	roster_view.hide()
	roster_view.edit_requested.connect(begin_party_edit)
	party_view = PartyView.new()
	party_view.position = Vector2(48, 64)
	party_view.size = Vector2(864, 396)
	add_child(party_view)
	party_view.hide()
	party_view.assigned.connect(assign_party_member)
	party_view.save_requested.connect(save_party_edit)
	party_view.cancel_requested.connect(cancel_party_edit)
	party_view.presets_requested.connect(open_party_presets)
	preset_view = PresetView.new()
	preset_view.position = Vector2(48, 64)
	preset_view.size = Vector2(864, 396)
	add_child(preset_view)
	preset_view.hide()
	preset_view.save_requested.connect(save_party_preset)
	preset_view.load_requested.connect(load_party_preset)
	preset_view.refresh_requested.connect(refresh_party_presets)
	preset_view.back_requested.connect(close_party_presets)


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
	presets = PresetService.new(persistence)
	load_saved_position(true)
	_refresh_view()


func save_current_position() -> bool:
	if persistence == null or session.world.is_empty():
		return false
	var result: Dictionary = persistence.save_position(session)
	status.text = "保存しました: " + profile_name if result["ok"] else "保存失敗: " + str(result["message"])
	if result["ok"]:
		_refresh_owned_snapshot()
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
	_refresh_owned_snapshot()
	return true


func _process(delta: float) -> void:
	if session.world.is_empty() or roster_view.visible or party_view.visible or preset_view.visible:
		return
	var step: Vector2i = keyboard.movement_step(delta)
	if step != Vector2i.ZERO:
		var result: Dictionary = session.move_player(step.x, step.y)
		if result["kind"] == "moved" and result.get("event") != null:
			_handle_event(result["event"])
		_refresh_view()


func _unhandled_key_input(event: InputEvent) -> void:
	if party_view.visible or roster_view.visible or preset_view.visible:
		return
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


func _input(event: InputEvent) -> void:
	if not event is InputEventKey or not event.pressed or persistence == null:
		return
	if preset_view.visible:
		match event.physical_keycode:
			KEY_ESCAPE, KEY_F6:
				close_party_presets()
			KEY_F5:
				refresh_party_presets()
			KEY_F9:
				pass  # Never field-load while a party draft is open.
			KEY_HOME, KEY_END, KEY_PAGEUP, KEY_PAGEDOWN:
				if not preset_view.handle_navigation(event.physical_keycode):
					return
			_:
				return  # Native list/LineEdit/Button keyboard handling, including text.
		get_viewport().set_input_as_handled()
		return
	if party_view.visible:
		if event.echo:
			return
		match event.physical_keycode:
			KEY_ESCAPE, KEY_F6:
				cancel_party_edit()
			KEY_DELETE:
				party_view.clear_selected()
			KEY_P:
				open_party_presets()
			KEY_S:
				if not event.ctrl_pressed:
					return
				save_party_edit()
			KEY_F5, KEY_F9:
				pass  # A draft can only be saved explicitly through the editor.
			KEY_HOME, KEY_END, KEY_PAGEUP, KEY_PAGEDOWN:
				if not party_view.handle_navigation(event.physical_keycode):
					return
			_:
				return  # Native ItemList/Button/Tab keyboard handling.
		get_viewport().set_input_as_handled()
		return
	if event.physical_keycode == KEY_F6 and not event.echo:
		if roster_view.visible:
			roster_view.hide()
		else:
			_refresh_owned_snapshot()
			roster_view.show_snapshot(owned_snapshot)
			roster_view.show()
	elif roster_view.visible:
		if event.physical_keycode == KEY_ESCAPE:
			roster_view.hide()
		elif event.physical_keycode == KEY_E and not event.echo:
			begin_party_edit()
		else:
			roster_view.handle_key(event.physical_keycode)
	else:
		return
	get_viewport().set_input_as_handled()


func begin_party_edit() -> void:
	var editor = PartyEditor.new(persistence)
	var result: Dictionary = editor.begin()
	if not result["ok"]:
		status.text = "編成を開けません: " + str(result["message"])
		return
	party_editor = editor
	roster_view.hide()
	party_view.show()
	party_view.show_snapshot(party_editor.snapshot(), true)


func assign_party_member(slot: int, id: Variant) -> void:
	var result: Dictionary = party_editor.assign(slot, id)
	party_view.show_snapshot(party_editor.snapshot())
	party_view.message.text = "未保存の編成です。保存またはキャンセルを選んでください。" if result["ok"] else str(result["message"])


func save_party_edit() -> void:
	var result: Dictionary = party_editor.save()
	if not result["ok"]:
		party_view.message.text = "編成保存失敗: " + str(result["message"])
		return
	status.text = result["message"]
	_finish_party_edit()


func cancel_party_edit() -> void:
	status.text = "編成をキャンセルしました。保存データは変更していません。"
	_finish_party_edit()


func _finish_party_edit() -> void:
	party_view.hide()
	party_editor = null
	_refresh_owned_snapshot()
	roster_view.show_snapshot(owned_snapshot)
	roster_view.show()


func open_party_presets() -> void:
	party_view.hide()
	preset_view.show()
	preset_view.name_input.clear()
	preset_view.show_catalog(presets.read_catalog(), true)


func refresh_party_presets() -> void:
	preset_view.show_catalog(presets.read_catalog())


func save_party_preset(name: String) -> void:
	var result: Dictionary = presets.save_new(name, party_editor.member_ids())
	if not result["ok"]:
		preset_view.message.text = "追加保存失敗: " + str(result["message"])
		return
	preset_view.show_catalog(presets.read_catalog(), false, result["filename"])
	preset_view.message.text = "追加保存しました: " + result["filename"] + "（現在パーティは未保存）"


func load_party_preset(filename: String) -> void:
	var result: Dictionary = presets.load_draft(filename, party_editor)
	if not result["ok"]:
		preset_view.message.text = "読込失敗: " + str(result["message"])
		return
	close_party_presets()
	party_view.show_snapshot(party_editor.snapshot(), true)
	party_view.message.text = "プリセットを下書きへ読み込みました。保存またはキャンセルを選んでください。"
	if not result["warnings"].is_empty():
		party_view.message.text = "注意%d件: %s（下書きのみ変更）" % [result["warnings"].size(), str(result["warnings"][0])]


func close_party_presets() -> void:
	preset_view.hide()
	party_view.show()
	party_view.slots.grab_focus.call_deferred()


func _refresh_owned_snapshot() -> void:
	var result: Dictionary = persistence.read_owned_roster()
	if result["ok"]:
		owned_snapshot = result
	else:
		owned_snapshot = {"records": {}, "party": [], "warnings": [result["message"]],
			"new_profile": result.get("error") == "not_found"}


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
