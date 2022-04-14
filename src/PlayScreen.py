import math
from random import choice
from threading import Thread
from pyglet.math import Vec2
from assets import assets
from Camera import Camera
from GameScreen import GameScreen
from cave_gen import (
    make_cave_grid,
    make_cave_contours,
    place_start_flat_and_flag_flat,
    make_sand_pits,
)
from Geometry import Geometry, ColoredPlatformBuffer
from Physics import Physics


def _gen_cave(width, height, pseudo_3d_ground_height):
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
    sand_pits = make_sand_pits(
        contours=cave_contours,
        min_sand_pit_area=2,
        max_sand_pit_area=36,
        max_sand_pits=choice((2, 3, 3, 3, 3, 4, 5)),
        avoid_rects=[
            start_flat.make_rect(pseudo_3d_ground_height),
            flag_flat.make_rect(pseudo_3d_ground_height),
        ],
    )
    return cave_contours, start_flat, flag_flat, sand_pits


class CallbackThread(Thread):
    def __init__(self, cb, target, args):
        Thread.__init__(self, None, target, None, args)
        self._cb = cb

    def run(self):
        self._cb(self._target(*self._args))


class PlayScreen(GameScreen):
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

        ball_radius = 0.7
        pseudo_3d_ground_height = 0.6
        shot_preview_simulation_updates = self._game.updates_per_second * 3
        ball_trail_points_per_second = 30
        num_ball_trail_points = ball_trail_points_per_second // 2

        width, height = 60, 30
        cave_contours, start_flat, flag_flat, sand_pits = self._cave or _gen_cave(
            width, height, pseudo_3d_ground_height
        )
        thread = CallbackThread(
            cb=self._on_thread_done,
            target=_gen_cave,
            args=(width, height, pseudo_3d_ground_height),
        )
        thread.start()

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
                ColoredPlatformBuffer(distance=1.5, color=(46, 197, 0)),
                ColoredPlatformBuffer(distance=6.5, color=(55, 30, 11)),
            ],
            pseudo_3d_ground_height=pseudo_3d_ground_height,
            pseudo_3d_ground_color=(68, 255, 15),
            unbuffed_platform_color=(24, 8, 2),
            sand_pits=sand_pits,
            sand_pits_color=(212, 139, 33),
            sand_pits_pseudo_3d_ground_color=(248, 235, 99),
            sticky_wall_buffer_distance=0.8,
            sticky_wall_outer_buffer_distance=0.2,
            sticky_wall_background_color=(138, 57, 225),
            sticky_wall_stripe_color=(156, 81, 224),
            sticky_wall_background_width=0.8,
            sticky_wall_stripe_width=1.2,
            sticky_wall_stripe_angle=-math.pi / 6,
            preview_sticky_wall_background_color=(251, 143, 249),
            preview_sticky_wall_stripe_color=(236, 103, 234),
            preview_sticky_wall_background_width=0.8,
            preview_sticky_wall_stripe_width=1.2,
            preview_sticky_wall_stripe_angle=-math.pi / 3,
            ball_image=assets().ball_image,
            max_shot_preview_points=shot_preview_simulation_updates + 1,
            shot_preview_lerp_up=0.15,
            shot_preview_lerp_down=0.05,
            shot_preview_dotted_line_space_size=5,
            shot_preview_dotted_line_dotted_size=10,
            shot_preview_dotted_line_color=(255, 255, 255),
            shot_preview_dotted_line_fade_factor=10.0,
            shot_preview_polygon_color=(255, 255, 255),
            shot_preview_base_alpha=0.25,
            shot_drawback_ring_width=0.25,
            shot_drawback_outer_ring_color=(178, 6, 0),
            shot_drawback_outer_ring_alpha=0.3,
            shot_drawback_inner_ring_color=(255, 255, 255),
            shot_drawback_inner_ring_alpha=0.3,
            num_ball_trail_points=num_ball_trail_points + 1,
            ball_trail_color=(255, 255, 255),
            ball_trail_fade_factor=10.0,
            ball_trail_base_alpha=0.6,
        )

        def shift_points(points):
            return [
                (
                    p[0] + self._geometry.raw_point_shift.x,
                    p[1] + self._geometry.raw_point_shift.y,
                )
                for p in points
            ]

        self._camera = Camera(self._game)
        self._physics = Physics(
            game=self._game,
            camera=self._camera,
            contours=[shift_points(contour) for contour in cave_contours[1:]],
            exterior_contour=shift_points(cave_contours[0]),
            sand_pits=[shift_points(sand_pit) for sand_pit in sand_pits],
            ball_position=start_flat.get_middle()
            + self._geometry.raw_point_shift
            + Vec2(0, ball_radius),
            ball_radius=ball_radius,
            max_power=75,
            shot_sensitivity=0.4,
            gravity=Vec2(0, -30),
            flag_position=flag_flat.get_middle() + self._geometry.raw_point_shift,
            flag_collision_shape_radius=1,
            shot_preview_simulation_updates=shot_preview_simulation_updates,
            updates_per_new_ball_trail_point=self._game.updates_per_second
            // ball_trail_points_per_second,
            num_ball_trail_points=num_ball_trail_points,
            ball_trail_width=ball_radius / 2,
            sticky_radius=6,
            on_new_sticky=self._geometry.add_sticky,
            on_sticky_removed=self._geometry.remove_sticky,
            on_level_complete=self._on_level_complete,
        )

    def render(self):
        self._camera.width = max(
            self._geometry.exterior_rect.width,
            self._geometry.exterior_rect.height / self._camera.get_aspect(),
        )
        self._camera.position = Vec2(
            (self._geometry.exterior_rect.width - self._camera.width) / 2,
            (self._geometry.exterior_rect.height - self._camera.get_height()) / 2,
        )
        self._geometry.render(camera=self._camera, physics=self._physics)
        if self._level_complete and self._next_cave is not None:
            self._game.set_screen(PlayScreen(cave=self._next_cave))

    def update(self, dt):
        if self._level_complete:
            return False
        return self._physics.update(dt)

    def _on_thread_done(self, cave):
        self._next_cave = cave
        if self._level_complete:
            self._game.set_screen(PlayScreen(cave=self._next_cave))

    def _on_level_complete(self):
        self._level_complete = True

    def unbind(self):
        self._game = None
        self._physics.dispose()
        self._geometry.dispose()
        self._geometry = None
        self._physics = None
        self._camera = None
