import math
from pyglet import gl
from pyglet.math import Vec2
from assets import assets
from Camera import Camera
from GameScreen import GameScreen
from cave_gen import make_cave_grid, make_cave_contours, place_start_flat_and_flag_flat
from Geometry import Geometry, ColoredPlatformBuffer
from Physics import Physics


class PlayInfiniteScreen(GameScreen):
    def __init__(self):
        self._game = None
        self._geometry = None
        self._camera = None
        self._physics = None

    def bind(self, game):
        self._game = game

        width, height = 35, 35
        cave_grid = make_cave_grid(
            width=width,
            height=height,
            wall_chance=35,
            min_surrounding_walls=5,
            iterations=5,
            pillar_iterations=5,
            min_open_percent=0.3,
        )
        cave_contours = make_cave_contours(cave_grid, width, height)
        start_flat, flag_flat = place_start_flat_and_flag_flat(cave_contours, cave_grid)
        ball_radius = 0.75
        pseudo_3d_ground_height = 1
        shot_preview_simulation_updates = self._game.updates_per_second // 2

        self._geometry = Geometry(
            contours=cave_contours[1:],
            exterior_contour=cave_contours[0],
            start_flat=start_flat,
            flag_flat=flag_flat,
            flag_ground_background_color=(20, 198, 22),
            flag_ground_stripe_color=(17, 180, 11),
            flag_ground_background_width=1,
            flag_ground_stripe_width=1,
            flag_ground_stripe_angle=math.pi / 4,
            platform_buffers=[
                ColoredPlatformBuffer(distance=0.2, color=(68, 255, 15)),
                ColoredPlatformBuffer(distance=2, color=(46, 197, 0)),
                ColoredPlatformBuffer(distance=6.5, color=(55, 30, 11)),
            ],
            pseudo_3d_ground_height=pseudo_3d_ground_height,
            pseudo_3d_ground_color=(68, 255, 15),
            unbuffed_platform_color=(24, 8, 2),
            ball_image=assets().ball_image,
            max_shot_preview_points=shot_preview_simulation_updates + 1,
            shot_preview_dotted_line_space_size=2,
            shot_preview_dotted_line_dotted_size=4,
        )

        def shift_contour(contour):
            return [
                (
                    p[0] + self._geometry.raw_point_shift.x,
                    p[1] + self._geometry.raw_point_shift.y,
                )
                for p in contour
            ]

        self._physics = Physics(
            game=self._game,
            contours=[shift_contour(contour) for contour in cave_contours[1:]],
            exterior_contour=shift_contour(cave_contours[0]),
            ball_position=start_flat.get_middle()
            + self._geometry.raw_point_shift
            + Vec2(0, ball_radius),
            ball_radius=ball_radius,
            gravity=Vec2(0, -100),
            flag_position=flag_flat.get_middle() + self._geometry.raw_point_shift,
            shot_preview_simulation_updates=shot_preview_simulation_updates,
            on_level_complete=self._on_level_complete,
        )
        self._camera = Camera(self._game)

    def render(self):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        gl.glLoadIdentity()
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        self._camera.width = max(
            self._geometry.exterior_rect.width,
            self._geometry.exterior_rect.height / self._camera.get_aspect(),
        )
        self._geometry.render(camera=self._camera, physics=self._physics)

    def update(self, dt):
        self._physics.update(dt)

    def _on_level_complete(self, num_shots):
        pass

    def unbind(self):
        self._game = None
        self._physics.dispose()
        self._geometry.dispose()
        self._geometry = None
        self._physics = None
        self._camera = None
