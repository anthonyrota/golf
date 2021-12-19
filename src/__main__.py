from Game import Game
from MainMenuScreen import MainMenuScreen


if __name__ == "__main__":
    game = Game(screen=MainMenuScreen(), updates_per_second=120)
    game.run()
