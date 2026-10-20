# {
#   責務: [test_context_router: AGENTSの読込量・開発規約の参照先・ゲーム領域の探索入口を静的検証します]
#   フィールド: []
# }
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


# {
#   責務: [test_agents_is_a_small_router_not_a_spec_dump: AGENTSが6000byte以内の探索入口で、個別ゲーム仕様を含まないことを確認します]
#   処理: [1: UTF-8の長さ・作業条件/探索リンク・詳細仕様の見出し未混入を照合します]
#   引数: []
#   戻り値: [result: なし（None）。入口の契約違反はassertionで失敗します]
# }
def test_agents_is_a_small_router_not_a_spec_dump() -> None:
    # 読込量の上限と必須の探索条件を同時に確認し、本文の削除だけで軽量化した偽成功を防ぎます。
    content = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert len(content.encode("utf-8")) <= 6000
    assert "docs/context/ROUTES.md" in content
    assert "Goal / Required / Acceptance" in content
    assert "Do not read the whole repository up front" in content
    assert "## Data contracts" not in content
    assert "## Fixed mobs" not in content
    assert "## Gameplay invariants already requested" not in content


# {
#   責務: [test_context_routes_cover_major_task_areas: 戦闘・フィールド・保存・エディタ等の既存探索入口が残ることを確認します]
#   処理: [1: ROUTESの本文へ必要な全タスク領域の見出しが含まれるか照合します]
#   引数: []
#   戻り値: [result: なし（None）。探索先の領域が欠けるとassertionで失敗します]
# }
def test_context_routes_cover_major_task_areas() -> None:
    # 開発規約の分離によって、ゲーム実装や保存などの入口が消えていないことを確認します。
    content = (ROOT / "docs" / "context" / "ROUTES.md").read_text(encoding="utf-8")

    for area in (
        "Battle rules",
        "Field movement",
        "Ranch / party management",
        "Simulation facility",
        "Save data",
        "Map / block / monster editors",
        "Developer environment / build",
        "Architecture / responsibility split",
        "Context / tooling",
        "CI / project integrity",
    ):
        assert area in content


# {
#   責務: [test_developer_rules_have_direct_agent_links_and_resolving_local_links: AGENTSと規約入口のリンクが実在する共有文書を指し、ローカル専用文書を必須参照しないことを確認します]
#   処理: [1: 正本三規約と入口への参照を確認し、選定した文書内のローカルMarkdownリンクをリポジトリ内で解決します]
#   引数: []
#   戻り値: [result: なし（None）。リンク切れ・境界外参照・非公開文書への必須リンクはassertionで失敗します]
# }
def test_developer_rules_have_direct_agent_links_and_resolving_local_links() -> None:
    # 公開cloneにはローカル追加規約がなくてもよいため、共有入口の必須リンクから除外します。
    developer_root = "docs/開発者向け"
    rules = ("コーディング規約.md", "CODING_RULES.md", "COMMENT_RULES.md")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert f"({developer_root}/README.md)" in agents
    for name in rules:
        assert f"({developer_root}/{name})" in agents
    documents = [ROOT / "AGENTS.md", ROOT / developer_root / "README.md"]
    documents += [ROOT / developer_root / name for name in rules]
    documents += [ROOT / "コーディング規約.md", ROOT / "docs/CODING_RULES.md", ROOT / "docs/COMMENT_RULES.md"]
    # 既知の規約文書だけのリンクを検査し、全仕様書の再走査や外部通信へ対象を広げません。
    for document in documents:
        content = document.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]*\]\(([^)\s]+)\)", content):
            if target.startswith(("https://", "http://", "#")):
                continue
            relative = target.split("#", 1)[0]
            resolved = (document.parent / relative).resolve()
            assert resolved.is_relative_to(ROOT), (document, target)
            assert resolved.is_file(), (document, target)
            assert "ローカル専用" not in resolved.parts, (document, target)


# {
#   責務: [test_legacy_rule_paths_are_short_redirects_to_one_canonical_text: 旧パスは短い移転案内だけを保持し、三規約の本文が新しい正本に残ることを確認します]
#   処理: [1: 旧パスの参照先と800byte上限、正本に必要な規約識別子・境界・コメント形式を照合します]
#   引数: []
#   戻り値: [result: なし（None）。本文の重複や正本の欠落はassertionで失敗します]
# }
def test_legacy_rule_paths_are_short_redirects_to_one_canonical_text() -> None:
    # 過去の公開リンクを壊さず、本文の二重管理へ戻らないよう案内の大きさと参照先を固定します。
    for legacy, target in (("コーディング規約.md", "docs/開発者向け/コーディング規約.md"),
                           ("docs/CODING_RULES.md", "開発者向け/CODING_RULES.md"),
                           ("docs/COMMENT_RULES.md", "開発者向け/COMMENT_RULES.md")):
        content = (ROOT / legacy).read_text(encoding="utf-8")
        assert len(content.encode("utf-8")) <= 800
        assert f"]({target})" in content
        assert "## " not in content
    # 案内だけが残り規約本文を失った状態を、移転成功として扱いません。
    canonical = ROOT / "docs/開発者向け"
    coding = (canonical / "コーディング規約.md").read_text(encoding="utf-8")
    for index in range(1, 21):
        assert f"| R{index:02} |" in coding
    assert "UI / Process / Data" in (canonical / "CODING_RULES.md").read_text(encoding="utf-8")
    assert "JSON-like" in (canonical / "COMMENT_RULES.md").read_text(encoding="utf-8")


# {
#   責務: [test_optional_local_rules_are_ignored_without_becoming_required_paths: ローカル追加規約はGit除外を維持し、共有プロジェクトの必須パスへ混入しないことを確認します]
#   処理: [1: 新しいローカル専用ディレクトリの除外と整合性checkerの共有パスだけの要求を照合します]
#   引数: []
#   戻り値: [result: なし（None）。共有cloneで任意規約を強制する変更はassertionで失敗します]
# }
def test_optional_local_rules_are_ignored_without_becoming_required_paths() -> None:
    # private文書の実在や内容を読まないため、このテストは公開cloneでも同じ条件で実行できます。
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "/docs/開発者向け/ローカル専用/" in ignored
    checker = (ROOT / "tools/project-integrity/script/check_project_rules.py").read_text(encoding="utf-8")
    for name in ("README.md", "コーディング規約.md", "CODING_RULES.md", "COMMENT_RULES.md"):
        assert f'"docs/開発者向け/{name}"' in checker
    assert "ローカル専用/" not in checker
