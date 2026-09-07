from __future__ import annotations

from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class ProjectMetadataTests(unittest.TestCase):
    def test_mit_license_is_declared_in_package_and_repository(self) -> None:
        package_metadata = (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        license_text = (REPOSITORY_ROOT / "LICENSE").read_text(encoding="utf-8")

        self.assertIn('license = {text = "MIT"}', package_metadata)
        self.assertTrue(license_text.startswith("MIT License\n"))

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
