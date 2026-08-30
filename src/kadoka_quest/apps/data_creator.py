from __future__ import annotations

import pygame

from kadoka_quest.data.developer_monster_creator import DeveloperMonsterCreator
from kadoka_quest.data.repository import GameRepository, STAT_KEYS
from kadoka_quest.ui.common import ACCENT, BG, GOOD, MUTED, PANEL, PANEL_ALT, SELECTED, TEXT, WARN, Button, ScrollBar, TextField, draw_status_bar, draw_text, draw_wrapped, handle_fields, init_pygame, smoke_frames


SPECIES_ROWS = 10
TARGET_LABELS = {
    "owned": "現在のセーブへ直接追加",
    "acquire": "獲得用 imports/acquire",
    "simulation": "模擬戦用 imports/simulation",
}


class DataCreatorApp:
    def __init__(
        self,
        repository: GameRepository | None = None,
        creator: DeveloperMonsterCreator | None = None,
    ) -> None:
        self.repository = repository or GameRepository()
        self.creator = creator or DeveloperMonsterCreator(self.repository)
        self.species_ids = self.repository.list_species_ids()
        self.selected_species = 0
        self.species_offset = 0
        self.target_index = 0
        self.name_field = TextField(pygame.Rect(390, 190, 300, 42))
        self.level_field = TextField(pygame.Rect(720, 190, 110, 42), "1", numeric=True)
        self.id_field = TextField(pygame.Rect(390, 290, 440, 42))
        self.status = "種族とレベルを選び、生成先を確認して作成してください。"
        self.target_button = Button(pygame.Rect(390, 405, 440, 48), "", self.cycle_target)
        self.create_button = Button(pygame.Rect(390, 500, 440, 58), "モンスターデータを作成", self.create_monster)
        self._refresh_target_label()
        if self.species_ids:
            self._use_species_defaults()

    @property
    def fields(self) -> list[TextField]:
        return [self.name_field, self.level_field, self.id_field]

    @property
    def selected_species_id(self) -> str:
        return self.species_ids[self.selected_species]

    @property
    def selected_target(self) -> str:
        return self.creator.TARGETS[self.target_index]

    def select_species(self, index: int) -> None:
        if not 0 <= index < len(self.species_ids):
            return
        self.selected_species = index
        self._use_species_defaults()

    def cycle_target(self) -> None:
        self.target_index = (self.target_index + 1) % len(self.creator.TARGETS)
        self._refresh_target_label()

    def preview(self) -> dict | None:
        if not self.species_ids:
            return None
        try:
            return self.creator.preview(self.selected_species_id, int(self.level_field.value))
        except (KeyError, TypeError, ValueError, OSError):
            return None

    def create_monster(self) -> bool:
        if not self.species_ids:
            self.status = "利用できるモンスター種族がありません。"
            return False
        try:
            record, path = self.creator.create(
                self.selected_species_id,
                int(self.level_field.value),
                self.name_field.value,
                self.selected_target,
                self.id_field.value,
            )
        except (FileExistsError, KeyError, TypeError, ValueError, OSError) as exc:
            self.status = f"モンスターデータを作成できません: {exc}"
            return False
        self.id_field.value = ""
        self.status = f"{record.name} Lv{record.level} を作成しました: {path}"
        return True

    def _use_species_defaults(self) -> None:
        bundle = self.repository.get_species(self.selected_species_id)
        self.name_field.value = str(bundle.definition.get("display_name", self.selected_species_id))

    def _refresh_target_label(self) -> None:
        self.target_button.label = f"生成先: {TARGET_LABELS[self.selected_target]}"


