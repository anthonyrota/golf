class Physics:
    def __init__(
        self,
        contours,
        exterior_contour,
        ball_position,
        ball_velocity,
        ball_radius,
        gravity,
        flag_position,
    ):
        self._contours = contours
        self._exterior_contour = exterior_contour
        self.ball_position = ball_position
        self._ball_velocity = ball_velocity
        self.ball_radius = ball_radius
        self._gravity = gravity
        self._flag_position = flag_position

    def update(self, dt):
        self._ball_velocity = self._ball_velocity + self._gravity.scale(dt)
        self.ball_position = self.ball_position + self._ball_velocity.scale(dt)
