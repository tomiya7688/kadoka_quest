# {
#   責務: [run_speed_multiplier_probe: 速度強化専用の一時JSONを読み、機能観測または反復計測を標準出力へ返します]
#   フィールド: []
# }
extends SceneTree

const Probe = preload("res://tests/speed_multiplier_probe.gd")
const SessionProbe = preload("res://tests/session_speed_probe.gd")
const Benchmark = preload("res://tests/speed_multiplier_benchmark.gd")


# {
#   責務: [_initialize: 専用要求を読み、機能検証と性能検証のどちらかへ委譲して終了します]
#   処理: [1: 一つのJSONファイル引数を検証し、専用ヘルパーの結果をBase64で出力します]
#   引数: []
#   戻り値: [result: なし（void）。引数/JSON形式不正は終了コード2、正常な観測は0です]
# }
func _initialize() -> void:
	# 保存先や正規データを受け付けず、テストが用意した要求ファイルを読み取るだけにします。
	var arguments := OS.get_cmdline_user_args()
	if arguments.size() != 1:
		quit(2)
		return
	var payload: Variant = JSON.parse_string(FileAccess.get_file_as_string(arguments[0]))
	if not payload is Dictionary:
		quit(2)
		return
	var result: Dictionary
	if payload.get("session_speed", false):
		result = SessionProbe.run(payload)
	elif payload.get("performance", false):
		result = Benchmark.run(payload)
	else:
		result = Probe.run(payload)
	print("KADOKA_SPEED_STATE_RESULT=" + Marshalls.utf8_to_base64(JSON.stringify(result)))
	quit(0)
