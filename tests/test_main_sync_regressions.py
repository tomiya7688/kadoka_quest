# {
#   責務: [test_main_sync_regressions: main統合レビューで見つかったセーブ隔離・再生成・評価進行・不正MODの回帰を検査します]
#   フィールド: []
# }
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from kadoka_engine.data_validator import DataValidator
from kadoka_quest.application.app_command import AppCommand
from kadoka_quest.apps.battle_command_app import BattleCommandApplication
from kadoka_quest.apps.battle_session import BattleSession
from kadoka_quest.core.monster import MonsterRecord
from kadoka_quest.data.battle_data import BattleDataLoader
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.devtools.game_evaluator import GameEvaluationRunner
from test_game_evaluator import _Game

ROOT = Path(__file__).resolve().parents[1]


# {
#   責務: [test_evaluator_cli_overrides_inherited_save: 継承した通常セーブ環境変数より、CLI指定または評価専用の既定保存先を優先することを検査します]
#   処理: [1: 全保存先を一時領域へ隔離してCLIを実行し、指定先の保存と継承先の不変を照合します]
#   引数: [
#     tmp_path: pytestが管理する一時ディレクトリ（Path）
#     explicit_save: --save-dirを明示する場合True（bool）
#   ]
#   戻り値: [result: なし（None）。誤った保存先やCLI失敗ならテストが失敗します]
# }
@pytest.mark.parametrize("explicit_save", [True, False])
def test_evaluator_cli_overrides_inherited_save(tmp_path: Path, explicit_save: bool) -> None:
    inherited_save = tmp_path / "inherited"
    inherited_save.mkdir()
    (inherited_save / "keep.json").write_text('{"keep": true}', encoding="utf-8")
    output = tmp_path / "report" / "evaluation.json"
    expected_save = tmp_path / "selected" if explicit_save else output.parent / "evaluator_save"
    environment = dict(os.environ, KADOKA_SAVE_DIR=str(inherited_save),
                       KADOKA_SAVEDATA_ROOT=str(tmp_path / "slots"),
                       KADOKA_IMPORT_DIR=str(tmp_path / "imports"),
                       SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    command = [sys.executable, str(ROOT / "game_evaluator.py"), "--steps", "1", "--output", str(output)]
    if explicit_save:
        command.extend(["--save-dir", str(expected_save)])
    # 実プロセスのimport順も検査し、既に読み込まれたpathsをモックして問題を隠しません。
    result = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True,
                            encoding="utf-8", timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(output.read_text(encoding="utf-8"))["kind"] == "game_evaluation"
    assert (expected_save / "state.json").is_file()
    assert sorted(path.name for path in inherited_save.iterdir()) == ["keep.json"]
    assert (inherited_save / "keep.json").read_text(encoding="utf-8") == '{"keep": true}'


# {
#   責務: [test_sample_regeneration_preserves_runtime_metadata: 再生成した種族の任意設定と森の出現表が正規データと一致することを検査します]
#   処理: [1: 生成器の出力先を一時領域へ差し替え、設定を比較し、正規JSONの不変も照合します]
#   引数: [tmp_path: 再生成JSONを置くpytest専用領域（Path）]
#   戻り値: [result: なし（None）。設定の消失・出現表の巻戻り・正規ファイル変更なら失敗します]
# }
def test_sample_regeneration_preserves_runtime_metadata(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        "kadoka_sample_review_regression", ROOT / "tools/sample-data/script/_generate_sample_data_impl.py")
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    generator.DATA = tmp_path / "generated"
    canonical = list((ROOT / "data/species").glob("*/species.json"))
    canonical += [ROOT / "data/maps" / map_id / "map.json" for map_id in ("greenwood", "fresh_forest")]
    before = {path: path.read_bytes() for path in canonical}
    # 正規data/へ生成器を実行せず、実際に出力されたJSONを検査します。
    generator.main()
    for path in canonical:
        original = json.loads(before[path])
        generated = json.loads((generator.DATA / path.relative_to(ROOT / "data")).read_text(encoding="utf-8"))
        keys = ("field_ai_weights", "experience_reward", "flee_rates", "status_resistances") if "species" in path.parts else ("spawns",)
        for key in keys:
            assert (key in generated) == (key in original), (path, key)
            assert generated.get(key) == original.get(key), (path, key)
        assert path.read_bytes() == before[path]


# {
#   責務: [test_malformed_flee_rates_are_reported_and_safe_at_encounter: オブジェクト以外の逃走設定を診断し、戦闘個体生成時には逃走なしへ退避することを検査します]
#   処理: [1: 正規データの一時コピーへ不正値を書き、診断コードと実際の戦闘個体を照合します]
#   引数: [
#     tmp_path: MODの一時コピーを置くpytest専用領域（Path）
#     malformed: 不正なJSON型の逃走設定（object）
#   ]
#   戻り値: [result: なし（None）。診断の欠落や遭遇時の例外なら失敗します]
# }
@pytest.mark.parametrize("malformed", ["invalid", [], [["normal", 1]], None, True, 1])
def test_malformed_flee_rates_are_reported_and_safe_at_encounter(tmp_path: Path, malformed: object) -> None:
    data_root = tmp_path / "data"
    shutil.copytree(ROOT / "data", data_root)
    path = data_root / "species/metal_slime/species.json"
    definition = json.loads(path.read_text(encoding="utf-8"))
    definition["flee_rates"] = malformed
    path.write_text(json.dumps(definition, ensure_ascii=False), encoding="utf-8")
    issues = DataValidator(data_root).validate()
    assert any(issue["code"] == "species.flee_rates_invalid" and issue["path"] == "species/metal_slime/species.json"
               for issue in issues)
    record = MonsterRecord({"id": "temporary", "name": "一時個体", "species_id": "metal_slime", "level": 1}, {})
    assert BattleDataLoader(GameRepository(data_root)).build_combatant(record).flee_rates == {}


# {
#   責務: [test_valid_flee_rates_remain_editable: 未知の遭遇状況名を含む正しいオブジェクトを変更せず戦闘へ渡すことを検査します]
#   処理: [1: 一時種族定義へ逃走率を設定し、診断がなく値と原本が保持されることを照合します]
#   引数: [
#     tmp_path: 編集可能な一時データ領域（Path）
#     rates: 有効な遭遇状況別の逃走率（dict）
#   ]
#   戻り値: [result: なし（None）。不必要な拒否や定義変更なら失敗します]
# }
@pytest.mark.parametrize("rates", [{}, {"normal": 0.15, "mod_area": 0.6}])
def test_valid_flee_rates_remain_editable(tmp_path: Path, rates: dict) -> None:
    data_root = tmp_path / "data"
    shutil.copytree(ROOT / "data", data_root)
    path = data_root / "species/metal_slime/species.json"
    definition = json.loads(path.read_text(encoding="utf-8"))
    definition["flee_rates"] = rates
    path.write_text(json.dumps(definition), encoding="utf-8")
    assert DataValidator(data_root).validate() == []
    record = MonsterRecord({"id": "temporary", "name": "一時個体", "species_id": "metal_slime", "level": 1}, {})
    assert BattleDataLoader(GameRepository(data_root)).build_combatant(record).flee_rates == rates
    assert json.loads(path.read_text(encoding="utf-8")) == definition


# {
#   責務: [test_approaching_interact_event_keeps_it_pending: 調査イベントの隣へ移動しただけでは試行済みにならず、次の調査が送られることを検査します]
#   処理: [1: 調査型遷移を持つ小マップで一歩接近し、次手のinteract送信と試行履歴を照合します]
#   引数: [activation: 明示したinteract、または省略時の既定動作を表すNone（str | None）]
#   戻り値: [result: なし（None）。接近によって調査を飛ばした場合は失敗します]
# }
@pytest.mark.parametrize("activation", ["interact", None])
def test_approaching_interact_event_keeps_it_pending(activation: str | None) -> None:
    game = _Game()
    event = game.maps["first"]["events"][1]
    if activation is None:
        event.pop("activation")
    else:
        event["activation"] = activation
    runner = GameEvaluationRunner(game)
    runner.run(1)
    assert "first:to_second" not in runner.attempted_events
    assert game.interactions == 0
    report = runner.run(1)
    assert "first:to_second" in runner.attempted_events
    assert game.interactions == 1
    assert any(entry["kind"] == "event_attempted" for entry in report["entries"])


# {
#   責務: [test_same_coordinate_transition_is_not_blocked: 遷移先の座標が移動前と同じでも、マップが変わった移動を通行不能にしないことを検査します]
#   処理: [1: 座標0から一歩で別マップの座標0へ移動し、遷移の試行履歴とログを照合します]
#   引数: []
#   戻り値: [result: なし（None）。遷移を通行不能と誤認した場合は失敗します]
# }
def test_same_coordinate_transition_is_not_blocked() -> None:
    game = _Game()
    game.maps["first"]["events"][1]["x"] = 1
    report = GameEvaluationRunner(game).run(1)
    assert game.field_session.map_data["id"] == "second"
    assert "first:to_second" in report["attempted_events"]
    assert not any(entry["kind"] == "blocked" for entry in report["entries"])


# {
#   責務: [test_unfinished_battle_does_not_report_success: 保存未確定・決着なし・再生停止を、それぞれ上限内で停止理由として記録することを検査します]
#   処理: [1: 各停止状態のコマンド受付を固定し、帰還しないことと操作回数の上限を照合します]
#   引数: [
#     outcome: テスト用の勝敗。Noneは未決着を表します（str | None）
#     playback: 再生を完了しない状態を再現する場合True（bool）
#     expected_reason: 期待する評価ログの停止理由（str）
#     expected_ticks: 停止までに送られるtickの期待回数（int）
#     expected_rounds: 停止までに実行されるfightの期待回数（int）
#   ]
#   戻り値: [result: なし（None）。未保存の帰還・成功の誤報・上限超過なら失敗します]
# }
@pytest.mark.parametrize("outcome,playback,expected_reason,expected_ticks,expected_rounds", [
    ("victory", False, "battle_not_finalized", 1, 0),
    ("victory", True, "battle_playback_limit", 12_000, 0),
    (None, False, "battle_round_limit", 121, 120),
])
def test_unfinished_battle_does_not_report_success(
    outcome: str | None, playback: bool, expected_reason: str, expected_ticks: int, expected_rounds: int,
) -> None:
    game = _Game()
    game.mode = "battle"
    game.battle_session = SimpleNamespace(battle=SimpleNamespace(outcome=outcome), playback=playback, finalized=False)
    game.runtime.dispatch = Mock(wraps=game.runtime.dispatch)
    report = GameEvaluationRunner(game).run(1)
    assert game.mode == "battle"
    assert any(entry["kind"] == "stalled" and entry["reason"] == expected_reason for entry in report["entries"])
    assert not any(entry["kind"] == "battle_finished" for entry in report["entries"])
    calls = game.runtime.dispatch.call_args_list
    assert sum(call.args[1] == "tick" for call in calls) == expected_ticks
    assert sum(call.args[1] == "execute" for call in calls) == expected_rounds


# {
#   責務: [test_evaluator_waits_for_playback_and_persists_progress: 長い戦闘再生を完了し、通常の成長保存を一回終えてからフィールドへ戻ることを検査します]
#   処理: [1: 実BattleCommandApplicationとSessionで勝利後の再生を進め、AI保存・経験値保存・帰還順を照合します]
#   引数: []
#   戻り値: [result: なし（None）。再生前の帰還・保存漏れ・保存重複なら失敗します]
# }
def test_evaluator_waits_for_playback_and_persists_progress() -> None:
    game = _Game()
    game.mode = "battle"
    game.battle_session = BattleSession()
    record = MonsterRecord({"id": "ally", "name": "味方", "species_id": "slime", "level": 1, "experience": 0}, {})
    battle = SimpleNamespace(outcome=None, log=[], learning_enabled=True,
                             allies=[SimpleNamespace(record=record, name=record.name)],
                             enemies=[SimpleNamespace(name="敵", record=SimpleNamespace(level=1), hp=0, fled=False, experience_reward=None)],
                             mark_battle_complete=Mock())
    game.battle_session.begin(battle, 0)
    game.monsters = Mock()
    game.monsters.get.return_value = record
    game.states = Mock()
    game.state = {}
    original_dispatch = game.runtime.dispatch

    # {
    #   責務: [win_round: 一回の戦闘実行で勝利と150行の再生ログを発生させます]
    #   処理: [1: 戦闘結果とログをテスト用の固定値へ設定します]
    #   引数: []
    #   戻り値: [result: なし（None）。テスト用戦闘の状態を更新します]
    # }
    def win_round() -> None:
        battle.outcome = "victory"
        battle.log.extend(["攻撃した。"] * 150)

    # {
    #   責務: [return_after_progress: 再生終了と成長保存を検査してから、通常のテスト帰還処理を呼びます]
    #   処理: [1: finalizedと経験値を照合し、フィールドへの帰還を実行します]
    #   引数: []
    #   戻り値: [result: なし（None）。帰還の前提が未達ならテストが失敗します]
    # }
    def return_after_progress() -> None:
        assert game.battle_session.finalized
        assert not game.battle_session.playback
        assert record.monster["experience"] == 11
        original_dispatch("battle", "return")

    battle.run_round = Mock(side_effect=win_round)
    game.return_to_field = Mock(side_effect=return_after_progress)
    application = BattleCommandApplication(game)

    # {
    #   責務: [dispatch: 戦闘操作だけを実アプリケーション境界へ委譲し、その他を小マップfixtureへ渡します]
    #   処理: [1: 宛先がbattleならAppCommandを処理し、それ以外は元のdispatchを呼びます]
    #   引数: [
    #     target: 操作を受け付ける画面名（str）
    #     action: 実行するコマンド名（str）
    #     payload: コマンド固有の入力（object）
    #   ]
    #   戻り値: [result: コマンド受付の処理結果（object）]
    # }
    def dispatch(target: str, action: str, **payload: object) -> object:
        if target == "battle":
            return application.handle(AppCommand(target, action, payload))
        return original_dispatch(target, action, **payload)

    game.runtime.dispatch = dispatch
    report = GameEvaluationRunner(game).run(1)
    assert game.mode == "field"
    battle.run_round.assert_called_once()
    battle.mark_battle_complete.assert_called_once()
    game.monsters.save_all_ai.assert_called_once()
    assert list(game.monsters.save_all_ai.call_args.args[0]) == [record]
    game.monsters.save.assert_called_once_with(record)
    game.return_to_field.assert_called_once()
    assert any(entry["kind"] == "battle_finished" and entry["outcome"] == "victory" for entry in report["entries"])
