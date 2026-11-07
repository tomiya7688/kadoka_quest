# {
#   責務: [run_focus_probe: 主要な選択部品が同じ黄色の輪郭規則を使い、キーボードとゲームパッドの移動操作が割り当て済みであることを実Godotで検証します。]
#   フィールド: [failures: 失敗した期待動作の説明一覧]
# }
extends SceneTree

const Style = preload("res://ui/pixel_theme.gd")
var failures: PackedStringArray = []


# {
#   責務: [_initialize: 検査本体を初期化後へ予約します。]
#   処理: [1: 検査本体を遅延実行します。]
#   引数: []
#   戻り値: [result: なし]
# }
func _initialize() -> void:
	_run.call_deferred()


# {
#   責務: [_run: テーマのフォーカス規則と移動操作の割り当てを確かめ、結果を出力して終了します。]
#   処理: [
#     1: Button・LineEdit・ItemListのフォーカス輪郭が同じ色で、背景を塗らないことを確かめます
#     2: 選択移動の操作にキーボードとゲームパッドの入力が割り当てられていることを確かめます
#     3: ボタンへ移動したとき、フォーカスの縁が他の枠と区別できることを確かめます
#   ]
#   引数: []
#   戻り値: [result: なし]
# }
func _run() -> void:
	# テーマの生成が、決定とキャンセルのゲームパッド入力を補う。
	var theme := Style.create()
	for type_name in ["Button", "LineEdit", "ItemList"]:
		var focus := theme.get_stylebox("focus", type_name) as StyleBoxFlat
		_check(focus != null, type_name + "にフォーカスの輪郭がある")
		if focus == null:
			continue
		_check(focus.border_color == Style.FOCUS, type_name + "のフォーカス色が共通の黄色")
		_check(not focus.draw_center, type_name + "のフォーカスが内容を隠さない")
		_check(focus.get_border_width(SIDE_LEFT) >= 2, type_name + "のフォーカス枠が2px以上")
	_check((theme.get_stylebox("selected_focus", "ItemList") as StyleBoxFlat).border_color == Style.FOCUS, "一覧の選択中の行が黄色の枠")
	_check(theme.get_stylebox("normal", "Button").border_color != Style.FOCUS, "未選択のボタンは黄色以外の枠")
	for action in ["ui_up", "ui_down", "ui_left", "ui_right", "ui_accept", "ui_cancel"]:
		var has_key := false
		var has_pad := false
		for event in InputMap.action_get_events(action):
			has_key = has_key or event is InputEventKey
			has_pad = has_pad or event is InputEventJoypadButton or event is InputEventJoypadMotion
		_check(has_key, action + "にキーボード入力がある")
		_check(has_pad, action + "にゲームパッド入力がある")
	var surface := Control.new()
	surface.theme = theme
	root.add_child(surface)
	var first := Style.button("A")
	var second := Style.button("B")
	surface.add_child(first)
	surface.add_child(second)
	var controls: Array[Control] = [first, second]
	Style.cycle_focus(controls)
	await process_frame
	first.grab_focus()
	await process_frame
	_check(first.has_focus() and not second.has_focus(), "選択中は一つだけ")
	var down := InputEventAction.new()
	down.action = "ui_focus_next"
	down.pressed = true
	Input.parse_input_event(down)
	await process_frame
	await process_frame
	_check(first.focus_next == first.get_path_to(second) and second.focus_next == second.get_path_to(first), "フォーカス移動が部品内で循環")
	print("KADOKA_FOCUS_RESULT=" + JSON.stringify({"ok": failures.is_empty(), "failures": failures}))
	print(
		"KADOKA_CONTRACT_RESULT=" + Marshalls.utf8_to_base64(JSON.stringify({"ok": failures.is_empty(), "failures": failures}))
	)
	surface.queue_free()
	await process_frame
	quit(0 if failures.is_empty() else 1)


# {
#   責務: [_check: 条件が偽なら失敗一覧へ説明を追加します。]
#   処理: [1: 偽の時だけ説明を追加します。]
#   引数: [
#     condition: 期待する条件
#     message: 失敗時の説明
#   ]
#   戻り値: [result: なし]
# }
func _check(condition: bool, message: String) -> void:
	if not condition:
		failures.append(message)
