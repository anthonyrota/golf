from pyglet.math import Vec2


class Rectangle:
    def __init__(self, pos, width, height):
        self.pos = pos
        self.width = width
        self.height = height
        self.right = self.pos.x + self.width
        self.top = self.pos.y + self.height

    def intersects(self, other):
        return (
            self.pos.y < other.top
            and other.pos.y < self.top
            and self.pos.x < other.right
            and other.pos.x < self.right
        )

    def subtract(self, hole):
        if not self.intersects(hole):
            yield Rectangle(self.pos, self.width, self.height)
            return

        # -------------------------
        # |          A            |
        # |-----------------------|
        # |  D  |   hole    |  B  |
        # |-----------------------|
        # |          C            |
        # -------------------------

        if self.top > hole.top:  # A
            yield Rectangle(Vec2(self.pos.x, hole.top), self.width, self.top - hole.top)

        if self.right > hole.right:  # B
            yield Rectangle(
                Vec2(hole.right, hole.pos.y), self.right - hole.right, hole.height
            )

        if hole.pos.y > self.pos.y:  # C
            yield Rectangle(self.pos, self.width, hole.pos.y - self.pos.y)

        if hole.pos.x > self.pos.x:  # D
            yield Rectangle(
                Vec2(self.pos.x, hole.pos.y), hole.pos.x - self.pos.x, hole.height
            )
