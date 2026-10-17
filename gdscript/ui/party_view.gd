# {
#   責務: [party_view: Selection/focus and draft projection only. All changes/save requests are signals.]
#   フィールド: [
#     presets_button: プリセット一覧・button（Button）
#     slots: 編成枠一覧（ItemList）
#     owned: owned（ItemList）
#     heading: heading（Label）
#     message: message（Label）
#     buttons: buttons（Dictionary）
#   ]
# }
extends PanelContainer
## Selection/focus and draft projection only. All changes/save requests are signals.

signal assigned(slot: int, id: Variant)
signal save_requested
signal cancel_requested
signal presets_requested
const Style = preload("res://ui/pixel_theme.gd")
var presets_button: Button
var slots: ItemList
var owned: ItemList
var heading: Label
var message: Label
var buttons: Dictionary = {}


# {
#   責務: [_ready: パーティ・表示のエントリ処理を実行する]
#   処理: [1: パーティ・表示のエントリ処理を実行する]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func _ready() -> void:
	# 共通のモーダル余白とスクロールで、編成操作を小さい画面でも到達可能にします。
	var column := Style.modal_column(self)
	var title_row := HBoxContainer.new()
	column.add_child(title_row)
	heading = Label.new()
	heading.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	title_row.add_child(heading)
	presets_button = Style.button("プリセット  [P]")
	presets_button.pressed.connect(func(): presets_requested.emit())
	title_row.add_child(presets_button)
	var help := Label.new()
	help.text = "左で編成枠、右で仲間を選び、Enterで入れてください。\nTab  移動 / Delete  外す / Ctrl+S  保存 / Esc  キャンセル"
	help.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	column.add_child(help)
	var lists := HBoxContainer.new()
	lists.size_flags_vertical = Control.SIZE_EXPAND_FILL
	column.add_child(lists)
	slots = _list(lists, 280)
	owned = _list(lists, 320)
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
	Style.cycle_focus([slots, owned, buttons["assign"], buttons["clear"], buttons["save"], buttons["cancel"], presets_button])


# {
#   責務: [_list: パーティ・表示を列挙する]
#   処理: [1: パーティ・表示を列挙する]
#   引数: [
#     parent: parent（Control）
#     width: 幅（float）
#   ]
#   戻り値: [result: パーティ・表示を列挙するための結果（ItemList）]
# }
func _list(parent: Control, width: float) -> ItemList:
	var list := ItemList.new()
	list.custom_minimum_size = Vector2(width, 168)
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	list.allow_reselect = true
	list.allow_search = false
	list.wraparound_items = false
	parent.add_child(list)
	return list


# {
#   責務: [_button: パーティ・表示のbuttonを求める]
#   処理: [1: パーティ・表示のbuttonを求める]
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
	button.pressed.connect(callback)
	parent.add_child(button)
	buttons[id] = button


# {
#   責務: [show_snapshot: パーティ・表示のshow・独立した状態の写しを求める]
#   処理: [1: パーティ・表示のshow・独立した状態の写しを求める]
#   引数: [
#     snapshot: 独立した状態の写し（Dictionary）
#     rebuild_owned: rebuild・owned（bool）
#   ]
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
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


# {
#   責務: [_summary: パーティ・表示のsummaryを求める]
#   処理: [1: パーティ・表示のsummaryを求める]
#   引数: [record: 個体レコード（Dictionary）]
#   戻り値: [result: パーティ・表示のsummaryを求めるための結果（String）]
# }
static func _summary(record: Dictionary) -> String:
	return "%s（%s） Lv.%d" % [record["monster"]["name"], record["species"].get("display_name", ""), int(record["monster"].get("level", 1))]


# {
#   責務: [assign_selected: パーティ・表示のassign・選択中を求める]
#   処理: [1: パーティ・表示のassign・選択中を求める]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func assign_selected() -> void:
	var selected := owned.get_selected_items()
	if selected.is_empty():
		message.text = "右側の保有個体を選択してください。"
		return
	assigned.emit(_selected_slot(), owned.get_item_metadata(selected[0]))


# {
#   責務: [clear_selected: 選択中を消去する]
#   処理: [1: 選択中を消去する]
#   引数: []
#   戻り値: [result: なし（void）。必要な状態更新は処理内で行う]
# }
func clear_selected() -> void:
	assigned.emit(_selected_slot(), null)


# {
#   責務: [handle_navigation: navigationを入力を処理する]
#   処理: [1: navigationを入力を処理する]
#   引数: [key: キー（int）]
#   戻り値: [result: navigationを入力を処理するための結果（bool）]
# }
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


# {
#   責務: [_selected_slot: パーティ・表示の選択中・編成枠を求める]
#   処理: [1: パーティ・表示の選択中・編成枠を求める]
#   引数: []
#   戻り値: [result: パーティ・表示の選択中・編成枠を求めるための結果（int）]
# }
func _selected_slot() -> int:
	var selected := slots.get_selected_items()
	return selected[0] if not selected.is_empty() else -1
