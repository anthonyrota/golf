import os
import pyglet

src_dir = os.path.dirname(os.path.abspath(__file__))
font_name = "Roboto Condensed"


def load_assets():
    pyglet.font.add_directory(
        os.path.join(src_dir, "..", "assets", "fonts", "Roboto_Condensed")
    )
