from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from kadoka_engine.spawn_settings import validate_map_spawns


class DataValidator:
    """Collect mod-data problems without stopping application startup."""

    REQUIRED_SPECIES_FILES = ("species.json", "stats.json", "skills.json", "plus.json")

    def __init__(self, data_root: Path) -> None:
        self.root = Path(data_root)
        self.issues: list[dict[str, str]] = []

    def _issue(self, code: str, path: Path | str, message: str, severity: str = "error") -> None:
        try:
            relative = Path(path).relative_to(self.root).as_posix()
        except (TypeError, ValueError):
            relative = str(path).replace("\\", "/")
        self.issues.append({"severity": severity, "code": code, "path": relative, "message": message})

    def _document(self, path: Path, required: bool = True) -> dict[str, Any] | None:
        if not path.is_file():
            if required:
                self._issue("file.missing", path, "必須JSONファイルがありません。")
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            self._issue("json.invalid", path, f"JSONを読み込めません: {error}")
            return None
        if not isinstance(payload, dict):
            self._issue("json.root_type", path, "JSONの最上位はオブジェクトにしてください。")
            return None
        return payload

    @staticmethod
    def _values(payload: dict[str, Any] | None, section: str, key: str) -> set[str]:
        if not payload:
            return set()
        source = payload.get(section, {})
        if not isinstance(source, dict):
            return set()
        values = source.get(key, [])
        return {str(value) for value in values} if isinstance(values, list) else set()

    def _catalog(self, path: Path, list_key: str) -> tuple[dict[str, dict[str, Any]], dict[str, Any] | None]:
        payload = self._document(path)
        catalog: dict[str, dict[str, Any]] = {}
        if payload is None:
            return catalog, payload
        entries = payload.get(list_key)
        if not isinstance(entries, list):
            self._issue("catalog.invalid", path, f"{list_key} は配列にしてください。")
            return catalog, payload
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict) or not str(entry.get("id", "")).strip():
                self._issue("catalog.id_missing", path, f"{list_key}[{index}] にIDがありません。")
                continue
            entry_id = str(entry["id"])
            if entry_id in catalog:
                self._issue("catalog.id_duplicate", path, f"ID {entry_id} が重複しています。")
            catalog[entry_id] = entry
        return catalog, payload

    def _validate_blocks(self) -> set[str]:
        block_ids: set[str] = set()
        for path in sorted((self.root / "blocks").glob("*.json")):
            block = self._document(path)
            if block is None:
                continue
            block_id = str(block.get("id", "")).strip()
            if not block_id:
                self._issue("block.id_missing", path, "ブロックIDがありません。")
                continue
            if block_id != path.stem:
                self._issue("block.id_mismatch", path, f"ID {block_id} とファイル名が一致しません。")
            if block_id in block_ids:
                self._issue("block.id_duplicate", path, f"ブロックID {block_id} が重複しています。")
            block_ids.add(block_id)
            for key in ("player_walkable", "enemy_spawnable", "enemy_walkable"):
                if not isinstance(block.get(key), bool):
                    self._issue("block.rule_invalid", path, f"{key} は true/false で指定してください。")
        if not block_ids:
            self._issue("block.none", self.root / "blocks", "利用可能なブロック定義がありません。")
        return block_ids

    def _validate_species(
        self,
        skill_ids: set[str],
        stat_ids: set[str],
        element_ids: set[str],
        resistance_values: set[str],
    ) -> set[str]:
        species_ids: set[str] = set()
        species_root = self.root / "species"
        folders = sorted(path for path in species_root.iterdir() if path.is_dir()) if species_root.is_dir() else []
        for folder in folders:
            documents = {name: self._document(folder / name) for name in self.REQUIRED_SPECIES_FILES}
            definition = documents["species.json"]
            if definition is None:
                continue
            species_id = str(definition.get("id", "")).strip()
            if not species_id:
                self._issue("species.id_missing", folder / "species.json", "種族IDがありません。")
                continue
            if species_id != folder.name:
                self._issue("species.id_mismatch", folder / "species.json", f"ID {species_id} とフォルダ名が一致しません。")
            if species_id in species_ids:
                self._issue("species.id_duplicate", folder / "species.json", f"種族ID {species_id} が重複しています。")
            species_ids.add(species_id)
            resistances = definition.get("resistances", {})
            if not isinstance(resistances, dict):
                self._issue("species.resistances_invalid", folder / "species.json", "resistances はオブジェクトにしてください。")
            else:
                for element, value in resistances.items():
                    if str(element) not in element_ids:
                        self._issue("resistance.element_unknown", folder / "species.json", f"未知の耐性名です: {element}")
                    if str(value) not in resistance_values:
                        self._issue("resistance.value_unknown", folder / "species.json", f"未知の耐性段階です: {value}")
            self._validate_stats(folder / "stats.json", documents["stats.json"], stat_ids)
            self._validate_learnset(folder / "skills.json", documents["skills.json"], skill_ids)
            self._validate_plus(folder / "plus.json", documents["plus.json"], skill_ids, stat_ids)
        if not species_ids:
            self._issue("species.none", species_root, "利用可能な種族定義がありません。")
        return species_ids

    def _validate_stats(self, path: Path, payload: dict[str, Any] | None, stat_ids: set[str]) -> None:
        if payload is None:
            return
        levels = payload.get("levels")
        if not isinstance(levels, dict):
            self._issue("stats.levels_invalid", path, "levels はオブジェクトにしてください。")
            return
        for level in range(1, 101):
            values = levels.get(str(level))
            if not isinstance(values, dict):
                self._issue("stats.level_missing", path, f"Lv{level} の能力値がありません。")
                continue
            for stat_id in stat_ids:
                if not isinstance(values.get(stat_id), (int, float)):
                    self._issue("stats.value_invalid", path, f"Lv{level} の {stat_id} は数値で指定してください。")

    def _validate_learnset(self, path: Path, payload: dict[str, Any] | None, skill_ids: set[str]) -> None:
        if payload is None:
            return
        learnset = payload.get("learnset")
        if not isinstance(learnset, list):
            self._issue("learnset.invalid", path, "learnset は配列にしてください。")
            return
        for index, entry in enumerate(learnset):
            if not isinstance(entry, dict):
                self._issue("learnset.entry_invalid", path, f"learnset[{index}] はオブジェクトにしてください。")
                continue
            skill_id = str(entry.get("skill_id", ""))
            if skill_id not in skill_ids:
                self._issue("learnset.skill_unknown", path, f"存在しないスキルIDです: {skill_id or '(空)'}")
            level = entry.get("level")
            if not isinstance(level, int) or not 1 <= level <= 100:
                self._issue("learnset.level_invalid", path, f"{skill_id or index} の習得Lvは1〜100にしてください。")

    def _validate_plus(
        self,
        path: Path,
        payload: dict[str, Any] | None,
        skill_ids: set[str],
        stat_ids: set[str],
    ) -> None:
        if payload is None:
            return
        stages = payload.get("stages")
        if not isinstance(stages, list):
            self._issue("plus.stages_invalid", path, "stages は配列にしてください。")
            return
        options: list[dict[str, Any]] = []
        for stage in stages:
            if isinstance(stage, dict) and isinstance(stage.get("options"), list):
                options.extend(option for option in stage["options"] if isinstance(option, dict))
        option_ids = {str(option.get("id")) for option in options if str(option.get("id", "")).strip()}
        if len(option_ids) != len(options):
            self._issue("plus.option_id_invalid", path, "＋選択肢IDの欠損または重複があります。")
        for option in options:
            option_id = str(option.get("id", "(IDなし)"))
            skill_id = option.get("skill_id")
            if skill_id is not None and str(skill_id) not in skill_ids:
                self._issue("plus.skill_unknown", path, f"{option_id} が存在しないスキル {skill_id} を参照しています。")
            stat_id = option.get("stat")
            if stat_id is not None and str(stat_id) not in stat_ids:
                self._issue("plus.stat_unknown", path, f"{option_id} が存在しない能力 {stat_id} を参照しています。")
            for requirement_key in ("requires_any", "requires_all"):
                requirements = option.get(requirement_key, [])
                if requirements is None:
                    continue
                if not isinstance(requirements, list):
                    self._issue("plus.requirements_invalid", path, f"{option_id} の {requirement_key} は配列にしてください。")
                    continue
                for required_id in requirements:
                    if str(required_id) not in option_ids:
                        self._issue("plus.requirement_unknown", path, f"{option_id} の分岐先 {required_id} が存在しません。")

    def _validate_skills(self, catalog: dict[str, dict[str, Any]], path: Path, kinds: set[str], elements: set[str]) -> None:
        for skill_id, skill in catalog.items():
            if str(skill.get("kind", "")) not in kinds:
                self._issue("skill.kind_unknown", path, f"{skill_id} のkindが不正です: {skill.get('kind')}")
            element = skill.get("element")
            if element is not None and str(element) not in elements:
                self._issue("skill.element_unknown", path, f"{skill_id} の属性が不正です: {element}")
            if not isinstance(skill.get("mp_cost"), (int, float)) or float(skill.get("mp_cost", -1)) < 0:
                self._issue("skill.mp_invalid", path, f"{skill_id} のMP消費は0以上の数値にしてください。")

    def _validate_equipment(
        self,
        catalog: dict[str, dict[str, Any]],
        path: Path,
        species_ids: set[str],
        skill_ids: set[str],
        stat_ids: set[str],
        categories: set[str],
        elements: set[str],
    ) -> None:
        for equipment_id, equipment in catalog.items():
            if str(equipment.get("category", "")) not in categories:
                self._issue("equipment.category_unknown", path, f"{equipment_id} の装備カテゴリが不正です: {equipment.get('category')}")
            allowed = equipment.get("allowed_species_ids")
            if not isinstance(allowed, list):
                self._issue("equipment.allowed_species_invalid", path, f"{equipment_id} の allowed_species_ids は配列にしてください。")
            else:
                for species_id in allowed:
                    if str(species_id) not in species_ids:
                        self._issue("equipment.species_unknown", path, f"{equipment_id} が存在しない種族 {species_id} を参照しています。")
            mappings = (
                ("stat_multipliers", stat_ids, "equipment.stat_unknown", "能力"),
                ("skill_modifiers", skill_ids, "equipment.skill_unknown", "スキル"),
                ("resistance_steps", elements, "equipment.element_unknown", "耐性"),
            )
            for field, known_ids, code, label in mappings:
                values = equipment.get(field, {})
                if not isinstance(values, dict):
                    self._issue("equipment.mapping_invalid", path, f"{equipment_id} の {field} はオブジェクトにしてください。")
                    continue
                for referenced_id in values:
                    if str(referenced_id) not in known_ids:
                        self._issue(code, path, f"{equipment_id} が存在しない{label} {referenced_id} を参照しています。")

    def _validate_maps(self, block_ids: set[str], species_ids: set[str]) -> None:
        map_paths = sorted((self.root / "maps").glob("*/map.json"))
        if not map_paths:
            self._issue("map.none", self.root / "maps", "利用可能なマップ定義がありません。")
        map_ids = {path.parent.name for path in map_paths}
        loaded = [(path, self._document(path)) for path in map_paths]
        for path, payload in loaded:
            if payload is None:
                continue
            map_id = str(payload.get("id", ""))
            if map_id != path.parent.name:
                self._issue("map.id_mismatch", path, f"ID {map_id or '(空)'} とフォルダ名が一致しません。")
            width, height = payload.get("width"), payload.get("height")
            tiles = payload.get("tiles")
            if not isinstance(width, int) or not isinstance(height, int) or not isinstance(tiles, list):
                self._issue("map.dimensions_invalid", path, "width、height、tiles の形式が不正です。")
            elif len(tiles) != height or any(not isinstance(row, list) or len(row) != width for row in tiles):
                self._issue("map.dimensions_mismatch", path, "tiles の行列数がwidth/heightと一致しません。")
            else:
                unknown = sorted({str(tile) for row in tiles for tile in row} - block_ids)
                for block_id in unknown:
                    self._issue("map.block_unknown", path, f"存在しないブロックIDです: {block_id}")
            for issue in validate_map_spawns(payload, species_ids):
                self._issue(issue["code"], path, f"{issue['field']}: {issue['message']}")
            for mob in payload.get("fixed_mobs", []) if isinstance(payload.get("fixed_mobs", []), list) else []:
                if isinstance(mob, dict) and str(mob.get("species_id", "")) not in species_ids:
                    self._issue("map.mob_species_unknown", path, f"固定モブが存在しない種族 {mob.get('species_id')} を参照しています。")
            events = payload.get("events", [])
            for event in events if isinstance(events, list) else []:
                if not isinstance(event, dict):
                    continue
                if event.get("type") == "transition":
                    target = event.get("target", {})
                    target_id = str(target.get("map_id", "")) if isinstance(target, dict) else ""
                    if target_id not in map_ids:
                        self._issue("map.transition_unknown", path, f"移動先マップ {target_id or '(空)'} が存在しません。")
                if event.get("type") != "use_requirement":
                    continue
                required = event.get("required")
                if not isinstance(required, dict) or required.get("kind") not in {"item", "skill"} or not isinstance(required.get("id"), str) or not required["id"]:
                    self._issue("map.use_requirement_invalid", path, "使用条件には item/skill と空でない ID が必要です。")
                try:
                    radius = int(event.get("radius", 0))
                except (TypeError, ValueError):
                    radius = -1
                if radius < 0:
                    self._issue("map.use_requirement_radius", path, "使用イベントの範囲は 0 以上の整数にしてください。")
                effect = event.get("effect", {})
                if not isinstance(effect, dict) or effect.get("kind", "message") not in {"message", "gain_item"}:
                    self._issue("map.use_requirement_effect", path, "使用イベントの effect.kind が未対応です。")

    def validate(self) -> list[dict[str, str]]:
        self.issues = []
        project = self._document(self.root / "project.json")
        stat_ids = self._values(project, "validation", "stat_ids")
        skill_kinds = self._values(project, "validation", "skill_kinds")
        categories = self._values(project, "validation", "equipment_categories")
        elements = self._values(project, "validation", "element_ids")
        resistance_values = self._values(project, "validation", "resistance_values")
        for key, values in (
            ("stat_ids", stat_ids),
            ("skill_kinds", skill_kinds),
            ("equipment_categories", categories),
            ("element_ids", elements),
            ("resistance_values", resistance_values),
        ):
            if not values:
                self._issue("project.rule_missing", self.root / "project.json", f"validation.{key} が未定義です。")
        skills_path = self.root / "skills" / "skills.json"
        skills, _ = self._catalog(skills_path, "skills")
        self._validate_skills(skills, skills_path, skill_kinds, elements)
        block_ids = self._validate_blocks()
        species_ids = self._validate_species(set(skills), stat_ids, elements, resistance_values)
        equipment_path = self.root / "equipment" / "equipment.json"
        equipment, _ = self._catalog(equipment_path, "equipment")
        self._validate_equipment(equipment, equipment_path, species_ids, set(skills), stat_ids, categories, elements)
        self._validate_maps(block_ids, species_ids)
        return sorted(self.issues, key=lambda issue: (issue["path"], issue["code"], issue["message"]))
