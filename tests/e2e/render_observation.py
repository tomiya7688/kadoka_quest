"""Observe real renderer calls; do not compare platform-dependent pixels."""
# {
#   責務: [render_observation: Observe real renderer calls; do not compare platform-dependent pixels.]
#   フィールド: []
# }

from unittest.mock import patch

import pygame

from kadoka_quest.apps import game as game_module
from kadoka_quest.ui import field_renderer


# {
#   責務: [render: render・observationを表示用データを生成する]
#   処理: [1: render・observationを表示用データを生成する]
#   引数: [driver: driver]
#   戻り値: [result: render・observationを表示用データを生成するための結果（dict）]
# }
def render(driver) -> dict:
    game = driver.game
    screen = pygame.Surface(game_module.SCREEN_SIZE)
    if game.mode == "field":
        module = field_renderer
        draw = lambda: module.draw_field(
            screen, game.field_session, game.character_images, game.party(),
            game.field_party_session.selected_index, driver.clock.now,
        )
    elif game.mode == "password":
        module = game_module
        draw = lambda: module.draw_password(screen, game.password_session)
    else:
        raise ValueError("This render observer supports field/password only")
    real_text = module.draw_text
    real_image = game.character_images.get
    texts = []
    images = []

    # {
    #   責務: [observe_text: render・observationのobserve・文字列を求める]
    #   処理: [1: render・observationのobserve・文字列を求める]
    #   引数: [
    #     surface: 描画面
    #     value: 値
    #     args: args
    #     kwargs: kwargs
    #   ]
    #   戻り値: [result: render・observationのobserve・文字列を求めるための結果（型注釈なし）]
    # }
    def observe_text(surface, value, *args, **kwargs):
        texts.append(str(value))
        return real_text(surface, value, *args, **kwargs)

    # {
    #   責務: [observe_image: render・observationのobserve・画像を求める]
    #   処理: [1: render・observationのobserve・画像を求める]
    #   引数: [
    #     species_id: 種族・識別子
    #     pose: pose
    #     size: 大きさ
    #   ]
    #   戻り値: [result: 画像（型注釈なし）]
    # }
    def observe_image(species_id, pose, size):
        image = real_image(species_id, pose, size)
        images.append({"species_id": species_id, "pose": pose, "loaded": image is not None})
        return image

    with patch.object(module, "draw_text", observe_text):
        with patch.object(game.character_images, "get", observe_image):
            draw()
    return {
        "mode": game.mode, "size": list(screen.get_size()), "texts": texts, "images": images,
        "player_visual": list(game.player_movement.position(driver.clock.now)),
    }
