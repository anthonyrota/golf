from pyglet import gl
from Camera import Camera
from GameScreen import GameScreen
from cave_gen import make_cave_grid, make_cave_contours, place_start_flat_and_flag_flat
from LevelGeometry import LevelGeometry, ColoredPlatformBuffer


class PlayInfiniteScreen(GameScreen):
    def __init__(self):
        self._game = None
        self._geometry = None
        self._camera = None

    def bind(self, game):
        self._game = game
        width, height = 45, 45
        cave_grid = make_cave_grid(width, height)
        cave_contours = make_cave_contours(cave_grid, width, height)
        start_flat, flag_flat = place_start_flat_and_flag_flat(
            cave_contours, cave_grid, 2, 0.5
        )
        self._geometry = LevelGeometry(
            contours=cave_contours[1:],
            exterior_contour=cave_contours[0],
            start_flat=start_flat,
            flag_flat=flag_flat,
            platform_buffers=[
                ColoredPlatformBuffer(distance=2, color=(72, 137, 62)),
                ColoredPlatformBuffer(distance=5, color=(86, 77, 64)),
            ],
            pseudo_3d_ground_height=1,
            pseudo_3d_ground_color=(79, 251, 22),
            unbuffed_platform_color=(66, 61, 54),
        )
        self._camera = Camera(self._game)

    def render(self):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        gl.glLoadIdentity()
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)

        self._camera.width = max(
            self._geometry.frame.width,
            self._geometry.frame.height
            * (self._game.window.width / self._game.window.height),
        )

        self._camera.transform_gl()
        self._geometry.render(self._camera)
        self._camera.undo_transform_gl()

    def update(self, dt):
        pass

    def unbind(self):
        self._game = None
        self._geometry.dispose()
        self._geometry = None
        self._camera = None
