extends PanelContainer
## Selection/focus and draft projection only. All changes/save requests are signals.

signal assigned(slot: int, id: Variant)
signal save_requested
signal cancel_requested
var slots: ItemList
var owned: ItemList
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
	help.text = "左で枠、右で個体を選択 → 入れる / Enter　Delete：外す\n↑↓・Home/End・PageUp/Down：選択　Tab：フォーカス移動　Ctrl+S：保存　Esc / F6：キャンセル"
	help.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	column.add_child(help)
	var lists := HBoxContainer.new()
	lists.size_flags_vertical = Control.SIZE_EXPAND_FILL
	column.add_child(lists)
	slots = _list(lists, 300)
	owned = _list(lists, 430)
	owned.item_activated.connect(func(_index: int): assign_selected())
	var actions := HBoxContainer.new()
	column.add_child(actions)
	_button(actions, "assign", "選択個体を入れる", assign_selected)
	_button(actions, "clear", "選択枠から外す", clear_selected)
	_button(actions, "save", "編成を保存", func(): save_requested.emit())
	_button(actions, "cancel", "キャンセル", func(): cancel_requested.emit())
	message = Label.new()
	message.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	column.add_child(message)
	# Do not let Tab or directional focus escape into the covered roster/field.
	var focus_order: Array[Control] = [slots, owned, buttons["assign"], buttons["clear"], buttons["save"], buttons["cancel"]]
	for index in focus_order.size():
		focus_order[index].focus_next = focus_order[index].get_path_to(focus_order[(index + 1) % focus_order.size()])
		focus_order[index].focus_previous = focus_order[index].get_path_to(focus_order[(index - 1 + focus_order.size()) % focus_order.size()])


func _list(parent: Control, width: float) -> ItemList:
	var list := ItemList.new()
	list.custom_minimum_size = Vector2(width, 120)
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	list.allow_reselect = true
	list.allow_search = false
	list.wraparound_items = false
	parent.add_child(list)
	return list


func _button(parent: Control, id: String, text: String, callback: Callable) -> void:
	var button := Button.new()
	button.text = text
	button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	button.pressed.connect(callback)
	parent.add_child(button)
	buttons[id] = button


func show_snapshot(snapshot: Dictionary, rebuild_owned: bool = false) -> void:
	heading.text = "現在パーティの編成" + ("（未保存）" if snapshot["dirty"] else "")
	var selected := slots.get_selected_items()
	var slot := selected[0] if not selected.is_empty() else 0
	slots.clear()
	for index in snapshot["party"].size():
		var entry: Dictionary = snapshot["party"][index]
		var label := "空き枠"
		if entry["record"] is Dictionary:
			label = _summary(entry["record"])
		elif entry["id"] != null:
			label = "読込不可: " + str(entry["id"])
		slots.add_item("%d. %s" % [index + 1, label])
		slots.set_item_tooltip(index, label)
	slots.select(slot)
	if rebuild_owned:
		owned.clear()
		for id: String in snapshot["records"]:
			var index := owned.add_item(_summary(snapshot["records"][id]))
			owned.set_item_metadata(index, id)
			owned.set_item_tooltip(index, _summary(snapshot["records"][id]) + "\nID: " + id)
		if owned.item_count > 0:
			owned.select(0)
		message.text = "保存するまで反映されません。個体/AIは変更しません。"
		if not snapshot["warnings"].is_empty():
			message.text = "読込不可の個体があります。一覧の注意を確認し、該当する枠は外してください。"
		slots.grab_focus.call_deferred()


static func _summary(record: Dictionary) -> String:
	return "%s（%s） Lv.%d" % [record["monster"]["name"], record["species"].get("display_name", ""), int(record["monster"].get("level", 1))]


func assign_selected() -> void:
	var selected := owned.get_selected_items()
	if selected.is_empty():
		message.text = "右側の保有個体を選択してください。"
		return
	assigned.emit(_selected_slot(), owned.get_item_metadata(selected[0]))


func clear_selected() -> void:
	assigned.emit(_selected_slot(), null)


func handle_navigation(key: int) -> bool:
	var focused := get_viewport().gui_get_focus_owner()
	if focused != slots and focused != owned:
		return false
	var list: ItemList = focused
	if list.item_count == 0:
		return true
	var selected := list.get_selected_items()
	var index := selected[0] if not selected.is_empty() else 0
	var page := maxi(1, int(list.size.y / maxf(1, list.get_item_rect(0).size.y)))
	match key:
		KEY_HOME: index = 0
		KEY_END: index = list.item_count - 1
		KEY_PAGEUP: index -= page
		KEY_PAGEDOWN: index += page
		_: return false
	list.select(clampi(index, 0, list.item_count - 1))
	list.ensure_current_is_visible()
	return true


func _selected_slot() -> int:
	var selected := slots.get_selected_items()
	return selected[0] if not selected.is_empty() else -1
