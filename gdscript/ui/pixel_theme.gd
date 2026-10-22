# {
#   責務: [pixel_theme: ゲーム画面共通の白黒矩形・ピクセルフォント・選択色を生成します。保存やゲーム状態は扱いません。]
#   フィールド: [
#     INK: 黒い背景色
#     PAPER: 通常文字と枠の白色
#     MUTED: 補助説明の灰色
#     FOCUS: 選択中の黄色
#   ]
# }
extends RefCounted

const INK := Color("#000000")
const PAPER := Color("#f5f5f5")
const MUTED := Color("#b7b7b7")
const FOCUS := Color("#ffe66d")
const PixelButton = preload("res://ui/pixel_button.gd")

# {
#   責務: [create: 日本語ピクセルフォントと矩形の共通Themeを組み立てます。]
#   処理: [
#     1: フォントの平滑化を無効にします
#     2: 入力部品とスクロール部品の状態別表示を定義します。
#   ]
#   引数: []
#   戻り値: [result: 画面ツリーで共有するTheme]
# }
static func create() -> Theme:
	var result := Theme.new()
	# FontFileを複製し、他の利用者のフォント設定を変えずに16px格子へ揃えます。
	var font := load("res://assets/fonts/DotGothic16-Regular.ttf").duplicate() as FontFile
	font.antialiasing = TextServer.FONT_ANTIALIASING_NONE
	font.subpixel_positioning = TextServer.SUBPIXEL_POSITIONING_DISABLED
	font.hinting = TextServer.HINTING_NONE
	result.default_font = font
	result.default_font_size = 16
	for type_name in ["Label", "Button", "LineEdit", "ItemList"]:
		result.set_color("font_color", type_name, PAPER)
		result.set_color("font_disabled_color", type_name, MUTED)
	result.set_constant("separation", "VBoxContainer", 12)
	result.set_constant("separation", "HBoxContainer", 12)
	result.set_constant("h_separation", "GridContainer", 4)
	result.set_constant("v_separation", "GridContainer", 4)
	result.set_stylebox("panel", "PanelContainer", frame(PAPER, 3, 16))
	result.set_stylebox("panel", "PopupPanel", frame(PAPER, 3, 12))
	# 黄色は選択・フォーカスに限定し、押せる操作は矩形の輪郭で区別します。
	for state in ["normal", "disabled"]:
		result.set_stylebox(state, "Button", frame(MUTED if state == "disabled" else PAPER, 2, 8))
	for state in ["hover", "pressed", "hover_pressed"]:
		result.set_stylebox(state, "Button", frame(FOCUS, 2, 8))
		result.set_color("font_" + state + "_color", "Button", FOCUS)
	result.set_stylebox("focus", "Button", outline(FOCUS, 3))
	result.set_color("font_focus_color", "Button", FOCUS)
	result.set_stylebox("normal", "LineEdit", frame(PAPER, 2, 10))
	result.set_stylebox("focus", "LineEdit", outline(FOCUS, 3))
	result.set_color("caret_color", "LineEdit", FOCUS)
	result.set_color("font_placeholder_color", "LineEdit", MUTED)
	result.set_stylebox("panel", "ItemList", frame(MUTED, 1, 8))
	result.set_stylebox("focus", "ItemList", outline(FOCUS, 2))
	result.set_stylebox("selected", "ItemList", frame(MUTED, 1, 6))
	result.set_stylebox("selected_focus", "ItemList", frame(FOCUS, 2, 6))
	result.set_color("font_selected_color", "ItemList", FOCUS)
	result.set_constant("v_separation", "ItemList", 12)
	for type_name in ["VScrollBar", "HScrollBar"]:
		result.set_stylebox("scroll", type_name, frame(MUTED, 1, 3))
		result.set_stylebox("grabber", type_name, frame(PAPER, 3, 3))
		result.set_stylebox("grabber_highlight", type_name, frame(FOCUS, 3, 3))
		result.set_stylebox("grabber_pressed", type_name, frame(FOCUS, 3, 3))
	return result

# {
#   責務: [frame: 黒い背景と角丸のない指定色の枠を作ります。]
#   処理: [1: 背景・枠幅・内側余白を指定したStyleBoxを生成します。]
#   引数: [
#     color: 枠の色
#     width: 枠のピクセル幅
#     padding: 内容と枠の間隔
#   ]
#   戻り値: [result: 新規StyleBoxFlat]
# }
static func frame(color: Color, width: int, padding: int) -> StyleBoxFlat:
	# アンチエイリアスを切り、整数座標の矩形辺を保ちます。
	var style := StyleBoxFlat.new()
	style.bg_color = INK
	style.border_color = color
	style.set_border_width_all(width)
	style.set_content_margin_all(padding)
	style.anti_aliasing = false
	return style

# {
#   責務: [outline: 内容を隠さないフォーカス専用の輪郭を作ります。]
#   処理: [1: 矩形枠の背景描画を無効にします。]
#   引数: [
#     color: 輪郭の色
#     width: 輪郭のピクセル幅
#   ]
#   戻り値: [result: 背景が透明なStyleBoxFlat]
# }
static func outline(color: Color, width: int) -> StyleBoxFlat:
	var style := frame(color, width, 0)
	style.draw_center = false
	return style

# {
#   責務: [button: フォーカス用ダイヤを持つゲーム操作ボタンを生成します。]
#   処理: [1: 表示文字を設定したボタンを返します。]
#   引数: [text: ボタンに表示する操作名]
#   戻り値: [result: シグナル未接続のButton]
# }
static func button(text: String) -> Button:
	var result := PixelButton.new()
	result.text = text
	return result

# {
#   責務: [modal_column: モーダルの内容が高さを超えても到達できる縦スクロール領域を作ります。]
#   処理: [1: フォーカス追従スクロールへ可変高の内容列を入れます。]
#   引数: [panel: 内容列を所有するモーダル]
#   戻り値: [result: 呼出元が表示部品を追加するVBoxContainer]
# }
static func modal_column(panel: PanelContainer) -> VBoxContainer:
	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.follow_focus = true
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	panel.add_child(scroll)
	var column := VBoxContainer.new()
	column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	column.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.add_child(column)
	return column

# {
#   責務: [place_modal: ビューポートの内側にモーダルを伸縮配置します。]
#   処理: [1: 全辺を親に固定し、視認できる外余白を設定します。]
#   引数: [panel: 親へ追加済みのモーダル]
#   戻り値: [result: なし]
# }
static func place_modal(panel: Control) -> void:
	panel.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	panel.offset_left = 36
	panel.offset_right = -36
	panel.offset_top = 44
	panel.offset_bottom = -28

# {
#   責務: [cycle_focus: モーダル内のTab移動を指定順で循環させます。]
#   処理: [1: 前後のフォーカス先を画面内の操作部品へ接続します。]
#   引数: [controls: 親へ追加済みの操作部品の表示順]
#   戻り値: [result: なし]
# }
static func cycle_focus(controls: Array[Control]) -> void:
	# 背面のフィールド操作へTabが抜けることを防ぎます。
	for index in controls.size():
		controls[index].focus_next = controls[index].get_path_to(controls[(index + 1) % controls.size()])
		controls[index].focus_previous = controls[index].get_path_to(controls[(index - 1 + controls.size()) % controls.size()])
