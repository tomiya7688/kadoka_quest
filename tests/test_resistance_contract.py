from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "docs" / "examples" / "resistance_contract.json"
DAMAGE_ELEMENTS = {
    "fire",
    "light",
    "lightning",
    "wood",
    "dark",
    "earth",
    "water",
    "ice",
    "wind",
}
STATUS_ELEMENTS = {
    "poison",
    "paralysis",
    "sleep",
    "confusion",
    "bind",
    "curse_bind",
    "curse",
}
RESISTANCE_LEVELS = (
    "very_weak",
    "weak",
    "normal",
    "resist",
    "strong",
    "immune",
    "absorb",
    "reflect",
)


def test_resistance_example_uses_formal_damage_elements_and_all_levels() -> None:
    payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    resistances = payload["species"]["resistances"]

    assert set(resistances) == DAMAGE_ELEMENTS
    assert tuple(resistances.values()) == RESISTANCE_LEVELS + ("normal",)


def test_status_resistances_are_separate_and_do_not_use_absorb_or_reflect() -> None:
    payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    status_resistances = payload["species"]["status_resistances"]

    assert set(status_resistances) == STATUS_ELEMENTS
    assert set(status_resistances.values()) <= set(RESISTANCE_LEVELS[:6])
    assert "absorb" not in status_resistances.values()
    assert "reflect" not in status_resistances.values()


def test_existing_resistance_names_remain_in_formal_scale() -> None:
    for legacy in ("weak", "normal", "strong", "immune", "absorb"):
        assert legacy in RESISTANCE_LEVELS
