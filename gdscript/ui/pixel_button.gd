# {
#   責務: [pixel_button: キーボードフォーカスを独自の小さなピクセルダイヤで示す操作ボタンです。]
#   フィールド: []
# }
extends Button

# {
#   責務: [_ready: フォーカスの出入りでダイヤを再描画します。]
#   処理: [1: ボタンの最低高とフォーカス通知を設定します。]
#   引数: []
#   戻り値: [result: なし]
# }
func _ready() -> void:
	custom_minimum_size.y = maxf(custom_minimum_size.y, 36)
	# 文字と重ならないよう、ダイヤは枠の左上へ配置します。
	focus_entered.connect(queue_redraw)
	focus_exited.connect(queue_redraw)

# {
#   責務: [_draw: フォーカス中のボタンの枠にピクセルダイヤを描きます。]
#   処理: [1: 中央と上下左右の四角を黄色で描画します。]
#   引数: []
#   戻り値: [result: なし]
# }
func _draw() -> void:
	if not has_focus():
		return
	# ハートなど他作品の記号を使用せず、5個の矩形で独自の目印を作ります。
	for offset in [Vector2(0, 0), Vector2(-3, 0), Vector2(3, 0), Vector2(0, -3), Vector2(0, 3)]:
		draw_rect(Rect2(Vector2(10, 1) + offset, Vector2(3, 3)), Color("#ffe66d"))
