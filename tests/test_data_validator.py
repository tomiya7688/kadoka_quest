from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from kadoka_quest.data.data_validator import DataValidator


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DataValidatorTests(unittest.TestCase):
    def test_bundled_data_has_no_validation_issues(self) -> None:
        self.assertEqual(DataValidator(PROJECT_ROOT / "data").validate(), [])

    def test_reference_and_typo_problems_are_collected_together(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "data"
            shutil.copytree(PROJECT_ROOT / "data", root)

            skills_path = root / "species" / "slime" / "skills.json"
            skills = json.loads(skills_path.read_text(encoding="utf-8"))
            skills["learnset"].append({"level": 3, "skill_id": "missing_skill"})
            skills_path.write_text(json.dumps(skills, ensure_ascii=False), encoding="utf-8")

            species_path = root / "species" / "slime" / "species.json"
            species = json.loads(species_path.read_text(encoding="utf-8"))
            species["resistances"]["frie"] = "normal"
            species_path.write_text(json.dumps(species, ensure_ascii=False), encoding="utf-8")

            plus_path = root / "species" / "slime" / "plus.json"
            plus = json.loads(plus_path.read_text(encoding="utf-8"))
            plus["stages"][0]["options"][0]["requires_any"] = ["missing_option"]
            plus_path.write_text(json.dumps(plus, ensure_ascii=False), encoding="utf-8")

            equipment_path = root / "equipment" / "equipment.json"
            equipment = json.loads(equipment_path.read_text(encoding="utf-8"))
            equipment["equipment"][0]["category"] = "unknown_category"
            equipment["equipment"][0]["allowed_species_ids"].append("missing_species")
            equipment_path.write_text(json.dumps(equipment, ensure_ascii=False), encoding="utf-8")

            map_path = root / "maps" / "fresh_forest" / "map.json"
            map_data = json.loads(map_path.read_text(encoding="utf-8"))
            map_data["tiles"][0][0] = "missing_block"
            map_path.write_text(json.dumps(map_data, ensure_ascii=False), encoding="utf-8")

            codes = {issue["code"] for issue in DataValidator(root).validate()}
            self.assertTrue({
                "learnset.skill_unknown",
                "resistance.element_unknown",
                "plus.requirement_unknown",
                "equipment.category_unknown",
                "equipment.species_unknown",
                "map.block_unknown",
            }.issubset(codes))

    def test_invalid_json_is_reported_without_raising(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "data"
            shutil.copytree(PROJECT_ROOT / "data", root)
            (root / "skills" / "skills.json").write_text("{broken", encoding="utf-8")
            issues = DataValidator(root).validate()
            self.assertIn("json.invalid", {issue["code"] for issue in issues})

    def test_invalid_nested_equipment_mapping_is_reported_without_raising(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "data"
            shutil.copytree(PROJECT_ROOT / "data", root)
            equipment_path = root / "equipment" / "equipment.json"
            equipment = json.loads(equipment_path.read_text(encoding="utf-8"))
            equipment["equipment"][0]["stat_multipliers"] = ["attack"]
            equipment_path.write_text(json.dumps(equipment, ensure_ascii=False), encoding="utf-8")

            issues = DataValidator(root).validate()
            self.assertIn("equipment.mapping_invalid", {issue["code"] for issue in issues})


if __name__ == "__main__":
    unittest.main()
