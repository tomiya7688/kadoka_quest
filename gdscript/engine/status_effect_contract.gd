# {
#   責務: [status_effect_contract: 治療と付与で共用する状態一覧の型・JSON互換性と比較用IDを検査し、入力を変更しません]
#   フィールド: []
# }
extends RefCounted

const Numbers = preload("res://engine/stat_numbers.gd")
const MAX_JSON_DEPTH := 32


# {
#   責務: [valid_effects: 状態一覧を文字列またはJSON互換辞書の配列に限定し、認識キーの型を確認します]
#   処理: [
#     1: 一覧全体の深さ・有限数値・文字列辞書キーを確認します
#     2: 各状態のid/表示名を文字列、指定済みremovableをboolに限定します
#   ]
#   引数: [effects: 順序付き状態一覧。未知IDとJSON互換拡張情報は効果を実行せず保持できます（Variant）]
#   戻り値: [result: 深いコピー可能な対応一覧ならtrue、不正型/循環/深さ超過ならfalse（bool）]
# }
static func valid_effects(effects: Variant) -> bool:
	# コピー前に一覧全体を検証し、Objectや循環を状態保持へ持ち込みません。
	if not effects is Array or not _is_json_value(effects):
		return false
	for effect in effects:
		if effect is String:
			continue
		if not effect is Dictionary:
			return false
		for field in ["id", "display_name"]:
			if effect.has(field) and not effect[field] is String:
				return false
		if effect.has("removable") and not effect["removable"] is bool:
			return false
	return true


# {
#   責務: [effect_id: 型検査済み状態から重複比較用IDを読み、保持済みIDの空白を変更しません]
#   処理: [1: 文字列状態はそのまま、辞書はidまたは省略時の空文字列を返します]
#   引数: [effect: valid_effectsに成功した一覧の一要素（Variant）]
#   戻り値: [result: Pythonのstatus_effect_idと同じ比較用文字列（String）]
# }
static func effect_id(effect: Variant) -> String:
	return effect if effect is String else effect.get("id", "")


# {
#   責務: [valid_json_value: コピー前の任意入力が深さ32以内の安全なJSON値かを、副作用なしで確認します]
#   処理: [1: 状態一覧と同じ再帰検査へ委譲し、Object/循環/非有限/精度超過を拒否します]
#   引数: [value: 自身を深さ0とするJSON由来の準備入力（Variant）]
#   戻り値: [result: コピー可能なJSON値ならtrue、不正型/値/深さならfalse（bool）]
# }
static func valid_json_value(value: Variant) -> bool:
	# 共用検査の内部関数を呼出側へ公開せず、未検証ネストの安全確認だけを提供します。
	return _is_json_value(value)


# {
#   責務: [_is_json_value: 状態拡張情報をJSON値に限定し、コピー前に非有限数値・循環・過深なコンテナを拒否します]
#   処理: [1: 子要素を再帰検査し、深さ32超過・数値精度超過・非文字列キー・Objectを拒否します]
#   引数: [
#     value: 状態一覧または再帰検査中の子要素（Variant）
#     depth: 状態一覧を0とする子要素の深さ（int）
#   ]
#   戻り値: [result: 有限数値の絶対値9007199254740991以内かつ深さ32以内のJSON値ならtrue（bool）]
# }
static func _is_json_value(value: Variant, depth: int = 0) -> bool:
	if depth > MAX_JSON_DEPTH:
		return false
	if value == null or value is String or value is bool:
		return true
	if value is int or value is float:
		return is_finite(float(value)) and absf(float(value)) <= Numbers.MAX_EXACT_INTEGER
	# 未知キーの情報も返却できる値に限定し、非JSON値を隠して成功と扱いません。
	if value is Array:
		for child in value:
			if not _is_json_value(child, depth + 1):
				return false
		return true
	if value is Dictionary:
		for key in value:
			if not key is String or not _is_json_value(value[key], depth + 1):
				return false
		return true
	return false

# {
#   責務: [normalized_id: 新規付与IDの前後にあるPythonのstr.strip対象空白だけを取り除きます]
#   処理: [1: Unicode空白の先頭/末尾位置を求め、内部空白を残した部分文字列を返します]
#   引数: [value: 型検査済みの新規状態ID（String）]
#   戻り値: [result: ASCII/Unicodeの前後空白を除いたID（String）]
# }
static func normalized_id(value: String) -> String:
	# Godotのstrip_edgesだけでは全角空白等が残るため、Pythonの空白集合に合わせます。
	var first := 0
	var last := value.length()
	while first < last and _is_python_space(value.unicode_at(first)):
		first += 1
	while last > first and _is_python_space(value.unicode_at(last - 1)):
		last -= 1
	return value.substr(first, last - first)


# {
#   責務: [_is_python_space: 状態IDの前後空白としてPythonが除くUnicodeコードポイントを判定します]
#   処理: [1: 制御空白・改行・各Unicode空白のコードポイント集合に一致するか返します]
#   引数: [codepoint: 状態IDの一文字のUnicode値（int）]
#   戻り値: [result: Python str.isspaceに対応する空白ならtrue（bool）]
# }
static func _is_python_space(codepoint: int) -> bool:
	return (codepoint >= 9 and codepoint <= 13) or (codepoint >= 28 and codepoint <= 32) \
		or (codepoint >= 8192 and codepoint <= 8202) \
		or codepoint in [133, 160, 5760, 8232, 8233, 8239, 8287, 12288]
