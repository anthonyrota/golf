from assets import assets
from Game import Game
from MainMenuScreen import MainMenuScreen


if __name__ == "__main__":
    assets()
    game = Game(screen=MainMenuScreen(), updates_per_second=240, target_fps=60)
    game.run()
