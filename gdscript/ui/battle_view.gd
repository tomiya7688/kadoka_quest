# {
#   責務: [battle_view: 戦闘Sessionのsnapshotを、モンスター・HP/MP・状態・コマンド中心の白黒画面として表示し、選ばれたコマンドをシグナルで返します。]
#   フィールド: [
#     LOG_LINES: 常時表示する戦闘ログの最大行数
#     enemy_cards: 敵モンスターの表示枠の並び
#     ally_rows: 味方の資源表示枠の並び
#     command_buttons: コマンドボタンの並び
#     log_label: 直近の戦闘ログを表示するLabel
#   ]
# }
extends Control

const Style = preload("res://ui/pixel_theme.gd")
const LOG_LINES := 3
signal command_selected(index: int)
var enemy_cards: Array[Control] = []
var ally_rows: Array[Control] = []
var command_buttons: Array[Control] = []
var log_label: Label
var _enemy_row: HBoxContainer
var _ally_column: VBoxContainer
var _command_column: VBoxContainer


# {
#   責務: [_ready: 敵・味方・コマンド・ログの四つの領域を960×540の内側に配置します。]
#   処理: [
#     1: 上段の大きな領域を敵モンスターの横並びにします
#     2: 下段の左を味方の資源、右をコマンド、最下部をログにします
#   ]
#   引数: []
#   戻り値: [result: なし]
# }
func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var page := VBoxContainer.new()
	add_child(page)
	page.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	page.offset_left = 20
	page.offset_top = 12
	page.offset_right = -20
	page.offset_bottom = -12
	# 敵を最も広い領域に置き、モンスターを画面の主役にします。
	_enemy_row = HBoxContainer.new()
	_enemy_row.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_enemy_row.alignment = BoxContainer.ALIGNMENT_CENTER
	page.add_child(_enemy_row)
	var lower := HBoxContainer.new()
	page.add_child(lower)
	_ally_column = VBoxContainer.new()
	_ally_column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_ally_column.add_theme_constant_override("separation", 4)
	lower.add_child(_ally_column)
	_command_column = VBoxContainer.new()
	_command_column.custom_minimum_size.x = 240
	_command_column.add_theme_constant_override("separation", 4)
	lower.add_child(_command_column)
	log_label = Label.new()
	log_label.custom_minimum_size.y = 24 * LOG_LINES
	log_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	log_label.add_theme_color_override("font_color", Style.MUTED)
	page.add_child(log_label)


# {
#   責務: [show_state: Sessionの状態と状態異常一覧、選べるコマンド、ログを受け取り、画面を作り直します。]
#   処理: [
#     1: 前回の表示枠を取り除きます
#     2: 敵と味方をsnapshotの並び順に表示し、倒れた個体と逃げた個体は補助色で理由を示します
#     3: コマンドを並べて先頭へフォーカスし、ログは最後のLOG_LINES行だけ表示します
#   ]
#   引数: [
#     session: 戦闘Sessionのsnapshot。teams.allies/enemiesに個体の辞書の並びを持ちます
#     statuses: 状態異常のsnapshot。teams.<陣営>.<個体id>に状態の並びを持ちます
#     commands: 利用者へ表示するコマンド名の並び。空なら操作を表示しません
#     log_lines: 古い順の戦闘ログ
#   ]
#   戻り値: [result: なし]
# }
func show_state(session: Dictionary, statuses: Dictionary, commands: Array, log_lines: Array) -> void:
	_clear(_enemy_row, enemy_cards)
	_clear(_ally_column, ally_rows)
	_clear(_command_column, command_buttons)
	var teams: Dictionary = session.get("teams", {})
	for member: Variant in teams.get("enemies", []):
		if not member is Dictionary:
			continue
		var card := _member_box(member, statuses, "enemies", true)
		_enemy_row.add_child(card)
		enemy_cards.append(card)
	for member: Variant in teams.get("allies", []):
		if not member is Dictionary:
			continue
		var row := _member_box(member, statuses, "allies", false)
		_ally_column.add_child(row)
		ally_rows.append(row)
	for index in commands.size():
		var button := Style.button(str(commands[index]))
		button.pressed.connect(func(): command_selected.emit(index))
		_command_column.add_child(button)
		command_buttons.append(button)
	if not command_buttons.is_empty():
		Style.cycle_focus(command_buttons)
		command_buttons[0].grab_focus.call_deferred()
	var shown: Array = log_lines.slice(maxi(0, log_lines.size() - LOG_LINES))
	log_label.text = "\n".join(PackedStringArray(shown.map(func(line): return str(line))))


