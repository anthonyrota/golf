import glooey
from assets import assets
from widgets import TopLeftHBox, ToggleSoundButton, BackButton
from GameScreen import GameScreen
from StaticBlurredBackground import StaticBlurredBackground
from gl_util import clear_gl
import MainMenuScreen


class LabelStack(glooey.VBox):
    custom_size = "small"
    custom_alignment = "top"
    custom_cell_padding = 8


class Label(glooey.Label):
    custom_color = "#ffffff"
    custom_font_name = assets().font_name
    custom_font_size = 14


class LabelStackLabel(Label):
    custom_font_size = 24
    custom_color = "#ffffff"
    custom_alignment = "center"
    custom_text_alignment = "center"


help_text = """Left click and drag the mouse
to aim and release to shoot the ball

Press "c" to cancel a shot

Press "g" to enter and exit sticky mode

In sticky mode, left click on a wall
to place goo that the ball sticks to"""


class HelpScreen(GameScreen):
    def __init__(self, blurred_background_img):
        self._game = None
        self._gui_elements = []
        self._blurred_background_img = blurred_background_img
        self._blurred_background = None

    def _add_gui(self):
        def on_back_btn_click(_widget):
            self._game.set_screen(
                MainMenuScreen.MainMenuScreen(self._blurred_background_img)
            )

        icons_hbox = TopLeftHBox()
        icons_hbox.set_size(self._game.size)
        self._gui_elements.append(icons_hbox)
        back_btn = BackButton(self._game)
        back_btn.push_handlers(on_click=on_back_btn_click)
        icons_hbox.add(back_btn)
        icons_hbox.add(ToggleSoundButton(self._game))
        label_stack = LabelStack()
        self._gui_elements.append(label_stack)
        label_stack.add(LabelStackLabel("Help"))
        label_stack.add(Label(help_text))
        self._game.gui.add(icons_hbox)
        self._game.gui.add(label_stack)

    def _remove_gui(self):
        for widget in self._gui_elements:
            self._game.gui.remove(widget)
        self._gui_elements = []

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
