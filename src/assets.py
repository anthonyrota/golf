import os
import pyglet


class _Assets:
    def __init__(self):
        src_dir = os.path.dirname(os.path.abspath(__file__))
        self.font_name = "Roboto Condensed"
        pyglet.font.add_directory(
            os.path.join(src_dir, "..", "assets", "fonts", "Roboto_Condensed")
        )
        self.ball_image = pyglet.image.load(
            os.path.join(src_dir, "..", "assets", "Ball.png")
        )


_assets = None


def assets():
    # pylint: disable-next=global-statement
    global _assets
    if _assets is None:
        _assets = _Assets()
    return _assets
