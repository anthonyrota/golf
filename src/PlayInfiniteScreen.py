import math
from threading import Thread
from pyglet.math import Vec2
from assets import assets
from Camera import Camera
from GameScreen import GameScreen
from cave_gen import make_cave_grid, make_cave_contours, place_start_flat_and_flag_flat
from Geometry import Geometry, ColoredPlatformBuffer
from Physics import Physics


def _gen_cave(width, height):
    cave_grid = make_cave_grid(
        width=width,
        height=height,
        wall_chance=40,
        min_surrounding_walls=5,
        iterations=5,
        pillar_iterations=2,
        min_open_percent=0.35,
    )
    cave_contours = make_cave_contours(cave_grid, width, height)
    start_flat, flag_flat = place_start_flat_and_flag_flat(cave_contours, cave_grid)
    return cave_contours, start_flat, flag_flat


class CallbackThread(Thread):
    def __init__(self, cb, target, args):
        Thread.__init__(self, None, target, None, args)
        self._cb = cb

    def run(self):
        self._cb(self._target(*self._args))


class PlayInfiniteScreen(GameScreen):
    def __init__(self, cave=None):
        self._game = None
        self._geometry = None
        self._camera = None
        self._physics = None
        self._level_complete = False
        self._cave = cave
        self._next_cave = None

    def bind(self, game):
        self._game = game

        width, height = 60, 30
        cave_contours, start_flat, flag_flat = self._cave or _gen_cave(width, height)
        thread = CallbackThread(
            cb=self._on_thread_done,
            target=_gen_cave,
            args=(width, height),
        )
        thread.start()
        ball_radius = 0.75
        pseudo_3d_ground_height = 1
        shot_preview_simulation_updates = self._game.updates_per_second * 3

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
            shot_preview_lerp_up=0.15,
            shot_preview_lerp_down=0.05,
            shot_preview_dotted_line_space_size=5,
            shot_preview_dotted_line_dotted_size=10,
            shot_preview_dotted_line_color=(1, 1, 1),
            shot_preview_dotted_line_fade_factor=250.0,
            shot_preview_polygon_color=(1, 1, 1),
            shot_preview_base_alpha=0.25,
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
            gravity=Vec2(0, -30),
            flag_position=flag_flat.get_middle() + self._geometry.raw_point_shift,
            flag_collision_shape_radius=1,
            shot_preview_simulation_updates=shot_preview_simulation_updates,
            on_level_complete=self._on_level_complete,
        )
        self._camera = Camera(self._game)

    def render(self):
        self._camera.width = max(
            self._geometry.exterior_rect.width,
            self._geometry.exterior_rect.height / self._camera.get_aspect(),
        )
        self._geometry.render(camera=self._camera, physics=self._physics)
        if self._level_complete and self._next_cave is not None:
            self._game.set_screen(PlayInfiniteScreen(cave=self._next_cave))

    def update(self, dt):
        if self._level_complete:
            return False
        return self._physics.update(dt)

    def _on_thread_done(self, cave):
        self._next_cave = cave
        if self._level_complete:
            self._game.set_screen(PlayInfiniteScreen(cave=self._next_cave))

    def _on_level_complete(self):
        self._level_complete = True

    def unbind(self):
        self._game = None
        self._physics.dispose()
        self._geometry.dispose()
        self._geometry = None
        self._physics = None
        self._camera = None
