from enum import Enum, auto
from time import time
import math
import pyglet
from pyglet.math import Vec2
from pyglet.window import key
import pymunk
from config import config


class _MouseDraggingState(Enum):
    PRESSED = auto()
    DRAGGING = auto()
    RELEASED = auto()


class _MouseDragging:
    def __init__(self, start):
        self.start = start
        self.current = start
        self.state = _MouseDraggingState.PRESSED


class _ModeState(Enum):
    MAKE_SHOT = auto()
    PLACE_STICKY = auto()


class _MakeShotMode:
    def __init__(self):
        self.state = _ModeState.MAKE_SHOT


class _PlaceStickyMode:
    def __init__(self, mouse_pos):
        self.state = _ModeState.PLACE_STICKY
        self.mouse_pos = mouse_pos


# The player can place stickies on the contour to which the ball will stick to
class Sticky:
    def __init__(self, wall, contour, is_exterior, is_preview):
        self.wall = wall
        self.contour = contour
        self.is_exterior = is_exterior
        self.is_preview = is_preview


def _encode_segment_coords(c1, c2):
    if c1 < c2:
        return (c1[0], c1[1], c2[0], c2[1])
    else:
        return (c2[0], c2[1], c1[0], c1[1])


class _ContourSegmentType(Enum):
    NORMAL = auto()
    SAND = auto()
    STICKY = auto()


class _ContourSegment:
    def __init__(self, pymunk_shape, seg_type):
        self.pymunk_shape = pymunk_shape
        self.seg_type = seg_type


_default_collision_type = 0
_ball_collision_type = 1
_sand_collision_type = 2
_sticky_collision_type = 3
_flag_collision_type = 4


def add_sticky_to_stickies(stickies, sticky):
    new_stickies = []
    removed_stickies = []
    new_sticky = sticky
    for existing_sticky in stickies:
        if existing_sticky.wall[0] == new_sticky.wall[-1]:
            new_sticky = Sticky(
                wall=new_sticky.wall[:-1] + existing_sticky.wall,
                contour=sticky.contour,
                is_exterior=sticky.is_exterior,
                is_preview=sticky.is_preview,
            )
            removed_stickies.append(existing_sticky)
        elif existing_sticky.wall[-1] == new_sticky.wall[0]:
            new_sticky = Sticky(
                wall=existing_sticky.wall[:-1] + new_sticky.wall,
                contour=sticky.contour,
                is_exterior=sticky.is_exterior,
                is_preview=sticky.is_preview,
            )
            removed_stickies.append(existing_sticky)
        else:
            new_stickies.append(existing_sticky)
    new_stickies.append(new_sticky)
    return new_stickies, new_sticky, removed_stickies


def do_circle_and_line_segment_intersect(
    circle_pos, circle_radius, line_segment_c1, line_segment_c2
):
    vx = line_segment_c1[0] - circle_pos[0]
    vy = line_segment_c1[1] - circle_pos[1]
    if (
        vx**2 + vy**2 <= circle_radius
        or (line_segment_c1[0] - circle_pos[0]) ** 2
        + (line_segment_c1[1] - circle_pos[1]) ** 2
        <= circle_radius
    ):
        # Intersects with endpoint
        return True
    dx = line_segment_c2[0] - line_segment_c1[0]
    dy = line_segment_c2[1] - line_segment_c1[1]
    if not 0 <= dx * vx + dy * vy <= dx**2 + dy**2:
        # Circle does not lie between the endpoints
        return False
    a = dy
    b = -dx
    c = dx * line_segment_c2[1] - dy * line_segment_c2[0]
    d = abs(a * circle_pos[0] + b * circle_pos[1] + c) / math.sqrt(a**2 + b**2)
    # Intersects somewhere in the middle of the segment
    return d <= circle_radius


