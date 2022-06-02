import math
from random import choice
from threading import Thread
from enum import Enum, auto
from time import time
from pyglet import gl
from pyglet.math import Vec2
import pyshaders
from Camera import Camera
from GameScreen import GameScreen
import MainMenuScreen
from cave_gen import (
    make_cave_grid,
    make_cave_contours,
    place_start_flat_and_flag_flat,
    make_sand_pits,
)
from Geometry import (
    Geometry,
    ColoredPlatformBuffer,
    ColoredPlatformBufferWithGradientTexture,
)
from Physics import Physics
from assets import assets
from widgets import (
    Label,
    PauseButton,
    ClosePauseButton,
    ToggleSoundButton,
    TopLeftHBox,
    CenteredButtonStack,
    ButtonStackLabel,
    Button,
)
from gl_util import clear_gl, Buffer, Framebuffer


blurred_background_shader = pyshaders.from_string(
    [
        """attribute vec2 a_vertex_position;
attribute vec2 a_texture_coord;
varying vec2 v_texture_coord;

void main() {
    v_texture_coord = a_texture_coord;
    gl_Position = vec4(a_vertex_position, 0.0, 1.0);
}"""
    ],
    [  # https://github.com/Jam3/glsl-fast-gaussian-blur/blob/master/9.glsl
        """uniform sampler2D u_texture;
uniform vec2 u_resolution;
uniform vec2 u_direction;
varying vec2 v_texture_coord;

vec4 blur9(sampler2D image, vec2 uv, vec2 resolution, vec2 direction) {
  vec4 color = vec4(0.0);
  vec2 off1 = vec2(1.3846153846) * direction;
  vec2 off2 = vec2(3.2307692308) * direction;
  color += texture2D(image, uv) * 0.2270270270;
  color += texture2D(image, uv + (off1 * 2.0 / resolution)) * 0.3162162162;
  color += texture2D(image, uv - (off1 * 2.0 / resolution)) * 0.3162162162;
  color += texture2D(image, uv + (off2 * 2.0 / resolution)) * 0.0702702703;
  color += texture2D(image, uv - (off2 * 2.0 / resolution)) * 0.0702702703;
  return color;
}

void main() {
    gl_FragColor = blur9(u_texture, v_texture_coord, u_resolution, u_direction);
}"""
    ],
)


whiten_texture_shader = pyshaders.from_string(
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
        """uniform float u_pct;
uniform sampler2D u_texture;
varying vec2 v_texture_coord;

void main() {
    gl_FragColor = mix(texture2D(u_texture, v_texture_coord), vec4(1.0), u_pct);
}"""
    ],
)


class Mode(Enum):
    EASY_5_HOLES = auto()
    EASY_10_HOLES = auto()
    HARD_5_HOLES = auto()
    HARD_10_HOLES = auto()


class GameState:
    def __init__(self, mode, hole_num=0, hole_shots=None):
        self.mode = mode
        self.hole_num = hole_num
        self.hole_shots = [] if hole_shots is None else hole_shots


def _gen_cave(width, height, pseudo_3d_ground_height, ball_radius):
    cave_grid = make_cave_grid(
        width=width,
        height=height,
        wall_chance=40,
        min_surrounding_walls=5,
        iterations=5,
        pillar_iterations=5,
        min_open_percent=0.3,
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
        ball_radius=ball_radius,
    )
    return cave_contours, start_flat, flag_flat, sand_pits


class CallbackThread(Thread):
    def __init__(self, cb, target, args):
        Thread.__init__(self, None, target, None, args)
        self._cb = cb

    def run(self):
        self._cb(self._target(*self._args))


def clamp(x, a, b):
    if x < a:
        return a
    if x > b:
        return b
    return x


def darken_color(color, pct):
    return (
        clamp(color[0] * (1 - pct), 0, 255),
        clamp(color[1] * (1 - pct), 0, 255),
        clamp(color[2] * (1 - pct), 0, 255),
    )


def lighten_color(color, pct):
    return (
        clamp(color[0] * (1 + pct), 0, 255),
        clamp(color[1] * (1 + pct), 0, 255),
        clamp(color[2] * (1 + pct), 0, 255),
    )


