from pyglet import gl
from Vector2 import Vector2
from Rectangle import Rectangle


class Camera:
    def __init__(self, game):
        self._game = game
        self.position = Vector2.zero()
        self.width = self._game.window.width

    def transform_gl(self):
        gl.glTranslatef(-self.position.x, -self.position.y, 0)
        scale = self._game.window.width / self.width
        gl.glScalef(scale, scale, 1)

    def undo_transform_gl(self):
        gl.glTranslatef(self.position.x, self.position.y, 0)
        scale = self.width / self._game.window.width
        gl.glScalef(scale, scale, 1)

    def get_view_rect(self):
        return Rectangle(
            self.position.x,
            self.position.y,
            self.width,
            self.width * (self._game.window.height / self._game.window.width),
        )
