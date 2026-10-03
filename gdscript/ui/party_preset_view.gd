extends PanelContainer
## Preset list/name input and semantic signals only; no files or party mutation.

signal save_requested(name: String)
signal load_requested(filename: String)
signal refresh_requested
signal back_requested
var listing: ItemList
var name_input: LineEdit
var heading: Label
var message: Label
var buttons: Dictionary = {}


func _ready() -> void:
	var style := StyleBoxFlat.new()
	style.bg_color = Color("#091329")
	style.border_color = Color("#d5e0f2")
	style.set_border_width_all(2)
	style.set_content_margin_all(16)
	add_theme_stylebox_override("panel", style)
	var column := VBoxContainer.new()
	add_child(column)
	heading = Label.new()
	heading.add_theme_font_size_override("font_size", 20)
	column.add_child(heading)
	var help := Label.new()
	help.text = "現在の下書きを別名で追加保存 / 選択プリセットを下書きへ読込\n↑↓・Home/End・PageUp/Down：選択　Tab：巡回　Enter：読込　F5：一覧更新　Esc/F6：戻る"
	help.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	column.add_child(help)
	listing = ItemList.new()
	listing.size_flags_vertical = Control.SIZE_EXPAND_FILL
	listing.custom_minimum_size.y = 100
	listing.allow_search = false
	listing.wraparound_items = false
	listing.item_activated.connect(func(_index: int): request_load())
	column.add_child(listing)
	name_input = LineEdit.new()
	name_input.placeholder_text = "新しいプリセット名（同名も別ファイルへ追加）"
	name_input.keep_editing_on_text_submit = true
	name_input.text_submitted.connect(func(_text: String): save_requested.emit(name_input.text))
	column.add_child(name_input)
	var actions := HBoxContainer.new()
	column.add_child(actions)
	_button(actions, "save", "下書きを追加保存", func(): save_requested.emit(name_input.text))
	_button(actions, "load", "選択を下書きへ読込", request_load)
	_button(actions, "refresh", "一覧更新", func(): refresh_requested.emit())
	_button(actions, "back", "編成へ戻る", func(): back_requested.emit())
	message = Label.new()
	message.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	column.add_child(message)
	var order: Array[Control] = [listing, name_input, buttons["save"], buttons["load"], buttons["refresh"], buttons["back"]]
	for index in order.size():
		order[index].focus_next = order[index].get_path_to(order[(index + 1) % order.size()])
		order[index].focus_previous = order[index].get_path_to(order[(index - 1 + order.size()) % order.size()])


func _button(parent: Control, id: String, text: String, callback: Callable) -> void:
	var button := Button.new()
	button.text = text
	button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	button.pressed.connect(callback)
	parent.add_child(button)
	buttons[id] = button


func show_catalog(catalog: Dictionary, focus_list: bool = false, prefer: String = "") -> void:
	var selected := listing.get_selected_items()
	var previous: String = prefer
	if previous.is_empty() and not selected.is_empty():
		previous = listing.get_item_metadata(selected[0])
	listing.clear()
	if not catalog["ok"]:
		heading.text = "保存パーティのプリセット"
		message.text = "一覧読込失敗: " + str(catalog["message"])
		if focus_list:
			listing.grab_focus.call_deferred()
		return
	heading.text = "保存パーティのプリセット（%d件 / 上限なし）" % catalog["entries"].size()
	var selected_index := 0
	for entry: Dictionary in catalog["entries"]:
		var members: PackedStringArray = []
		for id in entry["members"]:
			members.append(str(id) if id != null else "空き")
		var index := listing.add_item(str(entry["name"]).replace("\n", " ") + " — " + " / ".join(members))
		listing.set_item_metadata(index, entry["filename"])
		listing.set_item_tooltip(index, str(entry["name"]) + "\n" + entry["filename"] + "\n" + " / ".join(members))
		if entry["filename"] == previous:
			selected_index = index
	if listing.item_count > 0:
		listing.select(selected_index)
		listing.ensure_current_is_visible()
	message.text = "読込は下書きだけを置換します。現在パーティへの反映は編成画面の保存で行います。"
	if not catalog["warnings"].is_empty():
		message.text = "注意%d件: %s" % [catalog["warnings"].size(), str(catalog["warnings"][0])]
	if focus_list:
		listing.grab_focus.call_deferred()


func request_load() -> void:
	var selected := listing.get_selected_items()
	if selected.is_empty():
		message.text = "読込するプリセットを選択してください。"
		return
	load_requested.emit(str(listing.get_item_metadata(selected[0])))


func handle_navigation(key: int) -> bool:
	if not listing.has_focus():
		return false  # Home/End and Page keys must not steal the name field's caret.
	if listing.item_count == 0:
		return true
	var selected := listing.get_selected_items()
	var index := selected[0] if not selected.is_empty() else 0
	var page := maxi(1, int(listing.size.y / maxf(1, listing.get_item_rect(0).size.y)))
	match key:
		KEY_HOME: index = 0
		KEY_END: index = listing.item_count - 1
		KEY_PAGEUP: index -= page
		KEY_PAGEDOWN: index += page
		_: return false
	listing.select(clampi(index, 0, listing.item_count - 1))
	listing.ensure_current_is_visible()
	return true
