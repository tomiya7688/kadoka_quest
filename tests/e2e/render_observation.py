"""Observe real renderer calls; do not compare platform-dependent pixels."""

from unittest.mock import patch

import pygame

from kadoka_quest.apps import game as game_module
from kadoka_quest.ui import field_renderer


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

    def observe_text(surface, value, *args, **kwargs):
        texts.append(str(value))
        return real_text(surface, value, *args, **kwargs)

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
