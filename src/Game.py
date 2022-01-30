from time import time
import pyglet
import glooey


class Game:
    def __init__(self, screen, updates_per_second):
        self._updates_per_second = updates_per_second
        self._last_time = time()
        self.window = pyglet.window.Window(resizable=True, caption="Golf Adventure")
        self.window.set_minimum_size(640, 480)
        self.gui = glooey.Gui(self.window)
        self._screen = screen
        self._screen.bind(self)

    def run(self):
        def on_draw():
            self.update()
            self.render()

        def on_key_press(symbol, _modifiers):
            if symbol == pyglet.window.key.ESCAPE:
                return True

        self.window.push_handlers(on_draw)
        self.window.push_handlers(on_key_press)
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

    def set_screen(self, screen):
        self._screen.unbind()
        self._screen = screen
        self._screen.bind(self)

    def quit(self):
        self._screen.unbind()
        self.window.close()
