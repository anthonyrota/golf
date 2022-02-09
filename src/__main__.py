from assets import load_assets
from Game import Game
from PlayInfiniteScreen import PlayInfiniteScreen


if __name__ == "__main__":
    load_assets()
    game = Game(screen=PlayInfiniteScreen(), updates_per_second=120)
    game.run()
