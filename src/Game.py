from time import time
import pyglet
import pyglet.gl
import glooey
from widgets import large_window_width, large_window_height


class MyGui(glooey.Gui):
    def on_draw(self):
        pass


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
        self.gui = MyGui(self.window)
        self._screen = screen
        self._average_dt = []
        self._resize_handlers = []
        self.size = self._get_size()
        self.is_sound_enabled = True
        self._screen.bind(self)

    def _get_size(self):
        if (
            self.window.width >= large_window_width
            and self.window.height >= large_window_height
        ):
            return "large"
        return "small"

    def run(self):
        def on_key_press(symbol, _modifiers):
            if symbol == pyglet.window.key.ESCAPE:
                return pyglet.event.EVENT_HANDLED

        def on_resize(_w, _h):
            new_size = self._get_size()
            if new_size != self.size:
                self.size = new_size
                for handler in self._resize_handlers:
                    handler()
            self._screen.render()

        self.window.push_handlers(on_key_press, on_resize)
        pyglet.clock.schedule_interval(self._tick, 1 / self._target_fps)
        pyglet.app.run()

    def _tick(self, dt):
        self._average_dt.append(dt)
        if len(self._average_dt) == 60:
            print("fps", len(self._average_dt) / sum(self._average_dt))
            self._average_dt = []
        cur_time = time()
        num_updates = int((cur_time - self._last_time) * self.updates_per_second)
        self._last_time += num_updates / self.updates_per_second
        dt = 1 / self.updates_per_second
        for _ in range(num_updates):
            if self._screen.update(dt) is False:
                break
        self._screen.render()

    def draw_gui(self):
        self.gui.batch.draw()

    def set_is_sound_enabled(self, is_sound_enabled):
        self.is_sound_enabled = is_sound_enabled

    def on_size_change(self, handler):
        self._resize_handlers.append(handler)

    def off_size_change(self, handler):
        self._resize_handlers.remove(handler)

    def set_screen(self, screen):
        self._screen.unbind()
        self._screen = screen
        self._screen.bind(self)

    def quit(self):
        self._screen.unbind()
        self.window.close()
