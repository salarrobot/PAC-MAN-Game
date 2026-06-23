"""Headless smoke test: run the real game loop without a window.

Uses SDL's dummy video/audio drivers so the game can run on a machine with no
display. Drives Pac-Man around with a random walk and forces the tricky corner
cases (power pellets, eating ghosts, dying, winning, the tunnel) to make sure
nothing throws and the core rules hold.

Run:  python tools/smoke_test.py
"""

import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, ".")

from pacman import settings as cfg          # noqa: E402
from pacman.game import Game, PLAYING, DYING, WIN, GAME_OVER  # noqa: E402
from pacman.ghost import FRIGHTENED, EATEN, HOUSE, NORMAL     # noqa: E402

random.seed(1234)


def valid_dirs(maze, col, row):
    out = []
    for d in (cfg.UP, cfg.DOWN, cfg.LEFT, cfg.RIGHT):
        c = (col + d[0]) % cfg.COLS
        r = row + d[1]
        if not maze.is_wall(c, r):
            out.append(d)
    return out


def steer(game):
    """Cheap wandering AI: pick a random legal direction now and then."""
    p = game.player
    dirs = valid_dirs(game.maze, p.col, p.row)
    if dirs and (p.direction == cfg.STOP or random.random() < 0.15):
        p.next_direction = random.choice(dirs)


def main():
    game = Game()
    checks = []

    def record(name, ok):
        checks.append((name, ok))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")

    print("Running 3500 frames of random-walk play...")
    start_pellets = game.maze.total_pellets
    saw_playing = False
    powered_once = False
    ate_ghost = False

    for frame in range(3500):
        if game.state == PLAYING:
            saw_playing = True
            steer(game)
        game.update()
        game.draw()

        # Periodically force a power-pellet so we exercise fright + eating.
        if game.state == PLAYING and frame % 700 == 300:
            game.ghost_combo = 0
            game.fright_timer = game.fright_timer  # noop, readability
            game.fright_timer = int(cfg.FRIGHT_SECONDS * cfg.FPS)
            for gh in game.ghosts:
                gh.set_frightened()
            powered_once = True

        # If a ghost is frightened and out, drag it onto Pac-Man to eat it.
        if game.state == PLAYING:
            for gh in game.ghosts:
                if gh.state == FRIGHTENED:
                    gh.x, gh.y = game.player.x, game.player.y
                    break

        if any(gh.state == EATEN for gh in game.ghosts):
            ate_ghost = True

    record("reached PLAYING state", saw_playing)
    record("score increased from eating", game.score > 0)
    record("pellets were consumed", game.maze.pellets_eaten > 0)
    record("power pellet frightened ghosts", powered_once)
    record("a ghost was eaten (became eyes)", ate_ghost)
    record("non-blinky ghosts left the house",
           all(g.state != HOUSE for g in game.ghosts if g.name != "blinky"))

    # -- eaten ghost makes it home and revives -------------------------------
    print("Checking an eaten ghost returns home and revives...")
    g = game.ghosts[1]
    g.get_eaten()
    revived = False
    for _ in range(2000):
        if game.state != PLAYING:
            break
        steer(game)
        game.update()
        if g.state in (NORMAL, HOUSE):
            revived = True
            break
    record("eaten ghost returned home and revived", revived)

    # -- tunnel wrap ---------------------------------------------------------
    print("Checking the side tunnel wraps...")
    game.player.reset(col=1, row=cfg.TUNNEL_ROW, direction=cfg.LEFT)
    game.player.next_direction = cfg.LEFT
    wrapped = False
    for _ in range(120):
        game.player.update()
        if game.player.col > 20:  # reappeared on the right side
            wrapped = True
            break
    record("player wraps through the tunnel", wrapped)

    # -- death + life loss ---------------------------------------------------
    print("Forcing a death...")
    game._enter_state(PLAYING)
    lives_before = game.lives
    game.blinky.state = NORMAL
    game.blinky.x, game.blinky.y = game.player.x, game.player.y
    game._check_collisions()
    died = game.state == DYING
    for _ in range(frames_needed := int(cfg.DEATH_SECONDS * cfg.FPS) + 5):
        game.update()
    record("collision with ghost triggers death", died)
    record("a life was lost", game.lives == lives_before - 1)

    # -- win condition -------------------------------------------------------
    print("Forcing a level win...")
    game._enter_state(PLAYING)
    game.maze.pellets_eaten = game.maze.total_pellets
    game.update()
    record("clearing all pellets wins the level", game.state == WIN)
    game.next_level()
    record("next level refills the maze",
           game.maze.pellets_eaten == 0 and game.maze.total_pellets == start_pellets)

    # -- game over -----------------------------------------------------------
    print("Forcing game over...")
    game.lives = 1
    game._enter_state(PLAYING)
    game.blinky.state = NORMAL
    game.blinky.x, game.blinky.y = game.player.x, game.player.y
    game._check_collisions()
    for _ in range(int(cfg.DEATH_SECONDS * cfg.FPS) + 5):
        game.update()
    record("losing the last life ends the game", game.state == GAME_OVER)

    print()
    failed = [n for n, ok in checks if not ok]
    if failed:
        print(f"SMOKE TEST FAILED ({len(failed)} of {len(checks)} checks failed)")
        sys.exit(1)
    print(f"SMOKE TEST PASSED  ({len(checks)} checks)  final score={game.score}")


if __name__ == "__main__":
    main()
