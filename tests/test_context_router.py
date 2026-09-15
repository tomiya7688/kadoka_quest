from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_agents_is_a_small_router_not_a_spec_dump() -> None:
    content = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert len(content.encode("utf-8")) <= 6000
    assert "docs/context/ROUTES.md" in content
    assert "Goal / Required / Acceptance" in content
    assert "Do not read the whole repository up front" in content
    assert "## Data contracts" not in content
    assert "## Fixed mobs" not in content
    assert "## Gameplay invariants already requested" not in content


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
