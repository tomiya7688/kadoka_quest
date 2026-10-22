# {
#   責務: [test_project_metadata: test・project・metadataの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


# {
#   責務: [ProjectMetadataTests: project・metadata・testsの状態と振る舞いを担当する]
#   フィールド: []
# }
class ProjectMetadataTests(unittest.TestCase):
    # {
    #   責務: [test_package_uses_repository_component_license_notice: 検証: package uses repository component license notice]
    #   処理: [1: 検証: package uses repository component license notice]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_package_uses_repository_component_license_notice(self) -> None:
        package_metadata = (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        license_text = (REPOSITORY_ROOT / "LICENSE").read_text(encoding="utf-8")

        self.assertIn('license = {file = "LICENSE"}', package_metadata)
        for relative in ("LICENSE_SCOPE.md", "LICENSES/MIT.txt", "LICENSES/KADOKA-GAME.txt", "LICENSES/KADOKA-GAME-CREATION.txt"):
            self.assertIn(relative, license_text)
            self.assertTrue((REPOSITORY_ROOT / relative).is_file())

    # {
    #   責務: [test_obake_character_assets_have_their_own_license_notice: 検証: obake character assets have their own license notice]
    #   処理: [1: 検証: obake character assets have their own license notice]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_obake_character_assets_have_their_own_license_notice(self) -> None:
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        obake_license = (REPOSITORY_ROOT / "LICENSES" / "Obake-Character-License-v1.1.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("assets/characters/maru/", readme)
        self.assertIn("assets/characters/kadoka/", readme)
        self.assertIn("Obake Character License v1.1", readme)
        self.assertIn("Obake Character License v1.1", obake_license)

    # {
    #   責務: [test_security_policy_names_the_supported_release_line_and_private_route: 検証: security policy names the supported release line and private route]
    #   処理: [1: 検証: security policy names the supported release line and private route]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_security_policy_names_the_supported_release_line_and_private_route(self) -> None:
        policy = (REPOSITORY_ROOT / "SECURITY.md").read_text(encoding="utf-8")

        self.assertIn("0.1.x", policy)
        self.assertIn("security/advisories/new", policy)

    # {
    #   責務: [test_implementation_issue_template_has_minimum_self_contained_sections: 検証: implementation issue template has minimum self contained sections]
    #   処理: [1: 検証: implementation issue template has minimum self contained sections]
    #   引数: [self: 処理対象インスタンス]
    #   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
    # }
    def test_implementation_issue_template_has_minimum_self_contained_sections(self) -> None:
        template = (
            REPOSITORY_ROOT / ".github" / "ISSUE_TEMPLATE" / "implementation.yml"
        ).read_text(encoding="utf-8")

        for section in ("目的", "対象", "変更しない範囲", "受け入れ条件", "検証"):
            self.assertIn(f"label: {section}", template)
        self.assertIn("label: 関連仕様（必要な場合のみ）", template)
        self.assertIn("label: データ契約（必要な場合のみ）", template)
        self.assertIn("label: 移植境界（必要な場合のみ）", template)

    # {
    #   責務: [test_codemap_indexes_each_required_task_area: CODEMAPが戦闘・フィールド・保存・UI等の主要領域を案内することを確認します]
    #   処理: [1: 必須領域の名前と索引の更新ルール見出しを照合します]
    #   引数: [self: CODEMAPの探索案内を検査するテストケース]
    #   戻り値: [result: なし（None）。必須領域の案内が欠けるとassertionで失敗します]
    # }
    def test_codemap_indexes_each_required_task_area(self) -> None:
        # 規約の入口を追加しても、ゲーム実装を探す既存の領域一覧が残ることを確認します。
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

    # {
    #   責務: [test_agents_declares_context_budget_and_routes_to_codemap: AGENTSが読込量の方針とCODEMAPへの入口を保持することを確認します]
    #   処理: [1: コンテキスト方針の見出し・探索先・既定で読まない対象の記載を照合します]
    #   引数: [self: AGENTSの探索案内を検査するテストケース]
    #   戻り値: [result: なし（None）。必要な探索方針の欠落はassertionで失敗します]
    # }
    def test_agents_declares_context_budget_and_routes_to_codemap(self) -> None:
        # 開発規約を別文書へ移しても、作業対象の探索と読込量の制限を維持することを確認します。
        agents = (REPOSITORY_ROOT / "AGENTS.md").read_text(encoding="utf-8")

        self.assertIn("## Context Budget", agents)
        self.assertIn("docs/CODEMAP.md", agents)
        self.assertIn("not default reading", agents)
