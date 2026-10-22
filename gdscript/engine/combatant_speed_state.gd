# {
#   責務: [combatant_speed_state: 戦闘個体一体の速度倍率・残りラウンド数・期限切れの復元先を所有します]
#   フィールド: [
#     _initialized: 一度だけ行う初期化が成功したかどうか（bool）
#     _multiplier: 最新の速度へ掛ける倍率（float）
#     _remaining_turns: 期間付き強化の残りラウンド数。0は期間付き強化なしです（int）
#     _baseline: 期間付き強化が切れた後に戻す倍率（float）
#   ]
# }
extends RefCounted

const Numbers = preload("res://engine/stat_numbers.gd")
var _initialized := false
var _multiplier := 1.0
var _remaining_turns := 0
var _baseline := 1.0


# {
#   責務: [start: 未開始の所有者へ初期速度倍率を一度だけ設定します]
#   処理: [1: 再初期化と不正数値を拒否し、期間なしの初期倍率と復元先を設定します]
#   引数: [initial_multiplier: 0以上JSON整数精度上限以下の有限数値。省略値は1です（Variant）]
#   戻り値: [result: ok=trueと独立snapshot、または未変更の拒否理由（Dictionary）]
# }
func start(initial_multiplier: Variant = 1.0) -> Dictionary:
	# 初期値の検証が成功するまで開始済みにせず、不正な初回要求の再試行を許可します。
	if _initialized:
		return _reject("already_initialized")
	if not _valid_number(initial_multiplier):
		return _reject("invalid_speed_multiplier")
	_multiplier = float(initial_multiplier)
	_baseline = _multiplier
	_initialized = true
	return _result("combatant_speed_started")


# {
#   責務: [snapshot: 現在倍率・残り期間・復元先を独立した三キー辞書で返します]
#   処理: [1: 未開始なら空辞書、開始済みなら保持するスカラー値だけを返します]
#   引数: []
#   戻り値: [result: speed_multiplier/remaining_turns/baseline_multiplier、または未開始の空辞書（Dictionary）]
# }
func snapshot() -> Dictionary:
	# 数値資源の六キーsnapshotや個体保存形式を拡張せず、速度強化だけの読み取りを分離します。
	if not _initialized:
		return {}
	return {"speed_multiplier": _multiplier, "remaining_turns": _remaining_turns, "baseline_multiplier": _baseline}


# {
#   責務: [apply_multiplier: 検証済みの新しい倍率と任意期間を、Python正本と同じ最大値規則で保持します]
#   処理: [
#     1: 未開始・辞書以外・未知キー・不正倍率・不正期間を更新前に拒否します
#     2: 初回期間付き強化の復元先を保持し、倍率と残り期間をそれぞれ大きい値へ更新します
#     3: 期間なしの強化は、期間付き強化がある場合の復元先も大きい値へ更新します
#   ]
#   引数: [request: 必須multiplierと任意durationだけの辞書。durationの省略/nullは期間なし、指定値は1以上の整数値です（Variant）]
#   戻り値: [result: ok=trueと独立snapshot、または全状態を保持した拒否理由（Dictionary）]
# }
func apply_multiplier(request: Variant) -> Dictionary:
	# 外部snapshotや別の能力値を更新要求へ持ち込ませず、速度強化の入力だけを受け付けます。
	if not _initialized:
		return _reject("not_initialized")
	if not request is Dictionary:
		return _reject("invalid_speed_buff_request")
	for field in request:
		if field not in ["multiplier", "duration"]:
			return _reject("unsupported_speed_buff_request")
	if not _valid_number(request.get("multiplier")):
		return _reject("invalid_speed_multiplier")
	var duration: Variant = request.get("duration")
	if duration != null and (not _valid_number(duration) or float(duration) < 1 or float(duration) != floorf(float(duration))):
		return _reject("invalid_speed_duration")
	# 期間と倍率の最大値は独立です。弱い長期間の再付与でも、現在の強い倍率を期間いっぱい保持します。
	var multiplier := float(request["multiplier"])
	if duration != null:
		if _remaining_turns == 0:
			_baseline = _multiplier
		_remaining_turns = maxi(_remaining_turns, int(duration))
	else:
		_baseline = maxf(_baseline, multiplier)
	_multiplier = maxf(_multiplier, multiplier)
	return _result("combatant_speed_apply")


# {
#   責務: [elapse_round: 期間付き速度強化を一ラウンドだけ進め、期限切れなら保存した倍率へ戻します]
#   処理: [1: 未開始を拒否し、残り期間が正なら一減らし、0になったときだけ倍率を復元します]
#   引数: []
#   戻り値: [result: ok/scope/snapshotと今回期限切れしたかのexpired。期間なしは変更しません（Dictionary）]
# }
func elapse_round() -> Dictionary:
	# この所有者は死亡・逃走・予約を判断しません。呼出側が終了ラウンドごとの一回実行を保証します。
	if not _initialized:
		return _reject("not_initialized")
	var expired := false
	if _remaining_turns > 0:
		_remaining_turns -= 1
		expired = _remaining_turns == 0
		if expired:
			_multiplier = _baseline
	var result := _result("combatant_speed_elapsed")
	result["expired"] = expired
	return result


# {
#   責務: [_valid_number: 倍率と期間の数値を有限・非負・JSON整数精度内へ限定します]
#   処理: [1: bool/文字列/非数値を除き、符号・有限性・9007199254740991以下を確認します]
#   引数: [value: 倍率または残り期間の数値候補（Variant）]
#   戻り値: [result: 対応範囲内のint/floatだけがtrueです（bool）]
# }
static func _valid_number(value: Variant) -> bool:
	return (value is int or value is float) and is_finite(float(value)) \
		and float(value) >= 0 and float(value) <= Numbers.MAX_EXACT_INTEGER


# {
#   責務: [_result: 更新成功の区分と独立した速度強化snapshotをまとめます]
#   処理: [1: 成功フラグ・操作区分・新規snapshot辞書を返します]
#   引数: [scope: 成功した速度強化操作の区分名（String）]
#   戻り値: [result: ok=true/scope/snapshotの辞書（Dictionary）]
# }
func _result(scope: String) -> Dictionary:
	return {"ok": true, "scope": scope, "snapshot": snapshot()}


# {
#   責務: [_reject: 速度強化の拒否理由を、部分更新を含まない辞書で返します]
#   処理: [1: 失敗フラグと具体的な理由だけを返します]
#   引数: [reason: 初期化・要求・数値を拒否した理由（String）]
#   戻り値: [result: ok=false/reasonの辞書（Dictionary）]
# }
static func _reject(reason: String) -> Dictionary:
	return {"ok": false, "reason": reason}
