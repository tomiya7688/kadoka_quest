from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "docs" / "examples" / "conditional_dialogue.json"
ALLOWED_PREFIXES = ("story.", "map.", "npc.", "item.")


def test_conditional_dialogue_example_is_valid_json_contract() -> None:
    payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    mob = payload["fixed_mob"]

    assert mob["dialogue"]
    rules = mob["dialogue_rules"]
    assert rules
    assert rules[-1]["conditions"] == []

    for rule in rules:
        assert rule["id"]
        assert rule["lines"] and all(isinstance(line, str) and line for line in rule["lines"])
        assert isinstance(rule["once"], bool)
        for condition in rule["conditions"]:
            assert condition["flag"].startswith(ALLOWED_PREFIXES)
            assert isinstance(condition["equals"], bool)
        for effect in rule["effects"]:
            assert effect["type"] == "set_flag"
            assert effect["flag"].startswith(ALLOWED_PREFIXES)
            assert isinstance(effect["value"], bool)


def test_dialogue_contract_keeps_legacy_dialogue_compatible() -> None:
    payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    dialogue = payload["fixed_mob"]["dialogue"]

    assert isinstance(dialogue, list)
    assert all(isinstance(line, str) for line in dialogue)
