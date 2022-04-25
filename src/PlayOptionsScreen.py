from GameScreen import GameScreen
import MainMenuScreen
from PlayScreen import PlayScreen, Mode, GameState
from widgets import (
    TopLeftHBox,
    Button,
    BackButton,
    ToggleSoundButton,
    CenteredButtonStack,
    ButtonStackLabel,
)
from StaticBlurredBackground import StaticBlurredBackground
from gl_util import clear_gl


class PlayOptionsScreen(GameScreen):
    def __init__(self, blurred_background_img=None):
        self._game = None
        self._vbox = None
        self._sound_btn = None
        self._blurred_background_img = blurred_background_img
        self._blurred_background = None
        self._gui_elements = []

    def _add_gui(self):
        def on_back_btn_click(_widget):
            self._game.set_screen(
                MainMenuScreen.MainMenuScreen(self._blurred_background_img)
            )

        def on_sound_btn_click(_widget):
            self._game.set_is_sound_enabled(not sound_btn.is_checked)

        def make_on_mode_btn_click(mode):
            def on_mode_btn_click(_widget):
                self._game.set_screen(PlayScreen(GameState(mode)))

            return on_mode_btn_click

        icons_hbox = TopLeftHBox()
        icons_hbox.set_size(self._game.size)
        self._gui_elements.append(icons_hbox)
        back_btn = BackButton()
        back_btn.set_handler("on_click", on_back_btn_click)
        icons_hbox.add(back_btn)
        sound_btn = ToggleSoundButton(self._game.is_sound_enabled)
        sound_btn.set_handler("on_click", on_sound_btn_click)
        icons_hbox.add(sound_btn)
        btn_stack = CenteredButtonStack()
        self._gui_elements.append(btn_stack)
        btn_stack.set_size(self._game.size)
        label = ButtonStackLabel("Choose Mode")
        label.set_size(self._game.size)
        btn_stack.add(label)
        for label, mode in [
            ("Easy 5 Holes", Mode.EASY_5_HOLES),
            ("Easy 10 Holes", Mode.EASY_10_HOLES),
            ("Hard 5 Holes", Mode.HARD_5_HOLES),
            ("Hard 10 Holes", Mode.HARD_10_HOLES),
        ]:
            btn = Button(label)
            btn.set_handler("on_click", make_on_mode_btn_click(mode))
            btn.set_size(self._game.size)
            btn_stack.add(btn)
        self._game.gui.add(icons_hbox)
        self._game.gui.add(btn_stack)
        self._game.on_size_change(self._on_size_change)

    def _remove_gui(self):
        for widget in self._gui_elements:
            self._game.gui.remove(widget)
        self._gui_elements = []
        self._game.off_size_change(self._on_size_change)

    def _on_size_change(self):
        self._remove_gui()
        self._add_gui()

    def bind(self, game):
        self._game = game
        self._blurred_background = StaticBlurredBackground(
            self._game, self._blurred_background_img
        )
        self._blurred_background_img = self._blurred_background.background_img
        self._add_gui()

    def render(self):
        clear_gl((0, 0, 0))
        self._blurred_background.render()
        self._game.draw_gui()

    def update(self, dt):
        pass

    def unbind(self):
        self._remove_gui()
        self._game = None
        self._blurred_background.dispose()
        self._blurred_background = None
