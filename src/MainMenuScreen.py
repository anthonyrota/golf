import pyglet
from GameScreen import GameScreen


class MainMenuScreen(GameScreen):
    def __init__(self):
        self._game = None
        self._label = pyglet.text.Label(
            "Hello, world",
            font_name="Times New Roman",
            font_size=36,
            anchor_x="center",
            anchor_y="center",
        )

    def bind(self, game):
        self._game = game

    def render(self):
        self._game.clear_window()
        w, h = self._game.get_window_dimensions()
        self._label.x = w // 2
        self._label.y = h // 2
        self._label.draw()

    def update(self, dt):
        pass

    def dispose(self):
        pass
