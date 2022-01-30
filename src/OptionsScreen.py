from GameScreen import GameScreen


class OptionsScreen(GameScreen):
    def __init__(self):
        self._game = None

    def bind(self, game):
        self._game = game

    def render(self):
        pass

    def update(self, dt):
        pass

    def unbind(self):
        self._game = None
