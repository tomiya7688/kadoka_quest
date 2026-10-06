# {
#   責務: [field_application: Composition/coordinator: data -> session -> renderer. Source-only prototype.]
#   フィールド: [
#     repository: データ取得先（RefCounted）
#     session: セッション
#     keyboard: keyboard
#     images: 画像一覧（RefCounted）
#     blocks: ブロック定義（Dictionary）
#     view: 表示（Control）
#     title: title（Label）
#     status: 状態異常（Label）
#     persistence: persistence（RefCounted）
#     profile_name: プロファイル・名前
#     owned_snapshot: owned・独立した状態の写し（Dictionary）
#     roster_view: 所有個体台帳・表示（PanelContainer）
#     party_view: パーティ・表示（PanelContainer）
#     party_editor: パーティ・editor（RefCounted）
#     presets: プリセット一覧（RefCounted）
#     preset_view: プリセット・表示（PanelContainer）
#     password_session: 暗号・セッション
#     password_view: 暗号・表示（PanelContainer）
#     password_outcome: 暗号・結果（Dictionary）
#     ghost_acquisition: おばけ・acquisition（RefCounted）
#     ghost_request: おばけ・要求（Dictionary）
#     acquisition_result: acquisition・処理結果（Dictionary）
#     church_registration: 教会・registration（RefCounted）
#     church_result: 教会・処理結果（Dictionary）
#   ]
# }
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
const PasswordSession = preload("res://engine/password_session.gd")
const PasswordView = preload("res://ui/password_view.gd")
const GhostAcquisition = preload("res://application/ghost_acquisition.gd")
const ChurchRegistration = preload("res://application/church_registration.gd")
signal password_finished(result: Dictionary)

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
var password_session = PasswordSession.new()
var password_view: PanelContainer
var password_outcome: Dictionary = {}
var ghost_acquisition: RefCounted
var ghost_request: Dictionary = {}
var acquisition_result: Dictionary = {}
var church_registration: RefCounted
var church_result: Dictionary = {}


# {
#   責務: [_ready: フィールド・applicationのエントリ処理を実行する]
#   処理: [1: フィールド・applicationのエントリ処理を実行する]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
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


# {
#   責務: [_create_ui: uiを作成する]
#   処理: [1: uiを作成する]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
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
	password_view = PasswordView.new()
	password_view.position = Vector2(48, 24)
	password_view.size = Vector2(864, 492)
	add_child(password_view)
	password_view.hide()
	password_view.configure_keys(PasswordSession.KANA_KEYS)
	password_view.character_requested.connect(append_password)
	password_view.backspace_requested.connect(backspace_password)
	password_view.submit_requested.connect(submit_password)
	password_view.cancel_requested.connect(cancel_password)


# {
#   責務: [open_map: マップを開く]
#   処理: [1: マップを開く]
#   引数: [
#     map_id: マップ・識別子（String）
#     entry: 項目（Dictionary）
#   ]
#   戻り値: [result: マップを開くための結果（bool）]
# }
func open_map(map_id: String, entry: Dictionary = {}) -> bool:
	var world: Dictionary = repository.load_map(map_id)
	if world.is_empty():
		status.text = repository.last_error
		return false
	_enter_world(world, entry)
	return true


# {
#   責務: [_enter_world: フィールド・applicationのenter・マップ状態を求める]
#   処理: [1: フィールド・applicationのenter・マップ状態を求める]
#   引数: [
#     world: マップ状態（Dictionary）
#     entry: 項目（Dictionary）
#   ]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _enter_world(world: Dictionary, entry: Dictionary) -> void:
	session.enter_map(world, blocks, entry)
	session.direction = str(entry.get("direction", session.direction))
	for mob: Dictionary in session.visible_characters:
		var species_id := str(mob["species_id"])
		images.species[species_id] = repository.load_species(species_id)
	_refresh_view()


# {
#   責務: [_setup_persistence: フィールド・applicationのsetup・persistenceを求める]
#   処理: [1: フィールド・applicationのsetup・persistenceを求める]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _setup_persistence() -> void:
	var save_root := OS.get_environment("KADOKA_GDSCRIPT_SAVE_ROOT")
	if save_root.is_empty():
		save_root = "user://savedata"
	var configured_name := OS.get_environment("KADOKA_GDSCRIPT_SAVE_NAME")
	if not configured_name.is_empty():
		profile_name = configured_name
	persistence = Persistence.new(repository, SaveStore.new(save_root), blocks, profile_name)
	ghost_acquisition = GhostAcquisition.new(persistence)
	church_registration = ChurchRegistration.new(persistence)
	password_finished.connect(_on_password_finished)
	presets = PresetService.new(persistence)
	load_saved_position(true)
	_refresh_view()


