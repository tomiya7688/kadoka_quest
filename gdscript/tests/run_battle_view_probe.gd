# {
#   責務: [run_battle_view_probe: 戦闘画面の表示が、敵・味方・状態・コマンド・ログを960×540内に出し、選択を通知することを実Godotで検証します。]
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
#   責務: [_member: 検査用の個体snapshotを作ります。]
#   処理: [1: 指定の値でidentity・stats・hp・mp・fled・aliveを組み立てます。]
#   引数: [
#     id: 個体id
#     member_name: 表示名
#     hp: 現在HP
#     mp: 現在MP
#     fled: 逃走済みか
#   ]
#   戻り値: [result: 個体snapshot]
# }
func _member(id: String, member_name: String, hp: int, mp: int, fled: bool = false) -> Dictionary:
	return {
		"identity": {"id": id, "species_id": "x", "name": member_name},
		"stats": {"hp": 30, "mp": 10},
		"hp": hp,
		"mp": mp,
		"fled": fled,
		"alive": hp > 0 and not fled,
	}


# {
#   責務: [_run: 表示・倒れた個体・状態・コマンド選択・再表示の持ち越しなしを確認します。]
#   処理: [
#     1: 敵2体と味方3体、状態、コマンド4つ、ログ5行を表示します
#     2: 配置・文言・フォーカス・通知・再表示を確認し、結果を出力します
#   ]
#   引数: []
#   戻り値: [result: なし]
# }
func _run() -> void:
	root.size = Vector2i(960, 540)
	var surface := Control.new()
	root.add_child(surface)
	surface.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	surface.theme = Style.create()
	var view = load("res://ui/battle_view.gd").new()
	surface.add_child(view)
	await process_frame
	var session := {
		"teams":
		{
			"enemies": [_member("e1", "スライム", 30, 0), _member("e2", "ゴブリン", 0, 0)],
			"allies": [_member("a1", "ゆうしゃ", 18, 5), _member("a2", "まほう", 30, 10), _member("a3", "にげた子", 9, 3, true)],
		},
	}
	var statuses := {"teams": {"allies": {"a1": ["poison", {"id": "sleep"}]}, "enemies": {}}}
	var picked: Array[int] = []
	view.command_selected.connect(func(index: int): picked.append(index))
	view.show_state(session, statuses, ["こうげき", "ぼうぎょ", "とくぎ", "にげる"], ["1", "2", "3", "4", "5"])
	await process_frame
	_check(view.enemy_cards.size() == 2 and view.ally_rows.size() == 3, "敵2体・味方3体を表示")
	var enemy_h: float = view.enemy_cards[0].get_global_rect().size.y
	var ally_top: float = view.ally_rows[0].get_global_rect().position.y
	_check(view.enemy_cards[0].get_global_rect().position.y < ally_top, "敵を味方より上段に置く")
	_check(ally_top < 540 and view.command_buttons[3].get_global_rect().end.y <= 540, "味方とコマンドが画面内")
	_check(view.command_buttons[3].get_global_rect().end.x <= 960, "コマンドの右端が画面内")
	_check(_all_text(view.enemy_cards[0]).contains("スライム") and _all_text(view.enemy_cards[0]).contains("30/30"), "敵の名前とHPを表示")
	_check(_all_text(view.enemy_cards[1]).contains("たおれた"), "倒れた敵の理由を表示")
	_check(_all_text(view.ally_rows[0]).contains("18/30") and _all_text(view.ally_rows[0]).contains("5/10"), "味方のHP/MPを表示")
	_check(_all_text(view.ally_rows[0]).contains("poison") and _all_text(view.ally_rows[0]).contains("sleep"), "状態を一行で表示")
	_check(_all_text(view.ally_rows[2]).contains("にげた"), "逃げた味方の理由を表示")
	_check(view.log_label.text == "3\n4\n5", "ログは最後の3行だけ")
	_check(view.command_buttons[0].has_focus(), "先頭のコマンドへフォーカス")
	(view.command_buttons[2] as Button).pressed.emit()
	_check(picked == [2], "選んだコマンドの順番を通知")
	view.show_state(session, {}, [], [])
	await process_frame
	_check(view.command_buttons.is_empty() and view.log_label.text == "" and enemy_h > 0.0, "再表示でコマンドとログを持ち越さない")
	view.show_state({"teams": {"enemies": [null, 3, _member("e9", "ゴースト", 1, 0)], "allies": []}}, {"teams": null}, [], [])
	await process_frame
	_check(view.enemy_cards.size() == 1 and view.ally_rows.is_empty(), "辞書でない個体と不正な状態異常を無視して描画")
	print("KADOKA_BATTLE_VIEW_RESULT=" + JSON.stringify({"ok": failures.is_empty(), "failures": failures}))
	print(
		"KADOKA_CONTRACT_RESULT=" + Marshalls.utf8_to_base64(JSON.stringify({"ok": failures.is_empty(), "failures": failures}))
	)
	surface.queue_free()
	await process_frame
	quit(0 if failures.is_empty() else 1)


# {
#   責務: [_all_text: 表示枠の子孫のLabelの文字列を一つに連結します。]
#   処理: [1: 子孫を順にたどり、Labelの文字列を空白でつなぎます。]
#   引数: [node: 検査する表示枠]
#   戻り値: [result: 連結した文字列]
# }
func _all_text(node: Node) -> String:
	var text: String = node.text if node is Label else ""
	for child in node.get_children():
		text += " " + _all_text(child)
	return text


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
