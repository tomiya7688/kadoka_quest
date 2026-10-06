# {
#   責務: [test_session_ownership: test・セッション・ownershipの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import ast
import copy
from pathlib import Path
import random
from types import SimpleNamespace
from unittest import mock

import pytest

from kadoka_engine.field_engine import FieldEngine
from kadoka_engine.fixed_mob_controller import FixedMobController
from kadoka_engine.hidden_enemy_controller import HiddenEnemyController
from kadoka_engine.player_field_controller import PlayerFieldController
from kadoka_quest.application.app_command import AppCommand
from kadoka_quest.apps.battle_command_app import BattleCommandApplication
from kadoka_quest.apps.field_session import FieldSession
from kadoka_quest.apps.game import KadokaQuest
from kadoka_quest.apps.progress_session import ProgressSession
from kadoka_quest.data.monsters import MonsterStore
from kadoka_quest.data.parties import PartyStore
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.data.state import StateStore


REMOVED_ALIASES = (
    "selected_party", "preset_index", "battle_finalized", "auto_battle",
    "battle_action_line", "fixed_mob_battle_id", "password_message",
    "image_cache", "manager_process",
)


# {
#   責務: [test_unused_alias_is_not_defined_or_recreated: 検証: unused alias is not defined or recreated]
#   処理: [1: 検証: unused alias is not defined or recreated]
#   引数: [
#     game: ゲーム
#     name: 名前
#   ]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
@pytest.mark.parametrize("name", REMOVED_ALIASES)
def test_unused_alias_is_not_defined_or_recreated(game, name):
    assert name not in vars(KadokaQuest)
    assert not hasattr(game, name)


# {
#   責務: [test_runtime_has_no_removed_alias_access: 検証: runtime has no removed alias access]
#   処理: [1: 検証: runtime has no removed alias access]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_runtime_has_no_removed_alias_access():
    root = Path(__file__).resolve().parents[1]
    paths = [*root.joinpath("src").rglob("*.py"), *root.joinpath("tools").rglob("*.py"), *root.glob("*.py")]
    references = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in REMOVED_ALIASES:
                references.append(f"{path.relative_to(root)}:{node.lineno}:{node.attr}")
            if (
                isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in {"getattr", "setattr", "hasattr", "delattr"}
                and len(node.args) >= 2 and isinstance(node.args[1], ast.Constant)
                and node.args[1].value in REMOVED_ALIASES
            ):
                references.append(f"{path.relative_to(root)}:{node.lineno}:{node.args[1].value}")
    assert references == []


# {
#   責務: [game: test・セッション・ownershipのゲームを求める]
#   処理: [1: test・セッション・ownershipのゲームを求める]
#   引数: [tmp_path: tmp・パス]
#   戻り値: [result: test・セッション・ownershipのゲームを求めるための結果（型注釈なし）]
# }
@pytest.fixture
def game(tmp_path):
    repository = GameRepository(Path(__file__).resolve().parents[1] / "data")
    return KadokaQuest(
        repository,
        MonsterStore(tmp_path / "monsters", repository),
        StateStore(tmp_path / "state.json"),
        PartyStore(tmp_path / "parties"),
        random.Random(11),
    )


# {
#   責務: [test_progress_session_keeps_identity_and_allows_replacement: 検証: progress session keeps identity and allows replacement]
#   処理: [1: 検証: progress session keeps identity and allows replacement]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_progress_session_keeps_identity_and_allows_replacement():
    state = {"flags": {}}
    session = ProgressSession(state)
    assert session.state is state
    session.state["flags"]["opened"] = True
    assert state["flags"]["opened"] is True
    replacement = {"flags": {"new": True}}
    session.state = replacement
    assert session.state is replacement
    assert "new" not in state["flags"]


# {
#   責務: [test_field_session_rebinds_world_without_copying_actors: 検証: field session rebinds world without copying actors]
#   処理: [1: 検証: field session rebinds world without copying actors]
#   引数: []
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_field_session_rebinds_world_without_copying_actors():
    blocks = {"grass": {"player_walkable": True}}
    field = FieldEngine({"id": "first"}, blocks)
    player = PlayerFieldController(1, 2)
    fixed = FixedMobController(field, random.Random(1))
    hidden = HiddenEnemyController(field, random.Random(2))
    session = FieldSession(field, player, fixed, hidden)
    fixed.npcs.append({"id": "resident"})
    player.visual.move_to(2, 2, 10)
    next_map = {"id": "second"}
    session.enter_map(next_map, 4, 5)
    assert session.map_data is next_map is field.map_data is hidden.map_data
    assert session.blocks is blocks is hidden.blocks
    assert session.player is player
    assert session.fixed_mobs is fixed
    assert session.hidden_enemies is hidden
    assert fixed.npcs == [{"id": "resident"}]  # population reset is a separate step
    assert (player.x, player.y) == (4, 5)
    assert not player.visual.moving
    assert (player.visual.target_x, player.visual.target_y) == (4, 5)