# {
#   責務: [_clear: 前回の表示枠を親から外して破棄し、記録用の並びを空にします。]
#   処理: [1: 子を外して破棄し、並びを空にします。]
#   引数: [
#     parent: 表示枠を持つ親
#     list: 表示枠の記録
#   ]
#   戻り値: [result: なし]
# }
func _clear(parent: Control, list: Array) -> void:
	for child in parent.get_children():
		parent.remove_child(child)
		child.queue_free()
	list.clear()


# {
#   責務: [_member_box: 一体分の名前・HP/MP・状態を縦に並べた枠を作ります。]
#   処理: [
#     1: 名前の行に、倒れた・逃げた個体の理由を添えます
#     2: HPとMPを棒と数値で表示し、状態があれば一行で並べます
#   ]
#   引数: [
#     member: 個体のsnapshot（identity・stats・hp・mp・fled・alive）
#     statuses: 状態異常のsnapshot
#     side: allies または enemies
#     large: 敵の大きな枠にするか
#   ]
#   戻り値: [result: 個体の表示枠]
# }
func _member_box(member: Dictionary, statuses: Dictionary, side: String, large: bool) -> Control:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 2)
	if large:
		box.custom_minimum_size = Vector2(200, 0)
		box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var identity: Dictionary = member.get("identity", {})
	var stats: Dictionary = member.get("stats", {})
	var state := ""
	if member.get("fled", false):
		state = "  (にげた)"
	elif not member.get("alive", true):
		state = "  (たおれた)"
	var name_label := Label.new()
	name_label.text = str(identity.get("name", "?")) + state
	if large:
		name_label.add_theme_font_size_override("font_size", 24)
	if not state.is_empty():
		name_label.add_theme_color_override("font_color", Style.MUTED)
	box.add_child(name_label)
	box.add_child(_bar("HP", member.get("hp", 0), stats.get("hp", 0)))
	box.add_child(_bar("MP", member.get("mp", 0), stats.get("mp", 0)))
	var effects: Array = _effects_of(statuses, side, identity.get("id", ""))
	if not effects.is_empty():
		var line := Label.new()
		line.text = " ".join(PackedStringArray(effects.map(_effect_name)))
		line.add_theme_color_override("font_color", Style.FOCUS)
		box.add_child(line)
	return box


# {
#   責務: [_bar: ラベル・横棒・現在値/最大値を一行にまとめます。]
#   処理: [1: 棒は最大値が0以下なら空とし、現在値は0から最大値へ丸めて描きます。]
#   引数: [
#     caption: HPまたはMP
#     current: 現在値
#     maximum: 最大値
#   ]
#   戻り値: [result: 一行の表示枠]
# }
func _bar(caption: String, current: int, maximum: int) -> Control:
	var line := HBoxContainer.new()
	line.add_theme_constant_override("separation", 6)
	var tag := Label.new()
	tag.text = caption
	tag.custom_minimum_size.x = 28
	line.add_child(tag)
	var gauge := ProgressBar.new()
	gauge.show_percentage = false
	gauge.custom_minimum_size = Vector2(80, 12)
	gauge.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	gauge.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	gauge.max_value = maxi(maximum, 1)
	gauge.value = clampi(current, 0, maxi(maximum, 0))
	gauge.add_theme_stylebox_override("background", Style.frame(Style.MUTED, 1, 0))
	var fill := Style.frame(Style.PAPER, 0, 0)
	fill.bg_color = Style.PAPER
	gauge.add_theme_stylebox_override("fill", fill)
	line.add_child(gauge)
	var number := Label.new()
	number.text = "%d/%d" % [current, maximum]
	line.add_child(number)
	return line


# {
#   責務: [_effects_of: 状態異常snapshotから一体分の状態の並びを取り出し、型が合わない値は空として扱います。]
#   処理: [1: 陣営→個体idの順に辞書か確かめて辿り、配列でなければ空の並びを返します。]
#   引数: [
#     statuses: 状態異常のsnapshot
#     side: allies または enemies
#     id: 個体id
#   ]
#   戻り値: [result: 状態の並び]
# }
func _effects_of(statuses: Dictionary, side: String, id: Variant) -> Array:
	var teams: Variant = statuses.get("teams", {})
	var side_map: Variant = teams.get(side, {}) if teams is Dictionary else {}
	var list: Variant = side_map.get(id, []) if side_map is Dictionary else []
	return list if list is Array else []


# {
#   責務: [_effect_name: 状態異常の一件を、表示用の文字列にします。]
#   処理: [1: 辞書ならidを、それ以外は文字列化した値を返します。]
#   引数: [effect: 状態異常の一件]
#   戻り値: [result: 表示名]
# }
func _effect_name(effect: Variant) -> String:
	return str(effect.get("id", "?")) if effect is Dictionary else str(effect)