def main() -> None:
    screen = init_pygame("kadoka quest - データクリエイター", (1100, 720))
    clock = pygame.time.Clock()
    app = DataCreatorApp()
    species_scroll = ScrollBar(pygame.Rect(307, 125, 10, 460), "vertical")
    running = True
    smoke = smoke_frames()
    frames = 0

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            scroll_handled = species_scroll.handle(event)
            if scroll_handled:
                app.species_offset = species_scroll.value
            field_handled = handle_fields(app.fields, event)
            button_handled = app.target_button.handle(event) or app.create_button.handle(event)
            if not scroll_handled and not field_handled and not button_handled:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for row, _ in enumerate(app.species_ids[app.species_offset:app.species_offset + SPECIES_ROWS]):
                        if pygame.Rect(55, 125 + row * 46, 245, 40).collidepoint(event.pos):
                            app.select_species(app.species_offset + row)
                            break
                elif event.type == pygame.MOUSEWHEEL:
                    app.species_offset = max(0, min(max(0, len(app.species_ids) - SPECIES_ROWS), app.species_offset - event.y))

        screen.fill(BG)
        draw_text(screen, "データクリエイター", (35, 25), 36, ACCENT, True)
        draw_text(screen, "開発用モンスター個体を既存の公開JSON形式で生成します。", (375, 38), 17, MUTED)
        pygame.draw.rect(screen, PANEL, pygame.Rect(30, 85, 305, 540), border_radius=12)
        draw_text(screen, "種族", (55, 95), 22, ACCENT, True)
        for row, species_id in enumerate(app.species_ids[app.species_offset:app.species_offset + SPECIES_ROWS]):
            index = app.species_offset + row
            rect = pygame.Rect(55, 125 + row * 46, 245, 40)
            pygame.draw.rect(screen, SELECTED if index == app.selected_species else PANEL_ALT, rect, border_radius=6)
            display_name = str(app.repository.get_species(species_id).definition.get("display_name", species_id))
            draw_text(screen, display_name, (rect.x + 12, rect.y + 8), 17, TEXT, index == app.selected_species)
            draw_text(screen, species_id, (rect.x + 130, rect.y + 10), 13, ACCENT if index == app.selected_species else MUTED)
        species_scroll.configure(len(app.species_ids), SPECIES_ROWS)
        species_scroll.value = app.species_offset
        if species_scroll.maximum:
            species_scroll.draw(screen, pygame.mouse.get_pos())

        pygame.draw.rect(screen, PANEL, pygame.Rect(355, 85, 715, 540), border_radius=12)
        preview = app.preview()
        title = str(preview["display_name"]) if preview else "入力を確認してください"
        draw_text(screen, title, (390, 105), 27, GOOD if preview else WARN, True)
        app.name_field.draw(screen, "個体名（空欄なら種族名）")
        app.level_field.draw(screen, "レベル 1～100")
        app.id_field.draw(screen, "個体ID（空欄なら自動生成）")
        draw_text(screen, "生成先はボタンを押すたびに切り替わります。", (390, 375), 15, MUTED)
        app.target_button.draw(screen, pygame.mouse.get_pos())
        app.create_button.draw(screen, pygame.mouse.get_pos())

        pygame.draw.rect(screen, PANEL_ALT, pygame.Rect(855, 145, 190, 420), border_radius=9)
        draw_text(screen, "レベル時点の内容", (875, 165), 18, ACCENT, True)
        if preview:
            for row, key in enumerate(STAT_KEYS):
                draw_text(screen, f"{key}: {preview['stats'][key]}", (875, 205 + row * 31), 16, TEXT)
            draw_text(screen, "習得スキル", (875, 405), 17, ACCENT, True)
            draw_wrapped(screen, " / ".join(preview["skill_ids"]) or "なし", pygame.Rect(875, 435, 150, 105), 14, MUTED)
        else:
            draw_wrapped(screen, "レベルは1～100の整数で入力してください。", pygame.Rect(875, 210, 145, 100), 15, WARN)

        draw_status_bar(screen, app.status, pygame.Rect(30, 645, 1040, 48), warning="できません" in app.status)
        pygame.display.flip()
        clock.tick(60)
        frames += 1
        if smoke is not None and frames >= smoke:
            running = False

    pygame.quit()


if __name__ == "__main__":
    main()
