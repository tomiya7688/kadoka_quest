# {
#   責務: [status_resistance: 種族JSONの状態耐性を独立コピーし、属性耐性や装備段階と混ぜません]
#   フィールド: []
# }
extends RefCounted


# {
#   責務: [prepare: 種族定義のstatus_resistancesを読み、省略時だけ全状態が通常の空辞書へ補います]
#   処理: [1: 種族の外形を確認し、状態IDと耐性名の辞書検証へ委譲します]
#   引数: [species: 読取済みの正規/MOD種族定義（Variant）]
#   戻り値: [result: 独立status_resistances、または理由付き拒否（Dictionary）]
# }
static func prepare(species: Variant) -> Dictionary:
	# PythonのBattleDataLoaderと同様に、装備の属性resistance_stepsを状態耐性へ適用しません。
	if not species is Dictionary:
		return {"ok": false, "reason": "invalid_status_species"}
	return validate(species.get("status_resistances", {}))


# {
#   責務: [validate: 状態IDと耐性名を文字列に限定し、未知の文字列耐性も独立して保持します]
#   処理: [1: 不正な辞書/ID/耐性名を拒否し、文字列だけの辞書を複製します]
#   引数: [value: 戦闘準備へ渡す状態ID別耐性。空辞書は全状態normalを表します（Variant）]
#   戻り値: [result: ok=trueとstatus_resistances、またはinvalid_status_resistances（Dictionary）]
# }
static func validate(value: Variant) -> Dictionary:
	# 確率式や既知耐性の一覧を複製せず、未知名/absorb/reflectの解釈は付与契約へ任せます。
	if not value is Dictionary:
		return {"ok": false, "reason": "invalid_status_resistances"}
	for id in value:
		if not id is String or id.is_empty() or not value[id] is String:
			return {"ok": false, "reason": "invalid_status_resistances"}
	return {"ok": true, "status_resistances": value.duplicate()}
