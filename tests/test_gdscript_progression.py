"""Real Godot level-table/learnset parity and read-only owned-roster projection."""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import unittest

import test_gdscript_roster as fixture
from kadoka_quest.core.monster import MonsterRecord, calculate_stats
from kadoka_quest.data.repository import GameRepository, STAT_KEYS
from kadoka_quest.data.species_creator import SpeciesCreator

ROOT = fixture.ROOT


def row(value=12):
    return {key: value for key in STAT_KEYS}


def case(stats=None, skills=None, level=1, **extra):
    return {"stats": {"levels": {"1": row()}} if stats is None else stats,
            "skills": {"learnset": [{"skill_id": "attack"}]} if skills is None else skills,
            "level": level, **extra}


class ProgressionBoundaryTests(unittest.TestCase):
    def test_pure_calculation_service_and_renderer_keep_separate_responsibilities(self):
        engine = (ROOT / "gdscript/engine/monster_progression.gd").read_text(encoding="utf-8")
        self.assertIn("extends RefCounted", engine)
        for forbidden in ("FileAccess", "DirAccess", "Vector2", "Color(", "Label", "OS.", "load_progression("):
            self.assertNotIn(forbidden, engine)
        service = (ROOT / "gdscript/application/monster_progression.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "Label", "Input."):
            self.assertNotIn(forbidden, service)
        view = (ROOT / "gdscript/ui/roster_view.gd").read_text(encoding="utf-8")
        self.assertNotIn("load_progression(", view)
        self.assertNotIn("Progression.rebuild", view)


@unittest.skipUnless(fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real progression and roster probes")
class GDScriptProgressionTests(unittest.TestCase):
    setUp = fixture.GDScriptRosterTests.setUp
    seed_state = fixture.GDScriptRosterTests.seed_state
    seed_record = fixture.GDScriptRosterTests.seed_record
    write = fixture.GDScriptRosterTests.write
    saved_files = fixture.GDScriptRosterTests.saved_files

    def contracts(self, **request):
        path = self.content / "progression-probe.json"
        path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
        environment = dict(os.environ, KADOKA_CONTENT_ROOT=str(self.content), KADOKA_SAVE_DIR=str(self.legacy),
                           KADOKA_GDSCRIPT_SAVE_ROOT=str(self.saves), KADOKA_GDSCRIPT_SAVE_NAME="default")
        actual = subprocess.run(
            [str(fixture.GODOT), "--headless", "--path", str(ROOT / "gdscript"), "--script",
             "res://tests/run_progression_probe.gd", "--", str(path)],
            cwd=self.content, env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60, check=False,
        )
        self.assertEqual(actual.returncode, 0, actual.stderr + actual.stdout[-1200:])
        self.assertNotIn("SCRIPT ERROR", actual.stderr)
        for line in actual.stdout.splitlines():
            if line.startswith("KADOKA_PROGRESSION_RESULT="):
                return json.loads(base64.b64decode(line.split("=", 1)[1]).decode("utf-8"))
        self.fail(actual.stderr + actual.stdout[-1200:])

    def roster(self, actions=()):
        return fixture.GDScriptRosterTests.probe(self, actions)["observations"][-1]

    def template(self, species):
        bundle = GameRepository(self.content / "data").get_species(species)
        return {"stats": bundle.stats, "skills": bundle.skills}

    def content_hashes(self):
        return {str(path.relative_to(self.content)): hashlib.sha256(path.read_bytes()).hexdigest()
                for directory in ("data", "assets", "python-saves")
                for path in (self.content / directory).rglob("*") if path.is_file()}

    def test_all_sample_species_all_100_levels_match_python_base_and_no_plus_skills(self):
        repository = GameRepository(self.content / "data")
        ids = repository.list_species_ids()
        self.assertEqual(set(ids), {"hero", "slime", "ball_slime", "metal_slime", "ghost", "maru", "kadoka", "dice_slime"})
        cases = [{"template": identifier, "level": level} for identifier in ids for level in range(1, 101)]
        before = self.content_hashes()
        result = self.contracts(templates={identifier: self.template(identifier) for identifier in ids}, cases=cases)
        for parameters, actual in zip(cases, result["results"]):
            with self.subTest(**parameters):
                self.assertTrue(actual["ok"])
                self.assertEqual(actual["stats"], repository.stats_at(parameters["template"], parameters["level"]))
                self.assertEqual(actual["skill_ids"], repository.skill_ids_at(parameters["template"], parameters["level"]))
                self.assertFalse(actual["modifiers_applied"])
                self.assertEqual(actual["scope"], "level_base")
                self.assertEqual(actual["unimplemented_modifiers"], ["plus", "equipment"])
        self.assertTrue(all(result["input_preserved"]))
        self.assertEqual(self.content_hashes(), before)
        self.assertFalse(self.profile.exists())

    def test_growth_generated_explicit_rows_and_manual_override_match_python(self):
        spec = importlib.util.spec_from_file_location(
            "kadoka_sample_growth_reference", ROOT / "tools/sample-data/script/_generate_sample_data_impl.py")
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)  # main() is not invoked; do not regenerate canonical JSON.
        stats = {"levels": generator.level_table([1, 2, 3, 4, 5, 6], [101, 203, 305, 407, 509, 611])}
        stats["levels"]["50"] = row(777)  # Explicit editor change wins over any endpoint interpolation.
        skills = {"learnset": [{"level": 49, "skill_id": "first"}, {"level": 50, "skill_id": "second"}]}
        base = self.content / "data/species/slime"
        (base / "stats.json").write_text(json.dumps(stats), encoding="utf-8")
        (base / "skills.json").write_text(json.dumps(skills), encoding="utf-8")
        expected = GameRepository(self.content / "data")
        result = self.contracts(templates={"growth": {"stats": stats, "skills": skills}},
                                cases=[{"template": "growth", "level": level} for level in range(1, 101)])
        for level, actual in enumerate(result["results"], 1):
            with self.subTest(level=level):
                self.assertEqual(actual["stats"], expected.stats_at("slime", level))
                self.assertEqual(actual["skill_ids"], expected.skill_ids_at("slime", level))
        self.assertEqual(result["results"][49]["stats"], row(777))

    def test_new_species_draft_growth_is_read_without_a_runtime_formula(self):
        repository = GameRepository(self.content / "data")
        _, stats, skills, _ = SpeciesCreator(repository, self.content / "assets").build_draft()
        result = self.contracts(templates={"draft": {"stats": stats, "skills": skills}},
                                cases=[{"template": "draft", "level": level} for level in (1, 50, 100)])
        for level, actual in zip((1, 50, 100), result["results"]):
            with self.subTest(level=level):
                self.assertEqual(actual["stats"], stats["levels"][str(level)])
        self.assertEqual(result["results"][1]["skill_ids"], ["attack", "defend"])

    def test_every_sample_skill_threshold_before_at_and_after_matches_python(self):
        repository = GameRepository(self.content / "data")
        templates = {identifier: self.template(identifier) for identifier in repository.list_species_ids()}
        cases = [{"template": identifier, "level": level} for identifier, template in templates.items()
                 for entry in template["skills"]["learnset"]
                 for level in (max(1, entry["level"] - 1), entry["level"], entry["level"] + 1)]
        result = self.contracts(templates=templates, cases=cases)
        for parameters, actual in zip(cases, result["results"]):
            with self.subTest(**parameters):
                self.assertEqual(actual["skill_ids"], repository.skill_ids_at(parameters["template"], parameters["level"]))

    def test_order_duplicates_defaults_and_missing_learnset_follow_python(self):
        learnset = [{"level": 20, "skill_id": "later"}, {"skill_id": "first"},
                    {"level": "3", "skill_id": "second"}, {"level": 2.9, "skill_id": "first"}]
        actual = self.contracts(cases=[case(skills={"learnset": learnset}),
                                       case(skills={"learnset": learnset}, level=20,
                                            stats={"levels": {"20": row()}}), case(skills={})])["results"]
        self.assertEqual(actual[0]["skill_ids"], ["first"])
        self.assertEqual(actual[1]["skill_ids"], ["later", "first", "second"])
        self.assertEqual(actual[2]["skill_ids"], [])

    def test_old_schema_numeric_conversion_and_clamp_match_repository_contract(self):
        stats = self.template("slime")["stats"]
        stats.pop("schema_version")
        stats["levels"]["42"] = dict(zip(STAT_KEYS, ("  +27 ", 12.9, -1.9, "-3", 0, 45)))
        skills = {"learnset": [{"skill_id": "attack"}, {"level": 101, "skill_id": "future"}]}
        base = self.content / "data/species/slime"
        (base / "stats.json").write_text(json.dumps(stats), encoding="utf-8")
        (base / "skills.json").write_text(json.dumps(skills), encoding="utf-8")
        repository = GameRepository(self.content / "data")
        levels = (-9, 0, 1, 1.9, "  +42 ", 50, 100, 101, 999)
        result = self.contracts(templates={"old": {"stats": stats, "skills": skills}},
                                cases=[{"template": "old", "level": level} for level in levels])
        for level, actual in zip(levels, result["results"]):
            with self.subTest(level=level):
                self.assertTrue(actual["ok"])
                self.assertEqual(actual["stats"], repository.stats_at("slime", level))
                self.assertEqual(actual["skill_ids"], repository.skill_ids_at("slime", level))
                self.assertEqual(actual["stats_level"], max(1, min(100, int(level))))

    def test_invalid_documents_rows_schema_and_numbers_fail_without_placeholder_stats(self):
        cases = [case(stats={}), case(stats={"levels": []}), case(stats={"levels": {"1": []}}),
                 case(stats={"levels": {"2": row()}}), case(stats={"schema_version": 2, "levels": {"1": row()}}),
                 case(skills={"schema_version": True}), case(skills={"learnset": None}),
                 case(skills={"learnset": [None]}), case(skills={"learnset": [{}]}),
                 case(skills={"learnset": [{"skill_id": ""}]}),
                 case(skills={"learnset": [{"level": "not_a_number", "skill_id": "attack"}]}),
                 case(stats={"growth": {"base": 1, "final": 100}})]
        for value in (None, True, [], {}, "1.2", "NaN", 1e100, "9007199254740992"):
            invalid = row()
            invalid["attack"] = value
            cases.append(case(stats={"levels": {"1": invalid}}))
        missing = row()
        missing.pop("mp")
        cases.append(case(stats={"levels": {"1": missing}}))
        cases.extend([{**case(), "stats": None}, {**case(), "skills": []}])
        cases.extend(case(level=value) for value in (None, True, {}, "", "1.2", 1e100))
        actual = self.contracts(cases=cases)
        for index, result in enumerate(actual["results"]):
            with self.subTest(index=index):
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"], "invalid_progression")
                self.assertTrue(result["message"])
                self.assertNotIn("stats", result)
                self.assertNotIn("skill_ids", result)
        self.assertTrue(all(actual["input_preserved"]))

    def test_return_values_cannot_mutate_source_documents_or_next_result(self):
        actual = self.contracts(cases=[case(nonfinite=kind) for kind in ("level_inf", "stat_inf", "stat_nan")])
        self.assertTrue(all(not result["ok"] for result in actual["results"]))
        self.assertEqual(actual["input_preserved"], [True, True, True])
        template = self.template("slime")
        template["stats"]["extra"] = {"unknown": [True, "保持"]}
        actual = self.contracts(templates={"shared": template}, cases=[
            {"template": "shared", "level": 1, "mutate_result": True}, {"template": "shared", "level": 1}])
        self.assertEqual(actual["results"][0], actual["results"][1])
        self.assertEqual(actual["input_preserved"], [True, True])

    def test_repository_reads_bundles_without_changing_content_or_creating_profile(self):
        ids = GameRepository(self.content / "data").list_species_ids()
        before = self.content_hashes()
        actual = self.contracts(load_ids=ids)["bundles"]
        for identifier, bundle in zip(ids, actual):
            with self.subTest(identifier=identifier):
                self.assertEqual(bundle, {"ok": True, **self.template(identifier)})
        self.assertEqual(self.content_hashes(), before)
        self.assertFalse(self.profile.exists())

    def test_repository_rejects_unsafe_ids_missing_and_malformed_objects(self):
        invalid_ids = ("../slime", "", "Slime", "slime/../../", "does_not_exist")
        actual = self.contracts(load_ids=invalid_ids)["bundles"]
        for identifier, result in zip(invalid_ids, actual):
            with self.subTest(identifier=identifier):
                self.assertFalse(result["ok"])
                self.assertTrue(result["message"])
        path = self.content / "data/species/slime/stats.json"
        for raw in ("{broken", "[]", "null"):
            with self.subTest(raw=raw):
                path.write_text(raw, encoding="utf-8")
                self.assertEqual(self.contracts(load_ids=["slime"])["bundles"][0]["error"], "invalid_content")
                self.assertEqual(path.read_text(encoding="utf-8"), raw)

    def test_application_reads_one_bundle_per_species_per_scan_without_final_modifiers(self):
        actual = self.contracts(join_bundle={"ok": True, **self.template("slime")}, join_monsters=[
            {"species_id": "slime", "level": 1}, {"species_id": "slime", "level": 42},
            {"species_id": "slime", "level": 100, "equipment_id": "ken", "plus_choices": ["any"]}])
        self.assertEqual(actual["reads"], 1)
        self.assertEqual(actual["next_scan_reads"], 2)
        for level, result in zip((1, 42, 100), actual["joins"]):
            with self.subTest(level=level):
                self.assertEqual(result["stats"], GameRepository(self.content / "data").stats_at("slime", level))
                self.assertFalse(result["modifiers_applied"])

    def test_roster_projects_base_stats_and_level_skills_leaving_individual_and_ai_bytes(self):
        self.seed_state(current_party=["slimeA", "ghostA"])
        repository = GameRepository(self.content / "data")
        ghost_plus = next(option["id"] for stage in repository.get_species("ghost").plus["stages"]
                          for option in stage["options"] if option["kind"] == "skill")
        slime_plus = next(option["id"] for option in repository.get_species("slime").plus["stages"][0]["options"]
                          if option["kind"] == "stat_add")
        self.seed_record("slimeA", level=100, plus_choices=[slime_plus], equipment_id="ken")
        self.seed_record("ghostA", "ghost", level=1, plus_choices=[ghost_plus])
        before = self.saved_files()
        content = self.content_hashes()
        actual = self.roster([{"kind": "key", "key": "F6"}])
        for identifier, species, level in (("slimeA", "slime", 100), ("ghostA", "ghost", 1)):
            rebuilt = actual["owned"]["records"][identifier]["progression"]
            self.assertEqual(rebuilt["stats"], repository.stats_at(species, level))
            self.assertEqual(rebuilt["skill_ids"], repository.skill_ids_at(species, level))
        self.assertIn("基礎能力値（＋/装備補正は未反映）", actual["text"])
        self.assertIn("Lv習得スキルID（＋追加は未反映）", actual["text"])
        self.assertIn("HP 650 / MP 390", actual["text"])
        self.assertEqual(self.saved_files(), before)
        self.assertEqual(self.content_hashes(), content)
        record = MonsterRecord(json.loads(before[str(Path("monsters/slimeA/monster.json"))]), {})
        self.assertNotEqual(calculate_stats(repository, record), repository.stats_at("slime", 100))
        self.assertNotEqual(repository.skill_ids_at("ghost", 1, [ghost_plus]), repository.skill_ids_at("ghost", 1))

    def test_roster_invalid_progression_keeps_record_party_ai_and_warns_no_auto_repair(self):
        self.seed_state(current_party=["kept"])
        self.seed_record("kept", level=42)
        before = self.saved_files()
        path = self.content / "data/species/slime/stats.json"
        path.write_text("{broken", encoding="utf-8")
        content = self.content_hashes()
        actual = self.roster([{"kind": "key", "key": "F6"}])
        record = actual["owned"]["records"]["kept"]
        self.assertFalse(record["progression"]["ok"])
        self.assertEqual(actual["owned"]["party"][0]["id"], "kept")
        self.assertIn("基礎能力値/習得スキル: 読込不可", actual["text"])
        self.assertIn("注意", actual["text"])
        self.assertEqual(self.saved_files(), before)
        self.assertEqual(self.content_hashes(), content)

    def test_reopen_rebuilds_external_level_table_changes_without_mutating_individual(self):
        self.seed_state(current_party=["kept"])
        self.seed_record("kept", level=42)
        before = self.saved_files()
        first = self.roster([{"kind": "key", "key": "F6"}])
        path = self.content / "data/species/slime/stats.json"
        stats = json.loads(path.read_text(encoding="utf-8"))
        stats["levels"]["42"] = row(4321)
        path.write_text(json.dumps(stats), encoding="utf-8")
        second = self.roster([{"kind": "key", "key": "F6"}])
        self.assertNotEqual(first["owned"]["records"]["kept"]["progression"]["stats"], row(4321))
        self.assertEqual(second["owned"]["records"]["kept"]["progression"]["stats"], row(4321))
        self.assertEqual(self.saved_files(), before)

    def test_legacy_individual_without_level_uses_lv1_without_resaving(self):
        self.seed_state(current_party=["old"])
        monster = self.seed_record("old")
        monster.pop("level")
        self.write("monsters/old/monster.json", monster)
        before = self.saved_files()
        actual = self.roster([{"kind": "key", "key": "F6"}])
        rebuilt = actual["owned"]["records"]["old"]["progression"]
        self.assertEqual(rebuilt["level"], 1)
        self.assertEqual(rebuilt["stats"], GameRepository(self.content / "data").stats_at("slime", 1))
        self.assertEqual(self.saved_files(), before)


if __name__ == "__main__":
    unittest.main()
