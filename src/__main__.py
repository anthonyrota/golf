from assets import assets
from config import config
from Game import Game
from MainMenuScreen import MainMenuScreen


if __name__ == "__main__":
    assets()
    game = Game(
        screen=MainMenuScreen(),
        updates_per_second=config().updates_per_second,
        target_fps=config().target_fps,
    )
    game.run()
