extends PanelContainer
## Native/virtual input -> semantic signals; render snapshots, never judge a password.

signal character_requested(character: String)
signal backspace_requested
signal submit_requested
signal cancel_requested
var slots: Array[Label] = []
var buttons: Dictionary = {}
var text_input: LineEdit
var message: Label
var keyboard_grid: GridContainer


func _ready() -> void:
	var style := StyleBoxFlat.new()
	style.bg_color = Color("#091329")
	style.border_color = Color("#d5e0f2")
	style.set_border_width_all(2)
	style.set_content_margin_all(12)
	add_theme_stylebox_override("panel", style)
	var column := VBoxContainer.new()
	add_child(column)
	var heading := Label.new()
	heading.text = "水の湧き場 — 7文字のあいことば"
	heading.add_theme_font_size_override("font_size", 18)
	column.add_child(heading)
	var help := Label.new()
	help.add_theme_font_size_override("font_size", 14)
	help.text = "かな入力 / 下のキーをクリック　Enter：決定　Backspace：けす　Esc：やめる\nTab：入力欄とキーを巡回（探索・保存は入力中停止）"
	help.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	column.add_child(help)
	var slot_row := HBoxContainer.new()
	column.add_child(slot_row)
	for index in 7:
		var slot := Label.new()
		slot.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		slot.custom_minimum_size = Vector2(64, 32)
		slot.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		slot.add_theme_font_size_override("font_size", 22)
		slot_row.add_child(slot)
		slots.append(slot)
	text_input = LineEdit.new()
	text_input.add_theme_font_size_override("font_size", 14)
	text_input.placeholder_text = "日本語入力（確定した文字を上の7枠へ入力）"
	text_input.keep_editing_on_text_submit = true
	text_input.text_changed.connect(_committed_text)
	column.add_child(text_input)
	keyboard_grid = GridContainer.new()
	keyboard_grid.columns = 10
	keyboard_grid.size_flags_vertical = Control.SIZE_EXPAND_FILL
	column.add_child(keyboard_grid)
	var actions := HBoxContainer.new()
	column.add_child(actions)
	_button(actions, "backspace", "けす", func(): backspace_requested.emit())
	_button(actions, "submit", "決定", func(): submit_requested.emit())
	_button(actions, "cancel", "やめる", func(): cancel_requested.emit())
	message = Label.new()
	message.add_theme_font_size_override("font_size", 14)
	message.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	column.add_child(message)


func configure_keys(keys: String) -> void:
	for index in keys.length():
		var character := keys[index]
		_button(keyboard_grid, character, character, func(): character_requested.emit(character))
	var order: Array[Control] = [text_input]
	for index in keys.length():
		order.append(buttons[keys[index]])
	order.append_array([buttons["backspace"], buttons["submit"], buttons["cancel"]])
	for index in order.size():
		order[index].focus_next = order[index].get_path_to(order[(index + 1) % order.size()])
		order[index].focus_previous = order[index].get_path_to(order[(index - 1 + order.size()) % order.size()])


func _button(parent: Control, id: String, text: String, callback: Callable) -> void:
	var button := Button.new()
	button.text = text
	button.add_theme_font_size_override("font_size", 14)
	button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	button.custom_minimum_size = Vector2(64, 30)
	button.pressed.connect(callback)
	parent.add_child(button)
	buttons[id] = button


func show_snapshot(state: Dictionary, opening: bool = false) -> void:
	var value: String = state["input_text"]
	for index in slots.size():
		slots[index].text = value[index] if index < value.length() else "＿"
	message.text = state["message"]
	if opening:
		text_input.clear()
		show()
		text_input.grab_focus.call_deferred()


func _committed_text(value: String) -> void:
	# LineEdit owns IME composition; only committed text becomes plain character signals.
	for index in value.length():
		character_requested.emit(value[index])
	text_input.clear()  # clear() does not emit text_changed, so there is no recursive append.


func handle_key(event: InputEventKey) -> bool:
	if text_input.has_focus() and text_input.has_ime_text() and event.physical_keycode in [KEY_ENTER, KEY_KP_ENTER, KEY_ESCAPE, KEY_BACKSPACE]:
		return false  # Native IME composition consumes these before password commands.
	match event.physical_keycode:
		KEY_ENTER, KEY_KP_ENTER:
			if not event.echo:
				submit_requested.emit()
			return true
		KEY_ESCAPE:
			if not event.echo:
				cancel_requested.emit()
			return true
		KEY_BACKSPACE:
			backspace_requested.emit()
			return true
		KEY_F5, KEY_F9, KEY_F6:
			return true  # No save/load/management commands leak through the modal.
	if text_input.has_focus():
		# Committed native text arrives once via text_changed, not a second unicode path.
		return false
	if event.physical_keycode in [KEY_TAB, KEY_LEFT, KEY_RIGHT, KEY_UP, KEY_DOWN, KEY_SPACE]:
		return false  # Native focus/navigation and virtual Button activation.
	if event.unicode > 0 and not (event.ctrl_pressed or event.alt_pressed or event.meta_pressed):
		character_requested.emit(String.chr(event.unicode))
	return true