# {
#   責務: [save_current_position: current・座標を保存する]
#   処理: [1: current・座標を保存する]
#   引数: []
#   戻り値: [result: current・座標を保存するための結果（bool）]
# }
func save_current_position() -> bool:
	if password_session.active or persistence == null or session.world.is_empty():
		return false
	var result: Dictionary = persistence.save_position(session)
	status.text = "保存しました: " + profile_name if result["ok"] else "保存失敗: " + str(result["message"])
	if result["ok"]:
		_refresh_owned_snapshot()
	return result["ok"]


# {
#   責務: [load_saved_position: saved・座標を読み込む]
#   処理: [1: saved・座標を読み込む]
#   引数: [silent_missing: silent・missing（bool）]
#   戻り値: [result: saved・座標を読み込むための結果（bool）]
# }
func load_saved_position(silent_missing: bool = false) -> bool:
	if password_session.active:
		return false
	var result: Dictionary = persistence.load_position()
	if not result["ok"]:
		if not silent_missing or result["error"] != "not_found":
			status.text = "読込失敗: " + str(result["message"])
		return false
	var entry: Dictionary = result["value"]["player"].duplicate()
	entry["direction"] = entry.get("direction", "front")
	var despawned: Variant = result["value"].get("despawned_fixed_mobs", [])
	session.despawned_fixed_mobs = despawned.duplicate() if despawned is Array else []
	_enter_world(result["world"], entry)
	status.text = "読み込みました: " + profile_name
	_refresh_owned_snapshot()
	return true


# {
#   責務: [_process: フィールド・applicationのprocessを求める]
#   処理: [1: フィールド・applicationのprocessを求める]
#   引数: [delta: 経過時間（float）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _process(delta: float) -> void:
	if session.world.is_empty() or password_session.active or roster_view.visible or party_view.visible or preset_view.visible:
		return
	session.advance(delta)
	var step: Vector2i = keyboard.movement_step(delta)
	if step != Vector2i.ZERO:
		var result: Dictionary = session.move_player(step.x, step.y)
		if result["kind"] == "moved" and result.get("event") != null:
			_handle_event(result["event"])
		_refresh_view()
	elif not session.visible_characters.is_empty():
		_refresh_view()  # Publish interpolated positions; renderer never advances actors.


# {
#   責務: [_unhandled_key_input: フィールド・applicationのunhandled・キー・入力を求める]
#   処理: [1: フィールド・applicationのunhandled・キー・入力を求める]
#   引数: [event: イベント（InputEvent）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _unhandled_key_input(event: InputEvent) -> void:
	if password_session.active or party_view.visible or roster_view.visible or preset_view.visible:
		return
	if not event is InputEventKey or not event.pressed or event.echo or session.world.is_empty():
		return
	match event.physical_keycode:
		KEY_F5:
			save_current_position()
		KEY_F9:
			load_saved_position()
		KEY_ENTER, KEY_SPACE, KEY_E:
			_handle_interaction(session.interact())
		_:
			return
	get_viewport().set_input_as_handled()


# {
#   責務: [_input: フィールド・applicationの入力を求める]
#   処理: [1: フィールド・applicationの入力を求める]
#   引数: [event: イベント（InputEvent）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _input(event: InputEvent) -> void:
	if password_session.active:
		if event is InputEventKey and event.pressed and password_view.handle_key(event):
			get_viewport().set_input_as_handled()
		return
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
			open_owned_roster()
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


# {
#   責務: [open_owned_roster: owned・所有個体台帳を開く]
#   処理: [1: owned・所有個体台帳を開く]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func open_owned_roster() -> void:
	if password_session.active:
		return
	_refresh_owned_snapshot()
	roster_view.show_snapshot(owned_snapshot)
	roster_view.show()


# {
#   責務: [begin_party_edit: パーティ・editを開始する]
#   処理: [1: パーティ・editを開始する]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func begin_party_edit() -> void:
	if password_session.active:
		return
	var editor = PartyEditor.new(persistence)
	var result: Dictionary = editor.begin()
	if not result["ok"]:
		status.text = "編成を開けません: " + str(result["message"])
		return
	party_editor = editor
	roster_view.hide()
	party_view.show()
	party_view.show_snapshot(party_editor.snapshot(), true)


