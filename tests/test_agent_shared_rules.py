"""実装AIごとの入口文書と共有スキルが、共有ルールの正本へ案内し続けることを検査します。"""
# {
#   責務: [test_agent_shared_rules: Codex・Claude Code・GitHub Copilot向けの入口と共有スキルの一致・案内先を検証します]
#   フィールド: [
#     ROOT: 入口文書を探すリポジトリ直下のパス（Path）
#     SKILL_PATHS: 内容を一致させるCodex用とClaude Code用の共有スキルのパス一覧（tuple[Path, ...]）
#   ]
# }
from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL_PATHS = (
    ROOT / ".agents" / "skills" / "kadoka-task" / "SKILL.md",
    ROOT / ".claude" / "skills" / "kadoka-task" / "SKILL.md",
)


# {
#   責務: [AgentSharedRulesTests: 入口文書が正本へ案内し、共有スキルが実装AI間で食い違わないことを検査します]
#   フィールド: []
# }
class AgentSharedRulesTests(unittest.TestCase):
    # {
    #   責務: [test_agent_entry_files_route_to_agents_md: Claude Code・GitHub Copilotの入口がAGENTS.mdと共有ワークフローへ案内することを確認します]
    #   処理: [1: 各入口文書を読み、AGENTS.mdとワークフロー文書への参照を確認します]
    #   引数: [self: 入口文書を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_agent_entry_files_route_to_agents_md(self) -> None:
        # Claude CodeはCLAUDE.mdの@参照でAGENTS.mdを読み込むため、参照行そのものを要求します。
        claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("\n@AGENTS.md\n", claude)
        copilot = (ROOT / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
        self.assertIn("(../AGENTS.md)", copilot)
        for text in (claude, copilot):
            self.assertIn("ワークフロー/ワークフロー.md", text)
        # Copilotは@参照を使えないため、共同開発で必須のリモート確認コマンドを入口に直接要求します。
        self.assertIn("sync_remote_context.py", copilot)

    # {
    #   責務: [test_shared_skill_copies_are_identical: Codex用とClaude Code用の共有スキルが同じ内容で、名前と説明を持つことを確認します]
    #   処理: [
    #     1: 二つの共有スキルを読み、内容の一致を確認します
    #     2: 先頭のfrontmatterにnameとdescriptionがあることを確認します
    #   ]
    #   引数: [self: 共有スキルを検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_shared_skill_copies_are_identical(self) -> None:
        # 片方だけの更新で実装AIごとの手順が分かれないよう、二つの配置先を完全一致させます。
        texts = [path.read_text(encoding="utf-8") for path in SKILL_PATHS]
        self.assertEqual(texts[0], texts[1], "Update .agents/skills and .claude/skills together")
        header = texts[0].split("---")[1]
        self.assertIn("\nname: kadoka-task\n", header)
        self.assertIn("\ndescription: ", header)
        self.assertIn("docs/ワークフロー/ワークフロー.md", texts[0])

    # {
    #   責務: [test_workflow_documents_agent_entry_points: 共有ワークフローが各入口と共有スキルの配置先を案内することを確認します]
    #   処理: [1: ワークフロー文書を読み、入口・共有スキル・本検査の名前があることを確認します]
    #   引数: [self: ワークフロー文書を検証するテストケース]
    #   戻り値: [result: なし（None）]
    # }
    def test_workflow_documents_agent_entry_points(self) -> None:
        workflow = (ROOT / "docs" / "ワークフロー" / "ワークフロー.md").read_text(encoding="utf-8")
        for name in ("CLAUDE.md", ".github/copilot-instructions.md", ".agents/skills/", ".claude/skills/",
                     "tests/test_agent_shared_rules.py"):
            self.assertIn(name, workflow)


if __name__ == "__main__":
    unittest.main()
