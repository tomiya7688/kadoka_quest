"""Real Godot plus/equipment parity, error reasons and byte-preserving roster projection."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import unittest

import test_gdscript_roster as fixture
from kadoka_quest.core.monster import MonsterRecord, available_skill_ids, calculate_stats, equipment_allows_species
from kadoka_quest.data.repository import GameRepository, STAT_KEYS

ROOT = fixture.ROOT


def row(value=10):
    return {key: value for key in STAT_KEYS}


def plus_document(*options):
    return {"stages": [{"options": list(options)}]}


def equipment_document(multiplier=0.5, **changes):
    return {"equipment": [{"id": "test", "allowed_species_ids": ["slime"],
                           "stat_multipliers": {"speed": multiplier}, **changes}]}


def custom(*, plus=None, equipment=None, monster=None, **changes):
    return {"stats": {"levels": {"1": row()}}, "skills": {"learnset": [{"skill_id": "attack"}]},
            "plus": {} if plus is None else plus, "equipment": {"equipment": []} if equipment is None else equipment,
            "monster": {"species_id": "slime"} if monster is None else monster, **changes}


class ModifierBoundaryTests(unittest.TestCase):
    def test_calculation_service_and_renderer_keep_io_and_rendering_separate(self):
        for relative in ("engine/monster_modifiers.gd", "engine/stat_numbers.gd"):
            source = (ROOT / "gdscript" / relative).read_text(encoding="utf-8")
            for forbidden in ("FileAccess", "DirAccess", "OS.", "Label", "Vector2", "Color("):
                self.assertNotIn(forbidden, source)
        source = (ROOT / "gdscript/application/monster_reconstruction.gd").read_text(encoding="utf-8")
        for forbidden in ("FileAccess", "DirAccess", "Label", "Input.", "round("):
            self.assertNotIn(forbidden, source)
        self.assertNotIn("Modifiers.apply", (ROOT / "gdscript/ui/roster_view.gd").read_text(encoding="utf-8"))


@unittest.skipUnless(fixture.GODOT, "Set KADOKA_GODOT_EXECUTABLE for real modifier/roster probes")
class GDScriptModifierTests(unittest.TestCase):
    setUp = fixture.GDScriptRosterTests.setUp
    seed_state = fixture.GDScriptRosterTests.seed_state
    seed_record = fixture.GDScriptRosterTests.seed_record
    write = fixture.GDScriptRosterTests.write
    saved_files = fixture.GDScriptRosterTests.saved_files

    def contracts(self, **request):
        path = self.content / "modifiers-probe.json"
        path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
        environment = dict(os.environ, KADOKA_CONTENT_ROOT=str(self.content), KADOKA_SAVE_DIR=str(self.legacy),
                           KADOKA_GDSCRIPT_SAVE_ROOT=str(self.saves), KADOKA_GDSCRIPT_SAVE_NAME="default")
        actual = subprocess.run(
            [str(fixture.GODOT), "--headless", "--path", str(ROOT / "gdscript"), "--script",
             "res://tests/run_modifiers_probe.gd", "--", str(path)],
            cwd=self.content, env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60, check=False,
        )
        self.assertEqual(actual.returncode, 0, actual.stderr + actual.stdout[-1600:])
        self.assertNotIn("SCRIPT ERROR", actual.stderr)
        for line in actual.stdout.splitlines():
            if line.startswith("KADOKA_MODIFIERS_RESULT="):
                return json.loads(base64.b64decode(line.split("=", 1)[1]).decode("utf-8"))
        self.fail(actual.stderr + actual.stdout[-1600:])

    def roster(self):
        return fixture.GDScriptRosterTests.probe(self, [{"kind": "key", "key": "F6"}])["observations"][-1]

    def template(self, identifier):
        bundle = GameRepository(self.content / "data").get_species(identifier)
        return {"stats": bundle.stats, "skills": bundle.skills, "plus": bundle.plus}

    def content_hashes(self):
        return {str(path.relative_to(self.content)): hashlib.sha256(path.read_bytes()).hexdigest()
                for directory in ("data", "assets", "python-saves")
                for path in (self.content / directory).rglob("*") if path.is_file()}

    def reference(self, monster):
        repository = GameRepository(self.content / "data")
        record = MonsterRecord(monster, {})
        return calculate_stats(repository, record), available_skill_ids(repository, record)

    def install_custom(self, parameters):
        for name in ("stats", "skills", "plus"):
            path = self.content / "data/species/slime" / (name + ".json")
            path.write_text(json.dumps(parameters[name]), encoding="utf-8")
        (self.content / "data/equipment/equipment.json").write_text(json.dumps(parameters["equipment"]), encoding="utf-8")

    def assert_python(self, result, monster):
        stats, skills = self.reference(monster)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["stats"], stats)
        self.assertEqual(result["skill_ids"], skills)
        self.assertEqual(result["scope"], "stats_with_modifiers")

    def test_all_species_levels_choices_and_every_equipment_match_python(self):
        repository = GameRepository(self.content / "data")
        templates = {identifier: self.template(identifier) for identifier in repository.list_species_ids()}
        equipment = json.loads((self.content / "data/equipment/equipment.json").read_text(encoding="utf-8"))
        cases = []
        for identifier, template in templates.items():
            stages = template["plus"]["stages"]
            first = stages[0]["options"][0]["id"]
            chain = [stage["options"][0]["id"] for stage in stages]
            choices = [[], [first], [first, first], chain, list(reversed(chain)),
                       [stages[1]["options"][0]["id"]], [option["id"] for stage in stages for option in stage["options"]],
                       [first, "unknown_choice"]]
            for level in (1, 50, 100):
                for selected in choices:
                    for equipment_id in (None, *repository.get_equipment()):
                        cases.append({"template": identifier, "level": level, "monster": {
                            "species_id": identifier, "level": level, "plus_choices": selected, "equipment_id": equipment_id}})
        before = self.content_hashes()
        result = self.contracts(templates=templates, equipment=equipment, cases=cases)
        self.assertEqual(len(result["results"]), len(cases))
        for parameters, actual in zip(cases, result["results"]):
            with self.subTest(**parameters["monster"]):
                self.assert_python(actual, parameters["monster"])
                identifier = parameters["monster"]["equipment_id"]
                allowed = identifier is not None and equipment_allows_species(
                    repository.get_equipment()[identifier], parameters["monster"]["species_id"])
                self.assertEqual(actual["equipment_status"]["applied"], allowed)
        self.assertTrue(all(result["input_preserved"]))
        self.assertEqual(self.content_hashes(), before)
        self.assertFalse(self.profile.exists())

    def test_rounding_matches_python_even_ties_negative_and_near_half(self):
        values = [number / 2 for number in range(-19, 20)] + [2.499999999999, 2.500000000001, -2.500000000001]
        result = self.contracts(rounds=values, special_rounds=["inf", "nan"])["rounds"]
        for value, actual in zip(values, result):
            with self.subTest(value=value):
                self.assertEqual(actual, {"ok": True, "value": round(value)})
        self.assertEqual(result[-2:], [{"ok": False}, {"ok": False}])

    def test_json_order_not_choice_order_and_round_after_each_multiplier(self):
        options = [{"id": "multiply", "kind": "stat_multiplier", "stat": "attack", "value": 0.5},
                   {"id": "add", "kind": "stat_add", "stat": "attack", "value": 3},
                   {"id": "multiply2", "kind": "stat_multiplier", "stat": "attack", "value": 0.5}]
        parameters = custom(plus=plus_document(*options),
                            monster={"species_id": "slime", "plus_choices": ["add", "multiply2", "multiply"]})
        parameters["stats"]["levels"]["1"]["attack"] = 5
        self.install_custom(parameters)
        cases = [parameters, {**parameters, "monster": {
            "species_id": "slime", "plus_choices": ["multiply", "add", "multiply2"]}}]
        actual = self.contracts(cases=cases)["results"]
        for result, item in zip(actual, cases):
            self.assert_python(result, item["monster"])
        self.assertEqual(actual[0]["stats"]["attack"], 2)  # round(5*.5)=2, +3=5, round(5*.5)=2.
        self.assertEqual(actual[0]["stats"], actual[1]["stats"])

    def test_invalid_selection_order_count_and_prerequisite_not_silently_repaired(self):
        template = self.template("slime")
        stages = template["plus"]["stages"]
        first = stages[0]["options"][0]["id"]
        selected = [[], [first, first], [first, "missing", "missing"], [stages[1]["options"][0]["id"]],
                    [option["id"] for stage in stages for option in stage["options"]]]
        cases = [{"template": "slime", "monster": {"species_id": "slime", "level": 1, "plus_choices": value}}
                 for value in selected]
        actual = self.contracts(templates={"slime": template}, cases=cases)
        for parameters, result in zip(cases, actual["results"]):
            with self.subTest(choices=parameters["monster"]["plus_choices"]):
                self.assert_python(result, parameters["monster"])
        self.assertEqual(len(actual["results"][2]["warnings"]), 1)
        self.assertTrue(all(actual["input_preserved"]))

    def test_add_then_equipment_then_minimum_one_clamp_matches_python(self):
        parameters = custom(plus=plus_document({"id": "negative", "kind": "stat_add", "stat": "speed", "value": -7}),
                            equipment=equipment_document(-0.5),
                            monster={"species_id": "slime", "plus_choices": ["negative"], "equipment_id": "test"})
        parameters["stats"]["levels"]["1"] = {**row(0), "speed": 2}
        self.install_custom(parameters)
        actual = self.contracts(cases=[parameters])["results"][0]
        self.assert_python(actual, parameters["monster"])
        self.assertEqual(actual["stats"], {**row(1), "speed": 2})  # round((2-7)*-.5)=2 before final clamp.

    def test_old_defaults_integer_and_float_strings_plus_skill_deduplication(self):
        options = [{"id": "add", "kind": "stat_add", "stat": "hp", "value": "  +9 "},
                   {"id": "multiply", "kind": "stat_multiplier", "stat": "speed", "value": "0.25"},
                   {"id": "default_add", "kind": "stat_add", "stat": "hp"},
                   {"id": "default_multiplier", "kind": "stat_multiplier", "stat": "hp"},
                   {"id": "skill", "kind": "skill", "skill_id": "extra"},
                   {"id": "duplicate", "kind": "skill", "skill_id": "attack"}]
        parameters = custom(plus=plus_document(*options), equipment=equipment_document("1.5"),
                            monster={"species_id": "slime", "plus_choices": [item["id"] for item in options],
                                     "equipment_id": "test"})
        self.install_custom(parameters)
        actual = self.contracts(cases=[parameters])["results"][0]
        self.assert_python(actual, parameters["monster"])
        self.assertEqual(actual["skill_ids"], ["attack", "extra"])

    def test_equipment_whitelist_only_missing_denied_and_duplicate_definition_contract(self):
        cases = []
        for changes in ({"allowed_species_ids": []}, {"allowed_species_ids": ["ghost"]},
                        {"denied_species_ids": ["slime"]}, {"equipment_types": ["anything"]}):
            cases.append(custom(equipment=equipment_document(**changes),
                                monster={"species_id": "slime", "equipment_id": "test"}))
        no_allow = custom(equipment=equipment_document(), monster={"species_id": "slime", "equipment_id": "test"})
        no_allow["equipment"]["equipment"][0].pop("allowed_species_ids")
        cases.append(no_allow)
        duplicate = custom(equipment=equipment_document(), monster={"species_id": "slime", "equipment_id": "test"})
        duplicate["equipment"]["equipment"].append({
            "id": "test", "allowed_species_ids": ["slime"], "stat_multipliers": {"speed": 2}})
        cases.append(duplicate)
        actual = self.contracts(cases=cases)["results"]
        for parameters, result in zip(cases, actual):
            with self.subTest(equipment=parameters["equipment"]):
                self.install_custom(parameters)
                self.assert_python(result, parameters["monster"])
        self.assertEqual(actual[2]["equipment_status"]["reason"], "applied")  # No independent deny-list exists in Python.
        self.assertEqual(actual[-1]["stats"]["speed"], 20)

    def test_unknown_equipment_and_empty_ids_have_reasons_and_are_preserved(self):
        cases = [custom(equipment=equipment_document(), monster={"species_id": "slime", "equipment_id": identifier})
                 for identifier in (None, "", "unknown")]
        actual = self.contracts(cases=cases)
        for parameters, result in zip(cases, actual["results"]):
            self.install_custom(parameters)
            self.assert_python(result, parameters["monster"])
            self.assertEqual(result["equipment_status"]["requested_id"], parameters["monster"]["equipment_id"])
        self.assertEqual([item["equipment_status"]["reason"] for item in actual["results"]], ["none", "none", "unknown_id"])
        self.assertIn("unknown", actual["results"][-1]["warnings"][0])
        self.assertTrue(all(actual["input_preserved"]))

    def test_unknown_stat_and_future_plus_kind_match_ignored_python_effects_with_notes(self):
        options = [{"id": "unknown_stat", "kind": "stat_add", "stat": "unknown", "value": "not_used"},
                   {"id": "future", "kind": "trait", "value": "not_used"}]
        parameters = custom(plus=plus_document(*options), equipment=equipment_document(unknown="x"),
                            monster={"species_id": "slime", "plus_choices": [item["id"] for item in options],
                                     "equipment_id": "test"})
        parameters["equipment"]["equipment"][0]["stat_multipliers"]["unknown"] = "not_used"
        self.install_custom(parameters)
        actual = self.contracts(cases=[parameters])["results"][0]
        self.assert_python(actual, parameters["monster"])
        self.assertEqual(len(actual["warnings"]), 3)

    def test_broken_definitions_and_unsafe_values_fail_without_fabricated_result(self):
        cases = [custom(plus=[]), custom(plus={"schema_version": 2}), custom(plus={"stages": None}),
                 custom(plus={"stages": [None]}), custom(plus={"stages": [{"options": None}]}),
                 custom(plus=plus_document({})), custom(equipment=[]), custom(equipment={}),
                 custom(equipment={"equipment": [None]}), custom(equipment={"equipment": [{}]}),
                 custom(equipment={"schema_version": True, "equipment": []}),
                 custom(monster={"species_id": "slime", "plus_choices": None}),
                 custom(monster={"species_id": "slime", "plus_choices": [True]}),
                 custom(monster={"species_id": "slime", "equipment_id": {}}), custom(monster={"species_id": None}),
                 custom(base={"ok": True, "stats": row(), "skill_ids": [None]})]
        for value in (None, True, {}, "bad", "NaN", 1e100):
            cases.append(custom(plus=plus_document({"id": "bad", "kind": "stat_multiplier", "stat": "hp", "value": value}),
                                monster={"species_id": "slime", "plus_choices": ["bad"]}))
            cases.append(custom(equipment=equipment_document(value), monster={"species_id": "slime", "equipment_id": "test"}))
        cases.extend([custom(plus=plus_document({"id": "bad", "kind": "skill"}),
                             monster={"species_id": "slime", "plus_choices": ["bad"]}),
                      custom(equipment=equipment_document(allowed_species_ids="slime"),
                             monster={"species_id": "slime", "equipment_id": "test"}),
                      custom(equipment=equipment_document(stat_multipliers=[]),
                             monster={"species_id": "slime", "equipment_id": "test"}),
                      custom(equipment=equipment_document(1e15),
                             monster={"species_id": "slime", "equipment_id": "test"})])
        actual = self.contracts(cases=cases)
        for index, result in enumerate(actual["results"]):
            with self.subTest(index=index):
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"], "invalid_modifiers")
                self.assertTrue(result["message"])
                self.assertNotIn("stats", result)
        self.assertTrue(all(actual["input_preserved"]))

    def test_result_mutation_does_not_change_base_documents_equipment_or_individual(self):
        parameters = custom(equipment=equipment_document(), monster={"species_id": "slime", "equipment_id": "test"})
        actual = self.contracts(cases=[{**parameters, "mutate_result": True}, parameters])
        self.assertEqual(actual["results"][0], actual["results"][1])
        self.assertEqual(actual["input_preserved"], [True, True])

    def test_repository_reads_canonical_modifier_documents_without_writing(self):
        ids = GameRepository(self.content / "data").list_species_ids()
        before = self.content_hashes()
        actual = self.contracts(load_plus=ids, load_equipment=True)
        for identifier, document in zip(ids, actual["plus_documents"]):
            with self.subTest(identifier=identifier):
                self.assertEqual(document, {"ok": True, "value": self.template(identifier)["plus"]})
        self.assertEqual(actual["equipment_document"]["value"],
                         json.loads((self.content / "data/equipment/equipment.json").read_text(encoding="utf-8")))
        self.assertEqual(self.content_hashes(), before)
        self.assertFalse(self.profile.exists())

    def test_repository_missing_unsafe_and_malformed_documents_are_not_repaired(self):
        actual = self.contracts(load_plus=["../slime", "does_not_exist"])["plus_documents"]
        self.assertTrue(all(not item["ok"] for item in actual))
        for relative in ("data/species/slime/plus.json", "data/equipment/equipment.json"):
            for raw in ("{broken", "[]", "null"):
                with self.subTest(relative=relative, raw=raw):
                    path = self.content / relative
                    path.write_text(raw, encoding="utf-8")
                    result = self.contracts(load_plus=["slime"], load_equipment=True)
                    item = result["plus_documents"][0] if "plus" in relative else result["equipment_document"]
                    self.assertEqual(item["error"], "invalid_content")
                    self.assertEqual(path.read_text(encoding="utf-8"), raw)

    def test_service_caches_per_species_and_equipment_only_within_one_scan(self):
        bundle = {**self.template("slime"), "equipment": equipment_document()}
        monsters = [{"species_id": identifier, "level": 1} for identifier in ("slime", "slime", "ghost", "ghost")]
        actual = self.contracts(count_bundle=bundle, count_monsters=monsters)["counts"]
        self.assertEqual(actual["one_scan"], {"base": 2, "plus": 2, "equipment": 1})
        self.assertEqual(actual["next_scan"], {"base": 3, "plus": 3, "equipment": 2})

    def test_new_scan_reads_external_changes_while_existing_scan_keeps_its_cache(self):
        monster = {"species_id": "slime", "level": 1, "plus_choices": ["custom"], "equipment_id": "test"}
        actual = self.contracts(monsters=[monster], updates=[
            {"kind": "plus", "species_id": "slime", "value": plus_document(
                {"id": "custom", "kind": "stat_add", "stat": "hp", "value": 777})},
            {"kind": "equipment", "value": equipment_document(2)}])
        self.assertEqual(actual["joined"], actual["cached"])
        self.assertEqual(actual["refreshed"][0]["modifiers"]["stats"]["hp"], 813)
        self.assertEqual(actual["refreshed"][0]["modifiers"]["stats"]["speed"], 24)

    def test_same_species_and_level_have_individual_modifiers_in_readonly_roster(self):
        self.seed_state(current_party=["plain", "boosted"])
        plain = self.seed_record("plain", level=100, plus_choices=[], equipment_id=None)
        boosted = self.seed_record("boosted", level=100, plus_choices=["slime_plus_1_hp"], equipment_id="ken")
        before = self.saved_files()
        content = self.content_hashes()
        actual = self.roster()
        records = actual["owned"]["records"]
        self.assertEqual(records["plain"]["progression"]["stats"], records["boosted"]["progression"]["stats"])
        for identifier, monster in (("plain", plain), ("boosted", boosted)):
            self.assert_python(records[identifier]["progression"]["modifiers"], monster)
        self.assertNotEqual(records["plain"]["progression"]["modifiers"]["stats"],
                            records["boosted"]["progression"]["modifiers"]["stats"])
        self.assertIn("基礎能力値（＋/装備補正前）", actual["text"])
        self.assertIn("補正後能力値（＋/装備）: HP 665", actual["text"])
        self.assertIn("使用可能スキルID（Lv習得＋＋追加）", actual["text"])
        self.assertEqual(self.saved_files(), before)
        self.assertEqual(self.content_hashes(), content)

    def test_roster_unknown_choices_and_disallowed_equipment_warn_without_changing_ids(self):
        self.seed_state(current_party=["kept"])
        monster = self.seed_record("kept", "ghost", level=1, plus_choices=["unknown"], equipment_id="ken")
        before = self.saved_files()
        actual = self.roster()
        modified = actual["owned"]["records"]["kept"]["progression"]["modifiers"]
        self.assert_python(modified, monster)
        self.assertEqual(modified["equipment_status"]["reason"], "not_allowed")
        self.assertIn("不明な＋選択ID", actual["text"])
        self.assertIn("装備不可の種族", actual["text"])
        self.assertEqual(actual["owned"]["warnings"], [])  # Nonfatal ignored effects do not block initial-save policy.
        self.assertEqual(self.saved_files(), before)

    def test_broken_modifier_docs_keep_base_individual_party_ai_and_raw_definition(self):
        self.seed_state(current_party=["kept"])
        self.seed_record("kept", plus_choices=[], level=42)
        before = self.saved_files()
        for relative in ("data/species/slime/plus.json", "data/equipment/equipment.json"):
            with self.subTest(relative=relative):
                path = self.content / relative
                original = path.read_text(encoding="utf-8")
                path.write_text("{broken", encoding="utf-8")
                content = self.content_hashes()
                actual = self.roster()
                progression = actual["owned"]["records"]["kept"]["progression"]
                self.assertTrue(progression["ok"])
                self.assertFalse(progression["modifiers"]["ok"])
                self.assertEqual(actual["owned"]["party"][0]["id"], "kept")
                self.assertIn("補正後能力値: 読込不可", actual["text"])
                self.assertIn("注意", actual["text"])
                self.assertEqual(self.saved_files(), before)
                self.assertEqual(self.content_hashes(), content)
                path.write_text(original, encoding="utf-8")

    def test_legacy_individual_defaults_do_not_add_fields_or_change_ai(self):
        self.seed_state(current_party=["legacy"])
        monster = self.seed_record("legacy")
        for field in ("level", "plus_choices", "equipment_id"):
            monster.pop(field)
        self.write("monsters/legacy/monster.json", monster)
        before = self.saved_files()
        actual = self.roster()["owned"]["records"]["legacy"]["progression"]["modifiers"]
        self.assert_python(actual, monster)
        self.assertEqual(actual["equipment_status"]["reason"], "none")
        self.assertEqual(self.saved_files(), before)


if __name__ == "__main__":
    unittest.main()
