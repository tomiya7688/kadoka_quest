# {
#   責務: [simulation_facility_hooks: simulation・facility・hooksの公開機能・宣言を定義する]
#   フィールド: []
# }
from __future__ import annotations

import pygame

from kadoka_quest.apps.manager_process_service import ManagerProcessService
from kadoka_quest.apps.simulation_roster_service import SimulationRosterService
from kadoka_quest.core.battle import BattleEngine
from kadoka_quest.paths import IMPORT_ROOT, PROJECT_ROOT, SAVE_ROOT


# {
#   責務: [_components: simulation・facility・hooksのcomponentsを求める]
#   処理: [1: simulation・facility・hooksのcomponentsを求める]
#   引数: [session: セッション]
#   戻り値: [result: simulation・facility・hooksのcomponentsを求めるための結果（型注釈なし）]
# }
def _components(session):
    process = getattr(session, "_simulation_facility_process", None)
    roster = getattr(session, "_simulation_facility_roster", None)
    if process is None:
        process = ManagerProcessService(
            PROJECT_ROOT / "simulation_manager.py",
            frozen_argument="--simulation-manager",
        )
        session._simulation_facility_process = process
    if roster is None:
        roster = SimulationRosterService(
            SAVE_ROOT / "simulation",
            session.repository,
            IMPORT_ROOT / "simulation",
        )
        session._simulation_facility_roster = roster
    return process, roster


# {
#   責務: [open_simulation_manager: simulation・managerを開く]
#   処理: [1: simulation・managerを開く]
#   引数: [session: セッション]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def open_simulation_manager(session) -> None:
    process, _ = _components(session)
    if process.open() == "already_running":
        session.status = "模擬戦受付は既に開いています。"
        return
    session.status = "模擬戦受付を開きました。対戦相手を編成してください。"


# {
#   責務: [refresh_simulation_if_closed: simulation・if・closedを更新内容を読み直す]
#   処理: [1: simulation・if・closedを更新内容を読み直す]
#   引数: [session: セッション]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def refresh_simulation_if_closed(session) -> None:
    process, roster = _components(session)
    if not process.consume_closed():
        return
    opponents = roster.consume_battle_request()
    if not opponents:
        session.status = "模擬戦受付を閉じました。"
        return
    allies = session.party()
    if not allies:
        session.status = "現在パーティが空なので模擬戦を開始できません。"
        return
    battle = BattleEngine(
        session.repository,
        allies,
        opponents,
        session.rng,
        learning_enabled=False,
    )
    session.battle_session.begin(battle, pygame.time.get_ticks(), simulation=True)
    session.mode = "battle"
    session.status = "模擬戦を開始。AI学習・経験値・通常報酬は発生しません。"


# {
#   責務: [install_simulation_facility_hooks: Install only the facility lifecycle hooks needed by legacy launchers.]
#   処理: [1: Install only the facility lifecycle hooks needed by legacy launchers.]
#   引数: [game_class: ゲーム・クラス]
#   戻り値: [result: なし（None）。状態更新や検証は処理内で行う]
# }
def install_simulation_facility_hooks(game_class) -> None:
    """Install only the facility lifecycle hooks needed by legacy launchers."""
    if getattr(game_class, "_simulation_facility_hooks_installed", False):
        return
    game_class.open_simulation_manager = open_simulation_manager
    game_class.refresh_simulation_if_closed = refresh_simulation_if_closed
    game_class._simulation_facility_hooks_installed = True
