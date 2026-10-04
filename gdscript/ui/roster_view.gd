extends PanelContainer
## Read-only projection and explicit editor entry. No persistence or AI decisions.

signal edit_requested
var edit_button: Button

var heading: Label
var scrolling: ScrollContainer
var body: Label


func _ready() -> void:
	var style := StyleBoxFlat.new()
	style.bg_color = Color("#091329")
	style.border_color = Color("#d5e0f2")
	style.set_border_width_all(2)
	style.set_content_margin_all(16)
	add_theme_stylebox_override("panel", style)
	var column := VBoxContainer.new()
	add_child(column)
	heading = Label.new()
	heading.add_theme_font_size_override("font_size", 20)
	column.add_child(heading)
	var help := Label.new()
	help.text = "↑↓ / PageUp・Down / Home・End：スクロール　E：編成　F6 / Esc：閉じる"
	help.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	column.add_child(help)
	edit_button = Button.new()
	edit_button.text = "パーティを編成する（E）"
	edit_button.focus_mode = Control.FOCUS_NONE
	edit_button.pressed.connect(func(): edit_requested.emit())
	column.add_child(edit_button)
	scrolling = ScrollContainer.new()
	scrolling.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scrolling.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scrolling.focus_mode = Control.FOCUS_NONE
	column.add_child(scrolling)
	body = Label.new()
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	scrolling.add_child(body)


func show_snapshot(snapshot: Dictionary) -> void:
	var records: Dictionary = snapshot.get("records", {})
	heading.text = "パーティ・保有個体（%d体）" % records.size()
	var lines: PackedStringArray = ["現在パーティ（最大4枠）"]
	for index in 4:
		var entry: Dictionary = snapshot.get("party", [])[index] if index < snapshot.get("party", []).size() else {}
		var record: Variant = entry.get("record")
		var text := "空き枠"
		if record is Dictionary:
			text = _record_summary(record)
		elif entry.get("id") != null:
			text = "読込不可: " + str(entry["id"])
		lines.append("%d. %s" % [index + 1, text])
	lines.append("\n保有個体（所有数の上限なし／今回の画面では編集できません）")
	for id: String in records:
		var record: Dictionary = records[id]
		var ai: Dictionary = record["ai"]
		lines.append(_record_summary(record) + "\n  ID: " + id)
		lines.append(_progression_summary(record.get("progression", {})))
		lines.append("  装備: %s / AI: %s・%s / 戦闘経験: %s回\n" % [
			str(record["monster"].get("equipment_id")) if record["monster"].get("equipment_id") != null else "なし",
			str(ai.get("profile", "normal")),
			str(ai.get("tactic", "balanced")), str(ai.get("battles", 0)),
		])
	if records.is_empty():
		lines.append("新規セーブはF5で初期仲間を作成します。" if snapshot.get("new_profile", false)
			else "このセーブに読込可能な個体はありません。既存セーブへ初期仲間は自動追加しません。")
	for warning in snapshot.get("warnings", []):
		lines.append("注意: " + str(warning))
	body.text = "\n".join(lines)
	scrolling.set_deferred("scroll_vertical", 0)


static func _record_summary(record: Dictionary) -> String:
	var monster: Dictionary = record["monster"]
	return "%s（%s） Lv.%d / ＋%d" % [monster["name"], record["species"].get("display_name", monster["species_id"]),
		int(monster.get("level", 1)), monster.get("plus_choices", []).size()]


static func _progression_summary(progression: Dictionary) -> String:
	if not progression.get("ok", false):
		return "  基礎能力値/習得スキル: 読込不可（完成能力値ではありません）"
	var lines: PackedStringArray = ["  基礎能力値（＋/装備補正前）: " + _stats_text(progression["stats"]),
		"  Lv習得スキルID（＋追加前）: " + _skill_text(progression["skill_ids"])]
	var modified: Dictionary = progression.get("modifiers", {})
	if not modified.get("ok", false):
		lines.append("  補正後能力値: 読込不可（基礎値を補正後の代用にしません）: " + str(modified.get("message", "未構築")))
	else:
		lines.append("  補正後能力値（＋/装備）: " + _stats_text(modified["stats"]))
		lines.append("  使用可能スキルID（Lv習得＋＋追加）: " + _skill_text(modified["skill_ids"]))
		for note in modified.get("warnings", []):
			lines.append("  注意: " + str(note))
	return "\n".join(lines)


static func _stats_text(stats: Dictionary) -> String:
	return "HP %d / MP %d / 攻 %d / 防 %d / 速 %d / 魔 %d" % [
		stats["hp"], stats["mp"], stats["attack"], stats["defense"], stats["speed"], stats["magic"]]


static func _skill_text(ids: Array) -> String:
	var skills: PackedStringArray = []
	for id in ids:
		skills.append(str(id))
	return ", ".join(skills) if not skills.is_empty() else "なし"


func handle_key(key: int) -> void:
	var bar := scrolling.get_v_scroll_bar()
	match key:
		KEY_UP: scrolling.scroll_vertical -= 32
		KEY_DOWN: scrolling.scroll_vertical += 32
		KEY_PAGEUP: scrolling.scroll_vertical -= int(bar.page)
		KEY_PAGEDOWN: scrolling.scroll_vertical += int(bar.page)
		KEY_HOME: scrolling.scroll_vertical = 0
		KEY_END: scrolling.scroll_vertical = int(bar.max_value - bar.page)