# {
#   責務: [assign_party_member: フィールド・applicationのassign・パーティ・個体を求める]
#   処理: [1: フィールド・applicationのassign・パーティ・個体を求める]
#   引数: [
#     slot: 編成枠（int）
#     id: 識別子（Variant）
#   ]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func assign_party_member(slot: int, id: Variant) -> void:
	var result: Dictionary = party_editor.assign(slot, id)
	party_view.show_snapshot(party_editor.snapshot())
	party_view.message.text = "未保存の編成です。保存またはキャンセルを選んでください。" if result["ok"] else str(result["message"])


# {
#   責務: [save_party_edit: パーティ・editを保存する]
#   処理: [1: パーティ・editを保存する]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func save_party_edit() -> void:
	var result: Dictionary = party_editor.save()
	if not result["ok"]:
		party_view.message.text = "編成保存失敗: " + str(result["message"])
		return
	status.text = result["message"]
	_finish_party_edit()


# {
#   責務: [cancel_party_edit: フィールド・applicationのcancel・パーティ・editを求める]
#   処理: [1: フィールド・applicationのcancel・パーティ・editを求める]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func cancel_party_edit() -> void:
	status.text = "編成をキャンセルしました。保存データは変更していません。"
	_finish_party_edit()


# {
#   責務: [_finish_party_edit: パーティ・editを終了処理を行う]
#   処理: [1: パーティ・editを終了処理を行う]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _finish_party_edit() -> void:
	party_view.hide()
	party_editor = null
	_refresh_owned_snapshot()
	roster_view.show_snapshot(owned_snapshot)
	roster_view.show()


# {
#   責務: [open_party_presets: パーティ・プリセット一覧を開く]
#   処理: [1: パーティ・プリセット一覧を開く]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func open_party_presets() -> void:
	party_view.hide()
	preset_view.show()
	preset_view.name_input.clear()
	preset_view.show_catalog(presets.read_catalog(), true)


# {
#   責務: [refresh_party_presets: パーティ・プリセット一覧を更新内容を読み直す]
#   処理: [1: パーティ・プリセット一覧を更新内容を読み直す]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func refresh_party_presets() -> void:
	preset_view.show_catalog(presets.read_catalog())


# {
#   責務: [save_party_preset: パーティ・プリセットを保存する]
#   処理: [1: パーティ・プリセットを保存する]
#   引数: [name: 名前（String）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func save_party_preset(name: String) -> void:
	var result: Dictionary = presets.save_new(name, party_editor.member_ids())
	if not result["ok"]:
		preset_view.message.text = "追加保存失敗: " + str(result["message"])
		return
	preset_view.show_catalog(presets.read_catalog(), false, result["filename"])
	preset_view.message.text = "追加保存しました: " + result["filename"] + "（現在パーティは未保存）"


# {
#   責務: [load_party_preset: パーティ・プリセットを読み込む]
#   処理: [1: パーティ・プリセットを読み込む]
#   引数: [filename: filename（String）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
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


# {
#   責務: [close_party_presets: パーティ・プリセット一覧を閉じる]
#   処理: [1: パーティ・プリセット一覧を閉じる]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func close_party_presets() -> void:
	preset_view.hide()
	party_view.show()
	party_view.slots.grab_focus.call_deferred()


# {
#   責務: [_refresh_owned_snapshot: owned・独立した状態の写しを更新内容を読み直す]
#   処理: [1: owned・独立した状態の写しを更新内容を読み直す]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _refresh_owned_snapshot() -> void:
	var result: Dictionary = persistence.read_owned_roster()
	if result["ok"]:
		owned_snapshot = result
	else:
		owned_snapshot = {"records": {}, "party": [], "warnings": [result["message"]],
			"new_profile": result.get("error") == "not_found"}


# {
#   責務: [_handle_interaction: interactionを入力を処理する]
#   処理: [1: interactionを入力を処理する]
#   引数: [result: 処理結果（Dictionary）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _handle_interaction(result: Dictionary) -> void:
	match result["kind"]:
		"event":
			_handle_event(result["event"])
		"dialogue":
			status.text = "%s『%s』" % [result["name"], result["line"]]
			if result.get("unported_despawn", false):
				status.text += " [未移植: 会話後の消滅]"
		"dialogue_error":
			status.text = "%s: %s" % [result["name"], result["message"]]
	_refresh_view()  # Publish the NPC's turned direction, not a renderer-side effect.


