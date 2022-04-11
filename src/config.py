class _Config:
    def __init__(self):
        self.updates_per_second = 240


_config = None


def config():
    # pylint: disable-next=global-statement
    global _config
    if _config is None:
        _config = _Config()
    return _config
