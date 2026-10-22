# {
#   責務: [test_dialogue_contract: test・会話・契約の公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "docs" / "examples" / "conditional_dialogue.json"
ALLOWED_PREFIXES = ("story.", "map.", "npc.", "item.")


# {
#   責務: [test_conditional_dialogue_example_is_valid_json_contract: 検証: conditional dialogue example is valid json contract]
#   処理: [1: 検証: conditional dialogue example is valid json contract]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
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


# {
#   責務: [test_dialogue_contract_keeps_legacy_dialogue_compatible: 検証: dialogue contract keeps legacy dialogue compatible]
#   処理: [1: 検証: dialogue contract keeps legacy dialogue compatible]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_dialogue_contract_keeps_legacy_dialogue_compatible() -> None:
    payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    dialogue = payload["fixed_mob"]["dialogue"]

    assert isinstance(dialogue, list)
    assert all(isinstance(line, str) for line in dialogue)
