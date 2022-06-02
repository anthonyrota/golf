import glooey
from GameScreen import GameScreen
import PlayOptionsScreen
import HelpScreen
from widgets import Button, TopLeftHBox, ToggleSoundButton, ButtonStack, HelpButton
from assets import assets
from StaticBlurredBackground import StaticBlurredBackground
from gl_util import clear_gl


class MainMenuScreen(GameScreen):
    def __init__(self, blurred_background_img=None):
        self._game = None
        self._vbox = None
        self._icons_hbox = None
        self._blurred_background_img = blurred_background_img
        self._blurred_background = None

    def _add_gui(self):
        def on_play_btn_click(_widget):
            self._game.set_screen(
                PlayOptionsScreen.PlayOptionsScreen(self._blurred_background_img)
            )

        def on_help_btn_click(_widget):
            self._game.set_screen(HelpScreen.HelpScreen(self._blurred_background_img))

        def on_quit_btn_click(_widget):
            self._game.quit()

        self._vbox = glooey.VBox()
        if self._game.size == "small":
            logo = glooey.Image(image=assets().logo_small_img)
        else:
            logo = glooey.Image(image=assets().logo_large_img)
        self._vbox.add(logo)
        btn_stack = ButtonStack()
        btn_stack.set_size(self._game.size)
        self._vbox.add(btn_stack)
        play_btn = Button(self._game, "Play")
        play_btn.push_handlers(on_click=on_play_btn_click)
        play_btn.set_size(self._game.size)
        btn_stack.add(play_btn)
        quit_btn = Button(self._game, "Quit")
        quit_btn.push_handlers(on_click=on_quit_btn_click)
        quit_btn.set_size(self._game.size)
        btn_stack.add(quit_btn)
        self._icons_hbox = TopLeftHBox()
        self._icons_hbox.set_size(self._game.size)
        self._icons_hbox.add(ToggleSoundButton(self._game))
        help_btn = HelpButton(self._game)
        help_btn.push_handlers(on_click=on_help_btn_click)
        self._icons_hbox.add(help_btn)
        self._game.gui.add(self._vbox)
        self._game.gui.add(self._icons_hbox)
        self._game.on_size_change(self._on_size_change)

    def _remove_gui(self):
        self._game.gui.remove(self._vbox)
        self._game.gui.remove(self._icons_hbox)
        self._vbox = None
        self._icons_hbox = None
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
