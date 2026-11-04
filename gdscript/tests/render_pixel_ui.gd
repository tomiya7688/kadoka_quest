# {
#   責務: [render_pixel_ui: 指定した隔離保存先だけでGodotの実レンダラーを使い、既存画面のPNGを作ります。実GUI操作の検証ではありません。]
#   フィールド: [capture_root: 呼出元が指定する検査成果物の保存先]
# }
extends SceneTree

var capture_root := ""

# {
#   責務: [_initialize: SceneTreeの初期化後へ描画検査を予約します。]
#   処理: [1: 描画本体を遅延実行します。]
#   引数: []
#   戻り値: [result: なし]
# }
func _initialize() -> void:
	_run.call_deferred()

# {
#   責務: [_run: 実セーブへの書込を拒否し、タイトル画面・フィールド・既存モーダルの描画結果を保存します。]
#   処理: [
#     1: 隔離保存先と描画ドライバーを確認します。
#     2: セーブがない状態のタイトル画面とセーブ名入力を描画します。
#     3: 実Sceneを起動し、隔離プロフィールで既存画面を順に表示します。
#     4: 保存後のタイトル画面のセーブ一覧を描画し、Godotを終了します。
#   ]
#   引数: []
#   戻り値: [result: なし]
# }
func _run() -> void:
	capture_root = OS.get_environment("KADOKA_UI_CAPTURE_ROOT").replace("\\", "/").trim_suffix("/")
	var save_root := OS.get_environment("KADOKA_GDSCRIPT_SAVE_ROOT").replace("\\", "/").trim_suffix("/")
	# 一般のプロフィールへ誤って初期仲間を書き込まないよう、成果物内の保存先だけを許可します。
	if capture_root.is_empty() or save_root != capture_root.path_join("savedata") or DisplayServer.get_name() == "headless":
		push_error("描画検査には実レンダラーとKADOKA_UI_CAPTURE_ROOT配下のsavedataを指定してください。")
		quit(1)
		return
	DirAccess.make_dir_recursive_absolute(capture_root)
	root.size = Vector2i(960, 540)
	# セーブがない初回起動のタイトル画面と、セーブ名の入力画面を先に描画します。
	var title = load("res://scenes/title.tscn").instantiate()
	root.add_child(title)
	await _capture("title")
	title.view.open_page("new")
	await _capture("title_new")
	title.queue_free()
	await process_frame
	var scene = load("res://scenes/field.tscn").instantiate()
	root.add_child(scene)
	await process_frame
	scene.set_process(false)
	if not scene.save_current_position():
		push_error("隔離プロフィールを作成できませんでした: " + scene.status.text)
		quit(1)
		return
	await _capture("field")
	scene.chrome.toggle_menu()
	await _capture("menu")
	scene.chrome.close_menu()
	scene.open_owned_roster()
	await _capture("roster")
	scene.begin_party_edit()
	await _capture("party")
	scene.open_party_presets()
	scene.save_party_preset("はじめの仲間")
	await _capture("presets")
	scene.close_party_presets()
	scene.cancel_party_edit()
	scene.roster_view.hide()
	scene.chrome.show_dialogue("町のひと", "ようこそ、はじまりの町へ。\n小さな仲間といっしょに、外の世界を歩いてみてください。")
	await _capture("dialogue")
	scene.open_password_input()
	await _capture("password")
	scene.queue_free()
	await process_frame
	# フィールドで保存した隔離プロフィールが、タイトル画面のセーブ一覧に表示されることを描画します。
	title = load("res://scenes/title.tscn").instantiate()
	root.add_child(title)
	await process_frame
	title.view.open_page("profiles")
	await _capture("title_profiles")
	title.queue_free()
	await process_frame
	print("KADOKA_PIXEL_RENDER_RESULT=" + capture_root)
	quit(0)

# {
#   責務: [_capture: Controlの再配置と実レンダリングを待ち、現在のビューポートをPNGへ保存します。]
#   処理: [1: レイアウトと描画の完了後に画素を取得し、指定名で保存します。]
#   引数: [name: 成果物内で使う画面名]
#   戻り値: [result: なし]
# }
func _capture(name: String) -> void:
	# 最初のフレームだけではコンテナの再配置が終わらないため、次の描画まで待ちます。
	await process_frame
	await process_frame
	await RenderingServer.frame_post_draw
	var image := root.get_texture().get_image()
	var error := image.save_png(capture_root.path_join(name + ".png"))
	if error != OK:
		push_error("検査画像を保存できませんでした: " + name)
		quit(1)
