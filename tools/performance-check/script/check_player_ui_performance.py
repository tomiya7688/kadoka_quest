# {
#   責務: [check_player_ui_performance: キャッシュ済みPlayer画面のCPU描画時間を専用fixtureで測り、画面ごとの予算超過を検出します]
#   フィールド: []
# }
from __future__ import annotations

import argparse
import os
from pathlib import Path
import random
import sys
from types import SimpleNamespace
from typing import Callable

# 検査はゲームの保存先へアクセスせず、同じcheckoutの正規画像と定義だけを読みます。
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("KADOKA_PROJECT_ROOT", str(ROOT))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from check_runtime_performance import measure
from kadoka_engine.field_engine import FieldEngine
from kadoka_engine.fixed_mob_controller import FixedMobController
from kadoka_engine.hidden_enemy_controller import HiddenEnemyController
from kadoka_engine.player_field_controller import PlayerFieldController
from kadoka_quest.apps.battle_session import BattleSession
from kadoka_quest.apps.field_session import FieldSession
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.ui.battle_renderer import BattleRenderer, COMMAND_RECTS
from kadoka_quest.ui.character_image_provider import CharacterImageProvider
from kadoka_quest.ui.field_overlay import FieldOverlay
from kadoka_quest.ui.field_renderer import draw_field
from kadoka_quest.ui.game_ui import BG, Button, init_pygame
from kadoka_quest.ui.title_screen import TitleScreen


# {
#   責務: [build_draw_cases: 保存操作を使わず、タイトル・24野生個体のフィールド・八体戦闘の描画fixtureを組み立てます]
#   処理: [
#     1: 正規画像Providerとメモリ上のフィールド・戦闘・タイトル表示状態を用意します
#     2: 画面を消してから一画面を描く三つの反復処理を返します
#   ]
#   引数: [screen: 1120x740の計測用描画先]
#   戻り値: [result: 画面名と一フレームの描画関数の対応表]
# }
def build_draw_cases(screen: pygame.Surface) -> dict[str, Callable[[], None]]:
    images = CharacterImageProvider(GameRepository(ROOT / "data"), ROOT / "assets")
    world = {"id": "benchmark", "display_name": "描画計測用フィールド", "width": 40, "height": 36, "tiles": [["floor"] * 40 for _ in range(36)]}
    field = FieldEngine(world, {"floor": {"appearance": {"type": "color", "value": "#777777"}}})
    player = PlayerFieldController(20, 18)
    fixed = FixedMobController(field, random.Random(17))
    hidden = HiddenEnemyController(field, random.Random(18))
    species = ("slime", "ghost", "metal_slime", "maru")
    hidden.monsters = [{"x": 7 + index % 8 * 3, "y": 11 + index // 8 * 4, "direction": "front", "spawn": {"species_id": species[index % 4]}} for index in range(24)]
    session = FieldSession(field, player, fixed, hidden)
    overlay = FieldOverlay()
    overlay.observe_message("まる『この会話は描画性能の確認用です。』", 0)
    members = [SimpleNamespace(record=SimpleNamespace(monster_id=str(index), species_id=kind, level=3), name=kind, hp=24, mp=12, stats={"hp": 32, "mp": 16}, status_effects=[], fled=False) for index, kind in enumerate(species)]
    battle = SimpleNamespace(allies=members, enemies=members, outcome=None, log=["戦闘開始。", "まるのこうげき！", "8のダメージ。"], round_number=2)
    battle_session = BattleSession()
    battle_session.begin(battle, 0)
    battle_session.action_line = "まるのこうげき！"
    renderer = BattleRenderer(images)
    buttons = [Button(rect.copy(), label, lambda: None) for rect, label in zip(COMMAND_RECTS, ("たたかう", "スカウト", "どうぐ", "にげる"))]
    title = TitleScreen()
    title.set_profiles(["default"], "default", "default")

    # {
    #   責務: [draw_field_frame: 24野生個体と会話枠を含むフィールド一画面を描きます]
    #   処理: [1: 描画先を消去し、フィールドと会話を固定時刻で描きます]
    #   引数: []
    #   戻り値: [result: なし。移動・出現・保存は実行しません]
    # }
    def draw_field_frame() -> None:
        screen.fill(BG)
        draw_field(screen, session, images, [], 0, 0)
        overlay.draw(screen, [], 0, 0)

    # {
    #   責務: [draw_battle_frame: 敵四体・味方四体・ログ・コマンドを含む戦闘一画面を描きます]
    #   処理: [1: 描画先を消去し、固定された戦闘Sessionを描きます]
    #   引数: []
    #   戻り値: [result: なし。戦闘計算・学習・保存は実行しません]
    # }
    def draw_battle_frame() -> None:
        screen.fill(BG)
        renderer.draw(screen, battle_session, buttons)

    # {
    #   責務: [draw_title_frame: 記録一件を持つタイトルのホーム画面を描きます]
    #   処理: [1: 描画先を消去し、マウス位置を固定したタイトルを描きます]
    #   引数: []
    #   戻り値: [result: なし。記録の読み込みやゲーム起動は実行しません]
    # }
    def draw_title_frame() -> None:
        screen.fill(BG)
        title.draw(screen, (-1, -1))

    return {"field-24-wild-dialogue": draw_field_frame, "battle-four-versus-four": draw_battle_frame, "title-home": draw_title_frame}


# {
#   責務: [main: 三画面の画像・文字キャッシュを温めてCPU描画時間を測り、16.7msの既定予算との比較を表示します]
#   処理: [
#     1: 反復数と時間予算を読み、メモリ上の描画fixtureを用意します
#     2: 事前描画後のサンプル中央値を測り、超過した画面があれば終了コード1を返します
#   ]
#   引数: []
#   戻り値: [result: 全画面が予算内なら0、超過なら1。不正なCLI値はargparseが終了します]
# }
def main() -> int:
    parser = argparse.ArgumentParser(description="Measure cached Player CPU drawing; display flip, gameplay, input and physical GPU timing are excluded.")
    parser.add_argument("--iterations", type=int, default=60)
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=8)
    parser.add_argument("--limit-ms", type=float, default=16.7)
    args = parser.parse_args()
    if min(args.iterations, args.samples) <= 0 or args.warmup < 1 or args.limit_ms <= 0:
        parser.error("iterations/samples/limit-ms must be positive and warmup must be at least one")
    screen = init_pygame("Player CPU drawing benchmark", (1120, 740))
    try:
        cases = build_draw_cases(screen)
        failed = False
        print("Cached CPU drawing only; no display flip, gameplay tick, save, or real GUI input.")
        for name, operation in cases.items():
            elapsed_ms = measure(operation, args.iterations, args.samples, args.warmup) / 1_000_000
            passed = elapsed_ms <= args.limit_ms
            failed = failed or not passed
            print(f"{'OK' if passed else 'FAIL'} {name}: median {elapsed_ms:.3f}ms <= {args.limit_ms:.3f}ms")
        return int(failed)
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
