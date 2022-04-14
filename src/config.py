from pyglet.window import key


class _Config:
    def __init__(self):
        self.updates_per_second = 240
        self.target_fps = 60
        self.place_sticky_mode_keys = [key.G]
        self.cancel_shot_keys = [key.ESCAPE, key.DELETE, key.BACKSPACE, key.C]


_config = None


def config():
    # pylint: disable-next=global-statement
    global _config
    if _config is None:
        _config = _Config()
    return _config