# {
#   責務: [test_game_compatibility_views_have_no_shadow_state: 検証: game compatibility views have no shadow state]
#   処理: [1: 検証: game compatibility views have no shadow state]
#   引数: [game: ゲーム]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_game_compatibility_views_have_no_shadow_state(game):
    for name in ("state", "map_data", "blocks", "field", "player_field", "fixed_mobs", "hidden_enemies"):
        assert name not in vars(game)
    assert game.state is game.progress_session.state
    assert game.player_field is game.field_session.player
    assert game.fixed_mobs is game.field_session.fixed_mobs
    assert game.hidden_enemies is game.field_session.hidden_enemies
    replacement = copy.deepcopy(game.state)
    game.state = replacement
    assert game.progress_session.state is replacement
    game.progress_session.state = {"flags": {}}
    assert game.state is game.progress_session.state
    replacement_map = dict(game.map_data, id="alias")
    game.map_data = replacement_map
    assert game.map_data is game.field.map_data is game.hidden_enemies.map_data is replacement_map
    replacement_blocks = dict(game.blocks)
    game.blocks = replacement_blocks
    assert game.blocks is game.hidden_enemies.blocks is replacement_blocks
    replacement_field = FieldEngine(replacement_map, replacement_blocks)
    game.field = replacement_field
    assert game.field is game.fixed_mobs.field is game.hidden_enemies.field is replacement_field


# {
#   責務: [test_map_change_preserves_population_reset_and_save_order: 検証: map change preserves population reset and save order]
#   処理: [1: 検証: map change preserves population reset and save order]
#   引数: [game: ゲーム]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_map_change_preserves_population_reset_and_save_order(game):
    session = game.field_session
    game.player_field.visual.move_to(19, 14, 10)
    with mock.patch.object(game, "save_position", wraps=game.save_position) as save, \
         mock.patch.object(game, "reset_hidden_monsters", wraps=game.reset_hidden_monsters) as hidden, \
         mock.patch.object(game, "reset_home_npcs", wraps=game.reset_home_npcs) as fixed:
        calls = mock.Mock()
        calls.attach_mock(save, "save")
        calls.attach_mock(hidden, "hidden")
        calls.attach_mock(fixed, "fixed")
        game.change_map("ghost_home", 5, 5)
        assert calls.mock_calls == [mock.call.save(), mock.call.hidden(), mock.call.fixed()]
    assert game.field_session is session
    assert game.map_data is session.map_data is game.field.map_data is game.hidden_enemies.map_data
    assert game.map_data["id"] == "ghost_home"
    assert not game.player_field.visual.moving
    assert {npc["species_id"] for npc in game.home_npcs} >= {"maru", "kadoka"}
    saved = game.states.load()
    assert saved["map_id"] == "ghost_home"
    assert saved["player"] == {"x": game.player_x, "y": game.player_y}
    game.change_map("starting_town", 18, 14)
    assert game.field_session is session
    assert game.map_data["id"] == "starting_town"


# {
#   責務: [test_manager_reload_updates_existing_battle_flow_state_provider: 検証: manager reload updates existing battle flow state provider]
#   処理: [1: 検証: manager reload updates existing battle flow state provider]
#   引数: [game: ゲーム]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_manager_reload_updates_existing_battle_flow_state_provider(game):
    app = BattleCommandApplication(game)
    flow = app._battle_flow()
    assert flow is not None
    previous = game.state
    replacement = copy.deepcopy(previous)
    replacement["inventory"]["orange"] = 9
    replacement["current_party"] = list(reversed(previous["current_party"]))
    game.states.save(replacement)
    with mock.patch.object(game.manager_tool, "consume_closed", return_value=True):
        game.refresh_manager_if_closed()
    assert game.state is game.progress_session.state
    assert game.state is not previous
    assert flow.dependencies.state_provider() is game.state
    assert [record.monster_id for record in game.party()] == replacement["current_party"]
    battle = SimpleNamespace(log=[], use_party_item=mock.Mock(), run_round=mock.Mock())
    game.battle_session.battle = battle
    flow.progression.use_item()
    assert game.state["inventory"]["orange"] == 8
    assert game.states.load()["inventory"]["orange"] == 8
    assert previous["inventory"]["orange"] == 3
    battle.use_party_item.assert_called_once_with()
    current = game.state
    with mock.patch.object(game.manager_tool, "consume_closed", return_value=False):
        game.refresh_manager_if_closed()
    assert game.state is current


# {
#   責務: [test_battle_command_uses_progress_owner_without_reading_state_alias: 検証: battle command uses progress owner without reading state alias]
#   処理: [1: 検証: battle command uses progress owner without reading state alias]
#   引数: [game: ゲーム]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def test_battle_command_uses_progress_owner_without_reading_state_alias(game):
    with mock.patch.object(KadokaQuest, "state", new_callable=mock.PropertyMock, side_effect=AssertionError("compatibility state read")):
        app = BattleCommandApplication(game)
        flow = app._battle_flow()
        assert flow is not None
        assert flow.dependencies.state_provider() is game.progress_session.state
        replacement = {"inventory": {"orange": 7}}
        game.progress_session.state = replacement
        assert flow.dependencies.state_provider() is replacement
    started = object()
    caller = SimpleNamespace(battle_session=game.battle_session)
    caller.start_wild_battle = mock.Mock(side_effect=lambda *args, **kwargs: setattr(caller.battle_session, "battle", started))
    result = BattleCommandApplication(caller).handle(AppCommand("battle", "start.wild", {"spawn": {}, "fixed_mob_id": "boss"}))
    assert result is started
