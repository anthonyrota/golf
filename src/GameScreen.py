from abc import ABC, abstractmethod


class GameScreen(ABC):
    @abstractmethod
    def bind(self, game):
        pass

    @abstractmethod
    def render(self):
        pass

    @abstractmethod
    def update(self, dt):
        pass

    @abstractmethod
    def unbind(self):
        pass