# {
#   責務: [_handle_event: イベントを入力を処理する]
#   処理: [1: イベントを入力を処理する]
#   引数: [event: イベント（Dictionary）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
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
	elif event.get("type") == "open_manager":
		open_owned_roster()
		status.text = "牧場台帳を開きました。Eで編成、編成のPでプリセット。個体編集・AI変更は未移植です。"
	elif event.get("type") == "password_spring":
		open_password_input()
	elif event.get("type") == "church":
		register_church(event.get("revive"))
	else:
		status.text = "[未移植: %s] %s" % [event.get("type", "event"), event.get("text", "")]


# {
#   責務: [register_church: 教会を登録する]
#   処理: [1: 教会を登録する]
#   引数: [revive: 復活（Variant）]
#   戻り値: [result: 教会を登録するための結果（Dictionary）]
# }
func register_church(revive: Variant) -> Dictionary:
	if password_session.active or roster_view.visible or party_view.visible or preset_view.visible:
		return {"ok": false, "error": "modal_active", "message": "画面を閉じてから教会を調べてください。"}
	church_result = church_registration.register(revive)
	status.text = church_result["message"]
	return church_result


# {
#   責務: [open_password_input: 暗号・入力を開く]
#   処理: [1: 暗号・入力を開く]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func open_password_input() -> void:
	ghost_request = ghost_acquisition.begin()
	acquisition_result = {}
	password_session.open()
	password_outcome = {}
	keyboard.reset()
	password_view.show_snapshot(password_session.snapshot(), true)


# {
#   責務: [append_password: 暗号を末尾へ追加する]
#   処理: [1: 暗号を末尾へ追加する]
#   引数: [character: キャラクター（String）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func append_password(character: String) -> void:
	password_session.append(character)
	password_view.show_snapshot(password_session.snapshot())


# {
#   責務: [backspace_password: フィールド・applicationのbackspace・暗号を求める]
#   処理: [1: フィールド・applicationのbackspace・暗号を求める]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func backspace_password() -> void:
	password_session.backspace()
	password_view.show_snapshot(password_session.snapshot())


# {
#   責務: [submit_password: 暗号を確定する]
#   処理: [1: 暗号を確定する]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func submit_password() -> void:
	if not password_session.submit():
		password_view.show_snapshot(password_session.snapshot())
		return
	_finish_password({"kind": "password_matched"}, "あいことばは一致しました。")


# {
#   責務: [cancel_password: フィールド・applicationのcancel・暗号を求める]
#   処理: [1: フィールド・applicationのcancel・暗号を求める]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func cancel_password() -> void:
	password_session.cancel()
	_finish_password({"kind": "password_cancelled"}, "あいことばの入力をやめました。保存データは変更していません。")


# {
#   責務: [_finish_password: 暗号を終了処理を行う]
#   処理: [1: 暗号を終了処理を行う]
#   引数: [
#     result: 処理結果（Dictionary）
#     text: 文字列（String）
#   ]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _finish_password(result: Dictionary, text: String) -> void:
	password_view.hide()
	keyboard.reset()
	password_outcome = result
	status.text = text
	password_finished.emit(result.duplicate())


# {
#   責務: [_on_password_finished: フィールド・applicationのon・暗号・finishedを求める]
#   処理: [1: フィールド・applicationのon・暗号・finishedを求める]
#   引数: [result: 処理結果（Dictionary）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _on_password_finished(result: Dictionary) -> void:
	if result["kind"] != "password_matched":
		return
	acquisition_result = ghost_acquisition.acquire(ghost_request)
	status.text = acquisition_result["message"]
	_refresh_owned_snapshot()  # Publish verified additions, including explicit partial success.


# {
#   責務: [_refresh_view: 表示を更新内容を読み直す]
#   処理: [1: 表示を更新内容を読み直す]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _refresh_view() -> void:
	title.text = "%s  (%d, %d) — GDScript / %s" % [session.world.get("display_name", ""), session.x, session.y, profile_name]
	if not session.fixed_mobs.warnings.is_empty():
		title.text += " / " + str(session.fixed_mobs.warnings[0])
	view.show_snapshot({
		"map": session.world, "blocks": blocks, "characters": session.character_snapshot(),
		"player": {"species_id": "hero", "x": session.x, "y": session.y, "direction": session.direction},
	}, images)
