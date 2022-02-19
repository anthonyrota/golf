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
        shot_preview_simulation_updates,
        on_level_complete,
    ):
        self._game = game
        self._space = pymunk.Space()
        self._space.gravity = gravity

        friction = 0.5
        elasticity = 0.65

        for contour in [exterior_contour] + contours:
            for i, p1 in enumerate(contour):
                p2 = contour[(i + 1) % len(contour)]
                shape = pymunk.Segment(self._space.static_body, p1, p2, 0.0)
                shape.friction = friction
                shape.elasticity = elasticity
                self._space.add(shape)

        mass = 1
        moment = float("inf")
        body = pymunk.Body(mass, moment)
        body.position = ball_position
        shape = pymunk.Circle(body, ball_radius)
        shape.friction = friction
        shape.elasticity = elasticity
        self._space.add(body, shape)
        self._ball_shape = shape
        self.ball_radius = ball_radius
        self._gravity = gravity
        self._flag_position = flag_position
        self._mouse_dragging = None
        self._shot_preview_simulation_updates = shot_preview_simulation_updates
        self._bind_events()
        self._shot_number = 0
        self._on_level_complete = on_level_complete

    def update(self, dt):
        if (
            self._mouse_dragging
            and self._mouse_dragging.state == _MouseDraggingState.RELEASED
        ):
            self._shot_number += 1
            self._ball_shape.body.velocity = self._get_drag_velocity()
            self._mouse_dragging = None
        self._space.step(dt)

    def _get_drag_velocity(self):
        return self._mouse_dragging.start - self._mouse_dragging.current

    def preview_ball_path(self):
        assert self.is_dragging
        return self._simulate_ball_path_with_velocity(self._get_drag_velocity())

    def _simulate_ball_path_with_velocity(self, velocity):
        self._space.remove(self._ball_shape)
        space = self._space.copy()
        self._space.add(self._ball_shape)

        default_collision_type = 0
        ball_collision_type = 1
        collided = False

        def on_ball_collision(_arb, _space, _data):
            nonlocal collided
            collided = True
            return False

        collision_handler = space.add_collision_handler(
            default_collision_type, ball_collision_type
        )
        collision_handler.begin = on_ball_collision

        ball_shape = self._ball_shape.copy()
        ball_shape.body.velocity = velocity
        ball_shape.collision_type = ball_collision_type
        space.add(ball_shape.body, ball_shape)

        dt = 1 / self._game.updates_per_second
        positions = [Vec2(ball_shape.body.position[0], ball_shape.body.position[1])]
        for _ in range(self._shot_preview_simulation_updates):
            space.step(dt)
            pos = Vec2(ball_shape.body.position[0], ball_shape.body.position[1])
            if collided:
                break
            positions.append(pos)
        if len(positions) < 2:
            return None
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
            if buttons & pyglet.window.mouse.LEFT:
                self._mouse_dragging = _MouseDragging(Vec2(x, y))

        def on_mouse_drag(x, y, _dx, _dy, buttons, _modifiers):
            if (
                buttons & pyglet.window.mouse.LEFT
                and self._mouse_dragging
                and self._mouse_dragging.state != _MouseDraggingState.RELEASED
            ):
                self._mouse_dragging.current = Vec2(x, y)
                self._mouse_dragging.state = _MouseDraggingState.DRAGGING

        def on_mouse_release(_x, _y, buttons, _modifiers):
            if buttons & pyglet.window.mouse.LEFT and self._mouse_dragging:
                if self._mouse_dragging.state == _MouseDraggingState.PRESSED:
                    self._mouse_dragging = None
                else:
                    self._mouse_dragging.state = _MouseDraggingState.RELEASED

        def on_mouse_leave(_x, _y):
            self._mouse_dragging = None

        self._game.window.push_handlers(
            on_mouse_press, on_mouse_drag, on_mouse_release, on_mouse_leave
        )

    def _unbind_events(self):
        self._game.window.pop_handlers()
