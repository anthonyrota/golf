from time import time
import pyglet


class Game:
    def __init__(self, screen, updates_per_second):
        self._updates_per_second = updates_per_second
        self._last_time = time()
        self._window = pyglet.window.Window(resizable=True, caption="Golf Adventure")
        self._window.set_minimum_size(640, 480)
        self._screen = screen
        self._screen.bind(self)

    def run(self):
        @self._window.event
        def on_draw():
            self.update()
            self.render()

        pyglet.app.run()

    def update(self):
        cur_time = time()
        num_updates = int((cur_time - self._last_time) * self._updates_per_second)
        self._last_time += num_updates / self._updates_per_second
        dt = 1 / self._updates_per_second
        for _ in range(num_updates):
            self._screen.update(dt)

    def render(self):
        self._screen.render()

    def clear_window(self):
        self._window.clear()

    def get_window_dimensions(self):
        return (self._window.width, self._window.height)

    def set_screen(self, screen):
        self._screen.dispose()
        self._screen = screen
        self._screen.bind(self)
