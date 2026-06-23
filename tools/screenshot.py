"""Render a few representative frames to PNG files (headless).

Run:  python tools/screenshot.py
Produces tools/shot_play.png and tools/shot_fright.png.
"""

import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, ".")

import pygame  # noqa: E402
from pacman import settings as cfg            # noqa: E402
from pacman.game import Game, PLAYING         # noqa: E402

random.seed(7)


def valid_dirs(maze, col, row):
    out = []
    for d in (cfg.UP, cfg.DOWN, cfg.LEFT, cfg.RIGHT):
        if not maze.is_wall((col + d[0]) % cfg.COLS, row + d[1]):
            out.append(d)
    return out


def step(game, n, steer=True):
    for _ in range(n):
        if steer and game.state == PLAYING:
            p = game.player
            dirs = valid_dirs(game.maze, p.col, p.row)
            if dirs and (p.direction == cfg.STOP or random.random() < 0.2):
                p.next_direction = random.choice(dirs)
        game.update()
        game.draw()


game = Game()
step(game, 400)                       # play a while: ghosts spread out, dots eaten
pygame.image.save(game.screen, "tools/shot_play.png")
print("wrote tools/shot_play.png")

# Trigger a power pellet to capture frightened ghosts.
game.ghost_combo = 0
game.fright_timer = int(cfg.FRIGHT_SECONDS * cfg.FPS)
for gh in game.ghosts:
    gh.set_frightened()
step(game, 30)
pygame.image.save(game.screen, "tools/shot_fright.png")
print("wrote tools/shot_fright.png")
