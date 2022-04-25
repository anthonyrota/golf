import os
import pyglet


class _Assets:
    def __init__(self):
        src_dir = os.path.dirname(os.path.abspath(__file__))
        assets_dir = os.path.join(src_dir, "..", "assets")
        self.font_name = "Roboto Condensed"
        self.pixel_font_name = "Minecraft"
        pyglet.font.add_directory(os.path.join(assets_dir, "fonts"))
        self.flag_img = pyglet.image.load(os.path.join(assets_dir, "Flag.png"))
        self.dirt_texture_img = pyglet.image.load(
            os.path.join(assets_dir, "Dirt Texture.png")
        )
        self.sand_texture_img = pyglet.image.load(
            os.path.join(assets_dir, "Sand Texture.png")
        )
        self.logo_small_img = pyglet.image.load(
            os.path.join(assets_dir, "Logo Small.png")
        )
        self.logo_large_img = pyglet.image.load(
            os.path.join(assets_dir, "Logo Large.png")
        )
        self.pause_btn_img = pyglet.image.load(
            os.path.join(assets_dir, "Pause Btn.png")
        )
        self.close_pause_btn_img = pyglet.image.load(
            os.path.join(assets_dir, "Pause Btn Close.png")
        )
        self.sound_off_btn_img = pyglet.image.load(
            os.path.join(assets_dir, "Sound Off.png")
        )
        self.sound_on_btn_img = pyglet.image.load(
            os.path.join(assets_dir, "Sound On.png")
        )
        self.back_btn_img = pyglet.image.load(os.path.join(assets_dir, "Back.png"))
        self.btn_small_base_left_img = pyglet.image.load(
            os.path.join(assets_dir, "button", "small", "base_left.png")
        )
        self.btn_small_base_center_img = pyglet.image.load(
            os.path.join(assets_dir, "button", "small", "base_center.png")
        )
        self.btn_small_base_right_img = pyglet.image.load(
            os.path.join(assets_dir, "button", "small", "base_right.png")
        )
        self.btn_small_down_left_img = pyglet.image.load(
            os.path.join(assets_dir, "button", "small", "down_left.png")
        )
        self.btn_small_down_center_img = pyglet.image.load(
            os.path.join(assets_dir, "button", "small", "down_center.png")
        )
        self.btn_small_down_right_img = pyglet.image.load(
            os.path.join(assets_dir, "button", "small", "down_right.png")
        )
        self.btn_large_base_left_img = pyglet.image.load(
            os.path.join(assets_dir, "button", "large", "base_left.png")
        )
        self.btn_large_base_center_img = pyglet.image.load(
            os.path.join(assets_dir, "button", "large", "base_center.png")
        )
        self.btn_large_base_right_img = pyglet.image.load(
            os.path.join(assets_dir, "button", "large", "base_right.png")
        )
        self.btn_large_down_left_img = pyglet.image.load(
            os.path.join(assets_dir, "button", "large", "down_left.png")
        )
        self.btn_large_down_center_img = pyglet.image.load(
            os.path.join(assets_dir, "button", "large", "down_center.png")
        )
        self.btn_large_down_right_img = pyglet.image.load(
            os.path.join(assets_dir, "button", "large", "down_right.png")
        )
        self.backgrounds = [
            pyglet.image.load(os.path.join(assets_dir, "backgrounds", f"Bg{i}.png"))
            for i in range(1, 11)
        ]


_assets = None


def assets():
    # pylint: disable-next=global-statement
    global _assets
    if _assets is None:
        _assets = _Assets()
    return _assets
