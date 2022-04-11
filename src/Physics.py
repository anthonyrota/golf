from enum import Enum, auto
import pyglet
from pyglet.math import Vec2
import pymunk


class _MouseDraggingState(Enum):
    PRESSED = auto()
    DRAGGING = auto()
    RELEASED = auto()


class _MouseDragging:
    def __init__(self, start):
        self.start = start
        self.current = start
        self.state = _MouseDraggingState.PRESSED


default_collision_type = 0
ball_collision_type = 1
flag_collision_type = 2


class Physics:
    def __init__(
        self,
        game,
        contours,
        exterior_contour,
        ball_position,
        ball_radius,
        gravity,
        flag_position,
        flag_collision_shape_radius,
        shot_preview_simulation_updates,
        on_level_complete,
    ):
        self._game = game
        self._space = pymunk.Space()
        self._space.gravity = gravity

        self._friction = 0.5
        self._elasticity = 0.65
        self._gravity = gravity
        self._flag_position = flag_position
        self._mouse_dragging = None
        self._shot_preview_simulation_updates = shot_preview_simulation_updates
        self._shot_number = 0
        self._on_level_complete = on_level_complete

        for contour in [exterior_contour] + contours:
            for i, p1 in enumerate(contour):
                p2 = contour[(i + 1) % len(contour)]
                shape = pymunk.Segment(self._space.static_body, p1, p2, 0.1)
                shape.friction = self._friction
                shape.elasticity = self._elasticity
                self._space.add(shape)

        self._is_in_shot = False
        self.ball_radius = ball_radius
        shape = self._make_ball_shape(ball_position)
        self._space.add(shape.body, shape)
        self._ball_shape = shape

        self._flag_collision_shape = pymunk.Circle(
            self._space.static_body, flag_collision_shape_radius, self._flag_position
        )
        self._flag_collision_shape.collision_type = flag_collision_type
        self._space.add(self._flag_collision_shape)
        self._ball_flag_collision_handler = self._space.add_collision_handler(
            ball_collision_type, flag_collision_type
        )

        self._bind_events()

    def _on_ball_flag_collision(self, _arb, _space, _data):
        self._on_level_complete()
        return False

    def _make_ball_shape(self, position):
        mass = 1
        moment = float("inf")
        body = pymunk.Body(mass, moment)
        body.position = position
        shape = pymunk.Circle(body, self.ball_radius)
        shape.friction = self._friction
        shape.elasticity = self._elasticity
        shape.collision_type = ball_collision_type
        return shape

    def update(self, dt):
        assert not (self._is_in_shot and self._mouse_dragging)
        if (
            self._mouse_dragging
            and self._mouse_dragging.state == _MouseDraggingState.RELEASED
        ):
            self._shot_number += 1
            self._is_in_shot = True
            self._ball_shape.body.velocity = self.get_drag_velocity()
            self._mouse_dragging = None
            self._ball_flag_collision_handler.begin = self._on_ball_flag_collision
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
            print("stop")
            return False

    def get_drag_velocity(self):
        return self._mouse_dragging.start - self._mouse_dragging.current

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

    def dispose(self):
        self._unbind_events()

    @property
    def ball_position(self):
        position = self._ball_shape.body.position
        return Vec2(position[0], position[1])

    @property
    def is_dragging(self):
        return (
            self._mouse_dragging
            and self._mouse_dragging.state == _MouseDraggingState.DRAGGING
        )

    def _bind_events(self):
        def on_mouse_press(x, y, buttons, _modifiers):
            if self._is_in_shot:
                return
            if buttons & pyglet.window.mouse.LEFT:
                self._mouse_dragging = _MouseDragging(Vec2(x, y))

        def on_mouse_drag(x, y, _dx, _dy, buttons, _modifiers):
            if self._is_in_shot:
                return
            if buttons & pyglet.window.mouse.LEFT:
                if not self._mouse_dragging:
                    self._mouse_dragging = _MouseDragging(Vec2(x, y))
                if self._mouse_dragging.state != _MouseDraggingState.RELEASED:
                    self._mouse_dragging.current = Vec2(x, y)
                    self._mouse_dragging.state = _MouseDraggingState.DRAGGING

        def on_mouse_release(_x, _y, buttons, _modifiers):
            if self._is_in_shot:
                return
            if buttons & pyglet.window.mouse.LEFT and self._mouse_dragging:
                if self._mouse_dragging.state == _MouseDraggingState.PRESSED:
                    self._mouse_dragging = None
                else:
                    self._mouse_dragging.state = _MouseDraggingState.RELEASED

        def on_mouse_leave(_x, _y):
            if self._is_in_shot:
                return
            self._mouse_dragging = None

        self._game.window.push_handlers(
            on_mouse_press,
            on_mouse_drag,
            on_mouse_release,
            on_mouse_leave,
        )

    def _unbind_events(self):
        self._game.window.pop_handlers()
