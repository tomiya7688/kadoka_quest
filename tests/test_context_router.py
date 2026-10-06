# {
#   責務: [test_context_router: test・判断用コンテキスト・routerの公開機能・宣言を定義する]
#   フィールド: []
# }
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


# {
#   責務: [test_agents_is_a_small_router_not_a_spec_dump: 検証: agents is a small router not a spec dump]
#   処理: [1: 検証: agents is a small router not a spec dump]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_agents_is_a_small_router_not_a_spec_dump() -> None:
    content = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert len(content.encode("utf-8")) <= 6000
    assert "docs/context/ROUTES.md" in content
    assert "Goal / Required / Acceptance" in content
    assert "Do not read the whole repository up front" in content
    assert "## Data contracts" not in content
    assert "## Fixed mobs" not in content
    assert "## Gameplay invariants already requested" not in content


# {
#   責務: [test_context_routes_cover_major_task_areas: 検証: context routes cover major task areas]
#   処理: [1: 検証: context routes cover major task areas]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_context_routes_cover_major_task_areas() -> None:
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
