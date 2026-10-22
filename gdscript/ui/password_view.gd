# {
#   責務: [password_view: Native/virtual input -> semantic signals; render snapshots, never judge a password.]
#   フィールド: [
#     slots: 編成枠一覧（Array）
#     buttons: buttons（Dictionary）
#     text_input: 文字列・入力（LineEdit）
#     message: message（Label）
#     keyboard_grid: keyboard・マス（GridContainer）
#   ]
# }
extends PanelContainer
## Native/virtual input -> semantic signals; render snapshots, never judge a password.

signal character_requested(character: String)
signal backspace_requested
signal submit_requested
signal cancel_requested
const Style = preload("res://ui/pixel_theme.gd")
var slots: Array[Label] = []
var buttons: Dictionary = {}
var text_input: LineEdit
var message: Label
var keyboard_grid: GridContainer


# {
#   責務: [_ready: 暗号・表示のエントリ処理を実行する]
#   処理: [1: 暗号・表示のエントリ処理を実行する]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _ready() -> void:
	# かな配列が画面高を超えた場合も、Tabで選んだキーへスクロールが追従します。
	var column := Style.modal_column(self)
	column.add_theme_constant_override("separation", 4)
	var heading := Label.new()
	heading.text = "水の湧き場 — 7文字のあいことば"
	column.add_child(heading)
	var help := Label.new()
	help.text = "かな入力 / Tab・矢印  キー選択 / Enter  実行 / Backspace  消去 / Esc  戻る"
	help.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	column.add_child(help)
	var slot_row := HBoxContainer.new()
	column.add_child(slot_row)
	for index in 7:
		var slot := Label.new()
		slot.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		slot.custom_minimum_size = Vector2(64, 32)
		slot.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		slot.add_theme_color_override("font_color", Style.PAPER)
		slot_row.add_child(slot)
		slots.append(slot)
	text_input = LineEdit.new()
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
	message.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	column.add_child(message)


# {
#   責務: [configure_keys: キー一覧を設定する]
#   処理: [1: キー一覧を設定する]
#   引数: [keys: キー一覧（String）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func configure_keys(keys: String) -> void:
	for index in keys.length():
		var character := keys[index]
		_button(keyboard_grid, character, character, func(): character_requested.emit(character))
	var order: Array[Control] = [text_input]
	for index in keys.length():
		order.append(buttons[keys[index]])
	order.append_array([buttons["backspace"], buttons["submit"], buttons["cancel"]])
	Style.cycle_focus(order)


# {
#   責務: [_button: 暗号・表示のbuttonを求める]
#   処理: [1: 暗号・表示のbuttonを求める]
#   引数: [
#     parent: parent（Control）
#     id: 識別子（String）
#     text: 文字列（String）
#     callback: コールバック（Callable）
#   ]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _button(parent: Control, id: String, text: String, callback: Callable) -> void:
	var button := Style.button(text)
	button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	button.custom_minimum_size = Vector2(64, 30)
	button.pressed.connect(callback)
	parent.add_child(button)
	buttons[id] = button


# {
#   責務: [show_snapshot: 暗号・表示のshow・独立した状態の写しを求める]
#   処理: [1: 暗号・表示のshow・独立した状態の写しを求める]
#   引数: [
#     state: 状態（Dictionary）
#     opening: opening（bool）
#   ]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func show_snapshot(state: Dictionary, opening: bool = false) -> void:
	var value: String = state["input_text"]
	for index in slots.size():
		slots[index].text = value[index] if index < value.length() else "＿"
	message.text = state["message"]
	if opening:
		text_input.clear()
		show()
		text_input.grab_focus.call_deferred()


# {
#   責務: [_committed_text: 暗号・表示のcommitted・文字列を求める]
#   処理: [1: 暗号・表示のcommitted・文字列を求める]
#   引数: [value: 値（String）]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _committed_text(value: String) -> void:
	# LineEdit owns IME composition; only committed text becomes plain character signals.
	for index in value.length():
		character_requested.emit(value[index])
	text_input.clear()  # clear() does not emit text_changed, so there is no recursive append.


# {
#   責務: [handle_key: キーを入力を処理する]
#   処理: [1: キーを入力を処理する]
#   引数: [event: イベント（InputEventKey）]
#   戻り値: [result: キーを入力を処理するための結果（bool）]
# }
func handle_key(event: InputEventKey) -> bool:
	if text_input.has_focus() and text_input.has_ime_text() and event.physical_keycode in [KEY_ENTER, KEY_KP_ENTER, KEY_ESCAPE, KEY_BACKSPACE]:
		return false  # Native IME composition consumes these before password commands.
	match event.physical_keycode:
		KEY_ENTER, KEY_KP_ENTER:
			# かなボタンではEnterを文字入力へ渡し、入力欄のEnterだけを確定要求にします。
			if get_viewport().gui_get_focus_owner() is Button:
				return false
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