class TopRightHBox(TopLeftHBox):
    custom_alignment = "top right"


class BigLabel(Label):
    custom_small_font_size = 22
    custom_large_font_size = 32


def is_on_last_hole(game_state):
    return (
        game_state.mode in [Mode.EASY_5_HOLES, Mode.HARD_5_HOLES]
        and game_state.hole_num == 4
        or game_state.mode in [Mode.EASY_10_HOLES, Mode.HARD_10_HOLES]
        and game_state.hole_num == 9
    )


class PlayScreen(GameScreen):
    def __init__(self, game_state, cave=None):
        self._game = None
        self._geometry = None
        self._camera = None
        self._physics = None
        self._reached_flag = False
        self._level_complete = False
        self._game_state = game_state
        self._cave = cave
        self._next_cave = None
        self._did_delay = False
        self._shot_label = None
        self._game_done_time = None
        self._paused = False
        self._pause_time = None
        self._fboA = None
        self._fboB = None
        self._background_vertex_buffer = Buffer(
            [-1, 1, -1, -1, 1, 1, 1, -1], 2, "float"
        )
        self._background_tex_coords_buffer = Buffer(
            [0, 1, 0, 0, 1, 1, 1, 0], 2, "float"
        )
        self._gui_elements = []

    def _add_gui(self):
        def on_pause_btn_click(_widget):
            if self._reached_flag:
                return
            self._paused = not self._paused
            if self._paused:
                self._physics.reset_events()
            self._pause_time = time()
            self._refresh_gui()

        def on_play_again_btn_click(_widget):
            self._game.set_screen(PlayScreen(GameState(self._game_state.mode)))

        def on_menu_btn_click(_widget):
            self._game.set_screen(MainMenuScreen.MainMenuScreen())

        def make_labels_hbox():
            labels_hbox = TopRightHBox()
            self._gui_elements.append(labels_hbox)
            labels_hbox.set_size(self._game.size)
            hole_label = BigLabel(
                f"Hole {self._game_state.hole_num+1}/{5 if self._game_state.mode in [Mode.EASY_5_HOLES, Mode.HARD_5_HOLES] else 10}"
            )
            hole_label.set_size(self._game.size)
            labels_hbox.add(hole_label)
            self._shot_label = BigLabel(self._get_shot_label_text())
            self._shot_label.set_size(self._game.size)
            labels_hbox.add(self._shot_label)
            return labels_hbox

        if self._paused:
            icons_hbox = TopLeftHBox()
            icons_hbox.set_size(self._game.size)
            self._gui_elements.append(icons_hbox)
            close_pause_btn = ClosePauseButton(self._game)
            close_pause_btn.push_handlers(on_click=on_pause_btn_click)
            icons_hbox.add(close_pause_btn)
            icons_hbox.add(ToggleSoundButton(self._game))
            btn_stack = CenteredButtonStack()
            btn_stack.set_size(self._game.size)
            self._gui_elements.append(btn_stack)
            play_again_btn = Button(self._game, "New Game")
            play_again_btn.push_handlers(on_click=on_play_again_btn_click)
            play_again_btn.set_size(self._game.size)
            btn_stack.add(play_again_btn)
            menu_btn = Button(self._game, "Back to Menu")
            menu_btn.push_handlers(on_click=on_menu_btn_click)
            menu_btn.set_size(self._game.size)
            btn_stack.add(menu_btn)
            labels_hbox = make_labels_hbox()
            self._game.gui.add(icons_hbox)
            self._game.gui.add(btn_stack)
            self._game.gui.add(labels_hbox)
        elif self._level_complete and is_on_last_hole(self._game_state):
            icons_hbox = TopLeftHBox()
            icons_hbox.set_size(self._game.size)
            self._gui_elements.append(icons_hbox)
            icons_hbox.add(ToggleSoundButton(self._game))
            btn_stack = CenteredButtonStack()
            btn_stack.set_size(self._game.size)
            self._gui_elements.append(btn_stack)
            label = ButtonStackLabel(
                f"{self._game_state.hole_num+1} holes in {sum(self._game_state.hole_shots)+self._physics.shot_number} shots!"
            )
            label.set_size(self._game.size)
            btn_stack.add(label)
            play_again_btn = Button(self._game, "Play Again")
            play_again_btn.push_handlers(on_click=on_play_again_btn_click)
            play_again_btn.set_size(self._game.size)
            btn_stack.add(play_again_btn)
            menu_btn = Button(self._game, "Back to Menu")
            menu_btn.push_handlers(on_click=on_menu_btn_click)
            menu_btn.set_size(self._game.size)
            btn_stack.add(menu_btn)
            self._game.gui.add(icons_hbox)
            self._game.gui.add(btn_stack)
        else:
            icons_hbox = TopLeftHBox()
            icons_hbox.set_size(self._game.size)
            self._gui_elements.append(icons_hbox)
            pause_btn = PauseButton(self._game)
            pause_btn.push_handlers(on_click=on_pause_btn_click)
            icons_hbox.add(pause_btn)
            icons_hbox.add(ToggleSoundButton(self._game))
            labels_hbox = make_labels_hbox()
            self._game.gui.add(icons_hbox)
            self._game.gui.add(labels_hbox)

        self._game.on_size_change(self._refresh_gui)

    def _get_shot_label_text(self):
        return f"Shot {self._physics.shot_number+1}"

    def _remove_gui(self):
        for widget in self._gui_elements:
            self._game.gui.remove(widget)
        self._gui_elements = []
        self._game.off_size_change(self._refresh_gui)

    def _refresh_gui(self):
        self._remove_gui()
        self._add_gui()

    def bind(self, game):
        self._game = game

        ball_radius = 0.6
        pseudo_3d_ground_height = 0.6
        shot_preview_simulation_updates = self._game.updates_per_second * 3
        ball_trail_points_per_second = 30
        num_ball_trail_points = ball_trail_points_per_second // 2

        if self._game_state.mode in [Mode.EASY_5_HOLES, Mode.EASY_10_HOLES]:
            width, height = 35, 25
        else:
            width, height = 60, 30
        cave_contours, start_flat, flag_flat, sand_pits = self._cave or _gen_cave(
            width, height, pseudo_3d_ground_height, ball_radius
        )
        if not is_on_last_hole(self._game_state):
            thread = CallbackThread(
                cb=self._on_thread_done,
                target=_gen_cave,
                args=(width, height, pseudo_3d_ground_height, ball_radius),
            )
            thread.start()

        fb_width = self._game.window.width
        fb_height = self._game.window.height
        self._fboA = Framebuffer(fb_width, fb_height)
        self._fboB = Framebuffer(fb_width, fb_height)

        flag_width = 2
        flag_hole_pixels = 31
        flag_hole_width = flag_width * (flag_hole_pixels / assets().flag_img.width)
        sand_pits_color = (212, 139, 33)
        sand_pits_pseudo_3d_ground_color = (248, 235, 99)
        dirt_outline_color = (55, 30, 11)
        dirt_color = (32, 12, 4)
        dirt_texture_scale = 0.032
        self._geometry = Geometry(
            contours=cave_contours[1:],
            exterior_contour=cave_contours[0],
            start_flat=start_flat,
            flag_flat=flag_flat,
            flag_img=assets().flag_img,
            flag_width=flag_width,
            flag_height=flag_width * assets().flag_img.height / assets().flag_img.width,
            flag_offset=Vec2(-flag_hole_width / 2, 0.05),
            flag_ground_background_color=(20, 198, 22),
            flag_ground_stripe_color=(17, 180, 11),
            flag_ground_background_width=1,
            flag_ground_stripe_width=1,
            flag_ground_stripe_angle=math.pi / 4,
            platform_buffers=[
                ColoredPlatformBuffer(distance=0.2, color=(68, 255, 15)),
                ColoredPlatformBuffer(distance=1.5, color=(46, 197, 0)),
                ColoredPlatformBufferWithGradientTexture(
                    distance=6.5,
                    color=dirt_outline_color,
                    light_color=lighten_color(dirt_outline_color, 0.1),
                    dark_color=darken_color(dirt_outline_color, 0.1),
                    texture_img=assets().dirt_texture_img,
                    texture_scale=dirt_texture_scale,
                ),
            ],
            bg_color=(47, 168, 202),
            pseudo_3d_ground_height=pseudo_3d_ground_height,
            pseudo_3d_ground_color=(68, 255, 15),
            unbuffed_platform=ColoredPlatformBufferWithGradientTexture(
                distance=None,
                color=dirt_color,
                light_color=lighten_color(dirt_color, 0.1),
                dark_color=darken_color(dirt_color, 0.1),
                texture_img=assets().dirt_texture_img,
                texture_scale=dirt_texture_scale,
            ),
            ball_color=(255, 255, 255),
            ball_outline_color=(0, 0, 0),
            ball_outline_size=0.2,
            sand_pits=sand_pits,
            sand_pits_color=sand_pits_color,
            sand_pits_light_color=lighten_color(sand_pits_color, 0.1),
            sand_pits_dark_color=darken_color(sand_pits_color, 0.1),
            sand_pits_pseudo_3d_ground_color=sand_pits_pseudo_3d_ground_color,
            sand_pits_pseudo_3d_ground_light_color=lighten_color(
                sand_pits_pseudo_3d_ground_color, 0.1
            ),
            sand_pits_pseudo_3d_ground_dark_color=darken_color(
                sand_pits_pseudo_3d_ground_color, 0.1
            ),
            sand_pits_texture_img=assets().sand_texture_img,
            sand_pits_texture_scale=0.3,
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

        self._camera = Camera(self._game.window.width, self._game.window.height)
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
            flag_collision_shape_radius=flag_hole_width,
            shot_preview_simulation_updates=shot_preview_simulation_updates,
            updates_per_new_ball_trail_point=self._game.updates_per_second
            // ball_trail_points_per_second,
            num_ball_trail_points=num_ball_trail_points,
            ball_trail_width=ball_radius / 2,
            sticky_radius=6,
            on_new_sticky=self._geometry.add_sticky,
            on_sticky_removed=self._geometry.remove_sticky,
            on_reach_flag=self._on_reach_flag,
            on_hole_animation_done=self._on_hole_animation_done,
            hole_animation_to_over_hole_duration=0.1,
            hole_animation_to_in_hole_duration=0.2,
            on_shot_start=self._on_shot_start,
            on_shot_end=self._on_shot_end,
            get_is_paused=lambda: self._paused,
            on_ball_sticky_collision=self._on_ball_sticky_collision,
            on_ball_sand_collision=self._on_ball_sand_collision,
        )

        self._add_gui()

    def render(self):
        self._camera.set_window_dimensions(
            self._game.window.width, self._game.window.height
        )
        self._camera.width = max(
            self._geometry.exterior_rect.width,
            self._geometry.exterior_rect.height / self._camera.get_aspect(),
        )
        self._camera.position = Vec2(
            (self._geometry.exterior_rect.width - self._camera.width) / 2,
            (self._geometry.exterior_rect.height - self._camera.get_height()) / 2,
        )
        fade_anim_duration = 0.15
        if (
            not self._paused
            and self._pause_time is not None
            and min((time() - self._pause_time) / fade_anim_duration, 1) >= 1
        ):
            self._pause_time = None
        if (
            self._pause_time is not None
            or self._level_complete
            and is_on_last_hole(self._game_state)
        ):
            self._fboA.resize(self._game.window.width * 2, self._game.window.height * 2)
            self._fboB.resize(self._game.window.width * 2, self._game.window.height * 2)
            self._geometry.render(
                camera=self._camera,
                physics=self._physics,
                framebuffer=self._fboA,
            )
            iterations = 10
            read_fb = self._fboA
            write_fb = self._fboB
            blurred_background_shader.use()
            # pylint: disable=assigning-non-slot
            blurred_background_shader.uniforms.u_resolution = (
                write_fb.width,
                write_fb.height,
            )
            if self._pause_time is not None:
                if self._paused:
                    t = min((time() - self._pause_time) / fade_anim_duration, 1)
                else:
                    t = 1 - min((time() - self._pause_time) / fade_anim_duration, 1)
            else:
                t = min((time() - self._game_done_time) / fade_anim_duration, 1)
            T = 1 - (1 - t) ** 2
            for i in range(iterations):
                radius = (iterations - i) * T / 2
                gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, write_fb.fbo)
                gl.glBindTexture(gl.GL_TEXTURE_2D, read_fb.tex)
                blurred_background_shader.uniforms.u_direction = (
                    (radius, 0) if i % 2 == 0 else (0, radius)
                )
                # pylint: enable=assigning-non-slot
                gl.glClearColor(0, 0, 0, 0)
                gl.glClear(gl.GL_COLOR_BUFFER_BIT)
                self._background_vertex_buffer.bind_to_attrib(
                    blurred_background_shader.attributes.a_vertex_position
                )
                self._background_tex_coords_buffer.bind_to_attrib(
                    blurred_background_shader.attributes.a_texture_coord
                )
                gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, 4)
                read_fb, write_fb = write_fb, read_fb
            blurred_background_shader.clear()
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
            clear_gl((0, 0, 0))
            gl.glBindTexture(gl.GL_TEXTURE_2D, write_fb.tex)
            whiten_texture_shader.use()
            # pylint: disable-next=assigning-non-slot
            whiten_texture_shader.uniforms.u_pct = T * 0.05
            self._background_vertex_buffer.bind_to_attrib(
                whiten_texture_shader.attributes.a_vertex_position
            )
            self._background_tex_coords_buffer.bind_to_attrib(
                whiten_texture_shader.attributes.a_texture_coord
            )
            gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, 4)
            gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
            whiten_texture_shader.clear()
        else:
            self._geometry.render(
                camera=self._camera, physics=self._physics, framebuffer=None
            )
        if self._level_complete and is_on_last_hole(self._game_state):
            pass
        self._game.draw_gui()
        if self._level_complete and self._next_cave is not None:
            if self._did_delay:
                self._game.set_screen(
                    PlayScreen(
                        game_state=self._get_next_game_state(), cave=self._next_cave
                    )
                )
            else:
                self._did_delay = True

    def update(self, dt):
        if self._paused or self._level_complete:
            return False
        return self._physics.update(dt)

    def _get_next_game_state(self):
        return GameState(
            mode=self._game_state.mode,
            hole_num=self._game_state.hole_num + 1,
            hole_shots=self._game_state.hole_shots + [self._physics.shot_number],
        )

    def _on_thread_done(self, cave):
        self._next_cave = cave
        if self._level_complete:
            self._game.set_screen(
                PlayScreen(game_state=self._get_next_game_state(), cave=self._next_cave)
            )

    def _on_reach_flag(self):
        self._reached_flag = True
        if self._game.is_sound_enabled:
            assets().ball_in_hole_sound.play()
        self._physics.animate_ball_into_hole()

    def _on_ball_sticky_collision(self):
        if self._game.is_sound_enabled:
            assets().splat_sound.play()

    def _on_ball_sand_collision(self):
        if self._physics.ball_velocity.y < -1 and self._game.is_sound_enabled:
            assets().sand_sound.play()

    def _on_hole_animation_done(self):
        self._level_complete = True
        self._paused = False
        self._pause_time = None
        if is_on_last_hole(self._game_state):
            self._game_done_time = time()
            self._refresh_gui()

    def _on_shot_start(self):
        if self._game.is_sound_enabled:
            assets().shot_sound.play()

    def _on_shot_end(self):
        self._shot_label.set_text(self._get_shot_label_text())

    def unbind(self):
        self._remove_gui()
        self._game = None
        if self._physics:
            self._physics.dispose()
            self._physics = None
        self._geometry.dispose()
        self._geometry = None
        self._camera = None
        self._fboA.dispose()
        self._fboA = None
        self._fboB.dispose()
        self._fboB = None
