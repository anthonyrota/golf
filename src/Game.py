from time import time
import pyglet
import pyglet.gl
import glooey


class Game:
    def __init__(self, screen, updates_per_second, target_fps):
        self.updates_per_second = updates_per_second
        self._target_fps = target_fps
        self._last_time = time()
        self.window = pyglet.window.Window(
            config=pyglet.gl.Config(
                double_buffer=True,
                sample_buffers=1,
                samples=4,
                major_version=2,
                minor_version=1,
            ),
            resizable=True,
            caption="Golf Adventure",
        )
        self.window.set_minimum_size(640, 480)
        self.gui = glooey.Gui(self.window, clear_before_draw=False)
        self._screen = screen
        self._screen.bind(self)
        self._average_dt = []

    def run(self):
        def on_key_press(symbol, _modifiers):
            if symbol == pyglet.window.key.ESCAPE:
                return True

        self.window.push_handlers(on_key_press)
        pyglet.clock.schedule_interval(self._tick, 1 / self._target_fps)
        pyglet.app.run()

    def _tick(self, dt):
        self._average_dt.append(dt)
        if len(self._average_dt) == 60:
            print('fps', len(self._average_dt) / sum(self._average_dt))
            self._average_dt = []
        cur_time = time()
        num_updates = int((cur_time - self._last_time) * self.updates_per_second)
        self._last_time += num_updates / self.updates_per_second
        dt = 1 / self.updates_per_second
        for _ in range(num_updates):
            if self._screen.update(dt) is False:
                break
        self._screen.render()

    def set_screen(self, screen):
        self._screen.unbind()
        self._screen = screen
        self._screen.bind(self)

    def quit(self):
        self._screen.unbind()
        self.window.close()
