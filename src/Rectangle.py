class Rectangle:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.right = self.x + self.width
        self.top = self.y + self.height

    def intersects(self, other):
        return (
            self.y < other.top
            and other.y < self.top
            and self.x < other.right
            and other.x < self.right
        )

    def subtract(self, hole):
        if not self.intersects(hole):
            yield Rectangle(self.x, self.y, self.width, self.height)
            return

        # -------------------------
        # |          A            |
        # |-----------------------|
        # |  D  |   hole    |  B  |
        # |-----------------------|
        # |          C            |
        # -------------------------

        if self.top > hole.top:  # A
            yield Rectangle(self.x, hole.top, self.width, self.top - hole.top)

        if self.right > hole.right:  # B
            yield Rectangle(hole.right, hole.y, self.right - hole.right, hole.height)

        if hole.y > self.y:  # C
            yield Rectangle(self.x, self.y, self.width, hole.y - self.y)

        if hole.x > self.x:  # D
            yield Rectangle(self.x, hole.y, hole.x - self.x, hole.height)

    def __str__(self):
        return f"Rectangle({self.x},{self.y},{self.width},{self.height})"
