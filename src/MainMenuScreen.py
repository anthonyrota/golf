import glooey
from assets import assets
from GameScreen import GameScreen
from PlayScreen import PlayScreen
from OptionsScreen import OptionsScreen


class WhiteBackground(glooey.Background):
    custom_color = "#ffffff"


class NavigationButton(glooey.Button):
    class Foreground(glooey.Label):
        custom_color = "#ffffff"
        custom_font_size = 24
        custom_font_name = assets().font_name
        custom_alignment = "center"

    custom_alignment = "fill"

    class Base(glooey.Background):
        custom_color = "#146600"

    class Over(glooey.Background):
        custom_color = "#1D8F00"

    class Down(glooey.Background):
        custom_color = "#25B800"


def navigation_container_alignment(_self, child_rect, parent_rect):
    child_rect.width = min(0.7 * parent_rect.width, 700)
    child_rect.height = min(0.7 * parent_rect.height, 450)
    child_rect.center = parent_rect.center


class NavigationContainer(glooey.VBox):
    custom_alignment = navigation_container_alignment
    custom_cell_padding = 24


class MainMenuScreen(GameScreen):
    def __init__(self):
        self._game = None
        self._vbox = None
        self._white_background = None

    def bind(self, game):
        self._game = game

        def on_play_button_click(_widget):
            self._game.set_screen(PlayScreen())

        def on_options_button_click(_widget):
            self._game.set_screen(OptionsScreen())

        def on_quit_button_click(_widget):
            self._game.quit()

        self._white_background = WhiteBackground()
        self._game.gui.add(self._white_background)
        self._vbox = NavigationContainer()
        play_button = NavigationButton("Play")
        play_button.set_handler("on_click", on_play_button_click)
        self._vbox.add(play_button)
        options_button = NavigationButton("Options")
        options_button.set_handler("on_click", on_options_button_click)
        self._vbox.add(options_button)
        quit_button = NavigationButton("Quit")
        quit_button.set_handler("on_click", on_quit_button_click)
        self._vbox.add(quit_button)
        self._game.gui.add(self._vbox)

    def render(self):
        pass

    def update(self, dt):
        pass

    def unbind(self):
        self._game.gui.remove(self._vbox)
        self._game.gui.remove(self._white_background)
        self._game = None
        self._vbox = None
