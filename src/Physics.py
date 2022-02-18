from pyglet.math import Vec2
import pymunk


class Physics:
    def __init__(
        self,
        contours,
        exterior_contour,
        ball_position,
        ball_radius,
        gravity,
        flag_position,
    ):
        self._space = pymunk.Space()
        self._space.gravity = gravity

        for contour in [exterior_contour] + contours:
            for i, p1 in enumerate(contour):
                p2 = contour[(i + 1) % len(contour)]
                shape = pymunk.Segment(self._space.static_body, p1, p2, 0.0)
                shape.friction = 0.5
                self._space.add(shape)

        mass = 1
        moment = pymunk.moment_for_circle(mass, 0, ball_radius)
        body = pymunk.Body(mass, moment)
        body.position = ball_position
        shape = pymunk.Circle(body, ball_radius)
        shape.friction = 0.5
        self._space.add(body, shape)
        self._ball_shape = shape
        self.ball_radius = ball_radius
        self._gravity = gravity
        self._flag_position = flag_position

    def update(self, dt):
        self._space.step(dt)

    @property
    def ball_position(self):
        position = self._ball_shape.body.position
        return Vec2(position[0], position[1])
