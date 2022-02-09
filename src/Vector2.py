class Vector2:
    @staticmethod
    def zero():
        return Vector2(0, 0)

    def __init__(self, x, y):
        self.x = x
        self.y = y