class Physics:
    def __init__(
        self,
        game,
        camera,
        contours,
        exterior_contour,
        sand_pits,
        ball_position,
        ball_radius,
        max_power,
        shot_sensitivity,
        gravity,
        flag_position,
        flag_collision_shape_radius,
        shot_preview_simulation_updates,
        updates_per_new_ball_trail_point,
        num_ball_trail_points,
        ball_trail_width,
        sticky_radius,
        on_new_sticky,
        on_sticky_removed,
        on_reach_flag,
        on_hole_animation_done,
        hole_animation_to_over_hole_duration,
        hole_animation_to_in_hole_duration,
        on_shot_start,
        on_shot_end,
        get_is_paused,
        on_ball_sticky_collision,
        on_ball_sand_collision,
    ):
        self._game = game
        self._camera = camera
        self._space = pymunk.Space()
        self._space.gravity = gravity

        self._friction = 0.5
        self._elasticity = 0.65
        self._sand_friction = 1
        self._sand_elasticity = 0
        self._max_power = max_power
        self._shot_sensitivity = shot_sensitivity
        self._gravity = gravity
        self._flag_position = flag_position
        self._mouse_dragging = None
        self._canceled_shot = False
        self._has_pressed_mouse_in_current_mode = False
        self._shot_preview_simulation_updates = shot_preview_simulation_updates
        self.shot_number = 0
        self._updates_per_new_ball_trail_point = updates_per_new_ball_trail_point
        self._updates_until_new_ball_trail_point = 0
        self._num_ball_trail_points = num_ball_trail_points
        self._ball_trail_points = []
        self._ball_trail_width = ball_trail_width
        self._on_reach_flag = on_reach_flag
        self._mouse_position = None
        self._mode = _MakeShotMode()
        self._sticky_radius = sticky_radius
        self._stickies = []
        self._on_new_sticky = on_new_sticky
        self._on_sticky_removed = on_sticky_removed
        self._contours = contours
        self._exterior_contour = exterior_contour
        self._contour_segment_map = {}
        self._on_hole_animation_done = on_hole_animation_done
        self._hole_animation_start_time = None
        self._hole_animation_start_pos = None
        self._hole_animation_to_over_hole_duration = (
            hole_animation_to_over_hole_duration
        )
        self._hole_animation_to_in_hole_duration = hole_animation_to_in_hole_duration
        self._on_shot_start = on_shot_start
        self._on_shot_end = on_shot_end
        self._get_is_paused = get_is_paused
        self._did_unbind_events = False
        self._on_ball_sticky_collision_cb = on_ball_sticky_collision
        self._on_ball_sand_collision_cb = on_ball_sand_collision

        for contour_idx, contour in enumerate([exterior_contour] + contours):
            for i, p1 in enumerate(contour):
                p2 = contour[(i + 1) % len(contour)]
                r = 0.1
                if contour_idx == 0:
                    shape = pymunk.Segment(self._space.static_body, p1, p2, r)
                else:
                    shape = pymunk.Segment(self._space.static_body, p2, p1, r)
                shape.friction = self._friction
                shape.elasticity = self._elasticity
                self._space.add(shape)
                self._contour_segment_map[
                    _encode_segment_coords(p1, p2)
                ] = _ContourSegment(shape, _ContourSegmentType.NORMAL)

        for sand_pit in sand_pits:
            for i, p1 in enumerate(sand_pit):
                p2 = sand_pit[(i + 1) % len(sand_pit)]
                shape = pymunk.Segment(self._space.static_body, p1, p2, 0.1)
                shape.friction = self._sand_friction
                shape.elasticity = self._sand_elasticity
                shape.collision_type = _sand_collision_type
                self._space.add(shape)
                seg_key = _encode_segment_coords(p1, p2)
                if seg_key in self._contour_segment_map:
                    self._contour_segment_map[seg_key] = _ContourSegment(
                        shape, _ContourSegmentType.SAND
                    )

        self._is_in_shot = False
        self.ball_radius = ball_radius
        shape = self._make_ball_shape(ball_position)
        self._space.add(shape.body, shape)
        self._ball_shape = shape

        self._flag_collision_shape = pymunk.Poly(
            self._space.static_body,
            [
                (
                    flag_position[0] - flag_collision_shape_radius / 2,
                    flag_position[1] - 0.1,
                ),
                (
                    flag_position[0] + flag_collision_shape_radius / 2,
                    flag_position[1] - 0.1,
                ),
                (
                    flag_position[0] + flag_collision_shape_radius / 2,
                    flag_position[1] + 0.1,
                ),
                (
                    flag_position[0] - flag_collision_shape_radius / 2,
                    flag_position[1] + 0.1,
                ),
            ],
        )
        self._flag_collision_shape.collision_type = _flag_collision_type
        self._space.add(self._flag_collision_shape)
        self._ball_flag_collision_handler = self._space.add_collision_handler(
            _ball_collision_type, _flag_collision_type
        )
        ball_sticky_collision_handler = self._space.add_collision_handler(
            _ball_collision_type, _sticky_collision_type
        )
        ball_sticky_collision_handler.begin = self._on_ball_sticky_collision
        ball_sand_collision_handler = self._space.add_collision_handler(
            _ball_collision_type, _sand_collision_type
        )
        ball_sand_collision_handler.begin = self._on_ball_sand_collision

        self._bind_events()

    def _on_ball_flag_collision(self, _arb, _space, _data):
        if self._hole_animation_start_time is not None:
            return False
        self._on_reach_flag()
        return False

    def _on_ball_sticky_collision(self, _arb, _space, _data):
        if self._hole_animation_start_time is not None:
            return False
        self._space.gravity = (0, 0)
        self._ball_shape.body.velocity = (0, 0)
        self._ball_shape.body.angular_velocity = 0
        self._on_ball_sticky_collision_cb()
        return True

    def _on_ball_sand_collision(self, _arb, _space, _data):
        if self._hole_animation_start_time is not None:
            return False
        self._on_ball_sand_collision_cb()
        return True

    def _make_ball_shape(self, position):
        mass = 1
        moment = float("inf")
        body = pymunk.Body(mass, moment)
        body.position = position
        shape = pymunk.Circle(body, self.ball_radius)
        shape.friction = self._friction
        shape.elasticity = self._elasticity
        shape.collision_type = _ball_collision_type
        return shape

    def update(self, dt):
        assert not (self._is_in_shot and self._mouse_dragging)
        if self._hole_animation_start_time is not None:
            if self._hole_animation_start_time is False:
                return
            cur_time = time()
            over_hole_time = (
                self._hole_animation_start_time
                + self._hole_animation_to_over_hole_duration
            )
            in_hole_time = over_hole_time + self._hole_animation_to_in_hole_duration
            if cur_time < over_hole_time:
                t = (
                    cur_time - self._hole_animation_start_time
                ) / self._hole_animation_to_over_hole_duration
                self._ball_shape.body.velocity = Vec2(1, 0)
                self._ball_shape.body.position = self._hole_animation_start_pos + (
                    self._flag_position
                    + Vec2(0, self.ball_radius)
                    - self._hole_animation_start_pos
                ).scale(1 - (1 - t) ** 2)
                self._update_ball_trail()
            elif cur_time < in_hole_time:
                t = (
                    cur_time - over_hole_time
                ) / self._hole_animation_to_in_hole_duration
                self._ball_shape.body.velocity = Vec2(0, -1)
                self._ball_shape.body.position = self._flag_position + Vec2(
                    0, self.ball_radius - 1.2 * self.ball_radius * (t**2)
                )
                self._update_ball_trail()
            else:
                self._hole_animation_start_time = False
                self._on_hole_animation_done()
            return
        if (
            self._mouse_dragging
            and self._mouse_dragging.state == _MouseDraggingState.RELEASED
        ):
            self.shot_number += 1
            self._is_in_shot = True
            self._space.gravity = self._gravity
            self._ball_shape.body.velocity = self.get_drag_velocity()
            self._mouse_dragging = None
            self._ball_flag_collision_handler.begin = self._on_ball_flag_collision
            self._on_shot_start()
        self._space.step(dt)
        if (
            self._is_in_shot
            and self._ball_shape.body.velocity.get_length_sqrd() < 0.000000001
        ):
            shape = self._make_ball_shape(self._ball_shape.body.position)
            self._space.remove(self._ball_shape.body, self._ball_shape)
            self._space.add(shape.body, shape)
            self._ball_shape = shape
            self._is_in_shot = False
            self._ball_flag_collision_handler.begin = lambda _arb, _space, _data: False
            self._updates_until_new_ball_trail_point = 0
            self._ball_trail_points = []
            self._on_shot_end()
            return False
        if self._is_in_shot:
            self._update_ball_trail()

    def _update_ball_trail(self):
        if self._updates_until_new_ball_trail_point == 0:
            self._updates_until_new_ball_trail_point = (
                self._updates_per_new_ball_trail_point
            )
            self._ball_trail_points.append(self._get_ball_trail_point())
            if len(self._ball_trail_points) > self._num_ball_trail_points:
                self._ball_trail_points.pop(0)
        self._updates_until_new_ball_trail_point -= 1

    def animate_ball_into_hole(self):
        self._unbind_events()
        self._hole_animation_start_time = time()
        self._hole_animation_start_pos = self.ball_position

    def get_drag_velocity(self):
        vel = (self._mouse_dragging.start - self._mouse_dragging.current).scale(
            self._shot_sensitivity
        )
        if vel.dot(vel) > self._max_power**2:
            return vel.normalize().scale(self._max_power)
        return vel

    def get_drag_start(self):
        return self._mouse_dragging.start

    def get_drag_current(self):
        delta = self._mouse_dragging.current - self._mouse_dragging.start
        max_mag = self._max_power / self._shot_sensitivity
        if delta.dot(delta) > max_mag**2:
            return self._mouse_dragging.start + delta.normalize().scale(max_mag)
        return self._mouse_dragging.current

    def simulate_ball_path_from_position_with_velocity(self, position, velocity):
        space = pymunk.Space()
        space.gravity = self._gravity
        ball_shape = self._ball_shape.copy()
        ball_shape.body.position = position
        ball_shape.body.velocity = velocity
        space.add(ball_shape.body, ball_shape)
        dt = 1 / self._game.updates_per_second
        positions = [Vec2(ball_shape.body.position[0], ball_shape.body.position[1])]
        for _ in range(self._shot_preview_simulation_updates):
            space.step(dt)
            pos = Vec2(ball_shape.body.position[0], ball_shape.body.position[1])
            positions.append(pos)
        return positions

    def _get_ball_trail_point(self):
        pos = self.ball_position
        ccw_offset = (
            Vec2(-self._ball_shape.body.velocity[1], self._ball_shape.body.velocity[0])
            .normalize()
            .scale(self._ball_trail_width)
        )
        return (pos + ccw_offset, pos - ccw_offset)

    def get_ball_trail(self):
        return self._ball_trail_points + [self._get_ball_trail_point()]

    def get_preview_sticky(self):
        if self._mode.state != _ModeState.PLACE_STICKY or not isinstance(
            self._mode.mouse_pos, Vec2
        ):
            return None
        return self._get_closest_sticky_in_radius_of_position(
            position=self._camera.screen_position_to_world_position(
                self._mode.mouse_pos
            ),
            radius=self._sticky_radius,
            is_preview=True,
        )

    def _get_closest_sticky_in_radius_of_position(self, position, radius, is_preview):
        stickies = []
        for i, contour in enumerate([self._exterior_contour] + self._contours):
            is_exterior = i == 0
            cur_wall = []
            prev_collides = False
            for j, c1 in enumerate(contour):
                c2 = contour[(j + 1) % len(contour)]
                # Check segment type is normal.
                is_good = (
                    self._contour_segment_map[_encode_segment_coords(c1, c2)].seg_type
                    == _ContourSegmentType.NORMAL
                )
                # Check is not flat ground.
                is_good = is_good and not (
                    c2[1] == c1[1] and (c2[0] > c1[0] if i == 0 else c2[0] < c1[0])
                )
                # Check collides with circle.
                is_good = is_good and do_circle_and_line_segment_intersect(
                    position, radius, c1, c2
                )
                if is_good:
                    if not prev_collides:
                        cur_wall.append(c1)
                    cur_wall.append(c2)
                    prev_collides = True
                else:
                    if prev_collides:
                        stickies.append(
                            Sticky(
                                wall=cur_wall,
                                contour=contour,
                                is_exterior=is_exterior,
                                is_preview=is_preview,
                            )
                        )
                        cur_wall = []
                    prev_collides = False
            if len(cur_wall) > 0:
                stickies.append(
                    Sticky(
                        wall=cur_wall,
                        contour=contour,
                        is_exterior=is_exterior,
                        is_preview=is_preview,
                    )
                )
        if len(stickies) == 0:
            return None

        def distance_to_sticky(sticky):
            if len(sticky.wall) % 2 == 0:
                mid_point_a = sticky.wall[len(sticky.wall) // 2 - 1]
                mid_point_b = sticky.wall[len(sticky.wall) // 2]
                mid_point = (
                    (mid_point_a[0] + mid_point_b[0]) / 2,
                    (mid_point_a[1] + mid_point_b[1]) / 2,
                )
            else:
                mid_point = sticky.wall[len(sticky.wall) // 2]
            return (position[0] - mid_point[0]) ** 2 + (position[1] - mid_point[1]) ** 2

        return min(stickies, key=distance_to_sticky)

    def dispose(self):
        self._unbind_events()

    @property
    def existing_stickies(self):
        return self._stickies.copy()

    @property
    def ball_position(self):
        position = self._ball_shape.body.position
        return Vec2(position[0], position[1])

    @property
    def ball_velocity(self):
        velocity = self._ball_shape.body.velocity
        return Vec2(velocity[0], velocity[1])

    @property
    def is_dragging(self):
        return (
            self._mouse_dragging
            and self._mouse_dragging.state == _MouseDraggingState.DRAGGING
        )

    def reset_events(self):
        self._mouse_dragging = None
        self._mode = _MakeShotMode()
        self._canceled_shot = False
        self._has_pressed_mouse_in_current_mode = False

    def _bind_events(self):
        def on_mouse_press(x, y, buttons, _modifiers):
            if self._get_is_paused():
                return
            if buttons & pyglet.window.mouse.LEFT:
                self._has_pressed_mouse_in_current_mode = True
            if self._is_in_shot or self._mode.state != _ModeState.MAKE_SHOT:
                return
            if buttons & pyglet.window.mouse.LEFT:
                self._canceled_shot = False
                self._mouse_dragging = _MouseDragging(Vec2(x, y))

        def on_mouse_drag(x, y, _dx, _dy, buttons, _modifiers):
            self._mouse_position = Vec2(x, y)
            if self._get_is_paused():
                return
            if (
                self._mode.state == _ModeState.PLACE_STICKY
                and self._mode.mouse_pos is not False
            ):
                self._mode = _PlaceStickyMode(Vec2(x, y))
            if self._is_in_shot or self._mode.state != _ModeState.MAKE_SHOT:
                return
            if buttons & pyglet.window.mouse.LEFT:
                if not self._mouse_dragging and not self._canceled_shot:
                    self._mouse_dragging = _MouseDragging(Vec2(x, y))
                    self._mouse_dragging.state = _MouseDraggingState.DRAGGING
                elif (
                    self._mouse_dragging
                    and self._mouse_dragging.state != _MouseDraggingState.RELEASED
                ):
                    self._mouse_dragging.current = Vec2(x, y)
                    self._mouse_dragging.state = _MouseDraggingState.DRAGGING

        def on_mouse_release(_x, _y, buttons, _modifiers):
            if self._get_is_paused():
                return
            if (
                buttons & pyglet.window.mouse.LEFT
                and self._mode.state == _ModeState.PLACE_STICKY
                and self._has_pressed_mouse_in_current_mode
            ):
                if self._mode.mouse_pos is False:
                    self._mode = _PlaceStickyMode(self._mouse_position)
                elif isinstance(self._mode.mouse_pos, Vec2):
                    sticky = self._get_closest_sticky_in_radius_of_position(
                        position=self._camera.screen_position_to_world_position(
                            self._mode.mouse_pos
                        ),
                        radius=self._sticky_radius,
                        is_preview=False,
                    )
                    if sticky:
                        for c1, c2 in zip(sticky.wall, sticky.wall[1:]):
                            k = _encode_segment_coords(c1, c2)
                            shape = self._contour_segment_map[k].pymunk_shape
                            shape.collision_type = _sticky_collision_type
                            self._contour_segment_map[k] = _ContourSegment(
                                shape, _ContourSegmentType.STICKY
                            )
                        (
                            new_stickies,
                            new_sticky,
                            removed_stickies,
                        ) = add_sticky_to_stickies(self._stickies, sticky)
                        self._stickies = new_stickies
                        for removed_sticky in removed_stickies:
                            self._on_sticky_removed(removed_sticky)
                        self._on_new_sticky(new_sticky)
                        self._mode = _MakeShotMode()
            if self._is_in_shot or self._mode.state != _ModeState.MAKE_SHOT:
                return
            if (
                buttons & pyglet.window.mouse.LEFT
                and self._mouse_dragging
                and self._has_pressed_mouse_in_current_mode
            ):
                if self._mouse_dragging.state == _MouseDraggingState.PRESSED:
                    self._mouse_dragging = None
                else:
                    self._mouse_dragging.state = _MouseDraggingState.RELEASED

        def on_key_release(symbol, modifiers):
            if self._get_is_paused():
                return
            if (
                modifiers & key.MOD_SHIFT
                or modifiers & key.MOD_ALT
                or modifiers & key.MOD_WINDOWS
                or modifiers & key.MOD_COMMAND
                or modifiers & key.MOD_OPTION
            ):
                return
            if symbol in config().place_sticky_mode_keys:
                self._has_pressed_mouse_in_current_mode = False
                if self._mode.state == _ModeState.PLACE_STICKY:
                    self._canceled_shot = False
                    self._mode = _MakeShotMode()
                else:
                    self._canceled_shot = False
                    self._mode = _PlaceStickyMode(self._mouse_position)
                    self._mouse_dragging = None
            elif symbol in config().cancel_keys:
                self._has_pressed_mouse_in_current_mode = False
                if self._mode.state == _ModeState.MAKE_SHOT:
                    self._canceled_shot = True
                    self._mouse_dragging = None
                elif self._mode.state == _ModeState.PLACE_STICKY:
                    self._mode = _MakeShotMode()
                    self._canceled_shot = True

        def on_mouse_motion(x, y, _dx, _dy):
            self._mouse_position = Vec2(x, y)
            if self._get_is_paused():
                return
            if (
                self._mode.state == _ModeState.PLACE_STICKY
                and self._mode.mouse_pos is not False
            ):
                self._mode = _PlaceStickyMode(Vec2(x, y))

        self._game.window.push_handlers(
            on_mouse_press,
            on_mouse_drag,
            on_mouse_release,
            on_key_release,
            on_mouse_motion,
        )

    def _unbind_events(self):
        if self._did_unbind_events:
            return
        self._did_unbind_events = True
        self._game.window.pop_handlers()
