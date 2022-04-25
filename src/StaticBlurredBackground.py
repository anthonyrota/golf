from random import choice
from pyglet import gl
import pyshaders
from gl_util import Buffer, nearest_pow2
from assets import assets


texture_shader = pyshaders.from_string(
    [
        """attribute vec2 a_vertex_position;
attribute vec2 a_texture_coord;
varying vec2 v_texture_coord;

void main() {
    v_texture_coord = a_texture_coord;
    gl_Position = vec4(a_vertex_position, 0.0, 1.0);
}"""
    ],
    [
        """uniform sampler2D u_texture;
varying vec2 v_texture_coord;

void main() {
    gl_FragColor = texture2D(u_texture, v_texture_coord);
}"""
    ],
)


class StaticBlurredBackground:
    def __init__(self, game, img=None):
        self._game = game
        self.background_img = choice(assets().backgrounds) if img is None else img
        self._background_vertex_buffer = Buffer(
            [-1, 1, -1, -1, 1, 1, 1, -1], 2, "float"
        )
        self._background_tex_coords_buffer = Buffer(
            [0] * 8, 2, "float", is_dynamic=True
        )

    def render(self):
        background_texture = self.background_img.get_texture()
        background_aspect = background_texture.height / background_texture.width
        window_aspect = self._game.window.height / self._game.window.width
        max_w = background_texture.width / nearest_pow2(background_texture.width)
        max_h = background_texture.height / nearest_pow2(background_texture.height)
        if background_aspect >= window_aspect:
            bl_x = 0
            height = self._game.window.width * background_aspect
            bl_y = max_h * (height - self._game.window.height) / height / 2
            tr_x = max_w
            tr_y = max_h - bl_y
        else:
            width = self._game.window.height / background_aspect
            bl_x = max_h * (width - self._game.window.width) / width / 2
            bl_y = 0
            tr_x = max_w - bl_x
            tr_y = max_h
        self._background_tex_coords_buffer.update_part(
            [bl_x, tr_y, bl_x, bl_y, tr_x, tr_y, tr_x, bl_y], 0
        )
        texture_shader.use()
        self._background_vertex_buffer.bind_to_attrib(
            texture_shader.attributes.a_vertex_position
        )
        self._background_tex_coords_buffer.bind_to_attrib(
            texture_shader.attributes.a_texture_coord
        )
        gl.glEnable(background_texture.target)
        gl.glBindTexture(background_texture.target, background_texture.id)
        gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, 4)
        texture_shader.clear()

    def dispose(self):
        self._game = None
        self._background_vertex_buffer.dispose()
        self._background_vertex_buffer = None
        self._background_tex_coords_buffer.dispose()
        self._background_tex_coords_buffer = None
