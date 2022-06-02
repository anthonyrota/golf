import glooey
from assets import assets


large_window_height = 900
large_window_width = 750


class Label(glooey.Label):
    custom_size = "small"
    custom_color = "#aaaaaa"
    custom_font_name = assets().font_name
    custom_small_font_size = 14
    custom_large_font_size = 20

    def __init__(self, text=None):
        super().__init__(text)
        self._update_size()

    def set_size(self, size):
        self.custom_size = size
        self._update_size()

    def _update_size(self):
        if self.custom_size == "small":
            self.set_font_size(self.custom_small_font_size)
        else:
            self.set_font_size(self.custom_large_font_size)


class Button(glooey.Button):
    custom_size = "small"
    custom_alignment = "fill"

    class Foreground(Label):
        custom_alignment = "center"
        custom_font_weight = "bold"
        custom_horz_padding = 70

    def __init__(self, game, text=None):
        super().__init__(text)
        self._game = game
        self._update_size()
        self.foreground.color = "white"

        def play_sound(*_args, **_kwargs):
            if self._game.is_sound_enabled:
                assets().button_sound.play()

        self.push_handlers(on_mouse_press=play_sound)

    def set_size(self, size):
        self.custom_size = size
        self._update_size()

    def on_rollover(self, _widget, new_state, old_state):
        if new_state == "down":
            self.foreground.top_padding = 2 * 4
        if old_state == "down":
            self.foreground.top_padding = 0

    def _update_size(self):
        self.foreground.set_size(self.custom_size)
        if self.custom_size == "small":
            self.foreground.set_horz_padding(70)
            self.set_background(
                base_left=assets().btn_small_base_left_img,
                base_center=assets().btn_small_base_center_img.get_texture(),
                base_right=assets().btn_small_base_right_img,
                down_left=assets().btn_small_down_left_img,
                down_center=assets().btn_small_down_center_img.get_texture(),
                down_right=assets().btn_small_down_right_img,
            )
        else:
            self.foreground.set_horz_padding(120)
            self.set_background(
                base_left=assets().btn_large_base_left_img,
                base_center=assets().btn_large_base_center_img.get_texture(),
                base_right=assets().btn_large_base_right_img,
                down_left=assets().btn_large_down_left_img,
                down_center=assets().btn_large_down_center_img.get_texture(),
                down_right=assets().btn_large_down_right_img,
            )


class ButtonStack(glooey.VBox):
    custom_size = "small"
    custom_alignment = "top"
    custom_cell_padding = 8

    def __init__(self):
        super().__init__()
        self._update_size()

    def set_size(self, size):
        self.custom_size = size
        self._update_size()

    def _update_size(self):
        if self.custom_size == "small":
            self.set_cell_padding(12)
        else:
            self.set_cell_padding(20)


class CenteredButtonStack(ButtonStack):
    custom_alignment = "center"


class ButtonStackLabel(Label):
    custom_small_font_size = 16
    custom_large_font_size = 32
    custom_color = "#ffffff"
    custom_text_alignment = "center"


class IconButton(glooey.Button):
    def __init__(self, game, text=None):
        super().__init__(text)
        self._game = game

        def play_sound(*_args, **_kwargs):
            if self._game.is_sound_enabled:
                assets().icon_button_sound.play()

        self.push_handlers(on_mouse_press=play_sound)


class PauseButton(IconButton):
    class Background(glooey.Background):
        custom_image = assets().pause_btn_img


class ClosePauseButton(IconButton):
    class Background(glooey.Background):
        custom_image = assets().close_pause_btn_img


class ToggleSoundButton(glooey.Checkbox):
    custom_unchecked_base = assets().sound_off_btn_img
    custom_checked_base = assets().sound_on_btn_img

    def __init__(self, game):
        super().__init__(game.is_sound_enabled)
        self._game = game

        def toggle_sound(*_args, **_kwargs):
            self._game.set_is_sound_enabled(not self.is_checked)
            if self._game.is_sound_enabled:
                assets().icon_button_sound.play()

        self.push_handlers(on_click=toggle_sound)


class BackButton(IconButton):
    class Background(glooey.Background):
        custom_image = assets().back_btn_img


class HelpButton(IconButton):
    class Background(glooey.Background):
        custom_image = assets().help_btn_img


class TopLeftHBox(glooey.HBox):
    custom_size = "small"
    custom_alignment = "top left"
    custom_padding = 24

    def __init__(self):
        super().__init__()
        self._update_size()

    def set_size(self, size):
        self.custom_size = size
        self._update_size()

    def _update_size(self):
        if self.custom_size == "small":
            self.set_cell_padding(24)
        else:
            self.set_cell_padding(36)
