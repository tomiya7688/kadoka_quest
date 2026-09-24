from __future__ import annotations

from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class ProjectMetadataTests(unittest.TestCase):
    def test_package_uses_repository_component_license_notice(self) -> None:
        package_metadata = (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        license_text = (REPOSITORY_ROOT / "LICENSE").read_text(encoding="utf-8")

        self.assertIn('license = {file = "LICENSE"}', package_metadata)
        for relative in ("LICENSE_SCOPE.md", "LICENSES/MIT.txt", "LICENSES/KADOKA-GAME.txt", "LICENSES/KADOKA-GAME-CREATION.txt"):
            self.assertIn(relative, license_text)
            self.assertTrue((REPOSITORY_ROOT / relative).is_file())

    def test_obake_character_assets_have_their_own_license_notice(self) -> None:
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        obake_license = (REPOSITORY_ROOT / "LICENSES" / "Obake-Character-License-v1.1.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("assets/characters/maru/", readme)
        self.assertIn("assets/characters/kadoka/", readme)
        self.assertIn("Obake Character License v1.1", readme)
        self.assertIn("Obake Character License v1.1", obake_license)

    def test_security_policy_names_the_supported_release_line_and_private_route(self) -> None:
        policy = (REPOSITORY_ROOT / "SECURITY.md").read_text(encoding="utf-8")

        self.assertIn("0.1.x", policy)
        self.assertIn("security/advisories/new", policy)

    def test_implementation_issue_template_has_minimum_self_contained_sections(self) -> None:
        template = (
            REPOSITORY_ROOT / ".github" / "ISSUE_TEMPLATE" / "implementation.yml"
        ).read_text(encoding="utf-8")

        for section in ("目的", "対象", "変更しない範囲", "受け入れ条件", "検証"):
            self.assertIn(f"label: {section}", template)
        self.assertIn("label: 関連仕様（必要な場合のみ）", template)
        self.assertIn("label: データ契約（必要な場合のみ）", template)
        self.assertIn("label: 移植境界（必要な場合のみ）", template)

    def test_codemap_indexes_each_required_task_area(self) -> None:
        codemap = (REPOSITORY_ROOT / "docs" / "CODEMAP.md").read_text(encoding="utf-8")

        for area in (
            "戦闘 / AI",
            "フィールド",
            "fixed mob / 野生敵",
            "モンスター / 個体 / パーティ",
            "map / block",
            "editor / ドット絵",
            "runtime command",
            "save / data",
            "UI / input",
        ):
            self.assertIn(area, codemap)
        self.assertIn("## 更新ルール", codemap)

    def test_agents_declares_context_budget_and_routes_to_codemap(self) -> None:
        agents = (REPOSITORY_ROOT / "AGENTS.md").read_text(encoding="utf-8")

        self.assertIn("## Context Budget", agents)
        self.assertIn("docs/CODEMAP.md", agents)
        self.assertIn("not default reading", agents)
