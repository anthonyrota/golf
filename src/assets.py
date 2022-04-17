import os
import pyglet


class _Assets:
    def __init__(self):
        src_dir = os.path.dirname(os.path.abspath(__file__))
        assets_dir = os.path.join(src_dir, "..", "assets")
        self.font_name = "Roboto Condensed"
        pyglet.font.add_directory(os.path.join(assets_dir, "fonts", "Roboto_Condensed"))
        self.flag_img = pyglet.image.load(os.path.join(assets_dir, "Flag.png"))


_assets = None


def assets():
    # pylint: disable-next=global-statement
    global _assets
    if _assets is None:
        _assets = _Assets()
    return _assets
